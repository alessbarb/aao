"""PostgreSQL integration coverage for authenticated, immutable patch proposals."""

import os
import subprocess
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


@pytest.mark.skipif(
    not os.getenv("AAO_TEST_POSTGRES_URL") or os.getenv("AAO_TEST_DB_DISPOSABLE") != "yes",
    reason="Explicit disposable PostgreSQL test database required",
)
def test_agent_patch_proposal_is_authorized_immutable_and_visible(monkeypatch, tmp_path):
    from aao.postgresql_connection import connect_postgres
    from aao.work_management_api import app

    repository = tmp_path / "repo"
    repository.mkdir()
    subprocess.run(["git", "-C", str(repository), "init", "--quiet"], check=True)
    (repository / "src/aao").mkdir(parents=True)
    source_file = repository / "src/aao/sample.py"
    source_file.write_text("VALUE = 1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repository), "add", "src/aao/sample.py"], check=True)
    subprocess.run([
        "git", "-C", str(repository), "-c", "user.name=AAO test",
        "-c", "user.email=test@example.invalid", "commit", "--quiet", "-m", "base",
    ], check=True)
    base_sha = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    monkeypatch.setenv("AAO_POSTGRES_URL", os.environ["AAO_TEST_POSTGRES_URL"])
    monkeypatch.setenv("AAO_CEO_TOKEN", "patch-proposal-integration-ceo")
    monkeypatch.setenv("AAO_SELF_DEV_REPOSITORY", str(repository))
    ceo = {"X-CEO-Token": "patch-proposal-integration-ceo"}
    with TestClient(app) as client:
        agent_id = "patch-agent-" + str(uuid4())
        agent = {"X-Agent-Token": client.post(
            "/v1/principals/credentials", headers=ceo,
            json={"principal_id": agent_id, "kind": "AGENT"},
        ).json()["token"]}
        mandate = client.post("/v1/mandates", headers=ceo, json={
            "title": "Patch proposal test " + str(uuid4()),
            "objective": "Test constrained source patch proposal",
        }).json()["id"]
        assert client.post(f"/v1/mandates/{mandate}/confirm", headers=ceo).status_code == 200
        project = client.post("/v1/projects", headers=ceo, json={
            "name": "Patch proposal test", "mandate_id": mandate,
        }).json()["id"]
        for capability in ("work.create", "work.admit", "work.progress", "project.read", "code.propose"):
            response = client.post(f"/v1/projects/{project}/grants", headers=ceo, json={
                "principal_id": agent_id, "capability": capability,
            })
            assert response.status_code == 201, response.text
        work = client.post(f"/v1/projects/{project}/work", headers=agent, json={
            "title": "Propose a real source improvement",
            "author_id": "ignored-client-value",
            "acceptance_criteria": ["Patch is stored without changing canonical checkout"],
        }).json()["id"]
        assert client.post(f"/v1/work/{work}/admit", headers=agent).status_code == 200
        assert client.post(f"/v1/work/{work}/progress", headers=agent).json()["status"] == "IN_PROGRESS"

        patch = (
            "diff --git a/src/aao/sample.py b/src/aao/sample.py\n"
            "index 2c2b30a..981f5f4 100644\n"
            "--- a/src/aao/sample.py\n+++ b/src/aao/sample.py\n"
            "@@ -1 +1 @@\n-VALUE = 1\n+VALUE = 2\n"
        )
        payload = {"base_sha": base_sha, "patch": patch}
        proposal = client.post(f"/v1/work/{work}/patch-proposals", headers=agent, json=payload)
        assert proposal.status_code == 201, proposal.text
        result = proposal.json()
        assert result["status"] == "PROPOSED"
        assert result["base_sha"] == base_sha
        assert result["changed_paths"] == ["src/aao/sample.py"]
        assert result["validated_in_disposable_clone"] is False
        assert result["applied_to_canonical_checkout"] is False
        assert source_file.read_text(encoding="utf-8") == "VALUE = 1\n"
        duplicate = client.post(f"/v1/work/{work}/patch-proposals", headers=agent, json=payload)
        assert duplicate.status_code == 409
        validated = client.post(
            f"/v1/work/{work}/patch-proposals/{result['proposal_id']}/validate",
            headers=agent,
        )
        assert validated.status_code == 201, validated.text
        validation = validated.json()
        assert validation["patch_sha256"] == result["patch_sha256"]
        assert validation["base_sha"] == base_sha
        assert validation["validated_in_disposable_clone"] is True
        assert validation["applied_to_canonical_checkout"] is False
        duplicate_validation = client.post(
            f"/v1/work/{work}/patch-proposals/{result['proposal_id']}/validate",
            headers=agent,
        )
        assert duplicate_validation.status_code == 409
        assert source_file.read_text(encoding="utf-8") == "VALUE = 1\n"
        board = client.get(f"/v1/projects/{project}/board", headers=agent)
        task = next(item for item in board.json() if item["id"] == work)
        assert task["patch_proposals"][0]["patch_sha256"] == result["patch_sha256"]
        assert task["patch_proposals"][0]["applied"] is False
        assert task["patch_proposals"][0]["validations"][0]["candidate_tree"] == validation["candidate_tree"]
        with connect_postgres() as db:
            persisted = db.execute(
                "SELECT proposer_id,base_sha,patch_sha256,status FROM patch_proposals WHERE id=%s",
                (result["proposal_id"],),
            ).fetchone()
        assert tuple(persisted) == (
            agent_id, base_sha, result["patch_sha256"], "PROPOSED",
        )
