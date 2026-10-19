"""PostgreSQL integration tests, opt-in for explicitly disposable databases."""
import os
from datetime import UTC
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


@pytest.mark.skipif(
    not os.getenv("AAO_TEST_POSTGRES_URL") or os.getenv("AAO_TEST_DB_DISPOSABLE") != "yes",
    reason="Explicit disposable PostgreSQL database required",
)
def test_reconciliation_requires_distinct_granted_reviewer(monkeypatch):
    from datetime import datetime, timedelta

    from aao.execution_queue import claim, quarantine_expired, state
    from aao.execution_reconciliation import ReconciliationDenied, reconcile
    from aao.postgresql_connection import connect_postgres
    from aao.work_management_api import app

    monkeypatch.setenv("AAO_POSTGRES_URL", os.environ["AAO_TEST_POSTGRES_URL"])
    monkeypatch.setenv("AAO_CEO_TOKEN", "reconcile-ceo")
    monkeypatch.setenv("AAO_WORK_TOKEN", "reconcile-worker")
    monkeypatch.setenv("AAO_SANDBOX_QUEUE_ENABLED", "true")
    ceo = {"X-CEO-Token": "reconcile-ceo"}
    worker = {"X-Work-Token": "reconcile-worker"}
    worker_id = "worker-" + str(uuid4())
    auditor_id = "audit-" + str(uuid4())
    with TestClient(app) as client:
        issued = client.post("/v1/principals/credentials", headers=ceo, json={
            "principal_id": worker_id, "kind": "AGENT",
        })
        assert issued.status_code == 201, issued.text
        secret = issued.json()["token"]
        mid = client.post("/v1/mandates", headers=ceo, json={
            "title": "Recovery " + str(uuid4()), "objective": "Development only"
        }).json()["id"]
        client.post(f"/v1/mandates/{mid}/confirm", headers=ceo)
        project = client.post("/v1/projects", headers=ceo, json={
            "name": "Recovery project", "mandate_id": mid
        }).json()["id"]
        for principal_id, capability in (
            ("development-worker", "work.create"),
            ("development-worker", "work.admit"),
            (worker_id, "execution.claim"),
        ):
            client.post(f"/v1/projects/{project}/grants", headers=ceo, json={
                "principal_id": principal_id, "capability": capability
            })
        wid = client.post(f"/v1/projects/{project}/work", headers=worker, json={
            "title": "Inert recovery", "author_id": "development-worker",
            "acceptance_criteria": ["Recorded"]
        }).json()["id"]
        client.post(f"/v1/work/{wid}/admit", headers=worker)
        eid = client.post(f"/v1/work/{wid}/stage-inert", headers=worker).json()["execution_id"]
    base = datetime.now(UTC)
    lease = claim(worker_id, agent_credential=secret, project_id=project, now=base, seconds=1)
    assert lease["execution_id"] == eid
    # Quarantine is global: previous tests may leave other expired leases.
    assert quarantine_expired(now=base + timedelta(seconds=2)) >= 1
    assert state(eid)["status"] == "UNCERTAIN"
    # Re-running quarantine must not alter this execution again.
    assert state(eid)["attempts"] == 1
    with pytest.raises(ReconciliationDenied):
        reconcile(eid, reviewer_id=auditor_id, evidence=["operator checked"],
                  disposition="RETRY_CONFIRMED_SAFE")
    with connect_postgres() as db:
        db.execute(
            "INSERT INTO project_grants(principal_id,project_id,capability) "
            "VALUES (%s,%s,'execution.reconcile')",
            (auditor_id, project),
        )
    with pytest.raises(ReconciliationDenied):
        reconcile(eid, reviewer_id=worker_id, evidence=["operator checked"],
                  disposition="RETRY_CONFIRMED_SAFE")
    assert reconcile(eid, reviewer_id=auditor_id, evidence=["inert-only confirmed"],
                     disposition="RETRY_CONFIRMED_SAFE") == "QUEUED"
    with TestClient(app) as client:
        assert client.post(f"/v1/principals/{worker_id}/revoke", headers=ceo).status_code == 200
    from aao.execution_queue import ExecutionConflict
    with pytest.raises(ExecutionConflict):
        claim(worker_id, agent_credential=secret, project_id=project)
