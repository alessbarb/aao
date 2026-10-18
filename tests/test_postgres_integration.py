"""Opt-in PostgreSQL API integration, never run against valuable databases.

Requires an isolated disposable database with 001 and 002 applied.
Run with AAO_TEST_POSTGRES_URL and AAO_TEST_DB_DISPOSABLE=yes.
"""
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


@pytest.mark.skipif(
    not os.getenv("AAO_TEST_POSTGRES_URL") or
    os.getenv("AAO_TEST_DB_DISPOSABLE") != "yes",
    reason="PostgreSQL integration requires an explicitly disposable test database",
)
def test_postgres_mandate_project_grant_work_admission(monkeypatch):
    from aao.pg_work import app
    monkeypatch.setenv("AAO_POSTGRES_URL", os.environ["AAO_TEST_POSTGRES_URL"])
    monkeypatch.setenv("AAO_CEO_TOKEN", "test-ceo-key")
    monkeypatch.setenv("AAO_WORK_TOKEN", "test-worker-key")
    ceo = {"X-CEO-Token": "test-ceo-key"}
    worker = {"X-Work-Token": "test-worker-key"}
    with TestClient(app) as client:
        assert client.get("/health").json()["autonomous_execution"] is False
        mandate = client.post(
            "/v1/mandates", headers=ceo,
            json={"title": "Disposable " + str(uuid4()), "objective": "Test-only mandate"},
        )
        assert mandate.status_code == 201, mandate.text
        mid = mandate.json()["id"]
        assert client.post(
            "/v1/projects", headers=ceo,
            json={"name": "X", "mandate_id": mid},
        ).status_code == 409
        assert client.post(
            f"/v1/mandates/{mid}/confirm", headers=ceo,
        ).status_code == 200
        r = client.post(
            "/v1/projects", headers=ceo,
            json={"name": "Disposable pilot", "mandate_id": mid},
        )
        assert r.status_code == 201, r.text
        project = r.json()["id"]
        work_payload = {
            "title": "Isolated smoke test", "author_id": "development-worker",
            "acceptance_criteria": ["State recorded"],
        }
        assert client.post(
            f"/v1/projects/{project}/work", headers=worker,
            json=work_payload,
        ).status_code == 403
        for cap in ("work.create", "work.admit", "work.progress"):
            assert client.post(
                f"/v1/projects/{project}/grants", headers=ceo,
                json={"principal_id": "development-worker", "capability": cap},
            ).status_code == 201
        created = client.post(
            f"/v1/projects/{project}/work", headers=worker,
            json=work_payload,
        )
        assert created.status_code == 201, created.text
        wid = created.json()["id"]
        assert client.post(f"/v1/work/{wid}/admit").status_code == 403
        admitted = client.post(f"/v1/work/{wid}/admit", headers=worker)
        assert admitted.status_code == 200, admitted.text
        assert admitted.json()["status"] == "READY"
        assert client.post(f"/v1/work/{wid}/admit", headers=worker).status_code == 409
        board = client.get(f"/v1/projects/{project}/board", headers=ceo)
        assert board.status_code == 200
        assert any(w["id"] == wid and w["status"] == "READY" for w in board.json())


@pytest.mark.skipif(
    not os.getenv("AAO_TEST_POSTGRES_URL") or os.getenv("AAO_TEST_DB_DISPOSABLE") != "yes",
    reason="Explicit disposable PostgreSQL test database required",
)
def test_postgres_review_is_separate_from_author_and_required_for_done(monkeypatch):
    from aao.pg_work import app
    monkeypatch.setenv("AAO_POSTGRES_URL", os.environ["AAO_TEST_POSTGRES_URL"])
    monkeypatch.setenv("AAO_CEO_TOKEN", "integration-ceo")
    monkeypatch.setenv("AAO_WORK_TOKEN", "integration-worker")
    monkeypatch.setenv("AAO_REVIEW_TOKEN", "integration-reviewer")
    ceo = {"X-CEO-Token": "integration-ceo"}
    worker = {"X-Work-Token": "integration-worker"}
    auditor = {"X-Review-Token": "integration-reviewer"}
    with TestClient(app) as client:
        m = client.post("/v1/mandates", headers=ceo, json={"title": str(uuid4()), "objective": "Review gate test"}).json()["id"]
        client.post(f"/v1/mandates/{m}/confirm", headers=ceo)
        p = client.post("/v1/projects", headers=ceo, json={"name": "Audit smoke", "mandate_id": m}).json()["id"]
        for who, cap in (("development-worker", "work.create"), ("development-worker", "work.admit"), ("development-worker", "work.progress"), ("development-auditor", "work.review")):
            assert client.post(f"/v1/projects/{p}/grants", headers=ceo, json={"principal_id": who, "capability": cap}).status_code == 201
        w = client.post(f"/v1/projects/{p}/work", headers=worker, json={"title": "Review", "author_id": "spoofed", "acceptance_criteria": ["Reviewed"]}).json()["id"]
        assert client.post(f"/v1/work/{w}/progress", headers=worker).status_code == 409
        assert client.post(f"/v1/work/{w}/admit", headers=worker).status_code == 200
        assert client.post(f"/v1/work/{w}/progress", headers=worker).json()["status"] == "IN_PROGRESS"
        assert client.post(f"/v1/work/{w}/progress", headers=worker).json()["status"] == "IN_REVIEW"
        assert client.post(f"/v1/work/{w}/progress", headers=worker).status_code == 409
        assert client.post(f"/v1/work/{w}/reviews", headers=worker, json={"decision": "APPROVE", "evidence": ["test"]}).status_code == 403
        assert client.post(f"/v1/work/{w}/reviews", headers=auditor, json={"decision": "APPROVE", "evidence": [""]}).status_code == 422
        assert client.post(f"/v1/work/{w}/reviews", headers=auditor, json={"decision": "APPROVE", "evidence": ["sha256:review-evidence"]}).json()["status"] == "VERIFIED"
        assert client.post(f"/v1/work/{w}/progress", headers=worker).json()["status"] == "DONE"


@pytest.mark.skipif(
    not os.getenv("AAO_TEST_POSTGRES_URL") or
    os.getenv("AAO_TEST_DB_DISPOSABLE") != "yes",
    reason="Explicit disposable PostgreSQL database required",
)
def test_postgres_inert_staging_is_default_off_and_idempotent(monkeypatch):
    from aao.pg_work import app
    monkeypatch.setenv("AAO_POSTGRES_URL", os.environ["AAO_TEST_POSTGRES_URL"])
    monkeypatch.setenv("AAO_CEO_TOKEN", "test-ceo")
    monkeypatch.setenv("AAO_WORK_TOKEN", "test-worker")
    monkeypatch.delenv("AAO_SANDBOX_QUEUE_ENABLED", raising=False)
    ceo = {"X-CEO-Token": "test-ceo"}
    worker = {"X-Work-Token": "test-worker"}
    with TestClient(app) as client:
        mid = client.post("/v1/mandates", headers=ceo, json={
            "title": "Queue " + str(uuid4()), "objective": "Inert test"
        }).json()["id"]
        assert client.post(f"/v1/mandates/{mid}/confirm", headers=ceo).status_code == 200
        pid = client.post("/v1/projects", headers=ceo, json={
            "name": "Queue project", "mandate_id": mid
        }).json()["id"]
        for capability in ("work.create", "work.admit"):
            assert client.post(f"/v1/projects/{pid}/grants", headers=ceo, json={
                "principal_id": "development-worker", "capability": capability
            }).status_code == 201
        wid = client.post(f"/v1/projects/{pid}/work", headers=worker, json={
            "title": "Inert", "author_id": "development-worker",
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
    from aao.pg_work import app
    from aao.pg_execution import ExecutionConflict, claim, complete, state
    from aao.worker_auth import credential_digest
    from aao.postgres import connect_postgres

    monkeypatch.setenv("AAO_POSTGRES_URL", os.environ["AAO_TEST_POSTGRES_URL"])
    monkeypatch.setenv("AAO_CEO_TOKEN", "integration-ceo")
    monkeypatch.setenv("AAO_WORK_TOKEN", "integration-worker")
    monkeypatch.setenv("AAO_SANDBOX_QUEUE_ENABLED", "true")
    ceo = {"X-CEO-Token": "integration-ceo"}
    worker = {"X-Work-Token": "integration-worker"}
    worker_id = "worker-" + str(uuid4())
    token = "test-credential-" + str(uuid4())
    with connect_postgres() as db:
        db.execute(
            "INSERT INTO worker_registrations(worker_id,token_digest,enabled) VALUES (%s,%s,true)",
            (worker_id, credential_digest(token)),
        )
    with TestClient(app) as client:
        mid = client.post("/v1/mandates", headers=ceo, json={
            "title": "Lease " + str(uuid4()), "objective": "Isolated worker tests"
        }).json()["id"]
        client.post(f"/v1/mandates/{mid}/confirm", headers=ceo)
        project_id = client.post("/v1/projects", headers=ceo, json={
            "name": "Lease project", "mandate_id": mid
        }).json()["id"]
        for cap in ("work.create", "work.admit"):
            client.post(f"/v1/projects/{project_id}/grants", headers=ceo, json={
                "principal_id": "development-worker", "capability": cap
            })
        wid = client.post(f"/v1/projects/{project_id}/work", headers=worker, json={
            "title": "Lease test", "author_id": "development-worker",
            "acceptance_criteria": ["inert completion"]
        }).json()["id"]
        client.post(f"/v1/work/{wid}/admit", headers=worker)
        eid = client.post(f"/v1/work/{wid}/stage-inert", headers=worker).json()["execution_id"]
        with pytest.raises(ExecutionConflict):
            claim(worker_id, credential="wrong")
        lease = claim(worker_id, credential=token)
        assert lease is not None and lease["execution_id"] == eid
        with pytest.raises(ExecutionConflict):
            complete(eid, lease["token"], worker_id, {"ok": True}, credential="wrong")
        assert state(eid)["status"] == "RUNNING"
        with connect_postgres() as db:
            db.execute("UPDATE projects SET state='PAUSED' WHERE id=%s", (project_id,))
        with pytest.raises(ExecutionConflict):
            complete(eid, lease["token"], worker_id, {"ok": True}, credential=token)
        assert state(eid)["status"] == "RUNNING"
        with connect_postgres() as db:
            db.execute("UPDATE projects SET state='ACTIVE' WHERE id=%s", (project_id,))
        complete(eid, lease["token"], worker_id, {"ok": True}, credential=token)
        assert state(eid)["status"] == "SUCCEEDED"
