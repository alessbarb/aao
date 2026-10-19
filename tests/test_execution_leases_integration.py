"""PostgreSQL integration tests, opt-in for explicitly disposable databases."""
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


@pytest.mark.skipif(
    not os.getenv("AAO_TEST_POSTGRES_URL") or
    os.getenv("AAO_TEST_DB_DISPOSABLE") != "yes",
    reason="Explicit disposable PostgreSQL database required",
)
def test_postgres_inert_staging_is_default_off_and_idempotent(monkeypatch):
    from aao.work_management_api import app
    monkeypatch.setenv("AAO_POSTGRES_URL", os.environ["AAO_TEST_POSTGRES_URL"])
    monkeypatch.setenv("AAO_CEO_TOKEN", "test-ceo")
    monkeypatch.delenv("AAO_SANDBOX_QUEUE_ENABLED", raising=False)
    ceo = {"X-CEO-Token": "test-ceo"}
    with TestClient(app) as client:
        worker_id = "agent-" + str(uuid4())
        issued = client.post("/v1/principals/credentials", headers=ceo, json={"principal_id": worker_id, "kind": "AGENT"})
        assert issued.status_code == 201, issued.text
        worker = {"X-Agent-Token": issued.json()["token"]}
        mid = client.post("/v1/mandates", headers=ceo, json={
            "title": "Queue " + str(uuid4()), "objective": "Inert test"
        }).json()["id"]
        assert client.post(f"/v1/mandates/{mid}/confirm", headers=ceo).status_code == 200
        pid = client.post("/v1/projects", headers=ceo, json={
            "name": "Queue project", "mandate_id": mid
        }).json()["id"]
        for capability in ("work.create", "work.admit"):
            assert client.post(f"/v1/projects/{pid}/grants", headers=ceo, json={
                "principal_id": worker_id, "capability": capability
            }).status_code == 201
        wid = client.post(f"/v1/projects/{pid}/work", headers=worker, json={
            "title": "Inert", "author_id": worker_id,
            "acceptance_criteria": ["queued"]
        }).json()["id"]
        assert client.post(f"/v1/work/{wid}/stage-inert", headers=worker).status_code == 503
        assert client.post(f"/v1/work/{wid}/admit", headers=worker).status_code == 200
        monkeypatch.setenv("AAO_SANDBOX_QUEUE_ENABLED", "true")
        first = client.post(f"/v1/work/{wid}/stage-inert", headers=worker)
        assert first.status_code == 202, first.text
        again = client.post(f"/v1/work/{wid}/stage-inert", headers=worker)
        assert again.status_code == 202, again.text
        assert first.json()["execution_id"] == again.json()["execution_id"]


@pytest.mark.skipif(
    not os.getenv("AAO_TEST_POSTGRES_URL") or os.getenv("AAO_TEST_DB_DISPOSABLE") != "yes",
    reason="Explicit disposable PostgreSQL database required",
)
def test_worker_claim_complete_respects_identity_and_project_state(monkeypatch):
    from aao.execution_queue import ExecutionConflict, claim, complete, state
    from aao.postgresql_connection import connect_postgres
    from aao.work_management_api import app

    monkeypatch.setenv("AAO_POSTGRES_URL", os.environ["AAO_TEST_POSTGRES_URL"])
    monkeypatch.setenv("AAO_CEO_TOKEN", "integration-ceo")
    monkeypatch.setenv("AAO_SANDBOX_QUEUE_ENABLED", "true")
    ceo = {"X-CEO-Token": "integration-ceo"}
    worker_id = "worker-" + str(uuid4())
    with TestClient(app) as client:
        issued = client.post("/v1/principals/credentials", headers=ceo, json={
            "principal_id": worker_id, "kind": "AGENT",
        })
        assert issued.status_code == 201, issued.text
        token = issued.json()["token"]
        worker = {"X-Agent-Token": token}
        mid = client.post("/v1/mandates", headers=ceo, json={
            "title": "Lease " + str(uuid4()), "objective": "Isolated worker tests"
        }).json()["id"]
        client.post(f"/v1/mandates/{mid}/confirm", headers=ceo)
        project_id = client.post("/v1/projects", headers=ceo, json={
            "name": "Lease project", "mandate_id": mid
        }).json()["id"]
        for cap in ("work.create", "work.admit"):
            client.post(f"/v1/projects/{project_id}/grants", headers=ceo, json={
                "principal_id": worker_id, "capability": cap
            })
        assert client.post(f"/v1/projects/{project_id}/grants", headers=ceo, json={
            "principal_id": worker_id, "capability": "execution.claim",
        }).status_code == 201
        wid = client.post(f"/v1/projects/{project_id}/work", headers=worker, json={
            "title": "Lease test", "author_id": worker_id,
            "acceptance_criteria": ["inert completion"]
        }).json()["id"]
        client.post(f"/v1/work/{wid}/admit", headers=worker)
        eid = client.post(f"/v1/work/{wid}/stage-inert", headers=worker).json()["execution_id"]
        with pytest.raises(ExecutionConflict):
            claim(worker_id, agent_credential="wrong", project_id=project_id)
        lease = claim(worker_id, agent_credential=token, project_id=project_id)
        assert lease is not None and lease["execution_id"] == eid
        with pytest.raises(ExecutionConflict):
            complete(eid, lease["token"], worker_id, {"ok": True}, agent_credential="wrong")
        assert state(eid)["status"] == "RUNNING"
        with connect_postgres() as db:
            db.execute("UPDATE projects SET state='PAUSED' WHERE id=%s", (project_id,))
        with pytest.raises(ExecutionConflict):
            complete(eid, lease["token"], worker_id, {"ok": True}, agent_credential=token)
        assert state(eid)["status"] == "RUNNING"
        with connect_postgres() as db:
            db.execute("UPDATE projects SET state='ACTIVE' WHERE id=%s", (project_id,))
        complete(eid, lease["token"], worker_id, {"ok": True}, agent_credential=token)
        assert state(eid)["status"] == "SUCCEEDED"


@pytest.mark.skipif(
    not os.getenv("AAO_TEST_POSTGRES_URL") or os.getenv("AAO_TEST_DB_DISPOSABLE") != "yes",
    reason="Explicit disposable PostgreSQL database required",
)
def test_inert_worker_concurrent_claims_never_duplicate(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor

    from aao.execution_queue import claim, state
    from aao.work_management_api import app

    monkeypatch.setenv("AAO_POSTGRES_URL", os.environ["AAO_TEST_POSTGRES_URL"])
    monkeypatch.setenv("AAO_CEO_TOKEN", "concurrent-ceo")
    monkeypatch.setenv("AAO_SANDBOX_QUEUE_ENABLED", "true")
    ceo = {"X-CEO-Token": "concurrent-ceo"}
    identity = "concurrent-" + str(uuid4())
    with TestClient(app) as client:
        issued = client.post("/v1/principals/credentials", headers=ceo, json={
            "principal_id": identity, "kind": "AGENT",
        })
        assert issued.status_code == 201, issued.text
        secret = issued.json()["token"]
        worker = {"X-Agent-Token": secret}
        mid = client.post("/v1/mandates", headers=ceo, json={"title": str(uuid4()), "objective": "Concurrency"}).json()["id"]
        client.post(f"/v1/mandates/{mid}/confirm", headers=ceo)
        pid = client.post("/v1/projects", headers=ceo, json={"name": "Concurrency", "mandate_id": mid}).json()["id"]
        for cap in ("work.create", "work.admit"):
            client.post(f"/v1/projects/{pid}/grants", headers=ceo, json={"principal_id": identity, "capability": cap})
        assert client.post(f"/v1/projects/{pid}/grants", headers=ceo, json={
            "principal_id": identity, "capability": "execution.claim",
        }).status_code == 201
        ids = []
        for i in range(4):
            wid = client.post(f"/v1/projects/{pid}/work", headers=worker, json={"title": f"Batch {i}", "author_id": identity, "acceptance_criteria": ["inert"]}).json()["id"]
            client.post(f"/v1/work/{wid}/admit", headers=worker)
            ids.append(client.post(f"/v1/work/{wid}/stage-inert", headers=worker).json()["execution_id"])
    with ThreadPoolExecutor(max_workers=4) as pool:
        leases = list(pool.map(lambda _: claim(identity, agent_credential=secret, project_id=pid), range(4)))
    claimed = [lease["execution_id"] for lease in leases if lease is not None]
    assert set(claimed) == set(ids)
    assert len(claimed) == len(set(claimed)) == 4
    assert all(state(eid)["status"] == "RUNNING" for eid in ids)
