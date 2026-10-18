"""End-to-end inert admission: mandate -> project -> task -> durable queue."""
import os
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient


def test_inert_queue_is_disabled_until_explicitly_enabled():
    import aao.main as main
    with TemporaryDirectory() as tmp:
        main.DB_PATH = os.path.join(tmp, "aao.db")
        main.CEO_TOKEN = "dev-ceo"
        main.WORK_TOKEN = "dev-worker"
        main.SANDBOX_QUEUE_ENABLED = False
        with TestClient(main.app) as client:
            ceo = {"X-CEO-Token": "dev-ceo"}
            worker = {"X-Work-Token": "dev-worker"}
            mandate = client.post("/v1/mandates", headers=ceo,
                                  json={"title": "Sandbox", "objective": "Inert execution"}).json()["id"]
            assert client.post(f"/v1/mandates/{mandate}/confirm", headers=ceo).status_code == 200
            project = client.post("/v1/projects", headers=ceo,
                                  json={"name": "Sandbox", "mandate_id": mandate}).json()["id"]
            for cap in ("work.create", "work.transition"):
                assert client.post(f"/v1/projects/{project}/grants", headers=ceo, json={"principal_id": "development-worker", "capability": cap}).status_code == 201
            work = client.post(f"/v1/projects/{project}/work", headers=worker,
                               json={"title": "Dry run", "author_id": "dev-author",
                                     "acceptance_criteria": ["Entry recorded"]}).json()["id"]
            assert client.post(f"/v1/work/{work}/sandbox-queue", headers=worker).status_code == 503
            main.SANDBOX_QUEUE_ENABLED = True
            assert client.post(f"/v1/work/{work}/sandbox-queue", headers=worker).status_code == 409
            assert client.post(f"/v1/work/{work}/transition", headers=worker,
                               json={"status": "READY"}).status_code == 200
            assert client.post(f"/v1/work/{work}/sandbox-queue").status_code == 403
            first = client.post(f"/v1/work/{work}/sandbox-queue", headers=worker)
            assert first.status_code == 202
            second = client.post(f"/v1/work/{work}/sandbox-queue", headers=worker)
            assert second.status_code == 202
            assert second.json()["execution_id"] == first.json()["execution_id"]
            assert client.post(f"/v1/projects/{project}/pause", headers=worker).status_code == 200
            main.SANDBOX_QUEUE_ENABLED = False


def test_cancelled_project_never_admitted_to_sandbox():
    import aao.main as main
    with TemporaryDirectory() as tmp:
        main.DB_PATH = os.path.join(tmp, "aao.db")
        main.CEO_TOKEN = "dev-ceo"
        main.WORK_TOKEN = "dev-worker"
        main.SANDBOX_QUEUE_ENABLED = True
        with TestClient(main.app) as client:
            ceo = {"X-CEO-Token": "dev-ceo"}
            worker = {"X-Work-Token": "dev-worker"}
            mandate = client.post("/v1/mandates", headers=ceo,
                                  json={"title": "Pilot", "objective": "Safe"}).json()["id"]
            client.post(f"/v1/mandates/{mandate}/confirm", headers=ceo)
            project = client.post("/v1/projects", headers=ceo,
                                  json={"name": "Pilot", "mandate_id": mandate}).json()["id"]
            for cap in ("work.create", "work.transition"):
                grant = client.post(f"/v1/projects/{project}/grants", headers=ceo, json={"principal_id": "development-worker", "capability": cap})
                assert grant.status_code == 201
            work = client.post(f"/v1/projects/{project}/work", headers=worker,
                               json={"title": "Test", "author_id": "dev-author",
                                     "acceptance_criteria": ["x"]}).json()["id"]
            client.post(f"/v1/work/{work}/transition", headers=worker,
                        json={"status": "READY"})
            client.post(f"/v1/projects/{project}/cancel", headers=ceo)
            assert client.post(f"/v1/work/{work}/sandbox-queue", headers=worker).status_code == 409
            main.SANDBOX_QUEUE_ENABLED = False
