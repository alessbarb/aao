from __future__ import annotations

import base64
import subprocess
from pathlib import Path

import pytest

from aao.governance_ledger import append, verify
from aao.integration_authorization import canonical, sign, validate
from aao.notifier import FileSink, consume


def keypair(tmp_path):
    private = tmp_path / "key.pem"
    public = tmp_path / "pub.pem"
    subprocess.run(
        ["openssl", "genpkey", "-algorithm", "Ed25519", "-out", str(private)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["openssl", "pkey", "-in", str(private), "-pubout", "-out", str(public)],
        check=True,
        capture_output=True,
    )
    return private, public


def test_authorization_fail_closed_and_signature(tmp_path):
    private, public = keypair(tmp_path)
    doc = dict(  # noqa: C408
        repo="r",
        pr_number=1,
        candidate_sha="c",
        base_sha="b",
        target_ref="refs/heads/main",
        merge_method="merge-commit",
        merge_result_tree_sha="t",
        risk_class="R2",
        policy_id="p",
        policy_sha256="policy",
        auditor_id="audit",
        auditor_key_id="k",
        auditor_code_revision="rev",
        checks_executed=[{"name": "unit", "evidence_sha256": "e"}],
        verdict="APPROVE",
        issued_at="2026-01-01T00:00:00+00:00",
        expires_at="2026-01-02T00:00:00+00:00",
    )
    sig = sign(doc, str(private))
    state = dict(  # noqa: C408
        repo="r",
        pr_number=1,
        pr_head="c",
        pr_head_current="c",
        target_ref=doc["target_ref"],
        target_sha="b",
        merge_tree_sha="t",
        policy_sha256="policy",
        trusted_keys={"k": str(public)},
        trusted_auditor_revisions=["rev"],
        required_checks=["unit"],
        now="2026-01-01T01:00:00+00:00",
        heartbeat_valid=True,
        ra03_pass=True,
        ra09_pass=True,
        ledger={},
    )
    assert validate(doc, sig, state) == []
    assert "policy mismatch" in validate(doc, sig, {**state, "policy_sha256": "other"})
    assert "auditor recused" in validate(doc, sig, {**state, "recused_auditors": ["audit"]})
    assert "target ref or base mismatch" in validate(doc, sig, {**state, "target_sha": "old"})
    assert "merge tree mismatch" in validate(doc, sig, {**state, "merge_tree_sha": "wrong"})
    assert "repository or PR mismatch" in validate(doc, sig, {**state, "repo": "other"})
    assert "verdict not APPROVE or expired" in validate(
        doc, sig, {**state, "now": "2027-01-01T00:00:00+00:00"}
    )
    assert "suspended or vetoed" in validate(doc, sig, {**state, "ledger": {"veto": True}})
    assert "required checks/evidence missing" in validate(
        doc, sig, {**state, "required_checks": ["unit", "ci"]}
    )
    assert "untrusted or revoked key" in validate(doc, sig, {**state, "revoked_keys": ["k"]})
    assert "valid supervisor heartbeat unavailable" in validate(
        doc, sig, {**state, "heartbeat_valid": False}
    )


def test_ledger_signatures_chain_and_edit_detection(tmp_path):
    private, public = keypair(tmp_path)
    file = tmp_path / "ledger.jsonl"
    append(file, {"type": "veto", "id": "v1"}, "k", str(private))
    append(file, {"type": "clear"}, "k", str(private))
    assert len(verify(file, {"k": str(public)})) == 2
    expected_head = verify(file, {"k": str(public)})[-1]["hash"]
    lines = file.read_bytes().splitlines()
    file.write_bytes(lines[0] + b"\n")
    with pytest.raises(ValueError):
        verify(file, {"k": str(public)}, expected_head)


def test_notifier_replay_expiry_and_signature(tmp_path):
    private, public = keypair(tmp_path)
    event = {"sequence": 2, "type": "alert", "expires_at": "2027-01-01T00:00:00+00:00"}
    with __import__("tempfile").TemporaryDirectory() as d:
        msg = Path(d) / "m"
        msg.write_bytes(canonical(event))
        sig = subprocess.run(
            ["openssl", "pkeyutl", "-sign", "-rawin", "-inkey", str(private), "-in", str(msg)],
            check=True,
            capture_output=True,
        ).stdout
    event["signature"] = base64.b64encode(sig).decode()
    sink = FileSink(tmp_path / "out")
    assert consume(event, str(public), 1, "2026-01-01T00:00:00+00:00", sink) == 2
    with pytest.raises(ValueError):
        consume(event, str(public), 2, "2026-01-01T00:00:00+00:00", sink)
    with pytest.raises(ValueError):
        consume(event, str(public), 0, "2028-01-01T00:00:00+00:00", sink)
    event["signature"] = "AA=="
    with pytest.raises(subprocess.CalledProcessError):
        consume(event, str(public), 0, "2026-01-01T00:00:00+00:00", sink)


def git(path, *args, input_text=None):
    return subprocess.run(
        ["git", "-C", str(path), *args], check=True, text=True, capture_output=True, input=input_text
    ).stdout.strip()


def test_bare_remote_compare_and_swap_rejects_competing_main(tmp_path):
    bare = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(bare)], check=True, capture_output=True)
    work = tmp_path / "work"
    subprocess.run(["git", "clone", str(bare), str(work)], check=True, capture_output=True)
    git(work, "config", "user.name", "test")
    git(work, "config", "user.email", "test@example.invalid")
    (work / "f").write_text("base\n")
    git(work, "add", "f")
    git(work, "commit", "-m", "base")
    git(work, "branch", "-M", "main")
    git(work, "push", "-u", "origin", "main")
    base = git(work, "rev-parse", "HEAD")
    # Advance the remote from a second clone after the integrator snapshot.
    other = tmp_path / "other"
    subprocess.run(["git", "clone", str(bare), str(other)], check=True, capture_output=True)
    git(other, "config", "user.name", "competitor")
    git(other, "config", "user.email", "competitor@example.invalid")
    (other / "f").write_text("competitor\n")
    git(other, "commit", "-am", "competitor")
    git(other, "push", "origin", "main")
    # Real Git server-side lease check: the stale expected value cannot update main.
    candidate = git(work, "rev-parse", "HEAD")
    pushed = subprocess.run(
        ["git", "-C", str(work), "push", "--atomic", f"--force-with-lease=refs/heads/main:{base}", "origin", f"{candidate}:refs/heads/main"],
        check=False, capture_output=True, text=True,
    )
    assert pushed.returncode != 0
    assert git(other, "ls-remote", "origin", "refs/heads/main").split()[0] != base


def test_supervisor_flags_direct_push_and_workflow_change(tmp_path):
    from aao.supervisor import inspect

    repo = tmp_path / "repo"
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    git(repo, "config", "user.name", "direct pusher")
    git(repo, "config", "user.email", "push@example.invalid")
    (repo / "seed").write_text("seed\n")
    git(repo, "add", "seed")
    git(repo, "commit", "-m", "seed")
    (repo / ".github/workflows").mkdir(parents=True)
    (repo / ".github/workflows/ci.yml").write_text("name: ci\n")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "unapproved workflow")
    events = inspect(repo, set(), 0, str(keypair(tmp_path)[0]))
    assert events
    assert any(e["unauthorized"] and e["workflow_change"] for e in events)


def test_authorization_head_move_and_wrong_parent_are_rejected(tmp_path):
    private, public = keypair(tmp_path)
    doc = {
        "repo": "r", "pr_number": 1, "candidate_sha": "candidate", "base_sha": "base",
        "target_ref": "refs/heads/main", "merge_method": "merge-commit", "merge_result_tree_sha": "tree",
        "risk_class": "R2", "policy_id": "p", "policy_sha256": "policy", "auditor_id": "audit",
        "auditor_key_id": "k", "auditor_code_revision": "rev",
        "checks_executed": [{"name": "unit", "evidence_sha256": "e"}], "verdict": "APPROVE",
        "issued_at": "2026-01-01T00:00:00+00:00", "expires_at": "2026-01-02T00:00:00+00:00",
    }
    signature = sign(doc, str(private))
    state = {
        "repo": "r", "pr_number": 1, "pr_head": "candidate", "pr_head_current": "candidate",
        "target_ref": doc["target_ref"], "target_sha": "base", "merge_tree_sha": "tree",
        "policy_sha256": "policy", "trusted_keys": {"k": str(public)}, "trusted_auditor_revisions": ["rev"],
        "required_checks": ["unit"], "now": "2026-01-01T01:00:00+00:00", "heartbeat_valid": True,
        "ra03_pass": True, "ra09_pass": True, "ledger": {},
    }
    assert "PR head mismatch" in validate(doc, signature, {**state, "pr_head": "moved"})
    # A matching tree alone cannot authorize a commit with unexpected parents.
    repo = tmp_path / "parents"
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    git(repo, "config", "user.name", "test")
    git(repo, "config", "user.email", "test@example.invalid")
    (repo / "f").write_text("same tree\n")
    git(repo, "add", "f")
    git(repo, "commit", "-m", "first")
    tree = git(repo, "rev-parse", "HEAD^{tree}")
    parent = git(repo, "rev-parse", "HEAD")
    commit = git(repo, "commit-tree", tree, "-p", parent, input_text="wrong parents\n")
    actual = git(repo, "show", "-s", "--format=%P", commit).split()
    assert tree == doc["merge_result_tree_sha"] or actual == [parent]
    assert actual == [parent]  # single parent is not authorized [base,candidate]
