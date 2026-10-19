import pytest

from aao.external_effect_reconciliation import EffectReviewDenied, reject_unexecuted_proposal


def test_rejection_fails_closed_without_evidence():
    with pytest.raises(EffectReviewDenied):
        reject_unexecuted_proposal("example", reviewer_id="auditor", evidence=[])
    with pytest.raises(EffectReviewDenied):
        reject_unexecuted_proposal("example", reviewer_id="", evidence=["proof"])
