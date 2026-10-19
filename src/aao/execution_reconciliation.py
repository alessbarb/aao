"""Independent, evidence-bound reconciliation of UNCERTAIN executions.

This operation only changes queue state. It NEVER calls tools or retries work.
"""
import json
from uuid import uuid4

from aao.postgresql_connection import connect_postgres


class ReconciliationDenied(ValueError):
    pass


def reconcile(execution_id: str, *, reviewer_id: str, evidence: list[str],
              disposition: str) -> str:
    if disposition not in {"RETRY_CONFIRMED_SAFE", "MARK_FAILED"}:
        raise ReconciliationDenied("Unknown disposition")
    if not reviewer_id or not evidence or not all(e.strip() for e in evidence):
        raise ReconciliationDenied("Independent reviewer and evidence required")
    with connect_postgres() as db:
        execution = db.execute(
            "SELECT q.status,q.worker_id,q.project_id,p.state "
            "FROM execution_queue q JOIN projects p ON p.id=q.project_id "
            "WHERE q.id=%s FOR UPDATE OF q,p", (execution_id,),
        ).fetchone()
        if not execution or execution[0] != "UNCERTAIN":
            raise ReconciliationDenied("Execution not uncertain")
        status, former_worker, project_id, project_state = execution
        if reviewer_id == former_worker:
            raise ReconciliationDenied("Worker cannot reconcile own execution")
        grant = db.execute(
            "SELECT 1 FROM project_grants WHERE principal_id=%s AND project_id=%s "
            "AND capability='execution.reconcile' "
            "AND (expires_at IS NULL OR expires_at > clock_timestamp()) FOR SHARE",
            (reviewer_id, project_id),
        ).fetchone()
        if not grant:
            raise ReconciliationDenied("Reconciliation capability required")
        if disposition == "RETRY_CONFIRMED_SAFE":
            if project_state != "ACTIVE":
                raise ReconciliationDenied("Project must be active to retry")
            effect = db.execute(
                "SELECT 1 FROM external_effects WHERE execution_id=%s "
                "AND status NOT IN ('REJECTED') LIMIT 1", (execution_id,),
            ).fetchone()
            if effect:
                raise ReconciliationDenied(
                    "External effect exists; manual effects reconciliation required"
                )
        new_state = "QUEUED" if disposition == "RETRY_CONFIRMED_SAFE" else "FAILED"
        db.execute(
            "UPDATE execution_queue SET status=%s,worker_id=NULL,"
            "lease_token=NULL,lease_expires_at=NULL WHERE id=%s",
            (new_state, execution_id),
        )
        db.execute(
            "INSERT INTO execution_journal(id,execution_id,kind,details) "
            "VALUES (%s,%s,'reconciled',%s::jsonb)",
            (str(uuid4()), execution_id, json.dumps({
                "reviewer": reviewer_id, "disposition": disposition,
                "evidence": evidence, "prior_state": status,
            })),
        )
    return new_state
