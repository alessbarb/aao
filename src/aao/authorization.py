"""Pure, fail-closed project capability decisions.

Authentication must derive principal identity from a trusted verifier, never
from user-supplied headers or agent-generated text.
"""
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class Principal:
    id: str
    kind: str
    active: bool = True


@dataclass(frozen=True)
class Grant:
    principal_id: str
    project_id: str
    capability: str
    expires_at: datetime | None = None


def has_capability(principal: Principal, project_id: str,
                   capability: str, grants: list[Grant],
                   *, now: datetime | None = None) -> bool:
    if not principal.active or not project_id or not capability:
        return False
    at = now or datetime.now(timezone.utc)
    if at.tzinfo is None:
        raise ValueError("Authorization time must be timezone-aware")
    for grant in grants:
        if (grant.principal_id != principal.id
                or grant.project_id != project_id
                or grant.capability != capability):
            continue
        if grant.expires_at is None:
            return True
        if grant.expires_at.tzinfo is None:
            continue
        if grant.expires_at > at:
            return True
    return False


def may_review(author: Principal, reviewer: Principal, project_id: str,
               grants: list[Grant]) -> bool:
    return bool(
        reviewer.kind == "AUDITOR"
        and author.id != reviewer.id
        and has_capability(reviewer, project_id, "work.review", grants)
    )
