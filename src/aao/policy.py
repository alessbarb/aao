"""Constitutional authorization is deterministic and independent of LLM output."""
from dataclasses import dataclass
from enum import StrEnum


class Verdict(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRES_CEO = "REQUIRES_CEO"


RESERVED = frozenset({
    "project.create", "project.cancel", "project.mission.change",
    "organization.mission.change", "constitution.change", "authority.expand",
    "budget.exceed", "capacity.permanent_reduce",
    "risk.high.accept", "strategic.irreversible",
    "kernel.change", "autonomy.ceiling.raise", "production.first_enable",
})
FORBIDDEN = frozenset({"audit.evidence.forge", "security.bypass", "ceo.impersonate"})


@dataclass(frozen=True)
class Decision:
    verdict: Verdict
    reason: str


def authorize(operation: str, *, is_ceo: bool, confirmed_mandate: bool,
              residual_risk: str = "low", permitted: bool = False) -> Decision:
    if operation in FORBIDDEN:
        return Decision(Verdict.DENY, "Constitutionally forbidden operation")
    if operation in RESERVED or residual_risk in {"high", "critical"}:
        if not is_ceo or not confirmed_mandate:
            return Decision(Verdict.REQUIRES_CEO, "Reserved authority or high residual risk")
        return Decision(Verdict.ALLOW, "Confirmed CEO mandate")
    if not permitted:
        return Decision(Verdict.DENY, "No active delegated grant")
    return Decision(Verdict.ALLOW, "Within delegated authority")
