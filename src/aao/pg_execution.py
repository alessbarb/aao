"""PostgreSQL inert execution queue with atomic claims and quarantine.

No tool adapter or language model execution is provided. A failed lease is
UNCERTAIN and must be reconciled by a separate authorized procedure.
"""
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from aao.postgres import connect_postgres


class ExecutionConflict(ValueError):
    pass


def journal(db, execution_id: str, kind: str, details: dict):
    db.execute(
        "INSERT INTO execution_journal(id,execution_id,kind,details) VALUES (%s,%s,%s,%s::jsonb)",
        (str(uuid4()), execution_id, kind, json.dumps(details)),
    )


def claim(worker_id: str, *, seconds: int = 60, now: datetime | None = None):
    if not worker_id or seconds < 1:
        raise ExecutionConflict("Worker and positive lease duration required")
    instant = now or datetime.now(timezone.utc)
    with connect_postgres() as db:
        row = db.execute(
            "SELECT id FROM execution_queue WHERE status='QUEUED' "
            "ORDER BY created_at,id FOR UPDATE SKIP LOCKED LIMIT 1"
        ).fetchone()
        if not row:
            return None
        eid = str(row[0])
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
             *, now: datetime | None = None):
    instant = now or datetime.now(timezone.utc)
    with connect_postgres() as db:
        updated = db.execute(
            "UPDATE execution_queue SET status='SUCCEEDED',result_json=%s::jsonb "
            "WHERE id=%s AND status='RUNNING' AND lease_token=%s "
            "AND worker_id=%s AND lease_expires_at>%s RETURNING id",
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
