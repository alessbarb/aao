"""PostgreSQL-backed isolated API for AAO's mandate/project/work lifecycle.

This is a separate development service, not a transparent migration of the
SQLite API. No agent execution or external side effects are enabled.
"""
import json

from aao.settings import load_local_env
load_local_env()
import os
import secrets
from pathlib import Path
from contextlib import contextmanager
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from aao.planner import Admission, decide_admission


def require_ceo(x_ceo_token: str | None = Header(None)):
    expected = os.getenv("AAO_CEO_TOKEN")
    if not expected:
        raise HTTPException(503, "CEO credential not configured")
    if not x_ceo_token or not secrets.compare_digest(expected, x_ceo_token):
        raise HTTPException(403, "CEO authentication required")
    return "ceo"


def require_reviewer(
    x_review_token: str | None = Header(None),
    x_auditor_token: str | None = Header(None),
):
    # Individual credentials are preferred where provisioned. The shared
    # development reviewer token remains a transitional local-only fallback.
    if x_auditor_token:
        from aao.pg_principals import PrincipalDenied, authenticate
        try:
            return authenticate(x_auditor_token, kind="AUDITOR")
        except PrincipalDenied as exc:
            raise HTTPException(403, "Individual auditor credential rejected") from exc
    expected = os.getenv("AAO_REVIEW_TOKEN")
    if not expected:
        raise HTTPException(503, "Reviewer credential not configured")
    if not x_review_token or not secrets.compare_digest(expected, x_review_token):
        raise HTTPException(403, "Reviewer authentication required")
    return "development-auditor"


def require_worker(
    x_work_token: str | None = Header(None),
    x_agent_token: str | None = Header(None),
):
    # An individually issued credential takes precedence; invalid individual
    # credentials cannot silently fall back to a shared development token.
    if x_agent_token is not None:
        from aao.pg_principals import PrincipalDenied, authenticate
        try:
            return authenticate(x_agent_token, kind="AGENT")
        except PrincipalDenied as exc:
            raise HTTPException(403, "Individual agent credential rejected") from exc
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


class ReviewRequest(BaseModel):
    decision: str = Field(pattern="^(APPROVE|REJECT)$")
    evidence: list[str] = Field(min_length=1)


class GrantRequest(BaseModel):
    principal_id: str = Field(min_length=1)
    capability: str = Field(pattern=r"^(?:work\.(?:create|admit|review|progress)|project\.read|execution\.claim)$")


app = FastAPI(title="AAO PostgreSQL development core", version="0.2.0")


@app.get("/", include_in_schema=False)
def workboard_ui():
    """Serve the workboard from the same origin as the PostgreSQL API."""
    return FileResponse(Path(__file__).resolve().parents[2] / "frontend" / "index.html")


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


def read_principal(x_ceo_token: str | None = Header(None), x_work_token: str | None = Header(None)):
    ceo = os.getenv("AAO_CEO_TOKEN")
    worker = os.getenv("AAO_WORK_TOKEN")
    if ceo and x_ceo_token and secrets.compare_digest(ceo, x_ceo_token):
        return "ceo"
    if worker and x_work_token and secrets.compare_digest(worker, x_work_token):
        return "development-worker"
    raise HTTPException(403, "Authenticated reader required")


@app.get("/v1/projects")
def projects(principal: str = Depends(read_principal)):
    with tx() as db:
        if principal == "ceo":
            rows = db.execute("SELECT id,name,state FROM projects ORDER BY name,id").fetchall()
        else:
            rows = db.execute(
                "SELECT p.id,p.name,p.state FROM projects p JOIN project_grants g ON g.project_id=p.id "
                "WHERE g.principal_id=%s AND g.capability='project.read' "
                "AND (g.expires_at IS NULL OR g.expires_at > now()) ORDER BY p.name,p.id",
                (principal,),
            ).fetchall()
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
        "AND capability=%s AND (expires_at IS NULL OR expires_at > now())", (principal, project_id, capability),
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
            (wid, project_id, payload.title, principal,
             json.dumps(payload.acceptance_criteria)),
        )
        audit(db, wid, "work.created", {"project_id": project_id})
    return {"id": wid, "status": "INBOX"}


@app.get("/v1/projects/{project_id}/board")
def board(project_id: str, principal: str = Depends(read_principal)):
    with tx() as db:
        if not db.execute("SELECT 1 FROM projects WHERE id=%s", (project_id,)).fetchone():
            raise HTTPException(404, "Project not found")
        if principal != "ceo":
            require_grant(db, principal, project_id, "project.read")
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


@app.post("/v1/work/{work_id}/progress")
def progress(work_id: str, principal: str = Depends(require_worker)):
    with tx() as db:
        row = db.execute("SELECT project_id,status FROM work_items WHERE id=%s FOR UPDATE", (work_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Work not found")
        project_id, status = row
        require_grant(db, principal, project_id, "work.progress")
        active = db.execute("SELECT state FROM projects WHERE id=%s", (project_id,)).fetchone()
        if not active or active[0] != "ACTIVE":
            raise HTTPException(409, "Project not active")
        transition = {"READY": "IN_PROGRESS", "IN_PROGRESS": "IN_REVIEW", "VERIFIED": "DONE"}
        if status not in transition:
            raise HTTPException(409, "Invalid progression; independent review required")
        if status == "VERIFIED":
            approved = db.execute("SELECT 1 FROM reviews WHERE work_id=%s AND decision='APPROVE' ORDER BY created_at DESC LIMIT 1", (work_id,)).fetchone()
            if not approved:
                raise HTTPException(409, "Independent approval missing")
        next_state = transition[status]
        db.execute("UPDATE work_items SET status=%s WHERE id=%s", (next_state, work_id))
        audit(db, work_id, "work.progressed", {"from": status, "to": next_state})
    return {"id": work_id, "status": next_state}


@app.post("/v1/work/{work_id}/reviews", status_code=201)
def review(work_id: str, payload: ReviewRequest, principal: str = Depends(require_reviewer)):
    if not all(item.strip() for item in payload.evidence):
        raise HTTPException(422, "Blank evidence reference")
    with tx() as db:
        work = db.execute("SELECT project_id,status,author_id FROM work_items WHERE id=%s FOR UPDATE", (work_id,)).fetchone()
        if not work:
            raise HTTPException(404, "Work not found")
        project_id, status, author = work
        require_grant(db, principal, project_id, "work.review")
        active = db.execute("SELECT state FROM projects WHERE id=%s", (project_id,)).fetchone()
        if not active or active[0] != "ACTIVE" or status != "IN_REVIEW":
            raise HTTPException(409, "Work not reviewable")
        if principal == author:
            raise HTTPException(403, "Author cannot review own work")
        rid = str(uuid4())
        db.execute("INSERT INTO reviews(id,work_id,reviewer_id,decision,evidence) VALUES (%s,%s,%s,%s,%s::jsonb)", (rid, work_id, principal, payload.decision, json.dumps(payload.evidence)))
        next_state = "VERIFIED" if payload.decision == "APPROVE" else "IN_PROGRESS"
        db.execute("UPDATE work_items SET status=%s,evidence=%s::jsonb WHERE id=%s", (next_state, json.dumps(payload.evidence), work_id))
        audit(db, work_id, "work.reviewed", {"review_id": rid, "decision": payload.decision, "reviewer": principal})
    return {"review_id": rid, "status": next_state}

@app.post("/v1/work/{work_id}/stage-inert", status_code=202)
def stage_inert(work_id: str, principal: str = Depends(require_worker)):
    """Enqueue a fixed inert payload; no model or external action is possible."""
    if os.getenv("AAO_SANDBOX_QUEUE_ENABLED") != "true":
        raise HTTPException(503, "Sandbox queue disabled")
    with tx() as db:
        work = db.execute(
            "SELECT project_id,status FROM work_items WHERE id=%s FOR UPDATE",
            (work_id,),
        ).fetchone()
        if not work:
            raise HTTPException(404, "Work not found")
        project_id, status = work
        project = db.execute(
            "SELECT state FROM projects WHERE id=%s", (project_id,)
        ).fetchone()
        if not project or project[0] != "ACTIVE" or status != "READY":
            raise HTTPException(409, "Work not ready in active project")
        require_grant(db, principal, project_id, "work.admit")
        existing = db.execute(
            "SELECT id,status FROM execution_queue WHERE work_id=%s", (work_id,)
        ).fetchone()
        if existing:
            return {"execution_id": str(existing[0]), "status": existing[1]}
        execution_id = str(uuid4())
        db.execute(
            "INSERT INTO execution_queue(id,work_id,project_id,status,input_json) "
            "VALUES (%s,%s,%s,'QUEUED',%s::jsonb)",
            (execution_id, work_id, project_id, json.dumps({"type": "aao.inert.v1"})),
        )
        audit(db, execution_id, "execution.staged", {"work_id": work_id})
    return {"execution_id": execution_id, "status": "QUEUED"}
