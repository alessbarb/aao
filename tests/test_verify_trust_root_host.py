import importlib.util
import os
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("verifier", Path(__file__).parents[1] / "scripts/verify_trust_root_host.py")
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


def test_auditor_cgroup_accepts_only_auditor_units():
    ok = verifier.AUDITOR_CGROUP.match
    assert ok(r"0::/system.slice/system-aao\x2dauditor.slice/aao-auditor@abc.service")
    assert ok("0::/system.slice/aao-auditor-dispatch.service")
    assert not ok("0::/user.slice/user-1000.slice/session-3.scope")
    assert not ok("0::/system.slice/aao-auditor-evil.service")
    assert not ok(r"0::/system.slice/system-aao\x2dauditor.slice/aao-auditor@x.service/extra")


def test_tree_writers_flags_group_writable_and_foreign_owner(tmp_path):
    (tmp_path / "a").write_text("x")
    (tmp_path / "a").chmod(0o644)
    assert verifier.tree_writers(tmp_path, {os.getuid()}) == []
    (tmp_path / "a").chmod(0o664)
    assert verifier.tree_writers(tmp_path, {os.getuid()})
    (tmp_path / "a").chmod(0o644)
    assert verifier.tree_writers(tmp_path, {0})  # owned by us, not by an allowed uid


def test_tree_writers_flags_symlink_to_non_root_target(tmp_path):
    tree, outside = tmp_path / "tree", tmp_path / "outside.py"
    tree.mkdir(mode=0o755)
    tree.chmod(0o755)
    outside.write_text("x")
    outside.chmod(0o644)
    (tree / "link").symlink_to(outside)  # target owned by us, not root: a write path into the tree
    assert verifier.tree_writers(tree, {os.getuid()})


def test_tree_writers_accepts_symlink_to_root_only_target(tmp_path):
    tmp_path.chmod(0o755)
    (tmp_path / "python").symlink_to("/usr/bin/python3")
    assert verifier.tree_writers(tmp_path, {os.getuid()}) == []


def test_ancestors_safe_rejects_writable_parent(tmp_path):
    child = tmp_path / "d" / "f"
    child.parent.mkdir()
    child.parent.chmod(0o777)
    assert verifier.ancestors_safe(child, {os.getuid()})


def test_runas_users_parses_sudo_list_output():
    out = """User eve may run the following commands on host:
    (aao-pm, aao-impl-codex) ALL
    (ALL : ALL) NOPASSWD: /usr/bin/true
    (aao-auditor) /bin/sh
"""
    assert verifier.runas_users(out) == {"aao-pm", "aao-impl-codex", "ALL", "aao-auditor"}
    assert verifier.runas_users("User bob is not allowed to run sudo on host.") == set()


def test_cron_user_field(tmp_path, monkeypatch):
    crond = tmp_path / "cron.d"
    crond.mkdir()
    (crond / "x").write_text("*/5 * * * * aao-auditor /bin/true\n# 1 2 3 4 5 aao-auditor no\n@reboot aao-auditor /x\n")
    (crond / "y").write_text("1 2 3 4 5 root /bin/true\n")
    real_path = verifier.Path
    mapping = {"/etc/crontab": tmp_path / "none", "/etc/cron.d": crond,
               "/var/spool/cron/crontabs": tmp_path / "none", "/var/spool/cron/atjobs": tmp_path / "none"}
    monkeypatch.setattr(verifier, "Path", lambda p, *r: mapping.get(str(p)) or real_path(p, *r))
    monkeypatch.setattr(verifier, "uid", lambda name: 999999)
    assert len(verifier.cron_entries("aao-auditor")) == 2


def test_units_running_as_flags_foreign_unit(tmp_path, monkeypatch):
    system = tmp_path / "system"
    system.mkdir()
    (system / "aao-auditor@.service").write_text("[Service]\nUser=aao-auditor\n")
    monkeypatch.setattr(verifier, "UNIT_DIRS", (str(system),))
    monkeypatch.setattr(verifier, "uid", lambda name: 1005)
    allowed = {"aao-auditor@.service"}
    assert verifier.units_running_as("aao-auditor", allowed) == []
    (system / "evil.service.d").mkdir()
    (system / "evil.service.d" / "x.conf").write_text("[Service]\nUser = 1005\n")
    assert verifier.units_running_as("aao-auditor", allowed) == [str(system / "evil.service.d" / "x.conf")]


def test_sudo_grant_to_root_reaches_the_auditor(monkeypatch):
    class Result:
        returncode, stderr = 0, ""
        stdout = "User eve may run:\n    (root) /usr/bin/vim\n"
    monkeypatch.setattr(verifier.pwd, "getpwall", lambda: [verifier.pwd.struct_passwd(
        ("eve", "x", 2000, 2000, "", "/home/eve", "/bin/bash"))])
    monkeypatch.setattr(verifier.subprocess, "run", lambda *a, **k: Result())
    monkeypatch.setattr(verifier, "uid", lambda name: 1005)
    assert verifier.sudo_grants("aao-auditor") == ["eve: runas ['root']"]


def test_local_polkit_rule_is_flagged(tmp_path, monkeypatch):
    rules = tmp_path / "rules.d"
    rules.mkdir()
    (rules / "10-local.rules").write_text('polkit.addRule(function(a, s) { return polkit.Result.YES; });')
    (rules / "20-other.rules").write_text("// nothing relevant")
    monkeypatch.setattr(verifier, "POLKIT_DIRS", (str(rules),))
    monkeypatch.setattr(verifier, "POLKIT_ACTIONS", ())
    monkeypatch.setattr(verifier, "_package_pristine", lambda path: False)
    assert verifier.polkit_grants("aao-auditor") == [f"{rules / '10-local.rules'} (local or modified rule)"]
    monkeypatch.setattr(verifier, "_package_pristine", lambda path: True)
    assert verifier.polkit_grants("aao-auditor") == []
