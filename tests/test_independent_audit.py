import json
import os
import pwd
import shutil
import subprocess
from pathlib import Path

import pytest

from aao import independent_audit
from aao.independent_audit import (
    LEGACY_RETIRED,
    AuditError,
    audit_candidate,
    promotion_decision,
    run_sandboxed,
)

USER = pwd.getpwuid(os.geteuid()).pw_name


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


def commit(repo, files, message):
    for name, content in files.items():
        path = repo / name
        if content is None:
            path.unlink()
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", message)
    return git(repo, "rev-parse", "HEAD")


REVIEWED = "a" * 40


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(independent_audit, "auditor_revision", lambda: REVIEWED)
    if not shutil.which("openssl"):
        pytest.skip("openssl is required for auditor signatures")
    repo = tmp_path / "upstream"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "implementer")
    git(repo, "config", "user.email", "implementer@example.invalid")
    base = commit(repo, {"src/app.py": "X = 1\n", "tests/test_app.py": "def test_x():\n    assert 1\n    assert 2\n"},
                  "base")
    auditor = tmp_path / "auditor"
    auditor.mkdir()
    key, public = auditor / "key.pem", auditor / "key.pub"
    subprocess.run(["openssl", "genpkey", "-algorithm", "ED25519", "-out", str(key)], check=True)
    subprocess.run(["openssl", "pkey", "-in", str(key), "-pubout", "-out", str(public)], check=True)
    key.chmod(0o600)

    def write_policy(**overrides):
        policy = {
            "version": "GOV-REV-001/v1.1", "auditor_id": "aao-auditor", "auditor_os_user": USER,
            "developer_os_users": ["implementer-account"], "required_checks": ["test"],
            "auditors": {"aao-auditor": str(public)}, "audit_checks": {"unit": ["-m", "pytest"]},
            "protected_paths": ["src/aao/pr_conformity.py", ".github/workflows/"], "dispositions": {},
            "trusted_auditor_revisions": [REVIEWED],
            **overrides,
        }
        path = auditor / "policy.json"
        path.write_text(json.dumps(policy), encoding="utf-8")
        return path

    return {"repo": repo, "base": base, "auditor": auditor, "key": key, "policy": write_policy}


def ok_runner(clone, argv):
    return 0, "1 passed", ""


def ci(sha):
    return {"test": {"conclusion": "success", "head_sha": sha}}


def run_audit(env, sha, name="run", **kwargs):
    options = {"key_path": env["key"], "implementer_ids": ["implementer"], "ci_checks": ci(sha), "runner": ok_runner}
    options.update(kwargs)
    return audit_candidate(source=str(env["repo"]), candidate_sha=sha, base_sha=env["base"],
                           policy_path=options.pop("policy_path", None) or env["policy"](),
                           output=env["auditor"] / name, ledger=env["auditor"] / "ledger.jsonl", **options)


def gate(env, sha, name="run", implementer="implementer", checkout_name=None, base=None):
    checkout = env["auditor"] / f"merge-{checkout_name or name}"
    subprocess.run(["git", "clone", "-q", str(env["repo"]), str(checkout)], check=True)
    git(checkout, "checkout", "-q", "--detach", sha)
    out = env["auditor"] / name
    signature = out / "report.sig"
    return promotion_decision(checkout, env["auditor"] / "policy.json", out / "report.json",
                              signature if signature.exists() else None, ci(sha), implementer,
                              env["auditor"] / "ledger.jsonl", current_base_sha=base or env["base"])


def test_legacy_path_never_approves_signs_or_promotes(env):
    # SL-01 (second-line review): replaces the former "approved, signed and promotable" test. The legacy path
    # takes policy, key and ledger from its caller, so a clean candidate with full custody must still not pass.
    sha = commit(env["repo"], {"src/app.py": "X = 2\n"}, "change")
    report = run_audit(env, sha)
    assert report["verdict"] == "provisional" and not report["blocking_findings"]
    assert LEGACY_RETIRED in report["custody_problems"]
    assert report["candidate_sha"] == sha and report["base_sha"] == env["base"]
    assert not (env["auditor"] / "run" / "report.sig").exists()
    result = gate(env, sha)
    assert not result.conformant and LEGACY_RETIRED in result.reasons


def test_protected_path_blocks_until_exact_sha_disposition(env):
    sha = commit(env["repo"], {"src/aao/pr_conformity.py": "weakened = True\n"}, "touch gate")
    report = run_audit(env, sha)
    assert report["verdict"] == "reject"
    assert "protected-path:src/aao/pr_conformity.py" in report["blocking_findings"]
    assert not gate(env, sha).conformant
    disposed = env["policy"](dispositions={f"{sha}:protected-path:src/aao/pr_conformity.py": "reviewed"})
    report = run_audit(env, sha, name="disposed", policy_path=disposed)
    assert report["verdict"] == "provisional" and not report["blocking_findings"]  # SL-01: never "approve"
    assert not gate(env, sha, name="disposed").conformant


def test_test_weakening_is_a_blocking_finding(env):
    sha = commit(env["repo"], {"tests/test_app.py": "import pytest\n\n@pytest.mark.skip\ndef test_x():\n    pass\n"},
                 "weaken")
    blocking = run_audit(env, sha)["blocking_findings"]
    assert any(item.startswith("added-skip:tests/test_app.py") for item in blocking)
    assert "removed-asserts:tests/test_app.py" in blocking


def test_failing_audit_check_or_ci_rejects(env):
    sha = commit(env["repo"], {"src/app.py": "X = 3\n"}, "change")
    report = run_audit(env, sha, runner=lambda clone, argv: (1, "", "boom"), ci_checks={})
    assert report["verdict"] == "reject"
    assert {"audit-check-failed:unit", "ci-check-not-successful:test"} <= set(report["blocking_findings"])


def test_head_moving_before_verdict_records_nothing(env):
    sha = commit(env["repo"], {"src/app.py": "X = 4\n"}, "change")
    with pytest.raises(AuditError, match="moved"):
        run_audit(env, sha, current_head=lambda: "f" * 40)
    assert not (env["auditor"] / "ledger.jsonl").exists()
    assert not (env["auditor"] / "run" / "report.json").exists()


def test_veto_is_sticky_over_an_earlier_approval(env):
    sha = commit(env["repo"], {"src/app.py": "X = 5\n"}, "change")
    run_audit(env, sha)
    assert not gate(env, sha).conformant  # SL-01: the legacy gate always denies
    veto = run_audit(env, sha, name="veto", veto_reason="unsafe design")
    assert veto["verdict"] == "veto" and veto["veto"] is True
    reasons = gate(env, sha, checkout_name="again").reasons
    assert "candidate has a recorded audit veto" in reasons
    assert "audit report is not the latest recorded decision for this candidate" in reasons


def test_developer_controlled_custody_is_provisional_unsigned_and_rejected(env):
    sha = commit(env["repo"], {"src/app.py": "X = 6\n"}, "change")
    report = run_audit(env, sha, policy_path=env["policy"](developer_os_users=[USER]))
    assert report["verdict"] == "provisional" and report["custody_problems"]
    assert not (env["auditor"] / "run" / "report.sig").exists()
    assert "signed audit report is absent" in gate(env, sha).reasons


def test_unreviewed_auditor_code_cannot_sign(env, monkeypatch):
    sha = commit(env["repo"], {"src/app.py": "X = 9\n"}, "change")
    monkeypatch.setattr(independent_audit, "auditor_revision", lambda: REVIEWED + "-dirty")
    report = run_audit(env, sha)
    assert report["verdict"] == "provisional" and report["auditor_revision"].endswith("-dirty")
    assert not (env["auditor"] / "run" / "report.sig").exists()


def test_readable_key_and_self_audit_are_rejected(env):
    sha = commit(env["repo"], {"src/app.py": "X = 7\n"}, "change")
    env["key"].chmod(0o644)
    assert run_audit(env, sha)["verdict"] == "provisional"
    env["key"].chmod(0o600)
    report = run_audit(env, sha, name="self", implementer_ids=["aao-auditor"])
    assert "auditor-is-implementer-or-implementer-unknown" in report["blocking_findings"]


def test_naively_truncated_ledger_is_detected(env):
    sha = commit(env["repo"], {"src/app.py": "X = 8\n"}, "change")
    run_audit(env, sha, name="first", veto_reason="stop")
    run_audit(env, sha)
    ledger = env["auditor"] / "ledger.jsonl"
    lines = ledger.read_text().splitlines()
    ledger.write_text(lines[1] + "\n")  # drop the veto entry
    assert "audit ledger is missing or invalid" in gate(env, sha).reasons


def test_secrets_visible_inside_the_sandbox_are_refused(env):
    sha = commit(env["repo"], {"src/app.py": "X = 10\n"}, "change")
    with pytest.raises(AuditError, match="readable by candidate code"):
        run_audit(env, sha, key_path=Path("/etc/aao-auditor/key.pem"))
    assert not (env["auditor"] / "run").exists()


def test_unknown_sha_is_refused(env):
    with pytest.raises(AuditError):
        run_audit(env, "e" * 40)


def test_sandbox_has_read_only_candidate_and_no_network(tmp_path):
    if not shutil.which("bwrap") or subprocess.run(["bwrap", "--unshare-all", "--ro-bind", "/", "/", "true"], check=False, capture_output=True).returncode:
        pytest.skip("unprivileged bubblewrap namespaces are unavailable")
    (tmp_path / "f").write_text("x")
    probe = ("import socket, pathlib\n"
             "try:\n    pathlib.Path('f').write_text('y'); print('WROTE')\nexcept OSError: print('RO')\n"
             "try:\n    socket.create_connection(('1.1.1.1', 53), 2); print('NET')\nexcept OSError: print('NONET')\n")
    code, out, _ = run_sandboxed(tmp_path, ["-c", probe], timeout_seconds=30)
    assert code == 0 and "RO" in out and "NONET" in out
    assert (tmp_path / "f").read_text() == "x"


def test_base_moving_invalidates_the_verdict(env):
    sha = commit(env["repo"], {"src/app.py": "X = 11\n"}, "change")
    with pytest.raises(AuditError, match="base moved"):
        run_audit(env, sha, name="moving", current_base=lambda: "f" * 40)
    run_audit(env, sha)
    assert not gate(env, sha).conformant  # SL-01: the legacy gate always denies
    reasons = gate(env, sha, checkout_name="newbase", base="e" * 40).reasons
    assert "audit report targets a different base than the current pull request base" in reasons


def test_gate_rejects_report_from_auditor_revision_no_longer_trusted(env):
    sha = commit(env["repo"], {"src/app.py": "X = 12\n"}, "change")
    run_audit(env, sha)
    env["policy"](trusted_auditor_revisions=["c" * 40])
    reasons = gate(env, sha).reasons
    assert "audit report was produced by an auditor revision the policy does not trust" in reasons
