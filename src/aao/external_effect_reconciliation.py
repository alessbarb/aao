"""Reconcile effect records without ever invoking the external system.

Fail closed: only PROPOSED may be rejected; any other state requires
separate investigation before the executing system can be retried.
"""
import json
from uuid import uuid4

from aao.postgresql_connection import connect_postgres


class EffectReviewDenied(ValueError):
    pass


def reject_unexecuted_proposal(effect_id: str, *, auditor_credential: str, evidence: list[str]):
    if not auditor_credential or not evidence or not all(x.strip() for x in evidence):
        raise EffectReviewDenied("Active auditor credential and meaningful evidence required")
    with connect_postgres() as db:
        from aao.principal_credentials import PrincipalDenied, authenticate_in_transaction
        try:
            reviewer_id = authenticate_in_transaction(
                db, auditor_credential, kind="AUDITOR"
            )
        except PrincipalDenied as exc:
            raise EffectReviewDenied("Active auditor credential required") from exc
        effect = db.execute(
            "SELECT e.status,e.execution_id,q.project_id,q.worker_id "
            "FROM external_effects e JOIN execution_queue q ON q.id=e.execution_id "
            "WHERE e.id=%s FOR UPDATE OF e,q", (effect_id,),
        ).fetchone()
        if not effect or effect[0] != "PROPOSED":
            raise EffectReviewDenied("Only unexecuted proposals may be rejected")
        if reviewer_id == effect[3]:
            raise EffectReviewDenied("Execution worker may not review own effect")
        grant = db.execute(
            "SELECT 1 FROM project_grants WHERE principal_id=%s AND project_id=%s "
            "AND capability='effect.reconcile' "
            "AND (expires_at IS NULL OR expires_at > clock_timestamp()) FOR SHARE",
            (reviewer_id, effect[2]),
        ).fetchone()
        if not grant:
            raise EffectReviewDenied("Independent effect capability missing")
        db.execute("UPDATE external_effects SET status='REJECTED' WHERE id=%s", (effect_id,))
        db.execute(
            "INSERT INTO execution_journal(id,execution_id,kind,details) "
            "VALUES (%s,%s,'effect.rejected',%s::jsonb)",
            (str(uuid4()), str(effect[1]), json.dumps({
                "effect_id": effect_id, "reviewer": reviewer_id, "evidence": evidence,
            })),
        )
    return "REJECTED"
