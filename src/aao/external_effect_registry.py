"""Fail-closed external-effect ledger: *recording only*, no effects are executed."""
import hashlib
import json
from uuid import uuid4

from aao.postgresql_connection import connect_postgres


class EffectConflict(ValueError):
    pass


def canonical_digest(value: dict) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(data).hexdigest()


def propose(*, execution_id: str, idempotency_key: str, capability: str, request: dict):
    """Persist a proposal. Does not authorize, call tools or execute a request."""
    if not execution_id or not idempotency_key or not capability:
        raise EffectConflict("Execution, idempotency key and capability required")
    if len(idempotency_key) > 200:
        raise EffectConflict("Idempotency key too long")
    digest = canonical_digest(request)
    with connect_postgres() as db:
        row = db.execute(
            "SELECT id,execution_id,capability,request_digest FROM external_effects "
            "WHERE idempotency_key=%s FOR UPDATE", (idempotency_key,)
        ).fetchone()
        if row:
            if str(row[1]) != execution_id or row[2] != capability or row[3] != digest:
                raise EffectConflict("Idempotency key reused with different request")
            return {"id": str(row[0]), "status": "PROPOSED_OR_EXISTING"}
        exists = db.execute("SELECT id FROM execution_queue WHERE id=%s", (execution_id,)).fetchone()
        if not exists:
            raise EffectConflict("Unknown execution")
        effect_id = str(uuid4())
        db.execute(
            "INSERT INTO external_effects(id,execution_id,idempotency_key,capability,status,request_digest) "
            "VALUES (%s,%s,%s,%s,'PROPOSED',%s)",
            (effect_id, execution_id, idempotency_key, capability, digest),
        )
        return {"id": effect_id, "status": "PROPOSED"}
