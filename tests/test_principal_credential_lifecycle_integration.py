"""PostgreSQL integration tests, opt-in for explicitly disposable databases."""
import os
import time
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


@pytest.mark.skipif(
    not os.getenv("AAO_TEST_POSTGRES_URL") or os.getenv("AAO_TEST_DB_DISPOSABLE") != "yes",
    reason="Explicit disposable PostgreSQL database required",
)
def test_legacy_execution_identity_migration_is_applied(monkeypatch):
    from aao.postgresql_connection import connect_postgres

    monkeypatch.setenv("AAO_POSTGRES_URL", os.environ["AAO_TEST_POSTGRES_URL"])
    with connect_postgres() as db:
        assert db.execute(
            "SELECT to_regclass('public.worker_registrations') IS NULL"
        ).fetchone()[0]
        migrated = db.execute(
            "SELECT kind,token_digest,enabled FROM principal_credentials "
            "WHERE principal_id='legacy-ci-agent'"
        ).fetchone()
        if migrated is not None:
            assert migrated == (
                "AGENT", sha256(b"aao-ci-legacy-migration-token").hexdigest(), True
            )


@pytest.mark.skipif(
    not os.getenv("AAO_TEST_POSTGRES_URL") or os.getenv("AAO_TEST_DB_DISPOSABLE") != "yes",
    reason="Explicit disposable PostgreSQL database required",
)
def test_transactional_auditor_authentication_serializes_with_revocation(monkeypatch):
    from aao.postgresql_connection import connect_postgres
    from aao.principal_credentials import PrincipalDenied, authenticate_in_transaction
    from aao.work_management_api import app

    monkeypatch.setenv("AAO_POSTGRES_URL", os.environ["AAO_TEST_POSTGRES_URL"])
    monkeypatch.setenv("AAO_CEO_TOKEN", "auditor-race-ceo")
    identity = "auditor-" + str(uuid4())
    ceo = {"X-CEO-Token": "auditor-race-ceo"}
    with TestClient(app) as client:
        response = client.post("/v1/principals/credentials", headers=ceo, json={
            "principal_id": identity, "kind": "AUDITOR",
        })
        assert response.status_code == 201, response.text
        token = response.json()["token"]

    with ThreadPoolExecutor(max_workers=1) as pool, connect_postgres() as protected:
        assert authenticate_in_transaction(protected, token, kind="AUDITOR") == identity
        protected_pid = protected.execute("SELECT pg_backend_pid()").fetchone()[0]
        pid_ready = __import__("threading").Event()
        revoke_pid = []

        def revoke():
            with connect_postgres() as revoker:
                revoke_pid.append(revoker.execute("SELECT pg_backend_pid()").fetchone()[0])
                pid_ready.set()
                revoker.execute(
                    "UPDATE principal_credentials SET enabled=false WHERE principal_id=%s",
                    (identity,),
                )

        pending = pool.submit(revoke)
        assert pid_ready.wait(timeout=2)
        deadline = time.monotonic() + 3
        blocked = False
        while time.monotonic() < deadline:
            with connect_postgres() as observer:
                blocked = observer.execute(
                    "SELECT %s = ANY(pg_blocking_pids(%s))",
                    (protected_pid, revoke_pid[0]),
                ).fetchone()[0]
            if blocked:
                break
            time.sleep(0.01)
        assert blocked, "credential revocation was not blocked by the authenticated transaction"
        assert not pending.done()
    pending.result(timeout=2)
    with connect_postgres() as db, pytest.raises(PrincipalDenied):
        authenticate_in_transaction(db, token, kind="AUDITOR")


@pytest.mark.skipif(
    not os.getenv("AAO_TEST_POSTGRES_URL") or os.getenv("AAO_TEST_DB_DISPOSABLE") != "yes",
    reason="Explicit disposable PostgreSQL database required",
)
def test_individual_auditor_credential_is_bound_to_review(monkeypatch):
    from aao.postgresql_connection import connect_postgres
    from aao.principal_credentials import digest_token
    from aao.work_management_api import app

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
    from aao.postgresql_connection import connect_postgres
    from aao.principal_credentials import digest_token
    from aao.work_management_api import app

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
    from aao.execution_queue import ExecutionConflict, claim, complete, state
    from aao.postgresql_connection import connect_postgres
    from aao.principal_credentials import digest_token
    from aao.work_management_api import app

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
    from aao.postgresql_connection import connect_postgres
    from aao.principal_credentials import PrincipalDenied, authenticate
    from aao.work_management_api import app

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
