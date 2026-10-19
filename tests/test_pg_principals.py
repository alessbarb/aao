import pytest
from aao.pg_principals import PrincipalDenied, digest_token, authenticate


def test_credential_digest_is_stable_and_not_plaintext():
    assert digest_token("secret") == digest_token("secret")
    assert digest_token("secret") != "secret"


@pytest.mark.parametrize("value,kind", [(None, "AUDITOR"), ("", "AGENT"), ("key", "CEO")])
def test_unauthorized_inputs_rejected_without_database(value, kind):
    with pytest.raises(PrincipalDenied):
        authenticate(value, kind=kind)


def test_grant_contract_accepts_execution_claim_only_as_exact_capability():
    from pydantic import ValidationError
    from aao.pg_work import GrantRequest

    grant = GrantRequest(principal_id="agent-1", capability="execution.claim")
    assert grant.capability == "execution.claim"
    for invalid in ("execution.claim.other", "execution.reconcile", "work.create.extra"):
        with pytest.raises(ValidationError):
            GrantRequest(principal_id="agent-1", capability=invalid)


def test_shared_development_credentials_can_be_disabled(monkeypatch):
    from fastapi import HTTPException
    from aao.pg_work import require_worker, require_reviewer, read_principal

    monkeypatch.setenv("AAO_ENV", "production")
    monkeypatch.setenv("AAO_WORK_TOKEN", "dev-worker")
    monkeypatch.setenv("AAO_REVIEW_TOKEN", "dev-auditor")
    for call in (
        lambda: require_worker(x_work_token="dev-worker", x_agent_token=None),
        lambda: require_reviewer(x_review_token="dev-auditor", x_auditor_token=None),
        lambda: read_principal(x_ceo_token=None, x_work_token="dev-worker", x_agent_token=None),
    ):
        with pytest.raises(HTTPException) as denied:
            call()
        assert denied.value.status_code == 403


def test_shared_development_credentials_require_opt_in(monkeypatch):
    from fastapi import HTTPException
    from aao.pg_work import require_worker, require_reviewer, shared_dev_tokens_enabled

    monkeypatch.setenv("AAO_ENV", "development")
    monkeypatch.setenv("AAO_ALLOW_SHARED_DEV_TOKENS", "false")
    monkeypatch.setenv("AAO_WORK_TOKEN", "dev-worker")
    monkeypatch.setenv("AAO_REVIEW_TOKEN", "dev-auditor")
    assert not shared_dev_tokens_enabled()
    with pytest.raises(HTTPException):
        require_worker(x_work_token="dev-worker", x_agent_token=None)
    with pytest.raises(HTTPException):
        require_reviewer(x_review_token="dev-auditor", x_auditor_token=None)


def test_individual_reader_cannot_fall_back_to_shared_credential(monkeypatch):
    from fastapi import HTTPException
    from aao.pg_work import read_principal

    monkeypatch.setenv("AAO_ENV", "development")
    monkeypatch.setenv("AAO_ALLOW_SHARED_DEV_TOKENS", "true")
    monkeypatch.setenv("AAO_WORK_TOKEN", "dev-worker")
    with pytest.raises(HTTPException) as denied:
        read_principal(
            x_ceo_token=None, x_work_token="dev-worker",
            x_agent_token="invalid-individual-token",
        )
    assert denied.value.status_code == 403
