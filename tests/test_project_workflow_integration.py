"""PostgreSQL integration tests, opt-in for explicitly disposable databases."""
import os
import time
from concurrent.futures import ThreadPoolExecutor
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
    ceo = {"X-CEO-Token": "test-ceo-key"}
    with TestClient(app) as client:
        agent_id = "agent-" + str(uuid4())
        token = client.post("/v1/principals/credentials", headers=ceo, json={"principal_id": agent_id, "kind": "AGENT"}).json()["token"]
        worker = {"X-Agent-Token": token}
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
            "title": "Isolated smoke test", "author_id": agent_id,
            "acceptance_criteria": ["State recorded"],
        }
        assert client.post(
            f"/v1/projects/{project}/work", headers=worker,
            json=work_payload,
        ).status_code == 403
        for cap in ("work.create", "work.admit", "work.progress"):
            assert client.post(
                f"/v1/projects/{project}/grants", headers=ceo,
                json={"principal_id": agent_id, "capability": cap},
            ).status_code == 201
        created = client.post(
            f"/v1/projects/{project}/work", headers=worker,
            json=work_payload,
        )
        assert created.status_code == 201, created.text
        wid = created.json()["id"]
        assert client.get(f"/v1/projects/{project}", headers=worker).status_code == 403
        assert client.get(f"/v1/projects/{project}/work/{wid}", headers=worker).status_code == 403
        assert client.get(f"/v1/projects/{project}/activity", headers=worker).status_code == 403
        assert client.post(
            f"/v1/projects/{project}/grants", headers=ceo,
            json={"principal_id": agent_id, "capability": "project.read"},
        ).status_code == 201
        detail = client.get(f"/v1/projects/{project}", headers=worker)
        assert detail.status_code == 200, detail.text
        assert detail.json()["mandate"]["id"] == mid
        task_detail = client.get(f"/v1/projects/{project}/work/{wid}", headers=worker)
        assert task_detail.status_code == 200, task_detail.text
        assert task_detail.json()["id"] == wid
        assert task_detail.json()["executions"] == []
        activity = client.get(f"/v1/projects/{project}/activity", headers=worker)
        assert activity.status_code == 200, activity.text
        assert any(event["kind"] == "work.created" for event in activity.json())
        revoked_read = client.delete(
            f"/v1/projects/{project}/grants/{agent_id}/project.read", headers=ceo,
        )
        assert revoked_read.status_code == 204
        assert client.get(f"/v1/projects/{project}", headers=worker).status_code == 403
        assert client.get(f"/v1/projects/{project}/activity", headers=worker).status_code == 403
        assert client.get(f"/v1/projects/{project}/work/{wid}", headers=worker).status_code == 403
        assert client.post(
            f"/v1/projects/{project}/grants", headers=ceo,
            json={"principal_id": agent_id, "capability": "project.read"},
        ).status_code == 201
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
def test_grant_creation_requires_active_principal_with_matching_kind(monkeypatch):
    from aao.postgresql_connection import connect_postgres
    from aao.work_management_api import app

    monkeypatch.setenv("AAO_POSTGRES_URL", os.environ["AAO_TEST_POSTGRES_URL"])
    monkeypatch.setenv("AAO_CEO_TOKEN", "grant-kind-ceo")
    ceo = {"X-CEO-Token": "grant-kind-ceo"}
    with TestClient(app) as client:
        agent = "grant-agent-" + str(uuid4())
        auditor = "grant-auditor-" + str(uuid4())
        assert client.post("/v1/principals/credentials", headers=ceo, json={
            "principal_id": agent, "kind": "AGENT",
        }).status_code == 201
        assert client.post("/v1/principals/credentials", headers=ceo, json={
            "principal_id": auditor, "kind": "AUDITOR",
        }).status_code == 201
        mandate = client.post("/v1/mandates", headers=ceo, json={
            "title": "Grant validation " + str(uuid4()),
            "objective": "Reject grants inconsistent with principal authority",
        }).json()["id"]
        assert client.post(f"/v1/mandates/{mandate}/confirm", headers=ceo).status_code == 200
        project = client.post("/v1/projects", headers=ceo, json={
            "name": "Grant validation", "mandate_id": mandate,
        }).json()["id"]

        for principal, capability, status in (
            ("absent-principal", "work.create", 404),
            (agent, "work.review", 422),
            (auditor, "work.create", 422),
        ):
            response = client.post(f"/v1/projects/{project}/grants", headers=ceo, json={
                "principal_id": principal, "capability": capability,
            })
            assert response.status_code == status, response.text

        valid_agent = client.post(f"/v1/projects/{project}/grants", headers=ceo, json={
            "principal_id": agent, "capability": "work.create",
        })
        valid_auditor = client.post(f"/v1/projects/{project}/grants", headers=ceo, json={
            "principal_id": auditor, "capability": "work.review",
        })
        assert valid_agent.status_code == valid_auditor.status_code == 201
        duplicate = client.post(f"/v1/projects/{project}/grants", headers=ceo, json={
            "principal_id": agent, "capability": "work.create",
        })
        assert duplicate.status_code == 200, duplicate.text
        assert duplicate.json() == {
            "project_id": project, "capability": "work.create", "created": False,
        }
        with connect_postgres() as db:
            event_count = db.execute(
                "SELECT count(*) FROM events WHERE subject_id=%s "
                "AND kind='grant.created' AND details->>'principal_id'=%s "
                "AND details->>'capability'='work.create'",
                (project, agent),
            ).fetchone()[0]
        assert event_count == 1
        revoked = "revoked-grantee-" + str(uuid4())
        issued = client.post("/v1/principals/credentials", headers=ceo, json={
            "principal_id": revoked, "kind": "AGENT",
        })
        assert issued.status_code == 201, issued.text
        assert client.post(f"/v1/principals/{revoked}/revoke", headers=ceo).status_code == 200
        disabled_grant = client.post(f"/v1/projects/{project}/grants", headers=ceo, json={
            "principal_id": revoked, "capability": "work.create",
        })
        assert disabled_grant.status_code == 409, disabled_grant.text


@pytest.mark.skipif(
    not os.getenv("AAO_TEST_POSTGRES_URL") or os.getenv("AAO_TEST_DB_DISPOSABLE") != "yes",
    reason="Explicit disposable PostgreSQL test database required",
)
def test_postgres_review_is_separate_from_author_and_required_for_done(monkeypatch):
    from aao.work_management_api import app
    monkeypatch.setenv("AAO_POSTGRES_URL", os.environ["AAO_TEST_POSTGRES_URL"])
    monkeypatch.setenv("AAO_CEO_TOKEN", "integration-ceo")
    monkeypatch.setenv("AAO_SANDBOX_QUEUE_ENABLED", "true")
    ceo = {"X-CEO-Token": "integration-ceo"}
    with TestClient(app) as client:
        agent_id = "agent-" + str(uuid4())
        auditor_id = "auditor-" + str(uuid4())
        worker = {"X-Agent-Token": client.post("/v1/principals/credentials", headers=ceo, json={"principal_id": agent_id, "kind": "AGENT"}).json()["token"]}
        auditor = {"X-Auditor-Token": client.post("/v1/principals/credentials", headers=ceo, json={"principal_id": auditor_id, "kind": "AUDITOR"}).json()["token"]}
        m = client.post("/v1/mandates", headers=ceo, json={"title": str(uuid4()), "objective": "Review gate test"}).json()["id"]
        client.post(f"/v1/mandates/{m}/confirm", headers=ceo)
        p = client.post("/v1/projects", headers=ceo, json={"name": "Audit smoke", "mandate_id": m}).json()["id"]
        for who, cap in ((agent_id, "work.create"), (agent_id, "work.admit"),
                         (agent_id, "work.progress"), (agent_id, "execution.claim"),
                         (auditor_id, "work.review")):
            assert client.post(f"/v1/projects/{p}/grants", headers=ceo, json={"principal_id": who, "capability": cap}).status_code == 201
        w = client.post(f"/v1/projects/{p}/work", headers=worker, json={"title": "Review", "author_id": "spoofed", "acceptance_criteria": ["Reviewed"]}).json()["id"]
        assert client.post(f"/v1/work/{w}/progress", headers=worker).status_code == 409
        assert client.post(f"/v1/work/{w}/admit", headers=worker).status_code == 200
        execution_id = client.post(f"/v1/work/{w}/stage-inert", headers=worker).json()["execution_id"]
        from aao.execution_queue import claim, complete
        lease = claim(agent_id, agent_credential=worker["X-Agent-Token"],
                      project_id=p)
        assert lease and lease["execution_id"] == execution_id
        assert client.post(f"/v1/work/{w}/progress", headers=worker).json()["status"] == "IN_PROGRESS"
        assert client.post(f"/v1/work/{w}/progress", headers=worker).json()["status"] == "IN_REVIEW"
        assert client.post(f"/v1/work/{w}/reviews", headers=auditor, json={
            "decision": "APPROVE", "evidence": ["sha256:review-evidence"],
        }).status_code == 409
        rejected_while_running = client.post(f"/v1/work/{w}/reviews", headers=auditor, json={
            "decision": "REJECT", "evidence": ["execution still running"],
        })
        assert rejected_while_running.status_code == 201, rejected_while_running.text
        assert rejected_while_running.json()["status"] == "IN_PROGRESS"
        complete(execution_id, lease["token"], agent_id, {"ok": True},
                 agent_credential=worker["X-Agent-Token"])
        assert client.post(f"/v1/work/{w}/progress", headers=worker).json()["status"] == "IN_REVIEW"
        assert client.post(f"/v1/work/{w}/progress", headers=worker).status_code == 409
        assert client.post(f"/v1/work/{w}/reviews", headers=worker, json={"decision": "APPROVE", "evidence": ["test"]}).status_code == 403
        assert client.post(f"/v1/work/{w}/reviews", headers=auditor, json={"decision": "APPROVE", "evidence": [""]}).status_code == 422
        approval = client.post(f"/v1/work/{w}/reviews", headers=auditor, json={
            "decision": "APPROVE", "evidence": ["sha256:review-evidence"],
        })
        assert approval.status_code == 409, approval.text
        from aao.postgresql_connection import connect_postgres
        with connect_postgres() as db:
            approval_rows = db.execute(
                "SELECT count(*) FROM reviews WHERE work_id=%s AND decision='APPROVE'",
                (w,),
            ).fetchone()[0]
        assert approval_rows == 0
        board = client.get(f"/v1/projects/{p}/board", headers=ceo)
        assert board.status_code == 200, board.text
        assert any(item["id"] == w and item["status"] == "IN_REVIEW"
                   for item in board.json())
        rejected = client.post(f"/v1/work/{w}/reviews", headers=auditor, json={
            "decision": "REJECT", "evidence": ["review requires stronger evidence"],
        })
        assert rejected.status_code == 201, rejected.text
        assert rejected.json()["status"] == "IN_PROGRESS"
        assert client.post(f"/v1/work/{w}/progress", headers=worker).json()["status"] == "IN_REVIEW"
        retry_approval = client.post(f"/v1/work/{w}/reviews", headers=auditor, json={
            "decision": "APPROVE", "evidence": ["still-unverified"],
        })
        assert retry_approval.status_code == 409, retry_approval.text
        with connect_postgres() as db:
            db.execute(
                "UPDATE work_items SET status='VERIFIED' WHERE id=%s", (w,),
            )
            db.execute(
                "INSERT INTO reviews(id,work_id,reviewer_id,decision,evidence) "
                "VALUES (%s,%s,%s,'APPROVE',%s::jsonb)",
                (str(uuid4()), w, auditor_id, '["legacy unverified approval"]'),
            )
        legacy_completion = client.post(f"/v1/work/{w}/progress", headers=worker)
        assert legacy_completion.status_code == 409, legacy_completion.text
        legacy_board = client.get(f"/v1/projects/{p}/board", headers=ceo)
        assert any(item["id"] == w and item["status"] == "VERIFIED"
                   for item in legacy_board.json())


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
        for label in (
            "AAO Control Center", "Inicio", "Proyecto", "Actividad",
            "Evidencias", "Decisiones reservadas",
        ):
            assert label in page.text
        assert "No se presentan como disponibles" in page.text
        assert "localStorage" not in page.text
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
    ceo = {"X-CEO-Token": "scoped-read-ceo"}
    with TestClient(app) as client:
        agent_id = "agent-" + str(uuid4())
        worker = {"X-Agent-Token": client.post("/v1/principals/credentials", headers=ceo, json={"principal_id": agent_id, "kind": "AGENT"}).json()["token"]}
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
            "principal_id": agent_id, "capability": "project.read",
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
def test_grant_revocation_serializes_after_authorized_transaction(monkeypatch):
    """An in-flight grant-checked transaction completes before CEO revocation."""
    from aao.postgresql_connection import connect_postgres
    from aao.principal_credentials import digest_token
    from aao.work_management_api import AuthenticatedPrincipal, app, require_grant

    monkeypatch.setenv("AAO_POSTGRES_URL", os.environ["AAO_TEST_POSTGRES_URL"])
    monkeypatch.setenv("AAO_CEO_TOKEN", "grant-race-ceo")
    ceo = {"X-CEO-Token": "grant-race-ceo"}
    with TestClient(app) as client:
        agent_id = "agent-" + str(uuid4())
        worker = {"X-Agent-Token": client.post("/v1/principals/credentials", headers=ceo, json={"principal_id": agent_id, "kind": "AGENT"}).json()["token"]}
        mandate = client.post("/v1/mandates", headers=ceo, json={
            "title": f"Grant race {uuid4()}", "objective": "Test grant serialization",
        }).json()["id"]
        assert client.post(f"/v1/mandates/{mandate}/confirm", headers=ceo).status_code == 200
        project = client.post("/v1/projects", headers=ceo, json={
            "name": f"Grant race {uuid4()}", "mandate_id": mandate,
        }).json()["id"]
        assert client.post(f"/v1/projects/{project}/grants", headers=ceo, json={
            "principal_id": agent_id, "capability": "work.create",
        }).status_code == 201

        with ThreadPoolExecutor(max_workers=1) as pool, connect_postgres() as protected_db:
            require_grant(
                protected_db,
                AuthenticatedPrincipal(agent_id, digest_token(worker["X-Agent-Token"]), "AGENT"),
                project,
                "work.create",
            )
            revoke = pool.submit(client.delete,
                f"/v1/projects/{project}/grants/{agent_id}/work.create",
                headers=ceo,
            )
            deadline = time.monotonic() + 5
            waiting = False
            while time.monotonic() < deadline:
                with connect_postgres() as observer:
                    waiting = observer.execute(
                        "SELECT EXISTS (SELECT 1 FROM pg_stat_activity "
                        "WHERE query LIKE 'DELETE FROM project_grants%' "
                        "AND wait_event_type='Lock')"
                    ).fetchone()[0]
                if waiting:
                    break
                time.sleep(0.01)
            assert waiting, "grant revocation did not wait for the protected transaction"

        response = revoke.result(timeout=5)
        assert response.status_code == 204, response.text
        assert client.post(f"/v1/projects/{project}/work", headers={
            "X-Agent-Token": worker["X-Agent-Token"],
        }, json={"title": "Must be denied", "author_id": "ignored",
                "acceptance_criteria": ["denial"]}).status_code == 403


@pytest.mark.skipif(
    not os.getenv("AAO_TEST_POSTGRES_URL") or os.getenv("AAO_TEST_DB_DISPOSABLE") != "yes",
    reason="Explicit disposable PostgreSQL database required",
)
def test_grant_expiring_while_lock_waiting_is_denied(monkeypatch):
    """A grant is checked against wall-clock time after waiting for its row lock."""
    from fastapi import HTTPException

    from aao.postgresql_connection import connect_postgres
    from aao.principal_credentials import digest_token
    from aao.work_management_api import AuthenticatedPrincipal, app, require_grant

    monkeypatch.setenv("AAO_POSTGRES_URL", os.environ["AAO_TEST_POSTGRES_URL"])
    monkeypatch.setenv("AAO_CEO_TOKEN", "grant-expiry-ceo")
    ceo = {"X-CEO-Token": "grant-expiry-ceo"}
    with TestClient(app) as client:
        agent_id = "agent-" + str(uuid4())
        agent_token = client.post("/v1/principals/credentials", headers=ceo, json={"principal_id": agent_id, "kind": "AGENT"}).json()["token"]
        mandate = client.post("/v1/mandates", headers=ceo, json={
            "title": f"Grant expiry {uuid4()}", "objective": "Test expiry after lock wait",
        }).json()["id"]
        assert client.post(f"/v1/mandates/{mandate}/confirm", headers=ceo).status_code == 200
        project = client.post("/v1/projects", headers=ceo, json={
            "name": f"Grant expiry {uuid4()}", "mandate_id": mandate,
        }).json()["id"]
        assert client.post(f"/v1/projects/{project}/grants", headers=ceo, json={
            "principal_id": agent_id, "capability": "work.create",
        }).status_code == 201
        with connect_postgres() as setup:
            setup.execute(
                "UPDATE project_grants SET expires_at=clock_timestamp()+interval '1 second' "
                "WHERE project_id=%s AND principal_id=%s AND capability='work.create'", (project, agent_id),
            )

        def check_grant():
            try:
                with connect_postgres() as db:
                    require_grant(
                        db,
                        AuthenticatedPrincipal(agent_id, digest_token(agent_token), "AGENT"),
                        project,
                        "work.create",
                    )
                return "allowed"
            except HTTPException:
                return "denied"

        with ThreadPoolExecutor(max_workers=1) as pool, connect_postgres() as blocker:
            blocker.execute(
                "UPDATE project_grants SET expires_at=expires_at WHERE project_id=%s "
                "AND principal_id=%s AND capability='work.create'",
                (project, agent_id),
            )
            check = pool.submit(check_grant)
            deadline = time.monotonic() + 5
            waiting = False
            while time.monotonic() < deadline:
                with connect_postgres() as observer:
                    waiting = observer.execute(
                        "SELECT EXISTS (SELECT 1 FROM pg_stat_activity "
                        "WHERE query LIKE 'SELECT 1 FROM project_grants%' "
                        "AND wait_event_type='Lock')"
                    ).fetchone()[0]
                if waiting:
                    break
                time.sleep(0.01)
            assert waiting, "grant check did not wait for the held row lock"
            time.sleep(1.1)
        assert check.result(timeout=5) == "denied"
