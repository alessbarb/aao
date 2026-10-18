"""Development identity verification. Production requires OIDC/mTLS and revocation."""
import hashlib
import hmac
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Identity:
    principal_id: str
    kind: str


def verify_service_token(token: str | None) -> Identity | None:
    """Verify against individual configured tokens, never a caller-provided identity."""
    if not token:
        return None
    known = (
        ("AAO_CEO_TOKEN", "ceo", "CEO"),
        ("AAO_WORK_TOKEN", "development-worker", "SERVICE"),
        ("AAO_REVIEW_TOKEN", "development-auditor", "AUDITOR"),
    )
    digest = hashlib.sha256(token.encode()).digest()
    for key, principal_id, kind in known:
        configured = os.getenv(key)
        if configured and hmac.compare_digest(digest, hashlib.sha256(configured.encode()).digest()):
            return Identity(principal_id, kind)
    return None


def project_granted(principal_id: str, project_id: str, capability: str, grants: set[tuple[str, str, str]]) -> bool:
    return (principal_id, project_id, capability) in grants
