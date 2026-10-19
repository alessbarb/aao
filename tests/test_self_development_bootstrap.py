from scripts import bootstrap_self_dev_agent as bootstrap


def mandate_record(*, project=None, include_project_event=False):
    mandate_id = "mandate-1"
    events = [
        {"id": "event-draft", "subject_id": mandate_id, "kind": "mandate.drafted"},
        {"id": "event-confirmed", "subject_id": mandate_id, "kind": "mandate.confirmed"},
    ]
    if include_project_event:
        events.append({"id": "event-project", "subject_id": "project-1",
                       "kind": "project.created"})
    return {
        "id": mandate_id,
        "title": bootstrap.MANDATE_TITLE,
        "objective": bootstrap.MANDATE_OBJECTIVE,
        "status": "CONFIRMED",
        "project": project,
        "events": events,
    }


def test_bootstrap_registers_and_confirms_mandate_and_project_idempotently(monkeypatch):
    project = {"id": "project-1", "name": bootstrap.PROJECT_NAME, "state": "ACTIVE"}
    record = mandate_record(project=project, include_project_event=True)
    calls = []
    inventories = iter(([], [mandate_record()], [record]))

    def fake_request(_base_url, path, *, method="GET", ceo_token=None, body=None, **_):
        calls.append((method, path, body))
        assert ceo_token == "local-ceo-secret"
        if method == "GET":
            return next(inventories)
        if path == "/v1/mandates":
            return {"id": "mandate-1", "status": "DRAFT"}
        if path == "/v1/mandates/mandate-1/confirm":
            return {"id": "mandate-1", "status": "CONFIRMED"}
        if path == "/v1/projects":
            return {"id": "project-1", "state": "ACTIVE"}
        raise AssertionError(f"Unexpected bootstrap request: {method} {path}")

    monkeypatch.setattr(bootstrap, "request_json", fake_request)
    mandate, actual_project = bootstrap.ensure_mandated_project(
        "http://127.0.0.1:8001", "local-ceo-secret",
    )
    assert mandate["id"] == "mandate-1"
    assert actual_project == project
    assert [call[1] for call in calls if call[0] == "POST"] == [
        "/v1/mandates", "/v1/mandates/mandate-1/confirm", "/v1/projects",
    ]


def test_bootstrap_reuses_verified_existing_project_without_writes(monkeypatch):
    project = {"id": "project-1", "name": bootstrap.PROJECT_NAME, "state": "ACTIVE"}
    record = mandate_record(project=project, include_project_event=True)
    calls = []

    def fake_request(_base_url, path, *, method="GET", ceo_token=None, **_):
        calls.append((method, path))
        assert path == "/v1/mandates"
        return [record]

    monkeypatch.setattr(bootstrap, "request_json", fake_request)
    mandate, actual_project = bootstrap.ensure_mandated_project(
        "http://127.0.0.1:8001", "local-ceo-secret",
    )
    assert mandate["id"] == "mandate-1"
    assert actual_project == project
    assert calls == [("GET", "/v1/mandates"), ("GET", "/v1/mandates")]
