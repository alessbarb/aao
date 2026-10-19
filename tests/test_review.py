from aao.review import evaluate_review


def test_review_policy_fails_closed_for_approval():
    common = {"author_id": "author-1", "reviewer_id": "auditor-1",
              "evidence": ["sha256:example"], "decision": "APPROVE", "project_active": True}
    approval = evaluate_review(**common)
    assert not approval.allowed
    assert "verification" in approval.reason.lower()
    assert evaluate_review(**{**common, "decision": "REJECT"}).allowed
    assert not evaluate_review(**{**common, "reviewer_id": "author-1"}).allowed
    assert not evaluate_review(**{**common, "evidence": []}).allowed
    assert not evaluate_review(**{**common, "project_active": False}).allowed
    assert not evaluate_review(**{**common, "decision": "UNKNOWN"}).allowed
