"""Standalone authenticated worker verifier; no tools are accessible here."""
import hashlib
import hmac
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Worker:
    id: str


def credential_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def verify_registered_worker(worker_id: str, token: str | None, *, digest: str,
                             enabled: bool) -> Worker | None:
    if not worker_id or not token or not enabled:
        return None
    if not hmac.compare_digest(credential_digest(token), digest):
        return None
    return Worker(worker_id)


def dev_worker_bootstrap() -> tuple[str, str] | None:
    """Explicit opt-in only. Unset credentials always fail closed."""
    if os.getenv("AAO_DEV_WORKER_AUTH") != "true":
        return None
    worker_id = os.getenv("AAO_DEV_WORKER_ID")
    token = os.getenv("AAO_DEV_WORKER_TOKEN")
    if not worker_id or not token:
        return None
    return worker_id, credential_digest(token)
