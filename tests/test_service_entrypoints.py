from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

from aao import auditor_dispatch, r1_pipeline


def _write(path: Path, data: dict, mode: int = 0o600) -> Path:
    path.write_text(json.dumps(data))
    path.chmod(mode)
    return path


def _integrator_config(tmp_path: Path) -> tuple[dict, Path]:
    registry = _write(tmp_path / "registry.json", {"integrator_identity": "integrator"})
    config = {
        "schema": r1_pipeline.CONFIG_SCHEMA,
        "repo": "owner/project",
        "git_remote": "https://example.invalid/owner/project.git",
        "mirror": str(tmp_path / "mirror"), "inbox": str(tmp_path / "inbox"),
        "reports": str(tmp_path / "reports"), "state_dir": str(tmp_path / "state"),
        "trust_registry": str(registry), "ledger": str(tmp_path / "ledger"),
        "ledger_anchor": str(tmp_path / "ledger.anchor"), "heartbeat": str(tmp_path / "heartbeat"),
        "heartbeat_sequence": str(tmp_path / "integrator" / "heartbeat.sequence"),
        "freeze": str(tmp_path / "freeze"), "integrator_private_key": str(tmp_path / "integrator.pem"),
    }
    return config, registry


def _auditor_config(tmp_path: Path) -> dict:
    return {
        "schema": auditor_dispatch.CONFIG_SCHEMA,
        "inbox": str(tmp_path / "inbox"), "reports": str(tmp_path / "reports"),
        "key": str(tmp_path / "auditor.pem"), "repository_root": str(tmp_path / "mirror"),
        "repo": "owner/project",
    }


def test_integrator_config_custody_and_exact_fields(tmp_path: Path):
    config, _registry = _integrator_config(tmp_path)
    path = _write(tmp_path / "config.json", config)
    uid = os.getuid()
    assert r1_pipeline.load_config(path, owners=(uid,), registry_owners=(uid,))["repo"] == "owner/project"

    path.chmod(0o620)
    with pytest.raises(ValueError):
        r1_pipeline.load_config(path, owners=(uid,), registry_owners=(uid,))
    path.chmod(0o600)
    with pytest.raises(ValueError):
        r1_pipeline.load_config(path, owners=(uid + 1,), registry_owners=(uid,))
    for altered in ({**config, "unexpected": True}, {k: v for k, v in config.items() if k != "repo"}):
        _write(path, altered)
        with pytest.raises(ValueError):
            r1_pipeline.load_config(path, owners=(uid,), registry_owners=(uid,))


def test_integrator_main_rejects_unprotected_config_before_github(monkeypatch, tmp_path: Path, capsys):
    config, _ = _integrator_config(tmp_path)
    path = _write(tmp_path / "config.json", config, mode=0o622)
    monkeypatch.setattr(r1_pipeline, "CONFIG_PATH", path)
    monkeypatch.setattr(sys, "argv", ["aao.r1_pipeline", "tick"])
    monkeypatch.setattr(r1_pipeline, "GitHubAppClient", lambda *_: pytest.fail("GitHub must not be touched"))
    assert r1_pipeline.main() == 1
    assert json.loads(capsys.readouterr().err)["status"] == "failed"


def test_auditor_config_custody_and_exact_fields(tmp_path: Path):
    config = _auditor_config(tmp_path)
    path = _write(tmp_path / "dispatch.json", config)
    uid = os.getuid()
    assert auditor_dispatch.load_config(path, owners=(uid,))["repo"] == "owner/project"

    path.chmod(0o620)
    with pytest.raises(ValueError):
        auditor_dispatch.load_config(path, owners=(uid,))
    path.chmod(0o600)
    with pytest.raises(ValueError):
        auditor_dispatch.load_config(path, owners=(uid + 1,))
    for altered in ({**config, "unexpected": True}, {k: v for k, v in config.items() if k != "repo"}):
        _write(path, altered)
        with pytest.raises(ValueError):
            auditor_dispatch.load_config(path, owners=(uid,))


def test_auditor_main_rejects_unprotected_config_before_github(monkeypatch, tmp_path: Path, capsys):
    path = _write(tmp_path / "dispatch.json", _auditor_config(tmp_path), mode=0o622)
    monkeypatch.setattr(auditor_dispatch, "CONFIG_PATH", path)
    monkeypatch.setattr(sys, "argv", ["aao.auditor_dispatch", "once"])
    monkeypatch.setattr(auditor_dispatch, "GitHubAppClient", lambda *_: pytest.fail("GitHub must not be touched"))
    assert auditor_dispatch.main() == 1
    assert json.loads(capsys.readouterr().err)["status"] == "failed"


def test_integrator_main_one_pass_uses_fixed_role_and_prints_json(monkeypatch, tmp_path: Path, capsys):
    config, _ = _integrator_config(tmp_path)
    config["integrator_identity"] = "integrator"
    calls = {}

    class FakeClient:
        def installation_token(self, owner, repo):
            calls["token_for"] = (owner, repo)
    client = FakeClient()

    monkeypatch.setattr(r1_pipeline, "CONFIG_PATH", Path("/etc/test-integrator.json"))
    monkeypatch.setattr(r1_pipeline, "load_config", lambda path, owners, registry_owners: config)
    def fake_client(role):
        calls["role"] = role
        return client
    monkeypatch.setattr(r1_pipeline, "GitHubAppClient", fake_client)

    def fake_tick(*args, git_token=None):
        calls["tick_args"] = args
        calls["git_token"] = git_token
        return [{"status": "failed", "pr_number": 8}]

    monkeypatch.setattr(r1_pipeline, "integrator_tick", fake_tick)
    monkeypatch.setattr(sys, "argv", ["aao.r1_pipeline", "tick"])
    uid = os.getuid()
    assert r1_pipeline.main(owners=(uid,), registry_owners=(uid,)) == 0
    assert json.loads(capsys.readouterr().out) == [{"status": "failed", "pr_number": 8}]
    assert calls["role"] == "aao-integrator"
    assert calls["token_for"] == ("owner", "project")
    assert calls["tick_args"][0].repository == "owner/project"
    assert callable(calls["git_token"])


def test_auditor_main_one_pass_uses_fixed_role_anchor_and_prints_json(monkeypatch, tmp_path: Path, capsys):
    config = _auditor_config(tmp_path)
    calls = {}

    class FakeClient:
        def installation_token(self, owner, repo):
            calls["token_for"] = (owner, repo)
    client = FakeClient()

    monkeypatch.setattr(auditor_dispatch, "CONFIG_PATH", Path("/etc/test-dispatch.json"))
    monkeypatch.setattr(auditor_dispatch, "load_config", lambda path: config)
    def fake_client(role):
        calls["role"] = role
        return client
    monkeypatch.setattr(auditor_dispatch, "GitHubAppClient", fake_client)

    def fake_dispatch(*args, **kwargs):
        calls["args"], calls["kwargs"] = args, kwargs
        return [{"id": "a" * 64, "status": "failed"}]

    monkeypatch.setattr(auditor_dispatch, "dispatch_once", fake_dispatch)
    monkeypatch.setattr(sys, "argv", ["aao.auditor_dispatch", "once"])
    assert auditor_dispatch.main() == 0
    assert json.loads(capsys.readouterr().out) == [{"id": "a" * 64, "status": "failed"}]
    assert calls["role"] == "aao-auditor"
    assert calls["token_for"] == ("owner", "project")
    assert calls["kwargs"]["anchor_path"] == auditor_dispatch.ANCHOR_PATH
    assert calls["kwargs"]["expected_repo"] == "owner/project"
