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
    from aao.work_management_api import app
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
    from aao.work_management_api import app
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
    from aao.work_management_api import app
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
    from aao.work_management_api import app
    from aao.execution_queue import ExecutionConflict, claim, complete, state
    from aao.legacy_worker_authentication import credential_digest
    from aao.postgresql_connection import connect_postgres

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
            claim(worker_id, credential="wrong", project_id=project_id)
        with connect_postgres() as db:
            db.execute("INSERT INTO project_grants(principal_id,project_id,capability) VALUES (%s,%s,'execution.claim')", (worker_id, project_id))
        lease = claim(worker_id, credential=token, project_id=project_id)
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


@pytest.mark.skipif(
    not os.getenv("AAO_TEST_POSTGRES_URL") or os.getenv("AAO_TEST_DB_DISPOSABLE") != "yes",
    reason="Explicit disposable PostgreSQL database required",
)
def test_reconciliation_requires_distinct_granted_reviewer(monkeypatch):
    from aao.work_management_api import app
    from aao.execution_queue import claim, quarantine_expired, state
    from aao.execution_reconciliation import ReconciliationDenied, reconcile
    from aao.legacy_worker_authentication import credential_digest
    from aao.postgresql_connection import connect_postgres
    from datetime import datetime, timedelta, timezone

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
    base = datetime.now(timezone.utc)
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


@pytest.mark.skipif(
    not os.getenv("AAO_TEST_POSTGRES_URL") or os.getenv("AAO_TEST_DB_DISPOSABLE") != "yes",
    reason="Explicit disposable PostgreSQL database required",
)
def test_inert_worker_concurrent_claims_never_duplicate(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from aao.postgresql_connection import connect_postgres
    from aao.execution_queue import claim, state
    from aao.legacy_worker_authentication import credential_digest
    from aao.work_management_api import app

    monkeypatch.setenv("AAO_POSTGRES_URL", os.environ["AAO_TEST_POSTGRES_URL"])
    monkeypatch.setenv("AAO_CEO_TOKEN", "concurrent-ceo")
    monkeypatch.setenv("AAO_WORK_TOKEN", "concurrent-worker")
    monkeypatch.setenv("AAO_SANDBOX_QUEUE_ENABLED", "true")
    ceo = {"X-CEO-Token": "concurrent-ceo"}
    worker = {"X-Work-Token": "concurrent-worker"}
    identity = "concurrent-" + str(uuid4())
    secret = "concurrent-secret-" + str(uuid4())
    with connect_postgres() as db:
        db.execute("INSERT INTO worker_registrations(worker_id,token_digest,enabled) VALUES (%s,%s,true)", (identity, credential_digest(secret)))
    with TestClient(app) as client:
        mid = client.post("/v1/mandates", headers=ceo, json={"title": str(uuid4()), "objective": "Concurrency"}).json()["id"]
        client.post(f"/v1/mandates/{mid}/confirm", headers=ceo)
        pid = client.post("/v1/projects", headers=ceo, json={"name": "Concurrency", "mandate_id": mid}).json()["id"]
        for cap in ("work.create", "work.admit"):
            client.post(f"/v1/projects/{pid}/grants", headers=ceo, json={"principal_id": "development-worker", "capability": cap})
        ids = []
        for i in range(4):
            wid = client.post(f"/v1/projects/{pid}/work", headers=worker, json={"title": f"Batch {i}", "author_id": "development-worker", "acceptance_criteria": ["inert"]}).json()["id"]
            client.post(f"/v1/work/{wid}/admit", headers=worker)
            ids.append(client.post(f"/v1/work/{wid}/stage-inert", headers=worker).json()["execution_id"])
    with connect_postgres() as db:
        db.execute("INSERT INTO project_grants(principal_id,project_id,capability) VALUES (%s,%s,'execution.claim')", (identity, pid))
    with ThreadPoolExecutor(max_workers=4) as pool:
        leases = list(pool.map(lambda _: claim(identity, credential=secret, project_id=pid), range(4)))
    claimed = [lease["execution_id"] for lease in leases if lease is not None]
    assert set(claimed) == set(ids)
    assert len(claimed) == len(set(claimed)) == 4
    assert all(state(eid)["status"] == "RUNNING" for eid in ids)


@pytest.mark.skipif(
    not os.getenv("AAO_TEST_POSTGRES_URL") or os.getenv("AAO_TEST_DB_DISPOSABLE") != "yes",
    reason="Explicit disposable PostgreSQL database required",
)
def test_postgres_workboard_requires_ceo_read_credentials(monkeypatch):
    """The browser and API share an origin, but project reads stay protected."""
    from aao.work_management_api import app
    monkeypatch.setenv("AAO_POSTGRES_URL", os.environ["AAO_TEST_POSTGRES_URL"])
    monkeypatch.setenv("AAO_CEO_TOKEN", "read-only-test-ceo")
    with TestClient(app) as client:
        page = client.get("/")
        assert page.status_code == 200
        assert "AAO" in page.text
        assert client.get("/v1/projects").status_code == 403
        assert client.get("/v1/projects", headers={"X-CEO-Token": "wrong"}).status_code == 403
        allowed = client.get(
            "/v1/projects", headers={"X-CEO-Token": "read-only-test-ceo"}
        )
        assert allowed.status_code == 200
        assert isinstance(allowed.json(), list)


@pytest.mark.skipif(
    not os.getenv("AAO_TEST_POSTGRES_URL") or os.getenv("AAO_TEST_DB_DISPOSABLE") != "yes",
    reason="Explicit disposable PostgreSQL database required",
)
def test_project_reads_are_scoped_to_granted_worker(monkeypatch):
    from aao.work_management_api import app
    monkeypatch.setenv("AAO_POSTGRES_URL", os.environ["AAO_TEST_POSTGRES_URL"])
    monkeypatch.setenv("AAO_CEO_TOKEN", "scoped-read-ceo")
    monkeypatch.setenv("AAO_WORK_TOKEN", "scoped-read-worker")
    ceo = {"X-CEO-Token": "scoped-read-ceo"}
    worker = {"X-Work-Token": "scoped-read-worker"}
    with TestClient(app) as client:
        project_ids = []
        for i in range(2):
            mid = client.post("/v1/mandates", headers=ceo, json={
                "title": f"Read scope {i} {uuid4()}", "objective": "Disposable read test"
            }).json()["id"]
            assert client.post(f"/v1/mandates/{mid}/confirm", headers=ceo).status_code == 200
            pid = client.post("/v1/projects", headers=ceo, json={
                "name": f"Scope {i}", "mandate_id": mid,
            }).json()["id"]
            project_ids.append(pid)
        allow, deny = project_ids
        before = client.get("/v1/projects", headers=worker)
        assert before.status_code == 200
        assert allow not in [p["id"] for p in before.json()]
        assert deny not in [p["id"] for p in before.json()]
        assert client.get(f"/v1/projects/{deny}/board", headers=worker).status_code == 403
        granted = client.post(f"/v1/projects/{allow}/grants", headers=ceo, json={
            "principal_id": "development-worker", "capability": "project.read",
        })
        assert granted.status_code == 201, granted.text
        visible = client.get("/v1/projects", headers=worker)
        assert visible.status_code == 200
        ids = [p["id"] for p in visible.json()]
        assert allow in ids and deny not in ids
        assert client.get(f"/v1/projects/{allow}/board", headers=worker).status_code == 200
        assert client.get(f"/v1/projects/{deny}/board", headers=worker).status_code == 403
        assert client.get(f"/v1/projects/{deny}/board", headers=ceo).status_code == 200


@pytest.mark.skipif(
    not os.getenv("AAO_TEST_POSTGRES_URL") or os.getenv("AAO_TEST_DB_DISPOSABLE") != "yes",
    reason="Explicit disposable PostgreSQL database required",
)
def test_individual_auditor_credential_is_bound_to_review(monkeypatch):
    from aao.work_management_api import app
    from aao.principal_credentials import digest_token
    from aao.postgresql_connection import connect_postgres

    monkeypatch.setenv("AAO_POSTGRES_URL", os.environ["AAO_TEST_POSTGRES_URL"])
    monkeypatch.setenv("AAO_CEO_TOKEN", "individual-ceo")
    monkeypatch.setenv("AAO_WORK_TOKEN", "individual-worker")
    ceo = {"X-CEO-Token": "individual-ceo"}
    worker = {"X-Work-Token": "individual-worker"}
    auditor_id = "auditor-" + str(uuid4())
    secret = "individual-secret-" + str(uuid4())
    with connect_postgres() as db:
        db.execute(
            "INSERT INTO principal_credentials(principal_id,kind,token_digest,enabled) "
            "VALUES (%s,'AUDITOR',%s,true)",
            (auditor_id, digest_token(secret)),
        )
    with TestClient(app) as client:
        mandate = client.post("/v1/mandates", headers=ceo, json={
            "title": "Individual reviewer " + str(uuid4()),
            "objective": "Test credentials without external effects",
        }).json()["id"]
        assert client.post(f"/v1/mandates/{mandate}/confirm", headers=ceo).status_code == 200
        project = client.post("/v1/projects", headers=ceo, json={
            "name": "Audit test", "mandate_id": mandate
        }).json()["id"]
        for identity, capability in (
            ("development-worker", "work.create"),
            ("development-worker", "work.admit"),
            ("development-worker", "work.progress"),
        ):
            assert client.post(f"/v1/projects/{project}/grants", headers=ceo, json={
                "principal_id": identity, "capability": capability,
            }).status_code == 201
        with connect_postgres() as db:
            db.execute(
                "INSERT INTO project_grants(principal_id,project_id,capability) "
                "VALUES (%s,%s,'work.review')", (auditor_id, project),
            )
        work = client.post(f"/v1/projects/{project}/work", headers=worker, json={
            "title": "Individual audited work",
            "author_id": "spoof-attempt",
            "acceptance_criteria": ["independently reviewed"],
        }).json()["id"]
        assert client.post(f"/v1/work/{work}/admit", headers=worker).status_code == 200
        assert client.post(f"/v1/work/{work}/progress", headers=worker).status_code == 200
        assert client.post(f"/v1/work/{work}/progress", headers=worker).status_code == 200
        payload = {"decision": "APPROVE", "evidence": ["isolated local proof"]}
        denied = client.post(f"/v1/work/{work}/reviews",
                             headers={"X-Auditor-Token": "incorrect"}, json=payload)
        assert denied.status_code == 403
        allowed = client.post(f"/v1/work/{work}/reviews",
                              headers={"X-Auditor-Token": secret}, json=payload)
        assert allowed.status_code == 201, allowed.text
        with connect_postgres() as db:
            actual = db.execute(
                "SELECT reviewer_id FROM reviews WHERE id=%s",
                (allowed.json()["review_id"],),
            ).fetchone()
            assert actual[0] == auditor_id


@pytest.mark.skipif(
    not os.getenv("AAO_TEST_POSTGRES_URL") or os.getenv("AAO_TEST_DB_DISPOSABLE") != "yes",
    reason="Explicit disposable PostgreSQL database required",
)
def test_individual_agent_scoped_creation_and_revocation(monkeypatch):
    """Individual agent cannot write across projects and revocation is immediate."""
    from aao.work_management_api import app
    from aao.principal_credentials import digest_token
    from aao.postgresql_connection import connect_postgres

    monkeypatch.setenv("AAO_POSTGRES_URL", os.environ["AAO_TEST_POSTGRES_URL"])
    monkeypatch.setenv("AAO_CEO_TOKEN", "agent-scope-ceo")
    monkeypatch.setenv("AAO_WORK_TOKEN", "agent-scope-shared-worker")
    ceo = {"X-CEO-Token": "agent-scope-ceo"}
    identity = "agent-" + str(uuid4())
    secret = "agent-secret-" + str(uuid4())
    agent = {"X-Agent-Token": secret}
    with connect_postgres() as db:
        db.execute(
            "INSERT INTO principal_credentials(principal_id,kind,token_digest,enabled) "
            "VALUES (%s,'AGENT',%s,true)", (identity, digest_token(secret))
        )
    with TestClient(app) as client:
        projects = []
        for i in range(2):
            mid = client.post("/v1/mandates", headers=ceo, json={
                "title": f"Individual agent {i} {uuid4()}",
                "objective": "Project isolation",
            }).json()["id"]
            assert client.post(f"/v1/mandates/{mid}/confirm", headers=ceo).status_code == 200
            pid = client.post("/v1/projects", headers=ceo, json={
                "name": f"Agent scope {i}", "mandate_id": mid
            }).json()["id"]
            projects.append(pid)
        allowed, forbidden = projects
        assert client.post(f"/v1/projects/{allowed}/grants", headers=ceo, json={
            "principal_id": identity, "capability": "project.read",
        }).status_code == 201
        scoped = client.get("/v1/projects", headers=agent)
        assert scoped.status_code == 200, scoped.text
        assert [row["id"] for row in scoped.json()] == [allowed]
        assert client.get(f"/v1/projects/{forbidden}/board", headers=agent).status_code == 403
        assert client.get(f"/v1/projects/{allowed}/board", headers=agent).status_code == 200
        assert client.post(f"/v1/projects/{allowed}/grants", headers=ceo, json={
            "principal_id": identity, "capability": "work.create",
        }).status_code == 201
        payload = {"title": "Individual action", "author_id": "spoof-attempt",
                   "acceptance_criteria": ["Persisted"]}
        invalid = client.post(f"/v1/projects/{allowed}/work",
                              headers={"X-Agent-Token": "incorrect", "X-Work-Token": "agent-scope-shared-worker"},
                              json=payload)
        assert invalid.status_code == 403
        assert client.post(f"/v1/projects/{forbidden}/work",
                           headers=agent, json=payload).status_code == 403
        accepted = client.post(f"/v1/projects/{allowed}/work",
                               headers=agent, json=payload)
        assert accepted.status_code == 201, accepted.text
        work_id = accepted.json()["id"]
        with connect_postgres() as db:
            author = db.execute("SELECT author_id FROM work_items WHERE id=%s", (work_id,)).fetchone()
            assert author[0] == identity
            db.execute("UPDATE principal_credentials SET enabled=false WHERE principal_id=%s", (identity,))
        assert client.post(f"/v1/projects/{allowed}/work",
                           headers=agent, json=payload).status_code == 403


@pytest.mark.skipif(
    not os.getenv("AAO_TEST_POSTGRES_URL") or os.getenv("AAO_TEST_DB_DISPOSABLE") != "yes",
    reason="Explicit disposable PostgreSQL database required",
)
def test_individual_agent_claim_and_revocation(monkeypatch):
    from aao.work_management_api import app
    from aao.execution_queue import ExecutionConflict, claim, complete, state
    from aao.principal_credentials import digest_token
    from aao.postgresql_connection import connect_postgres

    monkeypatch.setenv("AAO_POSTGRES_URL", os.environ["AAO_TEST_POSTGRES_URL"])
    monkeypatch.setenv("AAO_CEO_TOKEN", "lease-ceo")
    monkeypatch.setenv("AAO_WORK_TOKEN", "lease-worker")
    monkeypatch.setenv("AAO_SANDBOX_QUEUE_ENABLED", "true")
    ceo = {"X-CEO-Token": "lease-ceo"}
    worker = {"X-Work-Token": "lease-worker"}
    principal = "agent-" + str(uuid4())
    secret = "secret-" + str(uuid4())
    with connect_postgres() as db:
        db.execute(
            "INSERT INTO principal_credentials(principal_id,kind,token_digest,enabled) "
            "VALUES (%s,'AGENT',%s,true)", (principal, digest_token(secret)),
        )
    with TestClient(app) as client:
        mid = client.post("/v1/mandates", headers=ceo, json={
            "title": "Unified agent lease " + str(uuid4()), "objective": "Isolated test"
        }).json()["id"]
        assert client.post(f"/v1/mandates/{mid}/confirm", headers=ceo).status_code == 200
        project = client.post("/v1/projects", headers=ceo, json={
            "name": "Unified lease", "mandate_id": mid
        }).json()["id"]
        for who, capability in (
            ("development-worker", "work.create"),
            ("development-worker", "work.admit"),
            (principal, "execution.claim"),
        ):
            assert client.post(f"/v1/projects/{project}/grants", headers=ceo, json={
                "principal_id": who, "capability": capability,
            }).status_code == 201
        wid = client.post(f"/v1/projects/{project}/work", headers=worker, json={
            "title": "Inert execution", "author_id": "ignored",
            "acceptance_criteria": ["completed"],
        }).json()["id"]
        assert client.post(f"/v1/work/{wid}/admit", headers=worker).status_code == 200
        eid = client.post(f"/v1/work/{wid}/stage-inert", headers=worker).json()["execution_id"]
    with pytest.raises(ExecutionConflict):
        claim(principal, project_id=project, agent_credential="wrong")
    lease = claim(principal, project_id=project, agent_credential=secret)
    assert lease is not None and lease["execution_id"] == eid
    with connect_postgres() as db:
        db.execute("UPDATE principal_credentials SET enabled=false WHERE principal_id=%s", (principal,))
    with pytest.raises(ExecutionConflict):
        complete(eid, lease["token"], principal, {"ok": True}, agent_credential=secret)
    assert state(eid)["status"] == "RUNNING"


@pytest.mark.skipif(
    not os.getenv("AAO_TEST_POSTGRES_URL") or os.getenv("AAO_TEST_DB_DISPOSABLE") != "yes",
    reason="Explicit disposable PostgreSQL database required",
)
def test_ceo_governed_principal_issue_rotate_revoke(monkeypatch):
    from aao.work_management_api import app
    from aao.principal_credentials import authenticate, PrincipalDenied
    from aao.postgresql_connection import connect_postgres

    monkeypatch.setenv("AAO_POSTGRES_URL", os.environ["AAO_TEST_POSTGRES_URL"])
    monkeypatch.setenv("AAO_CEO_TOKEN", "governance-ceo")
    name = "agent-" + str(uuid4())
    ceo = {"X-CEO-Token": "governance-ceo"}
    with TestClient(app) as client:
        payload = {"principal_id": name, "kind": "AGENT"}
        assert client.post("/v1/principals/credentials", json=payload).status_code == 403
        created = client.post("/v1/principals/credentials", headers=ceo, json=payload)
        assert created.status_code == 201, created.text
        initial = created.json()["token"]
        assert authenticate(initial, kind="AGENT") == name
        assert client.post("/v1/principals/credentials", headers=ceo, json=payload).status_code == 409
        changed = client.post(f"/v1/principals/{name}/rotate", headers=ceo)
        assert changed.status_code == 200, changed.text
        rotated = changed.json()["token"]
        assert rotated != initial
        with pytest.raises(PrincipalDenied):
            authenticate(initial, kind="AGENT")
        assert authenticate(rotated, kind="AGENT") == name
        assert client.post(f"/v1/principals/{name}/revoke", headers=ceo).status_code == 200
        with pytest.raises(PrincipalDenied):
            authenticate(rotated, kind="AGENT")
        assert client.post(f"/v1/principals/{name}/revoke", headers=ceo).status_code == 404
        # A revoked identity cannot be silently reactivated by token rotation.
        assert client.post(f"/v1/principals/{name}/rotate", headers=ceo).status_code == 404
        with connect_postgres() as db:
            events = db.execute(
                "SELECT kind FROM events WHERE details->>'principal_id'=%s "
                "AND kind LIKE %s", (name, "principal.credential.%")
            ).fetchall()
            assert {row[0] for row in events} == {
                "principal.credential.issued",
                "principal.credential.rotated",
                "principal.credential.revoked",
            }
