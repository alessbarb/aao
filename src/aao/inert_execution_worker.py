"""One-shot worker for inert markers and a fixed isolated repository check."""
import os
from datetime import UTC, datetime

from aao.execution_queue import ExecutionConflict, claim, complete, state
from aao.sandboxed_repository_checks import RepositoryCheckError, run_repository_check


def run_one(worker_id: str, agent_credential: str, *, project_id: str, seconds: int = 30) -> dict:
    lease = claim(worker_id, agent_credential=agent_credential, project_id=project_id, seconds=seconds)
    if lease is None:
        return {"status": "IDLE"}
    execution_id = lease["execution_id"]
    info = state(execution_id)
    if not info or info["status"] != "RUNNING":
        return {"status": "UNCERTAIN", "execution_id": execution_id}
    input_data = lease["input"]
    if input_data == {"type": "aao.inert.v1"}:
        result = {"kind": "aao.inert-worker.v1", "execution_id": execution_id,
                  "recorded_at": datetime.now(UTC).isoformat()}
    elif (isinstance(input_data, dict)
          and input_data.get("type") == "aao.repository-check.v1"
          and input_data.get("check_id") == "core-unit"
          and set(input_data) == {"type", "check_id"}):
        repository = os.getenv("AAO_SELF_DEV_REPOSITORY")
        if not repository:
            raise ExecutionConflict("Self-development candidate repository is not configured")
        try:
            result = run_repository_check(repository, input_data["check_id"])
        except RepositoryCheckError as exc:
            result = {"kind": "aao.repository-check.v1", "check_id": input_data["check_id"],
                      "conclusion": "blocked", "error": str(exc)}
    else:
        raise ExecutionConflict("Execution type is not supported")
    complete(execution_id, lease["token"], worker_id, result, agent_credential=agent_credential)
    return {"status": "SUCCEEDED", "execution_id": execution_id, "result": result}
