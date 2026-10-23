from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from aao import r1_pipeline
from aao.identity_attribution import GitHubIdentityProvider


def test_git_auth_is_environment_only(monkeypatch, tmp_path: Path):
    token = "private-test-token"
    seen = {}

    def fake_run(argv, **kwargs):
        seen.update(argv=argv, env=kwargs["env"])
        return SimpleNamespace(stdout="ok\n")

    monkeypatch.setattr(r1_pipeline.subprocess, "run", fake_run)
    assert r1_pipeline._git(tmp_path, "fetch", "https://github.com/o/r.git", token=token) == "ok"
    assert token not in " ".join(seen["argv"])
    assert token not in "".join(str(path.read_bytes()) for path in tmp_path.rglob("*") if path.is_file())
    assert seen["env"]["GIT_CONFIG_COUNT"] == "2"
    assert seen["env"]["GIT_CONFIG_KEY_0"] == "credential.helper"
    assert seen["env"]["GIT_CONFIG_VALUE_1"].startswith("AUTHORIZATION: basic ")
    assert seen["env"]["GIT_CONFIG_VALUE_0"] == ""
    assert seen["env"]["GIT_TERMINAL_PROMPT"] == "0"
    assert seen["env"]["GIT_CONFIG_NOSYSTEM"] == "1"
    assert seen["env"]["GIT_CONFIG_GLOBAL"] == "/dev/null"


def test_github_git_remote_requires_token(tmp_path: Path):
    with pytest.raises(RuntimeError, match="token is unavailable"):
        r1_pipeline._git(tmp_path, "fetch", "https://github.com/o/r.git")


@pytest.mark.parametrize(
    ("slug", "installation_id", "status", "expected"),
    [("integrator", 12, 200, "integrator"), ("other", 12, 200, ""),
     ("integrator", 99, 200, ""), ("integrator", 12, 500, "")],
)
def test_github_identity_requires_app_and_repository_installation(slug, installation_id, status, expected):
    class FakeAppClient:
        _installation_id = 12

        def app_request(self, method, path):
            body = {"slug": slug} if path == "/app" else {"id": installation_id}
            return SimpleNamespace(status=status, body=body)

    provider = GitHubIdentityProvider("integrator", FakeAppClient(), "owner/project")
    assert provider.push_identity("refs/heads/main", "old", "new") == expected


def test_github_identity_fails_closed_on_api_error():
    class FakeAppClient:
        _installation_id = 12

        def app_request(self, method, path):
            raise RuntimeError("API unavailable")

    provider = GitHubIdentityProvider("integrator", FakeAppClient(), "owner/project")
    assert provider.push_identity("refs/heads/main", "old", "new") == ""
