import importlib.util
import json
import os
import pwd
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "github_apps" / "verify_app_auth.py"
PERMS = {"contents": "write", "metadata": "read"}


def _load(tmp_path, monkeypatch, *, repos, app="aao-x", canonical_only=True, parent="org/aao", total=None):
    spec = importlib.util.spec_from_file_location("verify_app_auth", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    me = pwd.getpwuid(os.getuid())
    home = tmp_path / "home"
    (home / ".config" / "aao").mkdir(parents=True)
    key = home / ".config" / "aao" / f"{app}.pem"
    subprocess.run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(key)],
                   check=True, capture_output=True)
    key.chmod(0o600)
    reg = tmp_path / "reg.json"
    reg.write_text(json.dumps({"canonical_repository": "org/aao", "apps": [
        {"name": app, "app_id": 7, "installation_id": 9, "linux_uid": me.pw_name, "key_file": str(key)}]}))
    (tmp_path / "m").mkdir()
    (tmp_path / "m" / f"{app}.json").write_text(json.dumps({"default_permissions": PERMS}))
    monkeypatch.setattr(mod, "REGISTRY", reg)
    monkeypatch.setattr(mod, "MANIFESTS", tmp_path / "m")
    monkeypatch.setattr(mod, "_trusted", lambda path: True)
    monkeypatch.setattr(mod, "CANONICAL_ONLY", {app} if canonical_only else set())
    fake_me = pwd.struct_passwd((*me[:5], str(home), me[6]))
    monkeypatch.setattr(mod.pwd, "getpwuid", lambda uid: fake_me)
    calls = []

    def fake(method, path, token):
        calls.append((method, path, token))
        if path == "/app":
            return 200, {"id": 7, "slug": app, "owner": {"login": "org"}, "permissions": PERMS, "events": []}
        if path == "/app/installations/9":
            return 200, {"app_id": 7, "account": {"login": "org"}, "repository_selection": "selected",
                         "permissions": PERMS, "suspended_at": None}
        if path.endswith("/access_tokens"):
            return 201, {"token": "ghs_SECRET", "expires_at": "x"}
        if path.startswith("/installation/repositories"):
            return 200, {"total_count": len(repos) if total is None else total,
                         "repositories": [{"full_name": r} for r in repos]}
        if path.startswith("/repos/"):
            return 200, {"fork": parent is not None, "parent": {"full_name": parent} if parent else None}
        if method == "DELETE":
            return 204, None
        raise AssertionError(path)

    monkeypatch.setattr(mod, "_call", fake)
    return mod, calls, key


def test_pass_and_no_secret_in_output(tmp_path, monkeypatch):
    mod, calls, key = _load(tmp_path, monkeypatch, repos=["org/aao"])
    ok, rec = mod.verify("aao-x")
    assert ok, rec
    out = json.dumps(rec)
    assert "ghs_SECRET" not in out and "PRIVATE KEY" not in out and calls[0][2] not in out
    assert key.read_text().split("\n")[1] not in out
    assert calls[-1][:2] == ("DELETE", "/installation/token") and calls[-1][2] == "ghs_SECRET"
    assert rec["accessible_repositories"] == ["org/aao"]


def test_implementer_reaching_canonical_fails(tmp_path, monkeypatch):
    mod, _, _ = _load(tmp_path, monkeypatch, repos=["org/aao"], canonical_only=False)
    ok, rec = mod.verify("aao-x")
    assert not ok and rec["checks"]["implementer_cannot_reach_canonical"] is False


def test_extra_repo_fails_for_canonical_role(tmp_path, monkeypatch):
    mod, _, _ = _load(tmp_path, monkeypatch, repos=["org/aao", "org/other"])
    assert mod.verify("aao-x")[0] is False


@pytest.mark.parametrize("mode", [0o640, 0o644])
def test_key_mode_enforced(tmp_path, monkeypatch, mode):
    mod, calls, key = _load(tmp_path, monkeypatch, repos=["org/aao"])
    key.chmod(mode)
    ok, rec = mod.verify("aao-x")
    assert not ok and "0600" in rec["error"] and calls == []


def test_symlinked_key_refused(tmp_path, monkeypatch):
    mod, calls, key = _load(tmp_path, monkeypatch, repos=["org/aao"])
    real = tmp_path / "real.pem"
    key.rename(real)
    key.symlink_to(real)
    assert mod.verify("aao-x")[0] is False and calls == []


def test_linux_user_mapping():
    from aao.github_app_auth import linux_user
    assert linux_user("aao-impl-agy") == "aao-impl-ag" and linux_user("aao-pm") == "aao-pm"


def test_implementer_on_fork_passes(tmp_path, monkeypatch):
    mod, _, _ = _load(tmp_path, monkeypatch, repos=["agents/aao"], canonical_only=False)
    ok, rec = mod.verify("aao-x")
    assert ok, rec


@pytest.mark.parametrize("repos,parent", [([], "org/aao"), (["agents/aao"], None), (["agents/aao"], "else/aao")])
def test_implementer_without_fork_of_canonical_fails(tmp_path, monkeypatch, repos, parent):
    mod, _, _ = _load(tmp_path, monkeypatch, repos=repos, canonical_only=False, parent=parent)
    assert mod.verify("aao-x")[0] is False


def test_inconsistent_total_count_fails(tmp_path, monkeypatch):
    mod, calls, _ = _load(tmp_path, monkeypatch, repos=[], total=3)
    ok, rec = mod.verify("aao-x")
    assert not ok and "inconsistent" in rec["error"] and calls[-1][0] == "DELETE"


def test_untrusted_registry_refused(tmp_path, monkeypatch):
    mod, calls, _ = _load(tmp_path, monkeypatch, repos=["org/aao"])
    monkeypatch.setattr(mod, "_trusted", lambda path: False)
    assert mod.verify("aao-x")[0] is False and calls == []


def test_key_file_must_match_app(tmp_path, monkeypatch):
    mod, calls, _ = _load(tmp_path, monkeypatch, repos=["org/aao"])
    reg = json.loads(mod.REGISTRY.read_text())
    reg["apps"][0]["name"] = "aao-y"
    mod.REGISTRY.write_text(json.dumps(reg))
    (mod.MANIFESTS / "aao-y.json").write_text(json.dumps({"default_permissions": PERMS}))
    ok, rec = mod.verify("aao-y")
    assert not ok and "aao-y.pem" in rec["error"] and calls == []
