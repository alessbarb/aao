import pytest

from aao.execution_reconciliation import ReconciliationDenied, reconcile


@pytest.mark.parametrize("disposition", ["RETRY", "UNKNOWN", "", "APPROVE"])
def test_invalid_reconciliation_actions_fail_closed(disposition):
    with pytest.raises(ReconciliationDenied):
        reconcile("not-called", auditor_credential="test-token",
                  evidence=["reviewed"], disposition=disposition)


def test_evidence_is_mandatory():
    with pytest.raises(ReconciliationDenied):
        reconcile("not-called", auditor_credential="test-token",
                  evidence=[""], disposition="MARK_FAILED")
    with pytest.raises(ReconciliationDenied):
        reconcile("not-called", auditor_credential="",
                  evidence=["proof"], disposition="MARK_FAILED")
