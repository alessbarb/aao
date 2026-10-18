from aao.review import evaluate_review


def test_independence_gate():
    common = dict(author_id="author-1", reviewer_id="auditor-1",
                  evidence=["sha256:example"], decision="APPROVE", project_active=True)
    assert evaluate_review(**common).allowed
    assert not evaluate_review(**{**common, "reviewer_id": "author-1"}).allowed
    assert not evaluate_review(**{**common, "evidence": []}).allowed
    assert not evaluate_review(**{**common, "project_active": False}).allowed
    assert not evaluate_review(**{**common, "decision": "UNKNOWN"}).allowed
