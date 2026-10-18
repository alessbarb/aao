"""PostgreSQL-backed isolated API for AAO's mandate/project/work lifecycle.

This is a separate development service, not a transparent migration of the
SQLite API. No agent execution or external side effects are enabled.
"""
import json
import os
import secrets
from contextlib import contextmanager
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from aao.planner import Admission, decide_admission


def require_ceo(x_ceo_token: str | None = Header(None)):
    expected = os.getenv("AAO_CEO_TOKEN")
    if not expected:
        raise HTTPException(503, "CEO credential not configured")
    if not x_ceo_token or not secrets.compare_digest(expected, x_ceo_token):
        raise HTTPException(403, "CEO authentication required")
    return "ceo"


def require_worker(x_work_token: str | None = Header(None)):
    expected = os.getenv("AAO_WORK_TOKEN")
    if not expected:
        raise HTTPException(503, "Worker credential not configured")
    if not x_work_token or not secrets.compare_digest(expected, x_work_token):
        raise HTTPException(403, "Worker authentication required")
    return "development-worker"


@contextmanager
def tx():
    from aao.postgres import connect_postgres
    with connect_postgres() as db:
        yield db


def audit(db, subject: str, kind: str, details: dict):
    db.execute(
        "INSERT INTO events(id,subject_id,kind,details) VALUES (%s,%s,%s,%s::jsonb)",
        (str(uuid4()), subject, kind, json.dumps(details)),
    )


class MandateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    objective: str = Field(min_length=1, max_length=5000)


class ProjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    mandate_id: str


class WorkRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    author_id: str = Field(min_length=1)
    acceptance_criteria: list[str] = Field(min_length=1)


class GrantRequest(BaseModel):
    principal_id: str = Field(min_length=1)
    capability: str = Field(pattern="^(work.create|work.admit)$")


app = FastAPI(title="AAO PostgreSQL development core", version="0.2.0")


@app.get("/health")
def health():
    return {"service": "postgres-dev", "autonomous_execution": False}


@app.post("/v1/mandates", status_code=201)
def create_mandate(payload: MandateRequest, _: str = Depends(require_ceo)):
    mid = str(uuid4())
    with tx() as db:
        db.execute("INSERT INTO mandates(id,title,objective,status) VALUES (%s,%s,%s,'DRAFT')",
                   (mid, payload.title, payload.objective))
        audit(db, mid, "mandate.drafted", {"title": payload.title})
    return {"id": mid, "status": "DRAFT"}


@app.post("/v1/mandates/{mandate_id}/confirm")
def confirm_mandate(mandate_id: str, _: str = Depends(require_ceo)):
    with tx() as db:
        updated = db.execute(
            "UPDATE mandates SET status='CONFIRMED',confirmed_by='ceo' "
            "WHERE id=%s AND status='DRAFT' RETURNING id", (mandate_id,),
        ).fetchone()
        if not updated:
            raise HTTPException(409, "Mandate missing or not draft")
        audit(db, mandate_id, "mandate.confirmed", {"authority": "ceo"})
    return {"id": mandate_id, "status": "CONFIRMED"}


@app.post("/v1/projects", status_code=201)
def create_project(payload: ProjectRequest, _: str = Depends(require_ceo)):
    pid = str(uuid4())
    with tx() as db:
        mandate = db.execute("SELECT status FROM mandates WHERE id=%s FOR UPDATE",
                             (payload.mandate_id,)).fetchone()
        if not mandate or mandate[0] != "CONFIRMED":
            raise HTTPException(409, "Confirmed mandate required")
        if db.execute("SELECT 1 FROM projects WHERE mandate_id=%s",
                      (payload.mandate_id,)).fetchone():
            raise HTTPException(409, "Mandate already bound to project")
        db.execute(
            "INSERT INTO projects(id,name,mandate_id,state) VALUES (%s,%s,%s,'ACTIVE')",
            (pid, payload.name, payload.mandate_id),
        )
        audit(db, pid, "project.created", {"mandate_id": payload.mandate_id})
    return {"id": pid, "state": "ACTIVE"}


@app.get("/v1/projects")
def projects(_: str = Depends(require_ceo)):
    with tx() as db:
        rows = db.execute("SELECT id,name,state FROM projects ORDER BY name,id").fetchall()
        return [{"id": r[0], "name": r[1], "state": r[2]} for r in rows]


@app.post("/v1/projects/{project_id}/grants", status_code=201)
def grant(project_id: str, payload: GrantRequest, _: str = Depends(require_ceo)):
    with tx() as db:
        if not db.execute("SELECT 1 FROM projects WHERE id=%s", (project_id,)).fetchone():
            raise HTTPException(404, "Project not found")
        db.execute(
            "INSERT INTO project_grants(principal_id,project_id,capability) VALUES (%s,%s,%s) "
            "ON CONFLICT DO NOTHING",
            (payload.principal_id, project_id, payload.capability),
        )
        audit(db, project_id, "grant.created",
              {"principal_id": payload.principal_id, "capability": payload.capability})
    return {"project_id": project_id, "capability": payload.capability}


def require_grant(db, principal: str, project_id: str, capability: str):
    if not db.execute(
        "SELECT 1 FROM project_grants WHERE principal_id=%s AND project_id=%s "
        "AND capability=%s", (principal, project_id, capability),
    ).fetchone():
        raise HTTPException(403, "Project grant required")


@app.post("/v1/projects/{project_id}/work", status_code=201)
def create_work(project_id: str, payload: WorkRequest,
                principal: str = Depends(require_worker)):
    wid = str(uuid4())
    with tx() as db:
        row = db.execute("SELECT state FROM projects WHERE id=%s FOR UPDATE",
                         (project_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Project not found")
        if row[0] != "ACTIVE":
            raise HTTPException(409, "Project not active")
        require_grant(db, principal, project_id, "work.create")
        db.execute(
            "INSERT INTO work_items(id,project_id,title,author_id,status,acceptance_criteria) "
            "VALUES (%s,%s,%s,%s,'INBOX',%s::jsonb)",
            (wid, project_id, payload.title, payload.author_id,
             json.dumps(payload.acceptance_criteria)),
        )
        audit(db, wid, "work.created", {"project_id": project_id})
    return {"id": wid, "status": "INBOX"}


@app.get("/v1/projects/{project_id}/board")
def board(project_id: str, _: str = Depends(require_ceo)):
    with tx() as db:
        if not db.execute("SELECT 1 FROM projects WHERE id=%s", (project_id,)).fetchone():
            raise HTTPException(404, "Project not found")
        rows = db.execute(
            "SELECT id,title,status,acceptance_criteria,evidence FROM work_items "
            "WHERE project_id=%s ORDER BY id", (project_id,),
        ).fetchall()
        return [
            {"id": r[0], "title": r[1], "status": r[2],
             "acceptance_criteria": r[3], "evidence": r[4]} for r in rows
        ]


@app.post("/v1/work/{work_id}/admit")
def admit(work_id: str, principal: str = Depends(require_worker)):
    with tx() as db:
        work = db.execute("SELECT project_id,status FROM work_items WHERE id=%s FOR UPDATE",
                          (work_id,)).fetchone()
        if not work:
            raise HTTPException(404, "Work not found")
        project_id, current = work
        project = db.execute(
            "SELECT p.state,m.status FROM projects p JOIN mandates m ON "
            "p.mandate_id=m.id WHERE p.id=%s", (project_id,),
        ).fetchone()
        require_grant(db, principal, project_id, "work.admit")
        decision = decide_admission(
            project_active=project[0] == "ACTIVE",
            mandate_confirmed=project[1] == "CONFIRMED",
            authorized=True, dependencies_satisfied=True,
            capacity_available=True, within_budget=True,
            residual_risk="low", emergency_stop=False,
        )
        if current != "INBOX" or decision.status != Admission.READY:
            raise HTTPException(409, f"Admission rejected: {decision.reason}")
        db.execute("UPDATE work_items SET status='READY' WHERE id=%s", (work_id,))
        audit(db, work_id, "work.admitted", {"principal_id": principal})
    return {"id": work_id, "status": "READY"}
