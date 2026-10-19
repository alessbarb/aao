"""One-shot inert worker. Cannot access models, tools, shell or external effects."""
from datetime import UTC, datetime

from aao.execution_queue import claim, complete, state


def run_one(worker_id: str, agent_credential: str, *, project_id: str, seconds: int = 30) -> dict:
    lease = claim(worker_id, agent_credential=agent_credential, project_id=project_id, seconds=seconds)
    if lease is None:
        return {"status": "IDLE"}
    execution_id = lease["execution_id"]
    info = state(execution_id)
    if not info or info["status"] != "RUNNING":
        return {"status": "UNCERTAIN", "execution_id": execution_id}
    # The worker intentionally does no work beyond producing a deterministic,
    # bounded marker, and cannot accept arbitrary Python or tool instructions.
    marker = {"kind": "aao.inert-worker.v1", "execution_id": execution_id,
              "recorded_at": datetime.now(UTC).isoformat()}
    complete(execution_id, lease["token"], worker_id, marker, agent_credential=agent_credential)
    return {"status": "SUCCEEDED", "execution_id": execution_id}
