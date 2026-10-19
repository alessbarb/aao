import pytest

from aao.principal_credentials import PrincipalDenied, authenticate, digest_token


def test_credential_digest_is_stable_and_not_plaintext():
    assert digest_token("secret") == digest_token("secret")
    assert digest_token("secret") != "secret"


@pytest.mark.parametrize("value,kind", [(None, "AUDITOR"), ("", "AGENT"), ("key", "CEO")])
def test_unauthorized_inputs_rejected_without_database(value, kind):
    with pytest.raises(PrincipalDenied):
        authenticate(value, kind=kind)


def test_grant_contract_accepts_execution_capabilities_only_as_exact_values():
    from pydantic import ValidationError

    from aao.work_management_api import GrantRequest

    grant = GrantRequest(principal_id="agent-1", capability="execution.claim")
    assert grant.capability == "execution.claim"
    assert GrantRequest(
        principal_id="auditor-1", capability="execution.reconcile"
    ).capability == "execution.reconcile"
    assert GrantRequest(
        principal_id="auditor-1", capability="effect.reconcile"
    ).capability == "effect.reconcile"
    for invalid in (
        "execution.claim.other", "execution.reconcile.extra",
        "effect.reconcile.extra", "work.create.extra",
    ):
        with pytest.raises(ValidationError):
            GrantRequest(principal_id="agent-1", capability=invalid)


def test_shared_development_headers_are_not_accepted(monkeypatch):
    from fastapi import HTTPException

    from aao.work_management_api import read_principal, require_reviewer, require_worker

    monkeypatch.setenv("AAO_WORK_TOKEN", "dev-worker")
    monkeypatch.setenv("AAO_REVIEW_TOKEN", "dev-auditor")
    for call in (
        lambda: require_worker(x_agent_token=None),
        lambda: require_reviewer(x_auditor_token=None),
        lambda: read_principal(x_ceo_token=None, x_agent_token=None),
    ):
        with pytest.raises(HTTPException) as denied:
            call()
        assert denied.value.status_code == 403


def test_individual_reader_cannot_fall_back_to_shared_credential(monkeypatch):
    from fastapi import HTTPException

    from aao.work_management_api import read_principal

    monkeypatch.setenv("AAO_ENV", "development")
    monkeypatch.setattr("aao.principal_credentials.authenticate", lambda *_args, **_kwargs: (_ for _ in ()).throw(PrincipalDenied("invalid")))
    with pytest.raises(HTTPException) as denied:
        read_principal(x_ceo_token=None, x_agent_token="invalid-individual-token")
    assert denied.value.status_code == 403


class _GrantQuery:
    def __init__(self, principal_row):
        self.principal_row = principal_row
        self.queries = []

    def execute(self, sql, args):
        self.queries.append((sql, args))
        return self

    def fetchone(self):
        sql, _args = self.queries[-1]
        if "FROM principal_credentials" in sql:
            return self.principal_row
        return (1,)


def test_grant_rechecks_principal_inside_transaction(monkeypatch):
    from fastapi import HTTPException

    from aao.work_management_api import require_grant

    for record in (None, ("AGENT", False), ("AUDITOR", True)):
        db = _GrantQuery(record)
        with pytest.raises(HTTPException) as exc:
            require_grant(db, "agent-1", "project-1", "work.create")
        assert exc.value.status_code == 403
        assert len(db.queries) == 1
        assert "FOR SHARE" in db.queries[0][0]

    active = _GrantQuery(("AGENT", True))
    require_grant(active, "agent-1", "project-1", "work.create")
    assert len(active.queries) == 2
    assert active.queries[1][1] == ("agent-1", "project-1", "work.create")


def test_reviewer_grant_requires_individual_auditor_kind():
    from fastapi import HTTPException

    from aao.work_management_api import require_grant

    with pytest.raises(HTTPException) as exc:
        require_grant(_GrantQuery(("AGENT", True)), "agent-1", "project-1", "work.review")
    assert exc.value.status_code == 403
    db = _GrantQuery(("AUDITOR", True))
    require_grant(db, "auditor-1", "project-1", "work.review")
    assert len(db.queries) == 2


def test_legacy_shared_principal_has_no_grant_authority(monkeypatch):
    from fastapi import HTTPException

    from aao.work_management_api import require_grant

    with pytest.raises(HTTPException) as exc:
        require_grant(_GrantQuery(None), "development-worker", "project-1", "work.create")
    assert exc.value.status_code == 403


def test_project_listing_rechecks_active_reader_in_transaction(monkeypatch):
    from contextlib import contextmanager

    from fastapi import HTTPException

    from aao import work_management_api

    class ReaderDb:
        def __init__(self, row):
            self.row = row
            self.queries = []

        def execute(self, query, args=None):
            self.queries.append((query, args))
            return self

        def fetchone(self):
            return self.row

        def fetchall(self):
            return []

    def transaction_for(selected_db):
        @contextmanager
        def fake_tx():
            yield selected_db

        return fake_tx

    for record in (None, ("AGENT", False), ("AUDITOR", True)):
        db = ReaderDb(record)
        monkeypatch.setattr(work_management_api, "tx", transaction_for(db))
        with pytest.raises(HTTPException) as denied:
            work_management_api.projects(principal="agent-1")
        assert denied.value.status_code == 403
        assert len(db.queries) == 1
        assert "FOR SHARE" in db.queries[0][0]

    active = ReaderDb(("AGENT", True))

    @contextmanager
    def active_tx():
        yield active

    monkeypatch.setattr(work_management_api, "tx", active_tx)
    assert work_management_api.projects(principal="agent-1") == []
    assert len(active.queries) == 2
    assert active.queries[1][1] == ("agent-1",)


@pytest.mark.parametrize("environment", ["production", " PRODUCTION ", "prodution"])
def test_static_ceo_bearer_is_unavailable_outside_development(monkeypatch, environment):
    from fastapi import HTTPException
    from fastapi.testclient import TestClient

    from aao.work_management_api import app, read_principal, require_ceo

    monkeypatch.setenv("AAO_ENV", environment)
    monkeypatch.setenv("AAO_CEO_TOKEN", "development-ceo-token")
    with pytest.raises(HTTPException) as direct:
        require_ceo(x_ceo_token="development-ceo-token")
    assert direct.value.status_code == 503

    with pytest.raises(HTTPException) as reader:
        read_principal(
            x_ceo_token="development-ceo-token", x_agent_token=None,
        )
    assert reader.value.status_code == 403

    with TestClient(app) as client:
        response = client.post(
            "/v1/mandates",
            headers={"X-CEO-Token": "development-ceo-token"},
            json={"title": "Must be denied", "objective": "Test only"},
        )
    assert response.status_code == 503
    with TestClient(app) as client:
        response = client.get(
            "/v1/projects", headers={"X-CEO-Token": "development-ceo-token"},
        )
    assert response.status_code == 403
