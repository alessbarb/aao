from aao.identity import project_granted, verify_service_token


def test_token_maps_to_configured_identity(monkeypatch):
    monkeypatch.setenv("AAO_CEO_TOKEN", "ceo-only")
    monkeypatch.setenv("AAO_WORK_TOKEN", "worker-only")
    monkeypatch.setenv("AAO_REVIEW_TOKEN", "auditor-only")
    assert verify_service_token("ceo-only").kind == "CEO"
    assert verify_service_token("worker-only").principal_id == "development-worker"
    assert verify_service_token("auditor-only").kind == "AUDITOR"
    assert verify_service_token("wrong") is None
    assert verify_service_token(None) is None


def test_project_grants_are_explicit():
    grants = {("worker-a", "project-1", "work.create")}
    assert project_granted("worker-a", "project-1", "work.create", grants)
    assert not project_granted("worker-a", "project-2", "work.create", grants)
    assert not project_granted("worker-a", "project-1", "work.review", grants)
