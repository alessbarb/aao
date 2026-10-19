"""Deterministic work admission; does not execute agents or tools."""
from dataclasses import dataclass
from enum import StrEnum


class Admission(StrEnum):
    READY = "READY"
    DEFER = "DEFER"
    DENY = "DENY"


@dataclass(frozen=True)
class AdmissionDecision:
    status: Admission
    reason: str


def decide_admission(*, project_active: bool, mandate_confirmed: bool,
                     authorized: bool, dependencies_satisfied: bool,
                     capacity_available: bool, within_budget: bool,
                     residual_risk: str, emergency_stop: bool) -> AdmissionDecision:
    if emergency_stop:
        return AdmissionDecision(Admission.DENY, "Emergency stop active")
    if not authorized or not mandate_confirmed:
        return AdmissionDecision(Admission.DENY, "No authorized mandate or grant")
    if not project_active:
        return AdmissionDecision(Admission.DEFER, "Project inactive")
    if residual_risk in {"high", "critical"}:
        return AdmissionDecision(Admission.DEFER, "CEO review required")
    if residual_risk not in {"low", "moderate"}:
        return AdmissionDecision(Admission.DENY, "Unknown risk classification")
    if not dependencies_satisfied:
        return AdmissionDecision(Admission.DEFER, "Dependencies unresolved")
    if not capacity_available or not within_budget:
        return AdmissionDecision(Admission.DEFER, "Insufficient approved resources")
    return AdmissionDecision(Admission.READY, "All admission gates satisfied")
