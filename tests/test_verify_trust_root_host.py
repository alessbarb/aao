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


def test_tree_writers_flags_symlink_escaping_tree(tmp_path):
    (tmp_path / "link").symlink_to("/etc/passwd")
    assert verifier.tree_writers(tmp_path, {os.getuid()})


def test_ancestors_safe_rejects_writable_parent(tmp_path):
    child = tmp_path / "d" / "f"
    child.parent.mkdir()
    child.parent.chmod(0o777)
    assert verifier.ancestors_safe(child, {os.getuid()})


def test_sudoers_grants(tmp_path, monkeypatch):
    sudoers = tmp_path / "sudoers"
    sudoers.write_text("root ALL=(ALL:ALL) ALL\n%sudo ALL=(ALL:ALL) ALL\n"
                       "alessbarb ALL=(aao-pm,aao-impl-codex) ALL\n")
    real_path = verifier.Path

    def fake(path, *rest):
        if str(path) == "/etc/sudoers":
            return sudoers
        if str(path) == "/etc/sudoers.d":
            return tmp_path / "none"
        return real_path(path, *rest)

    monkeypatch.setattr(verifier, "Path", fake)
    assert verifier.sudoers_grants("aao-auditor") == []
    sudoers.write_text(sudoers.read_text() + "eve ALL=(aao-auditor) NOPASSWD: ALL\nbob ALL=(ALL) ALL\n")
    assert len(verifier.sudoers_grants("aao-auditor")) == 2
