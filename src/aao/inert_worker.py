"""One-shot inert worker. Cannot access models, tools, shell or external effects."""
import json
from datetime import datetime, timezone

from aao.pg_execution import claim, complete, state


def run_one(worker_id: str, credential: str, *, project_id: str, seconds: int = 30, agent_credential: str | None = None) -> dict:
    lease = claim(worker_id, credential=credential, project_id=project_id, seconds=seconds, agent_credential=agent_credential)
    if lease is None:
        return {"status": "IDLE"}
    execution_id = lease["execution_id"]
    info = state(execution_id)
    if not info or info["status"] != "RUNNING":
        return {"status": "UNCERTAIN", "execution_id": execution_id}
    # The worker intentionally does no work beyond producing a deterministic,
    # bounded marker, and cannot accept arbitrary Python or tool instructions.
    marker = {"kind": "aao.inert-worker.v1", "execution_id": execution_id,
              "recorded_at": datetime.now(timezone.utc).isoformat()}
    complete(execution_id, lease["token"], worker_id, marker, credential=credential, agent_credential=agent_credential)
    return {"status": "SUCCEEDED", "execution_id": execution_id}
