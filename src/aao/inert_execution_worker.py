"""One-shot worker for inert markers and one fixed sandboxed repo check."""
import os
from datetime import UTC, datetime

from aao.execution_queue import ExecutionConflict, claim, complete, state


def run_one(worker_id: str, agent_credential: str, *, project_id: str, seconds: int = 30) -> dict:
    lease = claim(worker_id, agent_credential=agent_credential, project_id=project_id, seconds=seconds)
    if lease is None:
        return {"status": "IDLE"}
    execution_id = lease["execution_id"]
    info = state(execution_id)
    if not info or info["status"] != "RUNNING":
        return {"status": "UNCERTAIN", "execution_id": execution_id}
    selected = lease.get("input")
    if isinstance(selected, dict) and selected.get("type") == "aao.repository-check.v1":
        if set(selected) != {"type", "check_id", "capability_id", "version"}:
            raise ExecutionConflict("Malformed registered capability selection")
        repository = os.getenv("AAO_SELF_DEV_REPOSITORY")
        if not repository:
            result = {
                "kind": "aao.repository-check.v1", "check_id": selected["check_id"],
                "capability_id": selected["capability_id"],
                "capability_version": selected["version"],
                "conclusion": "failure", "error": "repository path not configured",
            }
        else:
            from aao.sandboxed_repository_checks import (
                RepositoryCheckError,
                run_repository_check,
            )

            try:
                result = run_repository_check(repository, selected["check_id"])
                result["capability_id"] = selected["capability_id"]
                result["capability_version"] = selected["version"]
            except RepositoryCheckError as exc:
                # Do not represent a blocked or unsafe launch as a successful check.
                result = {
                    "kind": "aao.repository-check.v1", "check_id": selected["check_id"],
                    "capability_id": selected["capability_id"],
                    "capability_version": selected["version"], "conclusion": "failure",
                    "error": str(exc)[:500],
                }
        complete(execution_id, lease["token"], worker_id, result,
                 agent_credential=agent_credential)
        status = "FAILED" if result.get("conclusion") == "failure" else "SUCCEEDED"
        return {"status": status, "execution_id": execution_id}

    # No arbitrary command, model prompt, or tool input is accepted.
    marker = {"kind": "aao.inert-worker.v1", "execution_id": execution_id,
              "recorded_at": datetime.now(UTC).isoformat()}
    complete(execution_id, lease["token"], worker_id, marker, agent_credential=agent_credential)
    return {"status": "SUCCEEDED", "execution_id": execution_id}
