"""Small deterministic comparison for capability planning, not execution authority."""

from collections.abc import Mapping

SCORE_DIMENSIONS = ("fit", "security", "cost", "time", "tokens", "maintenance")
CHOICE_ORDER = ("reuse", "adapt", "build")


def recommend(options: list[Mapping[str, int | str]]) -> tuple[str | None, dict[str, float]]:
    """Return a unique equal-weighted best option; ties deliberately yield no recommendation."""
    scores = {
        option["choice"]: round(
            sum(option[dimension] for dimension in SCORE_DIMENSIONS) / len(SCORE_DIMENSIONS),
            3,
        )
        for option in options
    }
    if not scores:
        return None, scores
    best = max(scores.values())
    winners = [choice for choice in CHOICE_ORDER if scores.get(choice) == best]
    return (winners[0] if len(winners) == 1 else None), scores
