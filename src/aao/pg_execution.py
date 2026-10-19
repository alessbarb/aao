"""PostgreSQL inert execution queue with atomic claims and quarantine.

No tool adapter or language model execution is provided. A failed lease is
UNCERTAIN and must be reconciled by a separate authorized procedure.
"""
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from aao.postgres import connect_postgres
from aao.worker_auth import verify_registered_worker
from aao.pg_principals import digest_token
import hmac


class ExecutionConflict(ValueError):
    pass


def journal(db, execution_id: str, kind: str, details: dict):
    db.execute(
        "INSERT INTO execution_journal(id,execution_id,kind,details) VALUES (%s,%s,%s,%s::jsonb)",
        (str(uuid4()), execution_id, kind, json.dumps(details)),
    )


def claim(worker_id: str, *, credential: str | None = None, project_id: str, seconds: int = 60, now: datetime | None = None, agent_credential: str | None = None):
    if not worker_id or not project_id or seconds < 1:
        raise ExecutionConflict("Worker and positive lease duration required")
    instant = now or datetime.now(timezone.utc)
    with connect_postgres() as db:
        registration = db.execute("SELECT token_digest,enabled FROM worker_registrations WHERE worker_id=%s FOR SHARE", (worker_id,)).fetchone()
        if not registration or not verify_registered_worker(worker_id, credential, digest=registration[0], enabled=registration[1]):
            raise ExecutionConflict("Worker authentication failed")
        grant = db.execute(
            "SELECT 1 FROM project_grants WHERE principal_id=%s AND project_id=%s "
            "AND capability='execution.claim' "
            "AND (expires_at IS NULL OR expires_at > now())",
            (worker_id, project_id),
        ).fetchone()
        if not grant:
            raise ExecutionConflict("Project execution claim grant required")
        row = db.execute(
            "SELECT q.id FROM execution_queue q JOIN projects p ON p.id=q.project_id "
            "WHERE q.status='QUEUED' AND p.state='ACTIVE' AND q.project_id=%s "
            "ORDER BY q.created_at,q.id FOR UPDATE OF q SKIP LOCKED LIMIT 1",
            (project_id,),
        ).fetchone()
        if not row:
            return None
        eid = str(row[0])
        project_id = db.execute(
            "SELECT project_id FROM execution_queue WHERE id=%s", (eid,)
        ).fetchone()[0]
        project = db.execute(
            "SELECT state FROM projects WHERE id=%s FOR UPDATE", (project_id,)
        ).fetchone()
        if not project or project[0] != "ACTIVE":
            return None
        token = str(uuid4())
        expiry = instant + timedelta(seconds=seconds)
        db.execute(
            "UPDATE execution_queue SET status='RUNNING',lease_token=%s,"
            "worker_id=%s,lease_expires_at=%s,attempts=attempts+1 WHERE id=%s",
            (token, worker_id, expiry, eid),
        )
        journal(db, eid, "claimed", {"worker_id": worker_id})
    return {"execution_id": eid, "token": token, "worker_id": worker_id,
            "expires_at": expiry.isoformat()}


def complete(execution_id: str, token: str, worker_id: str, result: dict,
             *, credential: str | None = None, now: datetime | None = None, agent_credential: str | None = None):
    instant = now or datetime.now(timezone.utc)
    with connect_postgres() as db:
        registration = db.execute(
            "SELECT token_digest,enabled FROM worker_registrations "
            "WHERE worker_id=%s FOR SHARE", (worker_id,)
        ).fetchone()
        if not registration or not verify_registered_worker(
            worker_id, credential, digest=registration[0], enabled=registration[1]
        ):
            raise ExecutionConflict("Worker authentication failed")
        execution = db.execute(
            "SELECT project_id FROM execution_queue WHERE id=%s FOR UPDATE",
            (execution_id,),
        ).fetchone()
        if not execution:
            raise ExecutionConflict("Execution not found")
        project = db.execute(
            "SELECT state FROM projects WHERE id=%s FOR UPDATE", (execution[0],)
        ).fetchone()
        if not project or project[0] != "ACTIVE":
            raise ExecutionConflict("Project is not active")
        grant = db.execute(
            "SELECT 1 FROM project_grants WHERE principal_id=%s AND project_id=%s "
            "AND capability='execution.claim' "
            "AND (expires_at IS NULL OR expires_at > now())",
            (worker_id, str(execution[0])),
        ).fetchone()
        if not grant:
            raise ExecutionConflict("Project execution claim grant revoked")
        updated = db.execute(
            "UPDATE execution_queue SET status='SUCCEEDED',result_json=%s::jsonb "
            "WHERE id=%s AND status='RUNNING' AND lease_token=%s "
            "AND worker_id=%s AND lease_expires_at>%s AND EXISTS (SELECT 1 FROM projects p WHERE p.id=execution_queue.project_id AND p.state='ACTIVE') RETURNING id",
            (json.dumps(result), execution_id, token, worker_id, instant),
        ).fetchone()
        if not updated:
            raise ExecutionConflict("Lease stale, expired, or execution not running")
        journal(db, execution_id, "completed", {"worker_id": worker_id})


def quarantine_expired(*, now: datetime | None = None) -> int:
    instant = now or datetime.now(timezone.utc)
    with connect_postgres() as db:
        rows = db.execute(
            "UPDATE execution_queue SET status='UNCERTAIN' "
            "WHERE status='RUNNING' AND lease_expires_at<=%s RETURNING id",
            (instant,),
        ).fetchall()
        for row in rows:
            journal(db, str(row[0]), "quarantined", {"reason": "lease expired"})
        return len(rows)


def state(execution_id: str):
    with connect_postgres() as db:
        row = db.execute(
            "SELECT id,work_id,project_id,status,attempts,lease_expires_at "
            "FROM execution_queue WHERE id=%s", (execution_id,)
        ).fetchone()
        if not row:
            return None
        return {"id": str(row[0]), "work_id": str(row[1]),
                "project_id": str(row[2]), "status": row[3],
                "attempts": row[4], "lease_expires_at": row[5]}
