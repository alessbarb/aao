"""PostgreSQL integration tests, opt-in for explicitly disposable databases."""
import os
import time
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
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
def test_capability_catalog_is_project_scoped_and_does_not_grant_execution(monkeypatch):
    from aao.work_management_api import app

    monkeypatch.setenv("AAO_POSTGRES_URL", os.environ["AAO_TEST_POSTGRES_URL"])
    monkeypatch.setenv("AAO_CEO_TOKEN", "capability-ceo")
    ceo = {"X-CEO-Token": "capability-ceo"}
    with TestClient(app) as client:
        agent_id = "cap-agent-" + str(uuid4())
        token = client.post("/v1/principals/credentials", headers=ceo, json={
            "principal_id": agent_id, "kind": "AGENT",
        }).json()["token"]
        worker = {"X-Agent-Token": token}
        mandate_id = client.post("/v1/mandates", headers=ceo, json={
            "title": "Capability registry " + str(uuid4()), "objective": "Test local catalog",
        }).json()["id"]
        client.post(f"/v1/mandates/{mandate_id}/confirm", headers=ceo)
        project_id = client.post("/v1/projects", headers=ceo, json={
            "name": "Capability test", "mandate_id": mandate_id,
        }).json()["id"]
        payload = {
            "capability_id": "aao.test.skill", "version": "1.0.0",
            "capability_type": "agent_skill",
            "provenance": {
                "kind": "repository",
                "path": ".agents/skills/aao-postgres-authorization-concurrency/SKILL.md",
            },
            "contract": {
                "purpose": "Design and verify PostgreSQL authorization and concurrency behavior",
                "compatible_roles": ["engineering"],
                "inputs": ["authorization or concurrency change"],
                "outputs": ["verified implementation and test evidence"],
                "usage_limits": ["no production database", "no external effects"],
            },
            "required_permissions": ["execution.claim"],
            "risks": ["instructions are untrusted inputs and cannot grant permissions"],
            "dependencies": [],
            "tests": [
                (
                    "tests/test_project_workflow_integration.py::"
                    "test_capability_catalog_is_project_scoped_and_does_not_grant_execution"
                ),
            ],
            "compatibility": {"agent_roles": ["engineering"]},
            "evidence": [
                "sha256:" + sha256(Path(
                    ".agents/skills/aao-postgres-authorization-concurrency/SKILL.md",
                ).read_bytes()).hexdigest(),
            ],
        }
        path = f"/v1/projects/{project_id}/capabilities"
        assert client.post(path, headers=worker, json=payload).status_code == 403
        assert client.post(f"/v1/projects/{project_id}/grants", headers=ceo, json={
            "principal_id": agent_id, "capability": "work.create",
        }).status_code == 201
        assert client.post(path, headers=worker, json={
            **payload, "provenance": {},
        }).status_code == 422
        assert client.post(path, headers=worker, json={
            **payload, "evidence": [],
        }).status_code == 422
        assert client.post(path, headers=worker, json={
            **payload, "contract": {"purpose": "incomplete skill"},
        }).status_code == 422
        registered = client.post(path, headers=worker, json=payload)
        assert registered.status_code == 201, registered.text
        assert registered.json()["execution_authorized"] is False
        assert client.post(path, headers=worker, json=payload).status_code == 409

        listed = client.get(path, headers=ceo)
        assert listed.status_code == 200, listed.text
        catalog_entry = listed.json()[0]
        assert catalog_entry["capability_id"] == payload["capability_id"]
        assert catalog_entry["version"] == payload["version"]
        assert catalog_entry["capability_type"] == "agent_skill"
        assert catalog_entry["required_permissions"] == ["execution.claim"]
        assert catalog_entry["created_by"] == agent_id
        assert catalog_entry["status"] == "registered_local"
        assert catalog_entry["execution_authorized"] is False
        assert "project_id" not in catalog_entry
        assert client.get(path, headers=worker).status_code == 403
        task_response = client.post(f"/v1/projects/{project_id}/work", headers=worker, json={
            "title": "Evaluate PostgreSQL authorization skill reuse",
            "author_id": agent_id,
            "acceptance_criteria": ["Compare reuse, adaptation, and new build"],
        })
        assert task_response.status_code == 201, task_response.text
        task_id = task_response.json()["id"]
        evaluation_payload = {
            "task_id": task_id,
            "options": [
                {"choice": "reuse", "fit": 5, "security": 5, "cost": 5,
                 "time": 5, "tokens": 5, "maintenance": 5},
                {"choice": "adapt", "fit": 4, "security": 4, "cost": 3,
                 "time": 3, "tokens": 3, "maintenance": 4},
                {"choice": "build", "fit": 3, "security": 3, "cost": 2,
                 "time": 2, "tokens": 2, "maintenance": 2},
            ],
            "rationale": "The existing PostgreSQL concurrency skill covers this task's test procedure.",
            "evidence": payload["evidence"],
            "capability_id": payload["capability_id"], "version": payload["version"],
        }
        assessment_path = f"/v1/projects/{project_id}/capability-evaluations"
        evaluation = client.post(assessment_path, headers=worker, json=evaluation_payload)
        assert evaluation.status_code == 201, evaluation.text
        assert evaluation.json()["recommendation"] == "reuse"
        assert evaluation.json()["execution_authorized"] is False
        assert client.get(assessment_path, headers=worker).status_code == 403
        from aao.postgresql_connection import connect_postgres
        with connect_postgres() as db:
            assert db.execute(
                "SELECT 1 FROM project_grants WHERE project_id=%s AND principal_id=%s "
                "AND capability='execution.claim'", (project_id, agent_id),
            ).fetchone() is None
        assert client.post(f"/v1/projects/{project_id}/grants", headers=ceo, json={
            "principal_id": agent_id, "capability": "project.read",
        }).status_code == 201
        assert client.get(path, headers=worker).json()[0]["capability_id"] == "aao.test.skill"
        recorded_evaluation = client.get(assessment_path, headers=worker)
        assert recorded_evaluation.status_code == 200
        assert recorded_evaluation.json()[0]["task_id"] == task_id
        assert recorded_evaluation.json()[0]["details"]["recommendation"] == "reuse"
        assert client.get(path + "?capability_type=agent_skill", headers=ceo).json()[0]["capability_id"] == "aao.test.skill"
        assert client.get(path + "?capability_type=made_up", headers=ceo).status_code == 422
        promotion = {**payload, "capability_id": "forbidden.promotion", "status": "candidate_for_promotion"}
        assert client.post(path, headers=worker, json=promotion).status_code == 422

        isolated_agent = "cap-isolated-reader-" + str(uuid4())
        isolated_token = client.post("/v1/principals/credentials", headers=ceo, json={
            "principal_id": isolated_agent, "kind": "AGENT",
        }).json()["token"]
        isolated_reader = {"X-Agent-Token": isolated_token}
        isolated_mandate = client.post("/v1/mandates", headers=ceo, json={
            "title": "Isolated capability mandate " + str(uuid4()),
            "objective": "Check capability project isolation",
        }).json()["id"]
        assert client.post(f"/v1/mandates/{isolated_mandate}/confirm", headers=ceo).status_code == 200
        isolated_project = client.post("/v1/projects", headers=ceo, json={
            "name": "Isolated capability project " + str(uuid4()), "mandate_id": isolated_mandate,
        }).json()["id"]
        assert client.post(f"/v1/projects/{isolated_project}/grants", headers=ceo, json={
            "principal_id": isolated_agent, "capability": "project.read",
        }).status_code == 201
        isolated_capabilities = f"/v1/projects/{isolated_project}/capabilities"
        isolated_evaluations = f"/v1/projects/{isolated_project}/capability-evaluations"
        assert client.get(isolated_capabilities, headers=isolated_reader).json() == []
        assert client.get(isolated_evaluations, headers=isolated_reader).json() == []
        assert client.post(f"/v1/projects/{isolated_project}/grants", headers=ceo, json={
            "principal_id": isolated_agent, "capability": "work.create",
        }).status_code == 201
        assert client.post(isolated_evaluations, headers=isolated_reader,
                           json=evaluation_payload).status_code == 404


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


@pytest.mark.skipif(
    not os.getenv("AAO_TEST_POSTGRES_URL") or os.getenv("AAO_TEST_DB_DISPOSABLE") != "yes",
    reason="Explicit disposable PostgreSQL database required",
)
def test_registered_repository_check_requires_task_selection_before_queue_claim(monkeypatch):
    from aao.execution_queue import claim
    from aao.work_management_api import app

    monkeypatch.setenv("AAO_POSTGRES_URL", os.environ["AAO_TEST_POSTGRES_URL"])
    monkeypatch.setenv("AAO_CEO_TOKEN", "capability-check-ceo")
    monkeypatch.setenv("AAO_SANDBOX_QUEUE_ENABLED", "true")
    ceo = {"X-CEO-Token": "capability-check-ceo"}
    with TestClient(app) as client:
        identity = "check-agent-" + str(uuid4())
        issued = client.post("/v1/principals/credentials", headers=ceo, json={
            "principal_id": identity, "kind": "AGENT",
        })
        assert issued.status_code == 201, issued.text
        agent = {"X-Agent-Token": issued.json()["token"]}
        mandate = client.post("/v1/mandates", headers=ceo, json={
            "title": "Repository check " + str(uuid4()), "objective": "Test bounded repo check",
        }).json()["id"]
        assert client.post(f"/v1/mandates/{mandate}/confirm", headers=ceo).status_code == 200
        project = client.post("/v1/projects", headers=ceo, json={
            "name": "Repository check", "mandate_id": mandate,
        }).json()["id"]
        for capability in ("work.create", "work.admit", "execution.claim", "project.read"):
            assert client.post(f"/v1/projects/{project}/grants", headers=ceo, json={
                "principal_id": identity, "capability": capability,
            }).status_code == 201
        work = client.post(f"/v1/projects/{project}/work", headers=agent, json={
            "title": "Run registered core checks", "author_id": identity,
            "acceptance_criteria": ["Exact fixed check is executed in sandbox"],
        }).json()["id"]
        registered = client.post(f"/v1/projects/{project}/capabilities", headers=agent, json={
            "capability_id": "aao.repository-check", "version": "1.0.0",
            "capability_type": "cli_script", "provenance": {"kind": "repository"},
            "contract": {
                "purpose": "Run fixed allow-listed core tests",
                "entrypoint": "aao.sandboxed_repository_checks:core-unit",
                "inputs": ["fixed core-unit check id"],
                "outputs": ["test result and exact candidate SHA"],
                "platform": "Linux with bubblewrap",
            },
            "required_permissions": ["execution.claim"], "risks": ["local test code runs"],
            "dependencies": [], "tests": ["tests/test_sandboxed_repository_checks.py"],
            "compatibility": {}, "evidence": ["repo source"],
        })
        assert registered.status_code == 201, registered.text
        evaluation = client.post(
            f"/v1/projects/{project}/capability-evaluations", headers=agent,
            json={
                "task_id": work,
                "options": [
                    {"choice": choice, "fit": fit, "security": fit, "cost": fit,
                     "time": fit, "tokens": fit, "maintenance": fit}
                    for choice, fit in (("reuse", 5), ("adapt", 3), ("build", 1))
                ],
                "rationale": "Reuse the checked-in fixed sandbox instead of building a new tool.",
                "evidence": ["tests/test_sandboxed_repository_checks.py"],
                "capability_id": "aao.repository-check", "version": "1.0.0",
            },
        )
        assert evaluation.status_code == 201, evaluation.text
        assert evaluation.json()["recommendation"] == "reuse"
        assert client.post(f"/v1/work/{work}/admit", headers=agent).status_code == 200
        request = {"capability_id": "aao.repository-check", "version": "1.0.0",
                   "check_id": "core-unit"}
        not_selected = client.post(
            f"/v1/work/{work}/stage-repository-check", headers=agent,
            json={**request, "capability_id": "other"},
        )
        assert not_selected.status_code == 409
        staged = client.post(
            f"/v1/work/{work}/stage-repository-check", headers=agent, json=request,
        )
        assert staged.status_code == 202, staged.text
        lease = claim(identity, agent_credential=issued.json()["token"], project_id=project)
        assert lease["input"] == {
            "type": "aao.repository-check.v1", "check_id": "core-unit",
            "capability_id": "aao.repository-check", "version": "1.0.0",
        }
        board = client.get(f"/v1/projects/{project}/board", headers=agent)
        execution = board.json()[0]["executions"][0]
        assert execution["id"] == staged.json()["execution_id"]
        assert execution["status"] == "RUNNING"
