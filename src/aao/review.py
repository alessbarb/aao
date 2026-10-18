"""Independent evidence review, development-only implementation."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewDecision:
    allowed: bool
    reason: str


def evaluate_review(*, author_id: str, reviewer_id: str, evidence: list[str],
                    decision: str, project_active: bool) -> ReviewDecision:
    if not project_active:
        return ReviewDecision(False, "Project is not active")
    if not author_id or not reviewer_id or author_id == reviewer_id:
        return ReviewDecision(False, "Independent reviewer is required")
    if not evidence or not all(item.strip() for item in evidence):
        return ReviewDecision(False, "Evidence references required")
    if decision not in {"APPROVE", "REJECT"}:
        return ReviewDecision(False, "Unknown review decision")
    return ReviewDecision(True, "Independent review recorded")
