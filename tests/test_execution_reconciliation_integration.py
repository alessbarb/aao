"""PostgreSQL integration tests, opt-in for explicitly disposable databases."""
import os
import time
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


@pytest.mark.skipif(
    not os.getenv("AAO_TEST_POSTGRES_URL") or os.getenv("AAO_TEST_DB_DISPOSABLE") != "yes",
    reason="Explicit disposable PostgreSQL database required",
)
def test_reconciliation_requires_distinct_granted_reviewer(monkeypatch):
    from aao.execution_queue import claim, quarantine_expired, state
    from aao.execution_reconciliation import ReconciliationDenied, reconcile
    from aao.work_management_api import app

    monkeypatch.setenv("AAO_POSTGRES_URL", os.environ["AAO_TEST_POSTGRES_URL"])
    monkeypatch.setenv("AAO_CEO_TOKEN", "reconcile-ceo")
    monkeypatch.setenv("AAO_SANDBOX_QUEUE_ENABLED", "true")
    ceo = {"X-CEO-Token": "reconcile-ceo"}
    worker_id = "worker-" + str(uuid4())
    auditor_id = "audit-" + str(uuid4())
    with TestClient(app) as client:
        issued = client.post("/v1/principals/credentials", headers=ceo, json={
            "principal_id": worker_id, "kind": "AGENT",
        })
        assert issued.status_code == 201, issued.text
        secret = issued.json()["token"]
        worker = {"X-Agent-Token": secret}
        auditor_issued = client.post("/v1/principals/credentials", headers=ceo, json={
            "principal_id": auditor_id, "kind": "AUDITOR",
        })
        assert auditor_issued.status_code == 201, auditor_issued.text
        auditor_secret = auditor_issued.json()["token"]
        mid = client.post("/v1/mandates", headers=ceo, json={
            "title": "Recovery " + str(uuid4()), "objective": "Development only"
        }).json()["id"]
        client.post(f"/v1/mandates/{mid}/confirm", headers=ceo)
        project = client.post("/v1/projects", headers=ceo, json={
            "name": "Recovery project", "mandate_id": mid
        }).json()["id"]
        for principal_id, capability in (
            (worker_id, "work.create"),
            (worker_id, "work.admit"),
            (worker_id, "execution.claim"),
        ):
            client.post(f"/v1/projects/{project}/grants", headers=ceo, json={
                "principal_id": principal_id, "capability": capability
            })
        wid = client.post(f"/v1/projects/{project}/work", headers=worker, json={
            "title": "Inert recovery", "author_id": worker_id,
            "acceptance_criteria": ["Recorded"]
        }).json()["id"]
        client.post(f"/v1/work/{wid}/admit", headers=worker)
        eid = client.post(f"/v1/work/{wid}/stage-inert", headers=worker).json()["execution_id"]
    lease = claim(worker_id, agent_credential=secret, project_id=project, seconds=1)
    assert lease["execution_id"] == eid
    # Quarantine is global: previous tests may leave other expired leases.
    time.sleep(1.1)
    assert quarantine_expired() >= 1
    assert state(eid)["status"] == "UNCERTAIN"
    # Re-running quarantine must not alter this execution again.
    assert state(eid)["attempts"] == 1
    with pytest.raises(ReconciliationDenied):
        reconcile(eid, auditor_credential=auditor_secret, evidence=["operator checked"],
                  disposition="RETRY_CONFIRMED_SAFE")
    with TestClient(app) as client:
        granted = client.post(f"/v1/projects/{project}/grants", headers=ceo, json={
            "principal_id": auditor_id, "capability": "execution.reconcile",
        })
        assert granted.status_code == 201, granted.text
    with pytest.raises(ReconciliationDenied):
        reconcile(eid, auditor_credential=secret, evidence=["agent cannot review"],
                  disposition="RETRY_CONFIRMED_SAFE")
    assert reconcile(eid, auditor_credential=auditor_secret,
                     evidence=["inert-only confirmed"],
                     disposition="RETRY_CONFIRMED_SAFE") == "QUEUED"
    from aao.external_effect_reconciliation import EffectReviewDenied, reject_unexecuted_proposal
    from aao.external_effect_registry import EffectConflict, propose
    with pytest.raises(EffectConflict, match="running execution"):
        propose(
            execution_id=eid, idempotency_key="queued-" + str(uuid4()),
            capability="test.inert", request={"kind": "test-only"},
        )
    lease = claim(worker_id, agent_credential=secret, project_id=project)
    assert lease["execution_id"] == eid
    proposal = propose(
        execution_id=eid, idempotency_key="reconcile-" + str(uuid4()),
        capability="test.inert", request={"kind": "test-only"},
    )
    with pytest.raises(EffectReviewDenied):
        reject_unexecuted_proposal(
            proposal["id"], auditor_credential=secret, evidence=["agent denied"]
        )
    with TestClient(app) as client:
        granted = client.post(f"/v1/projects/{project}/grants", headers=ceo, json={
            "principal_id": auditor_id, "capability": "effect.reconcile",
        })
        assert granted.status_code == 201, granted.text
    assert reject_unexecuted_proposal(
        proposal["id"], auditor_credential=auditor_secret,
        evidence=["proposal not executed"],
    ) == "REJECTED"
    with TestClient(app) as client:
        assert client.post(f"/v1/principals/{worker_id}/revoke", headers=ceo).status_code == 200
    from aao.execution_queue import ExecutionConflict
    with pytest.raises(ExecutionConflict):
        claim(worker_id, agent_credential=secret, project_id=project)
