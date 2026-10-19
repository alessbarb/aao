from urllib.error import HTTPError

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


def test_request_json_explains_stale_api_method_mismatch(monkeypatch):
    def stale_api(*_args, **_kwargs):
        raise HTTPError("http://127.0.0.1:8001/v1/mandates", 405,
                        "Method Not Allowed", {}, None)

    monkeypatch.setattr(bootstrap, "urlopen", stale_api)
    try:
        bootstrap.request_json("http://127.0.0.1:8001", "/v1/mandates")
    except bootstrap.BootstrapError as exc:
        assert "restart it from the current checkout" in str(exc)
    else:
        raise AssertionError("expected stale API method mismatch to fail closed")


def test_bootstrap_reuses_supplied_ceo_credential_without_prompt(monkeypatch, tmp_path):
    token_path = tmp_path / "agent.token"
    project = {"id": "project-1", "name": bootstrap.PROJECT_NAME, "state": "ACTIVE"}
    mandate = {"id": "mandate-1"}
    monkeypatch.setattr(bootstrap, "private_runtime_file", lambda: token_path)
    monkeypatch.setattr(bootstrap, "ensure_mandated_project", lambda *_: (mandate, project))
    monkeypatch.setattr(
        bootstrap.getpass, "getpass",
        lambda *_: (_ for _ in ()).throw(AssertionError("credential prompted twice")),
    )
    calls = []

    def fake_request(_base_url, path, *, method="GET", ceo_token=None,
                     agent_token=None, body=None):
        calls.append((method, path))
        if agent_token:
            assert ceo_token is None
        else:
            assert ceo_token == "hidden-ceo-token"
        if path.endswith("/grants") and method == "GET":
            return []
        if path == "/v1/principals/credentials":
            return {"principal_id": body["principal_id"], "token": "hidden-agent-token"}
        if path.endswith("/grants") and method == "POST":
            return {"created": True}
        if path == "/v1/projects" and agent_token:
            return [project]
        raise AssertionError(f"unexpected API call: {method} {path}")

    monkeypatch.setattr(bootstrap, "request_json", fake_request)
    monkeypatch.setattr(bootstrap, "write_private_token", lambda path, _token: path.touch())

    principal, mandate_id, project_id, expiry, result_path = bootstrap.bootstrap(
        "http://127.0.0.1:8001", ceo_token="hidden-ceo-token",
    )

    assert principal.startswith("aao-selfdev-")
    assert (mandate_id, project_id, result_path) == ("mandate-1", "project-1", token_path)
    assert expiry.tzinfo is not None
    assert [path for method, path in calls if method == "POST" and path.endswith("/grants")] == [
        "/v1/projects/project-1/grants"
    ] * len(bootstrap.GRANTS)
