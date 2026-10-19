"""PostgreSQL-backed isolated API for AAO's mandate/project/work lifecycle.

This is a separate development service, not a transparent migration of the
SQLite API. No agent execution or external side effects are enabled.
"""
import json
import os
import secrets
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from aao.environment_settings import load_local_env

load_local_env()

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field

from aao.capability_contracts import missing_contract_fields
from aao.capability_evaluation import recommend
from aao.planner import Admission, decide_admission
from aao.review import evaluate_review


def _ceo_bearer_enabled() -> bool:
    mode = os.getenv("AAO_ENV", "").strip().lower()
    return mode in {"development", "test"}


def require_ceo(x_ceo_token: str | None = Header(None)):
    if not _ceo_bearer_enabled():
        raise HTTPException(503, "CEO development bearer is unavailable in this environment")
    expected = os.getenv("AAO_CEO_TOKEN")
    if not expected:
        raise HTTPException(503, "CEO credential not configured")
    if not x_ceo_token or not secrets.compare_digest(expected, x_ceo_token):
        raise HTTPException(403, "CEO authentication required")
    return "ceo"


def require_reviewer(
    x_auditor_token: str | None = Header(None),
):
    from aao.principal_credentials import PrincipalDenied
    try:
        return _authenticate_request_principal(x_auditor_token, "AUDITOR")
    except PrincipalDenied as exc:
        raise HTTPException(403, "Individual auditor credential rejected") from exc


def require_worker(
    x_agent_token: str | None = Header(None),
):
    from aao.principal_credentials import PrincipalDenied
    try:
        return _authenticate_request_principal(x_agent_token, "AGENT")
    except PrincipalDenied as exc:
        raise HTTPException(403, "Individual agent credential rejected") from exc


@contextmanager
def tx():
    from aao.postgresql_connection import connect_postgres
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


class ProjectStateRequest(BaseModel):
    action: str = Field(pattern=r"^(pause|resume|cancel)$")


class WorkRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    author_id: str = Field(min_length=1)
    acceptance_criteria: list[str] = Field(min_length=1)


class ReviewRequest(BaseModel):
    decision: str = Field(pattern="^(APPROVE|REJECT)$")
    evidence: list[str] = Field(min_length=1)


class PrincipalCredentialRequest(BaseModel):
    principal_id: str = Field(min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9_-]+$")
    kind: str = Field(pattern=r"^(AGENT|AUDITOR)$")


class GrantRequest(BaseModel):
    principal_id: str = Field(min_length=1)
    capability: str = Field(pattern=r"^(?:work\.(?:create|admit|review|progress)|project\.read|execution\.claim|execution\.reconcile|effect\.(?:propose|reconcile)|evidence\.submit)$")


class CapabilityRequest(BaseModel):
    capability_id: str = Field(min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9._-]+$")
    version: str = Field(min_length=1, max_length=64)
    capability_type: str = Field(pattern=r"^(cli_script|library|application_service|agent|agent_skill|knowledge_procedure|workflow)$")
    provenance: dict
    contract: dict
    required_permissions: list[str] = Field(default_factory=list, max_length=32)
    risks: list[str] = Field(default_factory=list, max_length=32)
    dependencies: list[str] = Field(default_factory=list, max_length=64)
    tests: list[str] = Field(default_factory=list, max_length=64)
    compatibility: dict = Field(default_factory=dict)
    evidence: list[str] = Field(default_factory=list, max_length=64)
    status: str = Field(default="registered_local", pattern=r"^registered_local$")


class CapabilityOption(BaseModel):
    choice: str = Field(pattern=r"^(reuse|adapt|build)$")
    fit: int = Field(ge=0, le=5)
    security: int = Field(ge=0, le=5)
    cost: int = Field(ge=0, le=5)
    time: int = Field(ge=0, le=5)
    tokens: int = Field(ge=0, le=5)
    maintenance: int = Field(ge=0, le=5)


class CapabilityEvaluationRequest(BaseModel):
    task_id: str
    options: list[CapabilityOption] = Field(min_length=3, max_length=3)
    rationale: str = Field(min_length=1, max_length=2000)
    evidence: list[str] = Field(min_length=1, max_length=32)
    capability_id: str | None = Field(default=None, max_length=128)
    version: str | None = Field(default=None, max_length=64)


app = FastAPI(title="AAO PostgreSQL development core", version="0.2.0")
_CEO_PRINCIPAL = object()

class AuthenticatedPrincipal(str):
    """Principal ID plus the exact bearer digest for transaction-time recheck."""

    def __new__(cls, principal_id: str, token_digest: str, kind: str):
        value = super().__new__(cls, principal_id)
        value.token_digest = token_digest
        value.kind = kind
        return value


def _authenticate_request_principal(token: str | None, kind: str):
    from aao.principal_credentials import authenticate, digest_token

    principal_id = authenticate(token, kind=kind)
    return AuthenticatedPrincipal(principal_id, digest_token(token), kind)



@app.get("/", include_in_schema=False)
def workboard_ui():
    """Serve the workboard from the same origin as the PostgreSQL API."""
    return FileResponse(Path(__file__).resolve().parents[2] / "frontend" / "index.html")


@app.get("/health")
def health():
    return {"service": "postgres-dev", "autonomous_execution": False}


@app.post("/v1/principals/credentials", status_code=201)
def issue_principal_credential(
    payload: PrincipalCredentialRequest, _: str = Depends(require_ceo)
):
    """CEO-only development issuance. Secret returned once, digest persisted."""
    from aao.principal_credentials import digest_token

    token = secrets.token_urlsafe(32)
    with tx() as db:
        if db.execute(
            "SELECT 1 FROM principal_credentials WHERE principal_id=%s FOR UPDATE",
            (payload.principal_id,),
        ).fetchone():
            raise HTTPException(409, "Principal already registered; use rotation")
        db.execute(
            "INSERT INTO principal_credentials(principal_id,kind,token_digest,enabled) "
            "VALUES (%s,%s,%s,true)",
            (payload.principal_id, payload.kind, digest_token(token)),
        )
        audit(db, str(uuid4()), "principal.credential.issued",
              {"principal_id": payload.principal_id, "kind": payload.kind})
    return {"principal_id": payload.principal_id, "kind": payload.kind, "token": token}


@app.post("/v1/principals/{principal_id}/revoke")
def revoke_principal(principal_id: str, _: str = Depends(require_ceo)):
    """Revocation prevents new authentication and lease completion."""
    with tx() as db:
        row = db.execute(
            "UPDATE principal_credentials SET enabled=false "
            "WHERE principal_id=%s AND enabled=true RETURNING kind",
            (principal_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Active principal credential not found")
        audit(db, str(uuid4()), "principal.credential.revoked",
              {"principal_id": principal_id, "kind": row[0]})
    return {"principal_id": principal_id, "enabled": False}


@app.post("/v1/principals/{principal_id}/rotate")
def rotate_principal(principal_id: str, _: str = Depends(require_ceo)):
    """Atomic rotation invalidates the previous token."""
    from aao.principal_credentials import digest_token

    token = secrets.token_urlsafe(32)
    with tx() as db:
        row = db.execute(
            "UPDATE principal_credentials SET token_digest=%s "
            "WHERE principal_id=%s AND enabled=true RETURNING kind",
            (digest_token(token), principal_id),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Active principal credential not found")
        audit(db, str(uuid4()), "principal.credential.rotated",
              {"principal_id": principal_id, "kind": row[0]})
    return {"principal_id": principal_id, "kind": row[0], "token": token}


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


@app.post("/v1/projects/{project_id}/state")
def change_project_state(
    project_id: str,
    payload: ProjectStateRequest,
    _: str = Depends(require_ceo),
):
    """CEO-controlled suspension state transition for the inert PostgreSQL path."""
    transitions = {
        ("ACTIVE", "pause"): "PAUSED",
        ("PAUSED", "resume"): "ACTIVE",
        ("ACTIVE", "cancel"): "CANCELLED",
        ("PAUSED", "cancel"): "CANCELLED",
    }
    with tx() as db:
        row = db.execute(
            "SELECT state FROM projects WHERE id=%s FOR UPDATE", (project_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Project not found")
        next_state = transitions.get((row[0], payload.action))
        if not next_state:
            raise HTTPException(409, "Invalid project state transition")
        db.execute(
            "UPDATE projects SET state=%s WHERE id=%s", (next_state, project_id),
        )
        audit(db, project_id, "project.state_changed", {
            "from": row[0], "to": next_state, "authority": "ceo",
        })
    return {"id": project_id, "state": next_state}


def read_principal(
    x_ceo_token: str | None = Header(None),
    x_agent_token: str | None = Header(None),
):
    ceo = os.getenv("AAO_CEO_TOKEN")
    if (_ceo_bearer_enabled() and ceo and x_ceo_token
            and secrets.compare_digest(ceo, x_ceo_token)):
        return _CEO_PRINCIPAL
    if x_agent_token is not None:
        from aao.principal_credentials import PrincipalDenied
        try:
            return _authenticate_request_principal(x_agent_token, "AGENT")
        except PrincipalDenied as exc:
            raise HTTPException(403, "Individual reader credential rejected") from exc
    raise HTTPException(403, "Authenticated reader required")


@app.get("/v1/projects")
def projects(principal: str = Depends(read_principal)):
    with tx() as db:
        if principal is _CEO_PRINCIPAL:
            rows = db.execute("SELECT id,name,state FROM projects ORDER BY name,id").fetchall()
        else:
            if not isinstance(principal, AuthenticatedPrincipal):
                raise HTTPException(403, "Individual reader credential required")
            credential = db.execute(
                "SELECT kind,enabled FROM principal_credentials "
                "WHERE principal_id=%s AND token_digest=%s FOR SHARE",
                (principal, principal.token_digest),
            ).fetchone()
            if not credential or credential[0] != "AGENT" or not credential[1]:
                raise HTTPException(403, "Individual reader invalid or revoked")
            rows = db.execute(
                "SELECT p.id,p.name,p.state FROM projects p JOIN project_grants g ON g.project_id=p.id "
                "WHERE g.principal_id=%s AND g.capability='project.read' "
                "AND (g.expires_at IS NULL OR g.expires_at > clock_timestamp()) ORDER BY p.name,p.id "
                "FOR SHARE OF g",
                (principal,),
            ).fetchall()
        return [{"id": r[0], "name": r[1], "state": r[2]} for r in rows]


@app.post("/v1/projects/{project_id}/grants")
def grant(project_id: str, payload: GrantRequest, _: str = Depends(require_ceo)):
    with tx() as db:
        if not db.execute("SELECT 1 FROM projects WHERE id=%s", (project_id,)).fetchone():
            raise HTTPException(404, "Project not found")
        principal = db.execute(
            "SELECT kind,enabled FROM principal_credentials "
            "WHERE principal_id=%s FOR SHARE", (payload.principal_id,),
        ).fetchone()
        if not principal:
            raise HTTPException(404, "Principal not found")
        if not principal[1]:
            raise HTTPException(409, "Principal credential is disabled")
        required_kind = (
            "AUDITOR" if payload.capability in {
                "work.review", "execution.reconcile", "effect.reconcile",
            } else "AGENT"
        )
        if principal[0] != required_kind:
            raise HTTPException(
                422, f"Capability requires a {required_kind} principal",
            )
        inserted = db.execute(
            "INSERT INTO project_grants(principal_id,project_id,capability) VALUES (%s,%s,%s) "
            "ON CONFLICT DO NOTHING RETURNING project_id",
            (payload.principal_id, project_id, payload.capability),
        ).fetchone()
        if inserted:
            audit(db, project_id, "grant.created",
                  {"principal_id": payload.principal_id, "capability": payload.capability})
    return JSONResponse(
        status_code=201 if inserted else 200,
        content={
            "project_id": project_id,
            "capability": payload.capability,
            "created": bool(inserted),
        },
    )


@app.delete("/v1/projects/{project_id}/grants/{principal_id}/{capability}", status_code=204)
def revoke_grant(
    project_id: str,
    principal_id: str,
    capability: str,
    _: str = Depends(require_ceo),
):
    """Revoke one project grant; row-locking protected operations serialize with this."""
    with tx() as db:
        if not db.execute("SELECT 1 FROM projects WHERE id=%s", (project_id,)).fetchone():
            raise HTTPException(404, "Project not found")
        deleted = db.execute(
            "DELETE FROM project_grants WHERE project_id=%s AND principal_id=%s "
            "AND capability=%s RETURNING principal_id",
            (project_id, principal_id, capability),
        ).fetchone()
        if not deleted:
            raise HTTPException(404, "Project grant not found")
        audit(db, project_id, "grant.revoked",
              {"principal_id": principal_id, "capability": capability})
    return Response(status_code=204)


def require_grant(db, principal: str, project_id: str, capability: str):
    """Recheck the presented credential and grant through the protected transaction."""
    if not isinstance(principal, AuthenticatedPrincipal):
        raise HTTPException(403, "Individual principal credential required")
    row = db.execute(
        "SELECT kind,enabled FROM principal_credentials "
        "WHERE principal_id=%s AND token_digest=%s FOR SHARE",
        (principal, principal.token_digest),
    ).fetchone()
    expected_kind = "AUDITOR" if capability in {"work.review", "execution.reconcile", "effect.reconcile"} else "AGENT"
    if not row or row[0] != expected_kind or row[0] != principal.kind or not row[1]:
        raise HTTPException(403, "Individual principal invalid or revoked")
    if not db.execute(
        "SELECT 1 FROM project_grants WHERE principal_id=%s AND project_id=%s "
        "AND capability=%s AND (expires_at IS NULL OR expires_at > clock_timestamp()) FOR SHARE",
        (principal, project_id, capability),
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
        if principal is not _CEO_PRINCIPAL:
            require_grant(db, principal, project_id, "project.read")
        rows = db.execute(
            "SELECT id,title,status,acceptance_criteria,evidence FROM work_items "
            "WHERE project_id=%s ORDER BY id", (project_id,),
        ).fetchall()
        return [
            {"id": r[0], "title": r[1], "status": r[2],
             "acceptance_criteria": r[3], "evidence": r[4]} for r in rows
        ]


@app.get("/v1/projects/{project_id}/capabilities")
def list_capabilities(
    project_id: str, principal: str = Depends(read_principal),
    query: str | None = None, capability_type: str | None = None,
):
    """Discover real project-local capability versions; listing grants no execution authority."""
    allowed_types = {
        "cli_script", "library", "application_service", "agent", "agent_skill",
        "knowledge_procedure", "workflow",
    }
    if capability_type is not None and capability_type not in allowed_types:
        raise HTTPException(422, "Unknown capability type")
    with tx() as db:
        if not db.execute("SELECT 1 FROM projects WHERE id=%s", (project_id,)).fetchone():
            raise HTTPException(404, "Project not found")
        if principal is not _CEO_PRINCIPAL:
            require_grant(db, principal, project_id, "project.read")
        rows = db.execute(
            "SELECT capability_id,version,capability_type,status,provenance,contract,"
            "required_permissions,risks,dependencies,tests,compatibility,evidence,created_by,created_at "
            "FROM capability_versions WHERE project_id=%s "
            "AND (%s::text IS NULL OR capability_type=%s) "
            "AND (%s::text IS NULL OR capability_id ILIKE %s OR contract::text ILIKE %s) "
            "ORDER BY capability_id,version",
            (project_id, capability_type, capability_type, query,
             f"%{query}%" if query else None, f"%{query}%" if query else None),
        ).fetchall()
        return [{
            "capability_id": str(row[0]), "version": row[1], "capability_type": row[2],
            "status": row[3], "provenance": row[4], "contract": row[5],
            "required_permissions": row[6], "risks": row[7], "dependencies": row[8],
            "tests": row[9], "compatibility": row[10], "evidence": row[11],
            "created_by": row[12], "created_at": row[13].isoformat(),
            "execution_authorized": False,
        } for row in rows]


@app.post("/v1/projects/{project_id}/capabilities", status_code=201)
def register_capability(
    project_id: str, payload: CapabilityRequest,
    principal: str = Depends(require_worker),
):
    """Record project-owned capability metadata, not an executable authorization."""
    if not payload.provenance or not payload.contract:
        raise HTTPException(422, "Capability provenance and contract are required")
    missing_fields = missing_contract_fields(payload.capability_type, payload.contract)
    if missing_fields:
        raise HTTPException(
            422, "Capability contract is incomplete: " + ", ".join(sorted(missing_fields)),
        )
    if not payload.tests or not payload.evidence:
        raise HTTPException(422, "At least one test reference and evidence reference are required")
    with tx() as db:
        project = db.execute(
            "SELECT state FROM projects WHERE id=%s FOR SHARE", (project_id,),
        ).fetchone()
        if not project:
            raise HTTPException(404, "Project not found")
        if project[0] != "ACTIVE":
            raise HTTPException(409, "Capabilities can only be registered in active projects")
        require_grant(db, principal, project_id, "work.create")
        inserted = db.execute(
            "INSERT INTO capability_versions(project_id,capability_id,version,capability_type,"
            "status,provenance,contract,required_permissions,risks,dependencies,tests,"
            "compatibility,evidence,created_by) VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,"
            "%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,%s) "
            "ON CONFLICT (project_id,capability_id,version) DO NOTHING RETURNING version",
            (project_id, payload.capability_id, payload.version, payload.capability_type,
             "registered_local", json.dumps(payload.provenance), json.dumps(payload.contract),
             json.dumps(payload.required_permissions), json.dumps(payload.risks),
             json.dumps(payload.dependencies), json.dumps(payload.tests),
             json.dumps(payload.compatibility), json.dumps(payload.evidence), principal),
        ).fetchone()
        if not inserted:
            raise HTTPException(409, "Capability version already exists and is immutable")
        audit(db, project_id, "capability.version_registered", {
            "capability_id": payload.capability_id, "version": payload.version,
            "capability_type": payload.capability_type, "created_by": principal,
            "execution_authorized": False,
        })
    return {"project_id": project_id, "capability_id": payload.capability_id,
            "version": payload.version, "status": "registered_local",
            "execution_authorized": False}


@app.post("/v1/projects/{project_id}/capability-evaluations", status_code=201)
def evaluate_capabilities(
    project_id: str, payload: CapabilityEvaluationRequest,
    principal: str = Depends(require_worker),
):
    """Compare reuse/adapt/build for a real project task and audit the recommendation."""
    choices = [option.choice for option in payload.options]
    if sorted(choices) != ["adapt", "build", "reuse"]:
        raise HTTPException(422, "Exactly one reuse, adapt, and build option is required")
    if not payload.rationale.strip() or any(not item.strip() for item in payload.evidence):
        raise HTTPException(422, "Rationale and evidence references must be non-blank")
    selected_options = [option.model_dump() for option in payload.options]
    recommendation, scores = recommend(selected_options)
    if recommendation in {"reuse", "adapt"}:
        if not payload.capability_id or not payload.version:
            raise HTTPException(422, "Reuse or adaptation requires a registered capability version")
    elif payload.capability_id or payload.version:
        raise HTTPException(422, "Build comparison must not claim an existing capability version")

    with tx() as db:
        project = db.execute(
            "SELECT state FROM projects WHERE id=%s FOR SHARE", (project_id,),
        ).fetchone()
        if not project:
            raise HTTPException(404, "Project not found")
        if project[0] != "ACTIVE":
            raise HTTPException(409, "Capability evaluation requires an active project")
        require_grant(db, principal, project_id, "work.create")
        task = db.execute(
            "SELECT 1 FROM work_items WHERE id=%s AND project_id=%s FOR SHARE",
            (payload.task_id, project_id),
        ).fetchone()
        if not task:
            raise HTTPException(404, "Task not found in this project")
        if recommendation in {"reuse", "adapt"}:
            capability = db.execute(
                "SELECT status FROM capability_versions WHERE project_id=%s "
                "AND capability_id=%s AND version=%s FOR SHARE",
                (project_id, payload.capability_id, payload.version),
            ).fetchone()
            if not capability or capability[0] != "registered_local":
                raise HTTPException(409, "Selected capability version is unavailable locally")
        details = {
            "project_id": project_id, "task_id": payload.task_id,
            "principal_id": principal, "options": selected_options,
            "scores": scores, "recommendation": recommendation,
            "capability_id": payload.capability_id, "version": payload.version,
            "rationale": payload.rationale, "evidence": payload.evidence,
            "score_method": "equal-weighted mean of six caller-assessed 0-5 dimensions",
            "execution_authorized": False,
        }
        audit(db, payload.task_id, "capability.evaluated", details)
    return {"task_id": payload.task_id, "recommendation": recommendation,
            "scores": scores, "capability_id": payload.capability_id,
            "version": payload.version, "execution_authorized": False}


@app.get("/v1/projects/{project_id}/capability-evaluations")
def list_capability_evaluations(
    project_id: str, principal: str = Depends(read_principal),
):
    with tx() as db:
        if not db.execute("SELECT 1 FROM projects WHERE id=%s", (project_id,)).fetchone():
            raise HTTPException(404, "Project not found")
        if principal is not _CEO_PRINCIPAL:
            require_grant(db, principal, project_id, "project.read")
        rows = db.execute(
            "SELECT e.subject_id,e.details,e.created_at,w.title FROM events e "
            "JOIN work_items w ON w.id=e.subject_id AND w.project_id=%s "
            "WHERE e.kind='capability.evaluated' ORDER BY e.created_at DESC",
            (project_id,),
        ).fetchall()
        return [{"task_id": str(row[0]), "details": row[1],
                 "created_at": row[2].isoformat(), "task_title": row[3]}
                for row in rows]


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
            raise HTTPException(
                409,
                "Completion disabled until independent approval verification exists",
            )
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
        executions = db.execute(
            "SELECT id,status FROM execution_queue WHERE work_id=%s FOR UPDATE",
            (work_id,),
        ).fetchall()
        if payload.decision == "APPROVE" and any(
            execution_status != "SUCCEEDED"
            for _, execution_status in executions
        ):
            raise HTTPException(409, "Execution must succeed before work review")
        if db.execute(
            "SELECT 1 FROM execution_journal j "
            "JOIN execution_queue q ON q.id=j.execution_id "
            "WHERE q.work_id=%s AND j.kind='claimed' "
            "AND j.details->>'worker_id'=%s LIMIT 1",
            (work_id, principal),
        ).fetchone():
            raise HTTPException(403, "Execution worker cannot review own work")
        review_decision = evaluate_review(
            author_id=author,
            reviewer_id=principal,
            evidence=payload.evidence,
            decision=payload.decision,
            project_active=active[0] == "ACTIVE",
        )
        if not review_decision.allowed:
            raise HTTPException(409, review_decision.reason)
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
        require_grant(db, principal, project_id, "execution.claim")
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
