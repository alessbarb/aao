"""Fail-closed contracts for SHA-bound auditor decisions."""

import pytest
from pydantic import ValidationError

from aao.review import evaluate_review
from aao.work_management_api import ReviewRequest


def test_review_requires_full_candidate_sha_and_content_addressed_evidence():
    with pytest.raises(ValidationError):
        ReviewRequest(decision="REJECT", evidence=["sha256:" + "a" * 64])
    with pytest.raises(ValidationError):
        ReviewRequest(decision="REJECT", candidate_sha="a" * 7,
                      evidence=["sha256:" + "a" * 64])
    request = ReviewRequest(decision="REJECT", candidate_sha="a" * 40,
                            evidence=["sha256:" + "a" * 64])
    assert request.candidate_sha == "a" * 40


def test_veto_is_recordable_but_does_not_authorize_approval():
    veto = evaluate_review(author_id="agent", reviewer_id="auditor",
                           evidence=["sha256:" + "a" * 64], decision="VETO",
                           project_active=True)
    approval = evaluate_review(author_id="agent", reviewer_id="auditor",
                               evidence=["sha256:" + "a" * 64], decision="APPROVE",
                               project_active=True)
    assert veto.allowed
    assert not approval.allowed


def test_reviewer_cannot_veto_own_work_or_inactive_project():
    assert not evaluate_review(author_id="same", reviewer_id="same",
                               evidence=["sha256:" + "a" * 64], decision="VETO",
                               project_active=True).allowed
    assert not evaluate_review(author_id="agent", reviewer_id="auditor",
                               evidence=["sha256:" + "a" * 64], decision="VETO",
                               project_active=False).allowed
