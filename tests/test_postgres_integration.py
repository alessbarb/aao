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
