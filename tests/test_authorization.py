from datetime import UTC, datetime, timedelta

from aao.authorization import Grant, Principal, has_capability, may_review


def test_grants_are_project_specific_and_expire():
    now = datetime(2026, 10, 18, tzinfo=UTC)
    worker = Principal(id="a", kind="AGENT")
    grant = Grant(principal_id="a", project_id="p1", capability="work.create",
                  expires_at=now + timedelta(minutes=1))
    assert has_capability(worker, "p1", "work.create", [grant], now=now)
    assert not has_capability(worker, "p2", "work.create", [grant], now=now)
    assert not has_capability(worker, "p1", "work.review", [grant], now=now)
    assert not has_capability(worker, "p1", "work.create", [grant],
                              now=now + timedelta(minutes=2))
    assert not has_capability(Principal(id="a", kind="AGENT", active=False),
                              "p1", "work.create", [grant], now=now)


def test_reviewer_needs_distinct_identity_role_and_grant():
    author = Principal("author", "AGENT")
    reviewer = Principal("auditor", "AUDITOR")
    grant = Grant("auditor", "p1", "work.review")
    assert may_review(author, reviewer, "p1", [grant])
    assert not may_review(author, reviewer, "p2", [grant])
    assert not may_review(author, author, "p1", [Grant("author", "p1", "work.review")])
    assert not may_review(author, Principal("auditor", "AGENT"), "p1", [grant])
