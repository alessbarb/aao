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
    from aao.legacy_worker_authentication import credential_digest
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
    secret = "token-" + str(uuid4())
    with connect_postgres() as db:
        db.execute(
            "INSERT INTO worker_registrations(worker_id,token_digest,enabled) VALUES (%s,%s,true)",
            (worker_id, credential_digest(secret)),
        )
    with TestClient(app) as client:
        mid = client.post("/v1/mandates", headers=ceo, json={
            "title": "Recovery " + str(uuid4()), "objective": "Development only"
        }).json()["id"]
        client.post(f"/v1/mandates/{mid}/confirm", headers=ceo)
        project = client.post("/v1/projects", headers=ceo, json={
            "name": "Recovery project", "mandate_id": mid
        }).json()["id"]
        for capability in ("work.create", "work.admit"):
            client.post(f"/v1/projects/{project}/grants", headers=ceo, json={
                "principal_id": "development-worker", "capability": capability
            })
        wid = client.post(f"/v1/projects/{project}/work", headers=worker, json={
            "title": "Inert recovery", "author_id": "development-worker",
            "acceptance_criteria": ["Recorded"]
        }).json()["id"]
        client.post(f"/v1/work/{wid}/admit", headers=worker)
        eid = client.post(f"/v1/work/{wid}/stage-inert", headers=worker).json()["execution_id"]
    base = datetime.now(UTC)
    with connect_postgres() as db:
        db.execute("INSERT INTO project_grants(principal_id,project_id,capability) VALUES (%s,%s,'execution.claim')", (worker_id, project))
    lease = claim(worker_id, credential=secret, project_id=project, now=base, seconds=1)
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
    with connect_postgres() as db:
        db.execute("UPDATE worker_registrations SET enabled=false WHERE worker_id=%s",
                   (worker_id,))
    from aao.execution_queue import ExecutionConflict
    with pytest.raises(ExecutionConflict):
        claim(worker_id, credential=secret, project_id=project)
