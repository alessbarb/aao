from aao.legacy_worker_authentication import (
    credential_digest,
    dev_worker_bootstrap,
    verify_registered_worker,
)


def test_worker_verifier_requires_exact_live_credential():
    digest = credential_digest("correct-token")
    assert verify_registered_worker("worker-1", "correct-token", digest=digest, enabled=True)
    assert verify_registered_worker("worker-1", "wrong", digest=digest, enabled=True) is None
    assert verify_registered_worker("worker-1", "correct-token", digest=digest, enabled=False) is None
    assert verify_registered_worker("", "correct-token", digest=digest, enabled=True) is None


def test_bootstrap_is_explicit_and_fail_closed(monkeypatch):
    monkeypatch.delenv("AAO_DEV_WORKER_AUTH", raising=False)
    monkeypatch.setenv("AAO_DEV_WORKER_ID", "worker-1")
    monkeypatch.setenv("AAO_DEV_WORKER_TOKEN", "token")
    assert dev_worker_bootstrap() is None
    monkeypatch.setenv("AAO_DEV_WORKER_AUTH", "true")
    assert dev_worker_bootstrap() == ("worker-1", credential_digest("token"))
