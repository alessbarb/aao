"""Minimal AAO API: CEO-confirmed mandates, projects and evidence-gated Kanban."""
import json
import os
import sqlite3
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from aao.policy import Verdict, authorize
from aao.storage import connect, event, initialize, transaction

DB_PATH = os.getenv("AAO_DB_PATH", "./data/aao.sqlite3")
CEO_TOKEN = os.getenv("AAO_CEO_TOKEN")


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize(DB_PATH)
    yield


app = FastAPI(title="AAO Core", version="0.1.0", lifespan=lifespan)


def require_ceo(x_ceo_token: str | None = Header(default=None)):
    if not CEO_TOKEN:
        raise HTTPException(503, "CEO token not configured: reserved writes disabled")
    import secrets
    if not x_ceo_token or not secrets.compare_digest(x_ceo_token, CEO_TOKEN):
        raise HTTPException(403, "CEO authentication required")
    return True


class MandateIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    objective: str = Field(min_length=1, max_length=5000)


class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    mandate_id: str


class WorkIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    acceptance_criteria: list[str] = Field(min_length=1)


class TransitionIn(BaseModel):
    status: str
    evidence: list[str] = Field(default_factory=list)


@app.get("/health")
def health():
    return {"status": "ok", "autonomous_execution": False}


@app.post("/v1/mandates", status_code=201)
def draft_mandate(payload: MandateIn):
    mid = str(uuid4())
    with transaction(DB_PATH) as db:
        db.execute("INSERT INTO mandates(id,title,objective,status) VALUES (?,?,?,'DRAFT')",
                   (mid, payload.title, payload.objective))
        event(db, mid, "mandate.drafted", {"title": payload.title})
    return {"id": mid, "status": "DRAFT"}


@app.post("/v1/mandates/{mandate_id}/confirm")
def confirm_mandate(mandate_id: str, _: bool = Depends(require_ceo)):
    with transaction(DB_PATH) as db:
        row = db.execute("SELECT status FROM mandates WHERE id=?", (mandate_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Mandate not found")
        if row["status"] != "DRAFT":
            raise HTTPException(409, "Mandate already confirmed")
        db.execute("UPDATE mandates SET status='CONFIRMED',confirmed_by='CEO' WHERE id=?",
                   (mandate_id,))
        event(db, mandate_id, "mandate.confirmed", {"authority": "CEO"})
    return {"id": mandate_id, "status": "CONFIRMED"}


@app.post("/v1/projects", status_code=201)
def create_project(payload: ProjectIn, _: bool = Depends(require_ceo)):
    decision = authorize("project.create", is_ceo=True, confirmed_mandate=True)
    if decision.verdict != Verdict.ALLOW:
        raise HTTPException(403, decision.reason)
    pid = str(uuid4())
    with transaction(DB_PATH) as db:
        mandate = db.execute("SELECT status FROM mandates WHERE id=?",
                             (payload.mandate_id,)).fetchone()
        if not mandate or mandate["status"] != "CONFIRMED":
            raise HTTPException(409, "Confirmed mandate required")
        existing = db.execute("SELECT id FROM projects WHERE mandate_id=?",
                              (payload.mandate_id,)).fetchone()
        if existing:
            raise HTTPException(409, "Mandate already used by a project")
        db.execute("INSERT INTO projects(id,name,mandate_id,state) VALUES (?,?,?,'ACTIVE')",
                   (pid, payload.name, payload.mandate_id))
        event(db, pid, "project.created", {"mandate_id": payload.mandate_id})
    return {"id": pid, "state": "ACTIVE"}


@app.get("/v1/projects")
def list_projects():
    with connect(DB_PATH) as db:
        return [dict(r) for r in db.execute("SELECT * FROM projects ORDER BY rowid")]


@app.post("/v1/projects/{project_id}/work", status_code=201)
def create_work(project_id: str, payload: WorkIn):
    wid = str(uuid4())
    with transaction(DB_PATH) as db:
        project = db.execute("SELECT state FROM projects WHERE id=?",
                             (project_id,)).fetchone()
        if not project:
            raise HTTPException(404, "Project not found")
        if project["state"] != "ACTIVE":
            raise HTTPException(409, "Project not active")
        db.execute("""INSERT INTO work_items
            (id,project_id,title,status,acceptance_criteria)
            VALUES (?,?,?,'INBOX',?)""",
            (wid, project_id, payload.title, json.dumps(payload.acceptance_criteria)))
        event(db, wid, "work.created", {"project_id": project_id})
    return {"id": wid, "status": "INBOX"}


@app.get("/v1/projects/{project_id}/board")
def board(project_id: str):
    with connect(DB_PATH) as db:
        if not db.execute("SELECT id FROM projects WHERE id=?", (project_id,)).fetchone():
            raise HTTPException(404, "Project not found")
        rows = db.execute("SELECT * FROM work_items WHERE project_id=? ORDER BY rowid",
                          (project_id,)).fetchall()
        return [{**dict(r), "evidence": json.loads(r["evidence"]),
                 "acceptance_criteria": json.loads(r["acceptance_criteria"])} for r in rows]


ALLOWED_NEXT = {
    "INBOX": {"READY"}, "READY": {"IN_PROGRESS"},
    "IN_PROGRESS": {"IN_REVIEW"}, "IN_REVIEW": {"VERIFIED"},
    "VERIFIED": {"DONE"}, "DONE": set(),
}


@app.post("/v1/work/{work_id}/transition")
def transition(work_id: str, payload: TransitionIn):
    if payload.status not in {s for opts in ALLOWED_NEXT.values() for s in opts}:
        raise HTTPException(422, "Unknown target state")
    with transaction(DB_PATH) as db:
        row = db.execute("SELECT * FROM work_items WHERE id=?", (work_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Work item not found")
        project = db.execute("SELECT state FROM projects WHERE id=?",
                             (row["project_id"],)).fetchone()
        if project["state"] != "ACTIVE":
            raise HTTPException(409, "Project not active")
        if payload.status not in ALLOWED_NEXT[row["status"]]:
            raise HTTPException(409, "Invalid state transition")
        evidence = json.loads(row["evidence"])
        evidence += payload.evidence
        if payload.status in {"VERIFIED", "DONE"} and not evidence:
            raise HTTPException(409, "Evidence required")
        # Independent-review enforcement is not implemented. Review states are
        # workflow placeholders and MUST NOT be treated as an audit approval.
        if payload.status in {"VERIFIED", "DONE"}:
            raise HTTPException(409, "Independent verification gate not implemented")
        db.execute("UPDATE work_items SET status=?, evidence=? WHERE id=?",
                   (payload.status, json.dumps(evidence), work_id))
        event(db, work_id, "work.transitioned", {"from": row["status"], "to": payload.status})
    return {"id": work_id, "status": payload.status}


@app.get("/v1/events")
def list_events():
    with connect(DB_PATH) as db:
        return [dict(r) for r in db.execute("SELECT * FROM events ORDER BY rowid")]
