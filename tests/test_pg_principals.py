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
