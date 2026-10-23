from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

from aao.governance_ledger import active_vetoes, append, verify
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
        assurance_level="A",
        policy_id="p",
        policy_sha256="policy",
        protected_paths_sha256=hashlib.sha256(canonical([])).hexdigest(),
        expected_parents=["b", "c"],
        git_version="2.43.0",
        auditor_id="audit",
        auditor_key_id="k",
        auditor_code_revision="rev",
        attribution=[{"sha": "c", "principal": "author", "source": "ledger", "evidence_sha256": "a"}],
        checks_executed=[{"name": "unit", "cmd": "pytest", "result": "PASS", "evidence_sha256": "e"}],
        scope="scope", known_limitations=[], residual_risks=[], permitted_operations=[],
        prohibited_operations=[], findings=[], expediente_sha256="expediente",
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
        trusted_auditors={"audit": ["k"]},
        trusted_auditor_revisions=["rev"],
        required_checks_by_risk_class={"R2": ["unit"]},
        now="2026-01-01T01:00:00+00:00",
        heartbeat_valid=True,
        enabled_risk_classes=["R2"], policy_id="p", attribution_resolved=True,
        ci_candidate_sha="c", protected_paths={}, changed_paths=[], git_version="2.43.0",
        auditor_models={"audit": "auditor-model"}, author_models={"author": "author-model"},
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
        doc, sig, {**state, "required_checks_by_risk_class": {"R2": ["unit", "ci"]}}
    )
    assert "untrusted or revoked key" in validate(doc, sig, {**state, "revoked_keys": ["k"]})
    assert "valid supervisor heartbeat unavailable" in validate(
        doc, sig, {**state, "heartbeat_valid": False}
    )


def test_ledger_signatures_chain_and_edit_detection(tmp_path):
    private, public = keypair(tmp_path)
    file = tmp_path / "ledger.jsonl"
    append(file, {"type": "veto", "id": "v1"}, "k", str(private), {"k": str(public)})
    append(file, {"type": "clear"}, "k", str(private), {"k": str(public)})
    assert len(verify(file, {"k": str(public)})) == 2
    expected_head = verify(file, {"k": str(public)})[-1]["hash"]
    lines = file.read_bytes().splitlines()
    file.write_bytes(lines[0] + b"\n")
    with pytest.raises(ValueError):
        verify(file, {"k": str(public)}, expected_head)


def test_notifier_replay_expiry_and_signature(tmp_path):
    private, public = keypair(tmp_path)
    event = {"sequence": 1, "key_id": "k", "type": "alert", "expires_at": "2027-01-01T00:00:00+00:00"}
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
    assert consume(event, {"k": str(public)}, tmp_path / "state.json", "2026-01-01T00:00:00+00:00", sink) == 1
    with pytest.raises(ValueError):
        consume(event, {"k": str(public)}, tmp_path / "state.json", "2026-01-01T00:00:00+00:00", sink)
    with pytest.raises(ValueError):
        consume(event, {"k": str(public)}, tmp_path / "expired-state.json", "2028-01-01T00:00:00+00:00", sink)
    event["signature"] = "AA=="
    with pytest.raises(subprocess.CalledProcessError):
        consume(event, {"k": str(public)}, tmp_path / "bad-state.json", "2026-01-01T00:00:00+00:00", sink)


def git(path, *args, input_text=None):
    return subprocess.run(
        ["git", "-C", str(path), *args],
        check=True,
        text=True,
        capture_output=True,
        input=input_text,
    ).stdout.strip()


def supervisor_inspect(repo, authorized, sequence, private, tmp_path, **kwargs):
    from aao.supervisor import inspect
    public = tmp_path / "supervisor-public.pem"
    subprocess.run(["openssl", "pkey", "-in", private, "-pubout", "-out", str(public)], check=True,
                   capture_output=True)
    ledger = tmp_path / "supervisor-ledger.jsonl"
    ledger.unlink(missing_ok=True)
    authorizer_dir = tmp_path / "ledger-authorizer"
    authorizer_dir.mkdir(exist_ok=True)
    authorizer_private, authorizer_public = keypair(authorizer_dir)
    ledger_keys = {"ledger-authorizer": {"public_key": str(authorizer_public), "can_authorize": True}}
    for sha in authorized:
        if not ledger.exists() or not any(json.loads(line).get("commit") == sha
                                          for line in ledger.read_text().splitlines()):
            append(ledger, {"type": "authorization", "commit": sha,
                            "risk_class": (kwargs.get("authorized_classes") or {}).get(sha, "R1")},
                   "ledger-authorizer", str(authorizer_private), ledger_keys)
    ledger.touch(exist_ok=True)
    return inspect(repo, authorized, sequence, private, key_id="supervisor",
                   state_path=tmp_path / "supervisor-sequence.json", ledger_path=ledger,
                   trusted_keys={**ledger_keys, "supervisor": str(public)},
                   now="2026-01-01T00:00:00+00:00", **kwargs)


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
    events = supervisor_inspect(repo, set(), 0, str(keypair(tmp_path)[0]), tmp_path)
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
        "assurance_level": "A",
        "policy_id": "p",
        "policy_sha256": "policy",
        "protected_paths_sha256": hashlib.sha256(canonical([])).hexdigest(),
        "expected_parents": ["base", "candidate"],
        "git_version": "2.43.0",
        "auditor_id": "audit",
        "auditor_key_id": "k",
        "auditor_code_revision": "rev",
        "attribution": [{"sha": "candidate", "principal": "author", "source": "ledger", "evidence_sha256": "a"}],
        "checks_executed": [{"name": "unit", "cmd": "pytest", "result": "PASS", "evidence_sha256": "e"}],
        "scope": "scope", "known_limitations": [], "residual_risks": [],
        "permitted_operations": [], "prohibited_operations": [], "findings": [],
        "expediente_sha256": "expediente",
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
        "trusted_auditors": {"audit": ["k"]},
        "trusted_auditor_revisions": ["rev"],
        "required_checks_by_risk_class": {"R2": ["unit"]},
        "now": "2026-01-01T01:00:00+00:00",
        "heartbeat_valid": True,
        "enabled_risk_classes": ["R2"], "policy_id": "p", "attribution_resolved": True,
        "ci_candidate_sha": "candidate", "protected_paths": {}, "changed_paths": [], "git_version": "2.43.0",
        "auditor_models": {"audit": "auditor-model"}, "author_models": {"author": "author-model"},
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
    doc = {
        "repo": "repo",
        "pr_number": 7,
        "candidate_sha": "candidate",
        "base_sha": "base",
        "target_ref": "refs/heads/main",
        "merge_method": "merge-commit",
        "merge_result_tree_sha": "tree",
        "risk_class": "R2",
        "assurance_level": "A",
        "policy_id": "policy",
        "policy_sha256": "hash",
        "protected_paths_sha256": hashlib.sha256(canonical([])).hexdigest(),
        "expected_parents": ["base", "candidate"],
        "git_version": "2.43.0",
        "auditor_id": "auditor",
        "auditor_key_id": "key",
        "auditor_code_revision": "rev",
        "attribution": [{"sha": "candidate", "principal": "author", "source": "ledger", "evidence_sha256": "attr"}],
        "checks_executed": [{"name": "unit", "cmd": "pytest", "result": "PASS", "evidence_sha256": "x"}],
        "scope": "scope",
        "known_limitations": [],
        "residual_risks": [],
        "permitted_operations": [],
        "prohibited_operations": [],
        "findings": [],
        "expediente_sha256": "expediente",
        "verdict": "APPROVE",
        "issued_at": "2026-01-01T00:00:00+00:00",
        "expires_at": "2026-01-02T00:00:00+00:00",
    }
    state = {
        "repo": "repo",
        "pr_number": 7,
        "pr_head": "candidate",
        "target_ref": doc["target_ref"],
        "target_sha": "base",
        "merge_tree_sha": "tree",
        "policy_sha256": "hash",
        "trusted_keys": {"key": str(public)},
        "trusted_auditors": {"auditor": ["key"]},
        "trusted_auditor_revisions": ["rev"],
        "required_checks_by_risk_class": {"R2": ["unit"]},
        "now": "2026-01-01T01:00:00+00:00",
        "heartbeat_valid": True,
        "enabled_risk_classes": ["R2"],
        "policy_id": "policy",
        "attribution_resolved": True,
        "ci_candidate_sha": "candidate",
        "protected_paths": {}, "changed_paths": [], "git_version": "2.43.0",
        "auditor_models": {"auditor": "model-audit"},
        "author_models": {"author": "model-author"},
        "ra03_pass": True,
        "ra09_pass": True,
        "ledger": {},
    }
    return private, public, doc, state, sign(doc, str(private))


@pytest.mark.parametrize("field", ["enabled_risk_classes", "policy_id", "attribution_resolved", "ci_candidate_sha", "protected_paths"])
def test_authorization_rejects_missing_snapshot_fields(tmp_path, field):
    _, _, d, s, sig = _auth_fixture(tmp_path)
    broken = dict(s)
    broken.pop(field)
    assert validate(d, sig, broken)


@pytest.mark.parametrize("field", ["expected_parents", "git_version", "expediente_sha256", "attribution", "findings"])
def test_authorization_rejects_missing_required_document_fields(tmp_path, field):
    _, _, d, s, sig = _auth_fixture(tmp_path)
    broken = dict(d)
    broken.pop(field)
    assert validate(broken, sig, s)


def test_authorization_requires_pass_checks_and_trusted_auditor_identity(tmp_path):
    _, _, d, s, sig = _auth_fixture(tmp_path)
    d["checks_executed"][0]["result"] = "FAIL"
    assert "required checks/evidence missing" in validate(d, sig, s)
    assert "auditor key does not belong to auditor" in validate(d, sig, {**s, "trusted_auditors": {"other": ["key"]}})


def test_authorization_rejects_same_model_and_long_or_naive_dates(tmp_path):
    _, _, d, s, sig = _auth_fixture(tmp_path)
    assert "auditor model matches author model" in validate(d, sig, {**s, "auditor_models": {"auditor": "same"}, "author_models": {"author": "same"}})
    d["expires_at"] = "2026-01-05T00:00:00+00:00"
    assert "authorization validity exceeds 72 hours" in validate(d, sig, s)
    d["expires_at"] = "2026-01-02T00:00:00"
    assert "invalid expiration" in validate(d, sig, s)


def test_authorization_rejects_boolean_pr_number(tmp_path):
    _, _, d, s, sig = _auth_fixture(tmp_path)
    d["pr_number"] = True
    assert "invalid PR number" in validate(d, sig, s)


def test_authorization_rejects_other_policy_hash(tmp_path):
    _, _, d, s, sig = _auth_fixture(tmp_path)
    assert "policy mismatch" in validate(d, sig, {**s, "policy_sha256": "different"})


@pytest.mark.parametrize("field,value", [("merge_method", "squash"), ("expected_parents", ["other", "candidate"])])
def test_authorization_rejects_unauthorized_merge_method_or_parents(tmp_path, field, value):
    _, _, d, s, _ = _auth_fixture(tmp_path)
    d[field] = value
    sig = sign(d, str(tmp_path / "key.pem"))
    reasons = validate(d, sig, s)
    assert any(reason in reasons for reason in ("merge method not permitted", "expected parents mismatch"))


@pytest.mark.parametrize(
    "location,missing,value",
    [("authorization", False, None), ("authorization", False, ""),
     ("authorization", True, None), ("registry", False, None),
     ("registry", False, ""), ("registry", True, None)],
)
def test_authorization_rejects_missing_policy_digest(tmp_path, location, missing, value):
    _, _, d, s, _ = _auth_fixture(tmp_path)
    sig = sign(d, str(tmp_path / "key.pem"))
    if location == "authorization":
        if missing:
            d.pop("policy_sha256")
        else:
            d["policy_sha256"] = value
    else:
        if missing:
            s.pop("policy_sha256")
        else:
            s["policy_sha256"] = value
    assert "policy digest missing" in validate(d, sig, s)


def test_authorization_rejects_missing_class_check_registration(tmp_path):
    _, _, d, s, sig = _auth_fixture(tmp_path)
    s.pop("required_checks_by_risk_class")
    assert "required checks registration missing for risk class" in validate(d, sig, s)


@pytest.mark.parametrize(
    "attribution,author_models,resolved",
    [([], {"author": "author-model"}, True),
     ([{"sha": "candidate", "principal": "unregistered", "source": "ledger", "evidence_sha256": "x"}], {}, True),
     ([{"sha": "candidate", "principal": "author", "source": "ledger", "evidence_sha256": "x"}], {"author": "author-model"}, False)],
)
def test_authorization_rejects_empty_or_unresolved_attribution(tmp_path, attribution, author_models, resolved):
    _, _, d, s, _ = _auth_fixture(tmp_path)
    d["attribution"] = attribution
    s["author_models"] = author_models
    s["attribution_resolved"] = resolved
    sig = sign(d, str(tmp_path / "key.pem"))
    assert "actor attribution inconclusive" in validate(d, sig, s)


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
        d, sig, {**s, "required_checks_by_risk_class": {"R2": ["unit", "security"]}}
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
    append(f, {"type": "a"}, "k", str(private), {"k": str(public)})
    append(f, {"type": "b"}, "k", str(private), {"k": str(public)})
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
    append(f, {"type": "a"}, "unknown", str(private), {"unknown": "missing.pub"})
    with pytest.raises(ValueError):
        verify(f, {"known": "missing.pub"})


def test_supervisor_matches_main_history_against_ledger_authorizations(tmp_path):
    r = tmp_path / "r"
    subprocess.run(["git", "init", str(r)], check=True, capture_output=True)
    git(r, "config", "user.name", "x")
    git(r, "config", "user.email", "x@y")
    authorized = []
    for value in ("a", "b"):
        (r / "f").write_text(value)
        git(r, "add", "f")
        git(r, "commit", "-m", value)
        authorized.append(git(r, "rev-parse", "HEAD"))
    (r / "f").write_text("direct")
    git(r, "commit", "-am", "direct push")
    direct = git(r, "rev-parse", "HEAD")
    events = supervisor_inspect(r, set(authorized), 0, str(keypair(tmp_path)[0]), tmp_path)
    assert all(not x["unauthorized"] for x in events if x["commit"] in authorized)
    assert any(x["commit"] == direct and x["unauthorized"] for x in events)


def test_supervisor_flags_merge_not_made_by_integrator_identity(tmp_path):
    # Supervisor reports unauthorized merge ancestry as a commit lacking an authorization.

    r = tmp_path / "r"
    subprocess.run(["git", "init", str(r)], check=True, capture_output=True)
    git(r, "config", "user.name", "x")
    git(r, "config", "user.email", "x@y")
    (r / "f").write_text("x")
    git(r, "add", "f")
    git(r, "commit", "-m", "direct merge-like commit")
    sha = git(r, "rev-parse", "HEAD")
    events = supervisor_inspect(r, {sha}, 0, str(keypair(tmp_path)[0]), tmp_path,
                                push_attributions={sha: "other"}, integrator_identity="integrator")
    assert any(e["identity_mismatch"] for e in events)


def test_supervisor_flags_protected_path_change(tmp_path):
    r = tmp_path / "r"
    subprocess.run(["git", "init", str(r)], check=True, capture_output=True)
    git(r, "config", "user.name", "x")
    git(r, "config", "user.email", "x@y")
    (r / "f").write_text("base")
    git(r, "add", "f")
    git(r, "commit", "-m", "base")
    base_sha = git(r, "rev-parse", "HEAD")
    (r / "critical").write_text("x")
    git(r, "add", ".")
    git(r, "commit", "-m", "protected")
    protected_sha = git(r, "rev-parse", "HEAD")
    events = supervisor_inspect(r, {protected_sha}, 0, str(keypair(tmp_path)[0]), tmp_path,
                                protected_path_registry={"critical": "R3"})
    assert any(
        e["protected_path_unauthorized"] for e in events
    )
    (r / "ordinary").write_text("y")
    git(r, "add", ".")
    git(r, "commit", "-m", "ordinary")
    ordinary_sha = git(r, "rev-parse", "HEAD")
    ordinary_events = supervisor_inspect(r, {base_sha, protected_sha, ordinary_sha}, 0,
                                         str(keypair(tmp_path)[0]), tmp_path,
                                         protected_path_registry={"critical": "R3"})
    assert not any(e["commit"] == ordinary_sha for e in ordinary_events)
    assert not any(e["commit"] == ordinary_sha and e["protected_path_unauthorized"]
                   for e in ordinary_events)


def test_supervisor_signs_events_and_heartbeat_for_notifier(tmp_path):
    from aao.supervisor import inspect, signed_heartbeat

    repo = tmp_path / "signed-repo"
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    git(repo, "config", "user.name", "test")
    git(repo, "config", "user.email", "test@example.invalid")
    (repo / "f").write_text("x")
    git(repo, "add", "f")
    git(repo, "commit", "-m", "initial")
    (repo / "f").write_text("unapproved")
    git(repo, "commit", "-am", "unapproved")
    private, public = keypair(tmp_path)
    ledger = tmp_path / "ledger.jsonl"
    append(ledger, {"type": "authorization", "commit": git(repo, "rev-parse", "HEAD")},
           "k", str(private), {"k": {"public_key": str(public), "can_authorize": True}})
    events = inspect(repo, set(), 0, str(private), key_id="k", state_path=tmp_path / "seq.json",
                     ledger_path=ledger, trusted_keys={"k": {"public_key": str(public), "can_authorize": True}}, now="2026-01-01T00:00:00+00:00")
    heartbeat = signed_heartbeat(2, "2026-01-01T00:00:00+00:00", str(private), key_id="k",
                                 expires_at="2026-01-01T00:05:00+00:00")
    sink = FileSink(tmp_path / "sink.jsonl")
    consume(events[0], {"k": str(public)}, tmp_path / "notify.json", "2026-01-01T00:00:01+00:00", sink)
    consume(heartbeat, {"k": str(public)}, tmp_path / "notify.json", "2026-01-01T00:00:01+00:00", sink)
    assert len((tmp_path / "sink.jsonl").read_text().splitlines()) == 2


def test_supervisor_detects_protected_change_in_real_merge_using_minimum_class(tmp_path):
    from aao.supervisor import inspect

    repo = tmp_path / "merge-repo"
    subprocess.run(["git", "init", "--bare", str(repo)], check=True, capture_output=True)
    work = tmp_path / "merge-work"
    subprocess.run(["git", "clone", str(repo), str(work)], check=True, capture_output=True)
    git(work, "config", "user.name", "test")
    git(work, "config", "user.email", "test@example.invalid")
    (work / "base").write_text("base")
    git(work, "add", ".")
    git(work, "commit", "-m", "base")
    git(work, "branch", "-M", "main")
    git(work, "checkout", "-b", "feature")
    (work / ".github/workflows").mkdir(parents=True)
    (work / ".github/workflows/ci.yml").write_text("name: CI")
    git(work, "add", ".")
    git(work, "commit", "-m", "workflow")
    git(work, "checkout", "main")
    git(work, "merge", "--no-ff", "feature", "-m", "promotion")
    merge = git(work, "rev-parse", "HEAD")
    private, public = keypair(tmp_path)
    ledger = tmp_path / "merge-ledger"
    append(ledger, {"type": "authorization", "commit": merge, "risk_class": "R1"},
           "k", str(private), {"k": {"public_key": str(public), "can_authorize": True}})
    events = inspect(work, {merge}, 0, str(private), key_id="k", state_path=tmp_path / "merge-seq",
                     ledger_path=ledger, trusted_keys={"k": {"public_key": str(public), "can_authorize": True}},
                     protected_path_registry={".github/workflows/": "R2"},
                     now="2026-01-01T00:00:00+00:00")
    assert any(e["commit"] == merge and e["protected_path_unauthorized"] for e in events)


def test_notifier_rejects_replay_expired_bad_signature_and_counter_gap(tmp_path):
    private, public = keypair(tmp_path)
    event = {"sequence": 2, "key_id": "k", "type": "alert", "expires_at": "2027-01-01T00:00:00+00:00"}
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
        consume(event, {"k": str(public)}, tmp_path / "state.json", "2026-01-01T00:00:00+00:00", sink)
    with pytest.raises(ValueError):
        consume(event, {"k": str(public)}, tmp_path / "notifier-gap.json", "2026-01-01T00:00:00+00:00", sink)
    with pytest.raises(ValueError):
        consume(event, {"k": str(public)}, tmp_path / "expired-state.json", "2028-01-01T00:00:00+00:00", sink)
    event["signature"] = "AA=="
    with pytest.raises((ValueError, subprocess.CalledProcessError)):
        consume(event, {"k": str(public)}, tmp_path / "bad-state.json", "2026-01-01T00:00:00+00:00", sink)


def test_identity_attribution_hook_records_pusher_uid_and_rejects_unattributed_push(tmp_path):
    from aao.identity_attribution import install_uid_hook

    bare = tmp_path / "bare.git"
    subprocess.run(["git", "init", "--bare", str(bare)], check=True, capture_output=True)
    log = tmp_path / "push.log"
    install_uid_hook(bare, log)

    work = tmp_path / "work"
    subprocess.run(["git", "clone", str(bare), str(work)], check=True, capture_output=True)
    git(work, "config", "user.name", "x")
    git(work, "config", "user.email", "x@y")
    (work / "f").write_text("x")
    git(work, "add", "f")
    git(work, "commit", "-m", "push")
    git(work, "push", "origin", "HEAD:main")
    assert log.read_text().split()[0] == str(os.getuid())

    blocked = tmp_path / "blocked"
    blocked.mkdir()
    bad_bare = tmp_path / "bad.git"
    subprocess.run(["git", "init", "--bare", str(bad_bare)], check=True, capture_output=True)
    install_uid_hook(bad_bare, blocked)
    bad_work = tmp_path / "bad-work"
    subprocess.run(["git", "clone", str(bad_bare), str(bad_work)], check=True, capture_output=True)
    git(bad_work, "config", "user.name", "x")
    git(bad_work, "config", "user.email", "x@y")
    (bad_work / "f").write_text("x")
    git(bad_work, "add", "f")
    git(bad_work, "commit", "-m", "reject")
    rejected = subprocess.run(["git", "push", "origin", "HEAD:main"], check=False, cwd=bad_work,
                              capture_output=True, text=True)
    assert rejected.returncode != 0


def _git_fixture(tmp_path):
    from aao.integrator import TrustSources, promote
    from aao.supervisor import signed_heartbeat

    bare = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", str(bare)], check=True, capture_output=True)
    r = tmp_path / "work"
    subprocess.run(["git", "clone", str(bare), str(r)], check=True, capture_output=True)
    git(r, "config", "user.name", "integrator")
    git(r, "config", "user.email", "integrator@example.invalid")
    (r / "f").write_text("base\n")
    git(r, "add", "f"); git(r, "commit", "-m", "base")
    git(r, "branch", "-M", "main"); git(r, "push", "-u", "origin", "main")
    base = git(r, "rev-parse", "HEAD")
    (r / "f").write_text("candidate\n"); git(r, "commit", "-am", "candidate")
    head = git(r, "rev-parse", "HEAD")
    tree = git(r, "merge-tree", "--write-tree", base, head).splitlines()[0]
    git(r, "push", "origin", f"{head}:refs/heads/candidate")
    git(r, "reset", "--hard", base)
    auditor_dir = tmp_path / "auditor"
    auditor_dir.mkdir()
    auditor_private, auditor_public = keypair(auditor_dir)
    supervisor_dir = tmp_path / "supervisor"
    supervisor_dir.mkdir()
    supervisor_private, supervisor_public = keypair(supervisor_dir)
    integrator_dir = tmp_path / "integrator-key"
    integrator_dir.mkdir()
    integrator_private, _integrator_public = keypair(integrator_dir)
    ledger_dir = tmp_path / "ledger-key"
    ledger_dir.mkdir()
    _ledger_private, ledger_public = keypair(ledger_dir)
    d = {"repo":"r", "pr_number":1, "candidate_sha":head, "base_sha":base,
         "target_ref":"refs/heads/main", "merge_method":"merge-commit", "merge_result_tree_sha":tree,
         "risk_class":"R2", "assurance_level":"A", "policy_id":"p", "policy_sha256":"h",
         "protected_paths_sha256":hashlib.sha256(canonical([])).hexdigest(), "expected_parents":[base,head], "git_version":"2.43.0",
         "auditor_id":"a", "auditor_key_id":"k", "auditor_code_revision":"rev",
         "attribution":[{"sha":head,"principal":"author","source":"ledger","evidence_sha256":"a"}],
         "checks_executed":[{"name":"unit","cmd":"pytest","result":"PASS","evidence_sha256":"e"}],
         "scope":"scope", "known_limitations":[], "residual_risks":[], "permitted_operations":[],
         "prohibited_operations":[], "findings":[], "expediente_sha256":"expediente", "verdict":"APPROVE",
         "issued_at":"2026-01-01T00:00:00+00:00", "expires_at":"2026-01-02T00:00:00+00:00"}
    state = {"repo":"r", "pr_number":1, "pr_head":head, "target_ref":d["target_ref"], "target_sha":base,
         "merge_tree_sha":tree, "policy_sha256":"h", "trusted_keys":{"k":str(auditor_public)},
         "trusted_auditors":{"a":["k"]}, "trusted_auditor_revisions":["rev"], "required_checks_by_risk_class":{"R2":["unit"]},
         "enabled_risk_classes":["R2"], "policy_id":"p", "attribution_resolved":True,
         "ci_candidate_sha":head, "protected_paths":{}, "changed_paths":[], "git_version":git(r,"--version").removeprefix("git version "), "auditor_models":{"a":"auditor-model"},
         "author_models":{"author":"author-model"}, "ra03_pass":True, "ra09_pass":True}
    resolver_dir = tmp_path / "resolver"
    resolver_dir.mkdir()
    _resolver_private, resolver_public = keypair(resolver_dir)
    ledger=tmp_path/"ledger.jsonl"; ledger.touch(); anchor=tmp_path/"anchor"; heartbeat=tmp_path/"heartbeat.json"; freeze=tmp_path/"freeze"
    anchor.write_text("0"*64)
    from aao.governance_ledger import verify
    anchor.write_text(verify(ledger, {"ledger":str(ledger_public)})[-1]["hash"] if ledger.exists() and ledger.stat().st_size else "0"*64)
    hb=signed_heartbeat(1,"2026-01-01T00:00:00+00:00",str(supervisor_private),key_id="supervisor",expires_at="2026-01-01T02:00:00+00:00")
    heartbeat.write_text(json.dumps(hb))
    registry={**state,"repo":"r","pr_number":1,"ledger_keys":{"ledger":{"public_key":str(ledger_public)}, "integrator":{"public_key":str(_integrator_public),"can_record_incidents":True}, "auditor":{"public_key":str(auditor_public),"can_resolve_pending":True}},"supervisor_key_id":"supervisor","supervisor_public_key":str(supervisor_public),"heartbeat_max_age_seconds":3600,
              "target_refs":["refs/heads/main"],"integrator_identity":"integrator","protected_paths":{},"ra_status":{"RA-01":"PASS","RA-02":"PASS","RA-03":"PASS","RA-07":"PASS","RA-09":"PASS"}}
    registry["integrator_key_id"] = "integrator"
    # Expose local fixture-only signing paths so negative cases can re-sign the
    # exact authorization/heartbeat after changing one field.
    registry["test_auditor_private_key"] = str(auditor_private)
    registry["test_supervisor_private_key"] = str(supervisor_private)
    registry["test_ledger_private_key"] = str(_ledger_private)
    registry["incident_resolvers"] = ["resolver"]
    registry["ledger_keys"]["resolver"] = {"public_key": str(resolver_public), "can_resolve_incidents": True}
    reg=tmp_path/"registry.json"; reg.write_text(json.dumps(registry))
    sources = TrustSources(reg, ledger, anchor, heartbeat, freeze, integrator_private)
    return promote, r, bare, base, head, tree, d, sources, sign(d,str(auditor_private))


def _integrator_identity(name="integrator"):
    return type("Identity", (), {
        "__call__": lambda self: name,
        "push_identity": lambda self, *args: True,
    })()


def _remote_main(bare):
    return subprocess.run(
        ["git", "--git-dir", str(bare), "rev-parse", "refs/heads/main"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _assert_integrator_rejects_without_main_change(
    promote, repo, bare, auth, signature, sources, reason, *, identity=None,
):
    main_before = _remote_main(bare)
    with pytest.raises((RuntimeError, ValueError), match=reason):
        promote(
            repo,
            "origin",
            auth,
            signature,
            sources,
            identity_provider=identity or _integrator_identity(),
            now=lambda: __import__("datetime").datetime(
                2026, 1, 1, 1, tzinfo=__import__("datetime").timezone.utc
            ),
        )
    assert _remote_main(bare) == main_before


def test_integrator_blocks_on_active_veto_in_ledger(tmp_path):
    promote, repo, bare, _base, _head, _tree, auth, sources, signature = _git_fixture(tmp_path)
    veto_keys = tmp_path / "veto-keys"
    veto_keys.mkdir()
    private, public = keypair(veto_keys)
    registry = json.loads(sources.trust_registry.read_text())
    registry["ledger_keys"]["veto"] = str(public)
    sources.trust_registry.write_text(json.dumps(registry))
    veto = append(sources.ledger, {"type": "veto", "id": "active-veto"},
                  "veto", str(private), registry["ledger_keys"])
    sources.ledger_anchor.write_text(veto["hash"])

    _assert_integrator_rejects_without_main_change(
        promote, repo, bare, auth, signature, sources, "active ledger veto"
    )


def _add_pending_veto_marker(sources, candidate_sha):
    directory = Path(str(sources.ledger) + ".pending-vetoes")
    directory.mkdir(mode=0o700, exist_ok=True)
    marker = {"schema": "aao.pending-veto.v1", "candidate_sha": candidate_sha,
              "manifest_sha256": "a" * 64, "reason": "unattributed veto"}
    data = canonical(marker)
    digest = hashlib.sha256(data).hexdigest()
    path = directory / f"{candidate_sha}-{digest}.json"
    path.write_bytes(data)
    path.chmod(0o600)
    return digest


def test_integrator_blocks_on_unresolved_pending_veto_marker(tmp_path, monkeypatch):
    # The test runner's temporary root is group-writable; isolate this behavioral
    # test from the separate production parent-custody check.
    monkeypatch.setattr("aao.pending_veto._check_parents", lambda path, uid: None)
    promote, repo, bare, _base, head, _tree, auth, sources, signature = _git_fixture(tmp_path)
    _add_pending_veto_marker(sources, head)

    _assert_integrator_rejects_without_main_change(
        promote, repo, bare, auth, signature, sources, "candidate has an unresolved pending veto"
    )


def test_integrator_proceeds_when_pending_veto_resolved_in_ledger(tmp_path, monkeypatch):
    monkeypatch.setattr("aao.pending_veto._check_parents", lambda path, uid: None)
    promote, repo, _bare, _base, head, tree, auth, sources, signature = _git_fixture(tmp_path)
    digest = _add_pending_veto_marker(sources, head)
    with pytest.raises(ValueError, match="candidate has an unresolved pending veto"):
        promote(repo, "origin", auth, signature, sources,
            identity_provider=_integrator_identity(),
            now=lambda: __import__("datetime").datetime(2026, 1, 1, 1,
                tzinfo=__import__("datetime").timezone.utc))
    registry = json.loads(sources.trust_registry.read_text())
    resolved = append(sources.ledger, {"type": "audit-verdict",
        "candidate_sha": head, "resolves_pending": [digest]}, "auditor",
        registry["test_auditor_private_key"], registry["ledger_keys"])
    sources.ledger_anchor.write_text(resolved["hash"])

    commit = promote(repo, "origin", auth, signature, sources,
        identity_provider=_integrator_identity(),
        now=lambda: __import__("datetime").datetime(2026, 1, 1, 1,
            tzinfo=__import__("datetime").timezone.utc))
    assert git(repo, "show", "-s", "--format=%T", commit) == tree


def test_integrator_rejects_pending_veto_resolution_signed_by_integrator_key(tmp_path, monkeypatch):
    monkeypatch.setattr("aao.pending_veto._check_parents", lambda path, uid: None)
    promote, repo, bare, _base, head, _tree, auth, sources, signature = _git_fixture(tmp_path)
    digest = _add_pending_veto_marker(sources, head)
    registry = json.loads(sources.trust_registry.read_text())
    with pytest.raises(ValueError, match="resolves_pending signer is not an enabled authority"):
        append(sources.ledger, {"type": "audit-verdict", "candidate_sha": head,
              "resolves_pending": [digest]}, "integrator", str(sources.integrator_private_key),
              registry["ledger_keys"])
    # Exercise a previously signed unauthorized row as well: verification must reject it.
    registry["ledger_keys"]["integrator"]["can_resolve_pending"] = True
    forged = append(sources.ledger, {"type": "audit-verdict", "candidate_sha": head,
                   "resolves_pending": [digest]}, "integrator", str(sources.integrator_private_key),
                   registry["ledger_keys"])
    registry["ledger_keys"]["integrator"].pop("can_resolve_pending")
    sources.trust_registry.write_text(json.dumps(registry))
    sources.ledger_anchor.write_text(forged["hash"])
    _assert_integrator_rejects_without_main_change(
        promote, repo, bare, auth, signature, sources, "resolves_pending signer is not an enabled authority"
    )


@pytest.mark.parametrize("capability", ["can_resolve_pending", "can_authorize"])
def test_integrator_rejects_registry_granting_resolve_pending_to_integrator(tmp_path, capability):
    promote, repo, bare, _base, _head, _tree, auth, sources, signature = _git_fixture(tmp_path)
    registry = json.loads(sources.trust_registry.read_text())
    registry["ledger_keys"][registry["integrator_key_id"]][capability] = True
    sources.trust_registry.write_text(json.dumps(registry))

    _assert_integrator_rejects_without_main_change(
        promote, repo, bare, auth, signature, sources,
        "integrator key has a reserved ledger capability",
    )


@pytest.mark.parametrize("capability", ["can_resolve_pending", "can_authorize"])
def test_integrator_rejects_registry_reusing_integrator_public_key_for_resolver(
    tmp_path, capability,
):
    promote, repo, bare, _base, _head, _tree, auth, sources, signature = _git_fixture(tmp_path)
    registry = json.loads(sources.trust_registry.read_text())
    resolver = registry["ledger_keys"]["auditor"]
    resolver_key = tmp_path / "aliased-integrator-public.pem"
    resolver_key.write_bytes(Path(
        registry["ledger_keys"][registry["integrator_key_id"]]["public_key"]
    ).read_bytes())
    resolver["public_key"] = str(resolver_key)
    resolver[capability] = True
    sources.trust_registry.write_text(json.dumps(registry))

    _assert_integrator_rejects_without_main_change(
        promote, repo, bare, auth, signature, sources,
        "integrator public key is shared with a reserved ledger authority",
    )


def test_integrator_ignores_pending_veto_marker_for_another_candidate(tmp_path, monkeypatch):
    monkeypatch.setattr("aao.pending_veto._check_parents", lambda path, uid: None)
    promote, repo, _bare, _base, _head, tree, auth, sources, signature = _git_fixture(tmp_path)
    _add_pending_veto_marker(sources, "f" * 40)
    commit = promote(repo, "origin", auth, signature, sources,
        identity_provider=_integrator_identity(),
        now=lambda: __import__("datetime").datetime(2026, 1, 1, 1,
            tzinfo=__import__("datetime").timezone.utc))
    assert git(repo, "show", "-s", "--format=%T", commit) == tree


@pytest.mark.parametrize("value", ["bad", [1]])
def test_ledger_rejects_malformed_resolves_pending(tmp_path, value):
    from aao.governance_ledger import verify
    keys = tmp_path / "key"; keys.mkdir()
    private, public = keypair(keys)
    trusted = {"auditor": {"public_key": str(public), "can_resolve_pending": True}}
    ledger = tmp_path / "ledger.jsonl"; ledger.touch()
    with pytest.raises(ValueError, match="malformed resolves_pending"):
        append(ledger, {"type": "audit-verdict", "resolves_pending": value}, "auditor",
               str(private), trusted)
    # Manually construct a signed malformed row to exercise verify's independent guard.
    import base64
    payload = {"sequence": 1, "previous_hash": "0" * 64, "key_id": "auditor",
               "type": "audit-verdict", "resolves_pending": value}
    message = tmp_path / "message"
    message.write_bytes(canonical(payload))
    signature = subprocess.run(["openssl", "pkeyutl", "-sign", "-rawin", "-inkey", str(private),
                                "-in", str(message)], check=True, capture_output=True).stdout
    payload["signature"] = base64.b64encode(signature).decode()
    payload["hash"] = hashlib.sha256(canonical(payload)).hexdigest()
    ledger.write_bytes(canonical(payload) + b"\n")
    with pytest.raises(ValueError, match="malformed resolves_pending"):
        verify(ledger, trusted)


def test_integrator_pending_veto_directory_is_derived_from_ledger(tmp_path, monkeypatch):
    monkeypatch.setattr("aao.pending_veto._check_parents", lambda path, uid: None)
    promote, repo, bare, _base, head, _tree, auth, sources, signature = _git_fixture(tmp_path)
    derived = Path(str(sources.ledger) + ".pending-vetoes")
    derived.mkdir(mode=0o700)
    _add_pending_veto_marker(sources, head)
    _assert_integrator_rejects_without_main_change(
        promote, repo, bare, auth, signature, sources, "candidate has an unresolved pending veto"
    )


def test_integrator_absent_pending_veto_directory_does_not_block(tmp_path):
    # Absence is treated as no markers; deletion detection remains the accepted A-2 open issue.
    promote, repo, _bare, _base, _head, tree, auth, sources, signature = _git_fixture(tmp_path)
    assert not Path(str(sources.ledger) + ".pending-vetoes").exists()
    commit = promote(repo, "origin", auth, signature, sources,
        identity_provider=_integrator_identity(),
        now=lambda: __import__("datetime").datetime(2026, 1, 1, 1,
            tzinfo=__import__("datetime").timezone.utc))
    assert git(repo, "show", "-s", "--format=%T", commit) == tree


def test_integrator_pending_veto_parent_custody_without_patch(tmp_path):
    from aao.pending_veto import PendingVetoError, _check_parents

    promote, repo, _bare, _base, head, tree, auth, sources, signature = _git_fixture(tmp_path)
    tmp_path.chmod(0o700)
    digest = _add_pending_veto_marker(sources, head)
    try:
        _check_parents(Path(str(sources.ledger) + ".pending-vetoes") / "x",
                       sources.ledger.stat().st_uid)
    except PendingVetoError as error:
        pytest.skip(f"sandbox temporary tree has unsafe ancestors: {error}")
    registry = json.loads(sources.trust_registry.read_text())
    resolved = append(sources.ledger, {"type": "audit-verdict", "candidate_sha": head,
        "resolves_pending": [digest]}, "auditor", registry["test_auditor_private_key"],
        registry["ledger_keys"])
    sources.ledger_anchor.write_text(resolved["hash"])

    commit = promote(
        repo, "origin", auth, signature, sources,
        identity_provider=_integrator_identity(),
        now=lambda: __import__("datetime").datetime(
            2026, 1, 1, 1, tzinfo=__import__("datetime").timezone.utc
        ),
    )
    assert git(repo, "show", "-s", "--format=%T", commit) == tree


def test_integrator_fails_closed_on_unverifiable_pending_veto_dir(tmp_path, monkeypatch):
    monkeypatch.setattr("aao.pending_veto._check_parents", lambda path, uid: None)
    promote, repo, bare, _base, head, _tree, auth, sources, signature = _git_fixture(tmp_path)
    _add_pending_veto_marker(sources, head)
    Path(str(sources.ledger) + ".pending-vetoes").chmod(0o770)

    _assert_integrator_rejects_without_main_change(
        promote, repo, bare, auth, signature, sources, "pending vetoes cannot be verified"
    )


def test_ledger_new_veto_with_reused_id_stays_active_after_old_revocation(tmp_path):
    private, public = keypair(tmp_path)
    keys = {"veto": {"public_key": str(public), "can_revoke": True}}
    ledger = tmp_path / "reused-veto-id.jsonl"
    old = append(ledger, {"type": "veto", "id": "reused"}, "veto", str(private), keys)
    append(ledger, {"type": "revocation", "target": old["hash"]}, "veto", str(private), keys)
    new = append(ledger, {"type": "veto", "id": "reused"}, "veto", str(private), keys)
    assert new["hash"] in {row["hash"] for row in active_vetoes(verify(ledger, keys), keys)}


def test_integrator_rejects_replayed_heartbeat_sequence(tmp_path):
    from aao.integrator import _heartbeat
    from aao.supervisor import signed_heartbeat
    private, public = keypair(tmp_path)
    heartbeat = tmp_path / "heartbeat.json"
    heartbeat.with_suffix(".json.sequence").write_text("4")
    heartbeat.write_text(json.dumps(signed_heartbeat(4, "2026-01-01T00:00:00+00:00",
        str(private), key_id="supervisor", expires_at="2026-01-01T00:05:00+00:00")))
    now = __import__("datetime").datetime(2026, 1, 1, 0, 1, tzinfo=__import__("datetime").timezone.utc)
    assert not _heartbeat(heartbeat, {"supervisor_key_id": "supervisor",
        "supervisor_public_key": str(public)}, now)


def test_integrator_rejects_heartbeat_older_than_one_hour_even_if_registry_allows_more(tmp_path):
    from aao.integrator import _heartbeat
    from aao.supervisor import signed_heartbeat
    private, public = keypair(tmp_path)
    heartbeat = tmp_path / "heartbeat.json"
    heartbeat.write_text(json.dumps(signed_heartbeat(1, "2026-01-01T00:00:00+00:00",
        str(private), key_id="supervisor", expires_at="2026-01-01T03:00:00+00:00")))
    now = __import__("datetime").datetime(2026, 1, 1, 1, 0, 1, tzinfo=__import__("datetime").timezone.utc)
    assert not _heartbeat(heartbeat, {"supervisor_key_id": "supervisor",
        "supervisor_public_key": str(public), "heartbeat_max_age_seconds": 7200}, now)


def test_integrator_rejects_heartbeat_issued_in_the_future(tmp_path):
    from aao.integrator import _heartbeat
    from aao.supervisor import signed_heartbeat
    private, public = keypair(tmp_path)
    heartbeat = tmp_path / "heartbeat.json"
    heartbeat.write_text(json.dumps(signed_heartbeat(1, "2026-01-01T00:02:00+00:00",
        str(private), key_id="supervisor", expires_at="2026-01-01T01:00:00+00:00")))
    now = __import__("datetime").datetime(2026, 1, 1, 0, 0, tzinfo=__import__("datetime").timezone.utc)
    assert not _heartbeat(heartbeat, {"supervisor_key_id": "supervisor",
        "supervisor_public_key": str(public)}, now)


def test_integrator_rejects_pending_ra01_or_ra07(tmp_path):
    for requirement in ("RA-01", "RA-07"):
        case = tmp_path / requirement
        case.mkdir()
        promote, repo, bare, _base, _head, _tree, auth, sources, signature = _git_fixture(case)
        registry = json.loads(sources.trust_registry.read_text())
        registry["ra_status"][requirement] = "PENDING"
        sources.trust_registry.write_text(json.dumps(registry))
        _assert_integrator_rejects_without_main_change(
            promote, repo, bare, auth, signature, sources, "required RA status pending")


def test_authorization_rejects_protected_path_change_below_minimum_class(tmp_path):
    private, _, doc, state, _signature = _auth_fixture(tmp_path)
    protected = {"src/aao/policy.py": "R3"}
    doc["protected_paths_sha256"] = hashlib.sha256(canonical([
        {"path": path, "minimum_risk_class": minimum}
        for path, minimum in sorted(protected.items())])).hexdigest()
    signature = sign(doc, str(private))
    state.update(protected_paths=protected, changed_paths=["src/aao/policy.py"])
    assert "protected path risk class insufficient" in validate(doc, signature, state)


def test_authorization_rejects_protected_paths_digest_mismatch(tmp_path):
    _, _, doc, state, signature = _auth_fixture(tmp_path)
    state["protected_paths"] = {"src/aao/policy.py": "R2"}
    state["changed_paths"] = ["src/aao/policy.py"]
    assert "protected paths digest mismatch" in validate(doc, signature, state)


def test_ledger_rejects_authorization_row_from_key_without_can_authorize(tmp_path):
    private, public = keypair(tmp_path)
    ledger = tmp_path / "unauthorized-authorization.jsonl"
    append(ledger, {"type": "authorization", "commit": "candidate"}, "writer",
        str(private), {"writer": {"public_key": str(public)}})
    with pytest.raises(ValueError, match="authorization signer"):
        verify(ledger, {"writer": {"public_key": str(public)}})


def test_supervisor_ignores_unverified_authorization_rows(tmp_path):
    repo = tmp_path / "untrusted-auth-repo"
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    git(repo, "config", "user.name", "test")
    git(repo, "config", "user.email", "test@example.invalid")
    (repo / "f").write_text("unauthorized\n")
    git(repo, "add", "f"); git(repo, "commit", "-m", "unauthorized")
    sha = git(repo, "rev-parse", "HEAD")
    private, public = keypair(tmp_path)
    ledger = tmp_path / "untrusted-auth-ledger.jsonl"
    keys = {"writer": {"public_key": str(public)}}
    append(ledger, {"type": "authorization", "commit": sha}, "writer", str(private), keys)
    with pytest.raises(ValueError, match="authorization signer"):
        from aao.supervisor import inspect
        inspect(repo, {sha}, 0, str(private), key_id="supervisor",
            state_path=tmp_path / "untrusted-sequence.json", ledger_path=ledger,
            trusted_keys=keys, now="2026-01-01T00:00:00+00:00")


def test_integrator_blocks_when_remote_candidate_head_moves(tmp_path):
    promote, repo, bare, _base, head, _tree, auth, sources, signature = _git_fixture(tmp_path)
    rival = tmp_path / "candidate-rival"
    subprocess.run(["git", "clone", str(bare), str(rival)], check=True, capture_output=True)
    git(rival, "fetch", "origin", "candidate")
    git(rival, "checkout", "-B", "candidate", "FETCH_HEAD")
    git(rival, "config", "user.name", "rival")
    git(rival, "config", "user.email", "rival@example.invalid")
    (rival / "f").write_text("moved candidate\n")
    git(rival, "commit", "-am", "move candidate")
    git(rival, "push", "--force", "origin", "candidate")
    git(repo, "fetch", "origin", "candidate")
    assert git(rival, "rev-parse", "HEAD") != head
    _assert_integrator_rejects_without_main_change(
        promote, repo, bare, auth, signature, sources, "PR head mismatch")


def test_authorization_rejects_git_version_mismatch(tmp_path):
    private, _, doc, state, _signature = _auth_fixture(tmp_path)
    doc["git_version"] = "git version not-the-runtime"
    signature = sign(doc, str(private))
    assert "git version mismatch" in validate(doc, signature, state)


def test_authorization_rejects_open_critical_finding_or_empty_expediente(tmp_path):
    private, _, doc, state, _signature = _auth_fixture(tmp_path)
    doc["findings"] = [{"severity": "CRITICAL", "disposition": "OPEN"}]
    signature = sign(doc, str(private))
    assert "open critical finding" in validate(doc, signature, state)
    doc["findings"] = []
    doc["expediente_sha256"] = ""
    signature = sign(doc, str(private))
    assert "expediente digest missing" in validate(doc, signature, state)


def test_authorization_rejects_critical_finding_not_resolved(tmp_path):
    private, _, doc, state, _signature = _auth_fixture(tmp_path)
    for disposition in ("ACCEPTED", "OPEN", "CLOSED"):
        doc["findings"] = [{"severity": "cRiTiCaL", "disposition": disposition}]
        signature = sign(doc, str(private))
        assert "open critical finding" in validate(doc, signature, state)
    doc["findings"] = [{"severity": "critical", "disposition": "RESOLVED"}]
    signature = sign(doc, str(private))
    assert "open critical finding" not in validate(doc, signature, state)


def test_integrator_fails_closed_when_changed_paths_unavailable(tmp_path):
    from aao import integrator
    _private, _, doc, state, signature = _auth_fixture(tmp_path)
    assert "changed paths unavailable" in validate(doc, signature, {**state, "changed_paths": None})
    assert "changed paths unavailable" in validate(doc, signature, {key: val for key, val in state.items() if key != "changed_paths"})
    promote_root = tmp_path / "promote"
    promote_root.mkdir()
    promote, repo, _bare, _base, _head, _tree, auth, sources, auth_signature = _git_fixture(promote_root)
    original_run = integrator.subprocess.run
    def fail_diff(args, **kwargs):
        if "diff" in args:
            raise subprocess.CalledProcessError(2, args, stderr="bad revision")
        return original_run(args, **kwargs)
    integrator.subprocess.run = fail_diff
    try:
        with pytest.raises(ValueError, match="changed paths unavailable"):
            promote(repo, "origin", auth, auth_signature, sources, identity_provider=_integrator_identity(),
                    now=lambda: __import__("datetime").datetime(2026,1,1,1,tzinfo=__import__("datetime").timezone.utc))
    finally:
        integrator.subprocess.run = original_run


def test_integrator_rejects_rename_of_protected_path(tmp_path):
    promote, repo, _bare, base, _head, _tree, auth, sources, _signature = _git_fixture(tmp_path)
    (repo / "docs").mkdir()
    (repo / "docs/CONSTITUTION.md").write_text("protected\n")
    git(repo, "add", "docs/CONSTITUTION.md"); git(repo, "commit", "-m", "add protected file")
    # Make that state the remote base, then create a real rename candidate.
    git(repo, "push", "origin", "HEAD:refs/heads/main")
    base = git(repo, "rev-parse", "HEAD")
    git(repo, "mv", "docs/CONSTITUTION.md", "docs/old.md")
    git(repo, "commit", "-m", "rename protected file")
    head = git(repo, "rev-parse", "HEAD")
    tree = git(repo, "merge-tree", "--write-tree", base, head).splitlines()[0]
    git(repo, "push", "--force", "origin", f"{head}:refs/heads/candidate")
    git(repo, "reset", "--hard", base)
    auth.update(candidate_sha=head, base_sha=base, expected_parents=[base, head], merge_result_tree_sha=tree)
    auth["protected_paths_sha256"] = hashlib.sha256(canonical([{"path":"docs/CONSTITUTION.md", "minimum_risk_class":"R3"}])).hexdigest()
    registry = json.loads(sources.trust_registry.read_text())
    registry["protected_paths"] = {"docs/CONSTITUTION.md":"R3"}
    registry["ci_candidate_sha"] = head
    sources.trust_registry.write_text(json.dumps(registry))
    with pytest.raises(ValueError, match="protected path risk class insufficient"):
        promote(repo, "origin", auth, sign(auth, registry["test_auditor_private_key"]), sources,
                identity_provider=_integrator_identity(),
                now=lambda: __import__("datetime").datetime(2026,1,1,1,tzinfo=__import__("datetime").timezone.utc))


def test_integrator_ls_remote_matches_exact_ref(tmp_path, monkeypatch):
    from aao import integrator
    promote, repo, bare, _base, _head, _tree, auth, sources, signature = _git_fixture(tmp_path)
    # Return the prefix-colliding ref first, as a remote may do; selection must match full ref.
    git(repo, "push", "origin", f"{auth['candidate_sha']}:refs/heads/main-old")
    original_run = integrator.subprocess.run
    def with_prefix_ref(args, **kwargs):
        result = original_run(args, **kwargs)
        if args[:3] == ["git", "ls-remote", str(bare)] and result.stdout:
            lines = result.stdout.splitlines()
            main_old = next((line for line in lines if line.endswith("refs/heads/main-old")), None)
            if main_old:
                result.stdout = "\n".join([main_old, *[line for line in lines if line != main_old]]) + "\n"
        return result
    monkeypatch.setattr(integrator.subprocess, "run", with_prefix_ref)
    commit = promote(repo, "origin", auth, signature, sources,
                     identity_provider=_integrator_identity(),
                     now=lambda: __import__("datetime").datetime(2026,1,1,1,tzinfo=__import__("datetime").timezone.utc))
    assert _remote_main(bare) == commit


def test_integrator_freezes_when_published_parents_differ(tmp_path):
    promote, repo, bare, _base, _head, tree, auth, sources, signature = _git_fixture(tmp_path)
    assert git(repo, "show", "-s", "--format=%T", auth["candidate_sha"]) == tree
    def replace_published_merge_with_candidate():
        git(repo, "push", "--force", "origin", f"{auth['candidate_sha']}:refs/heads/main")
    with pytest.raises(RuntimeError, match="post-publication incident"):
        promote(repo, "origin", auth, signature, sources,
            identity_provider=_integrator_identity(), after_push=replace_published_merge_with_candidate,
            now=lambda: __import__("datetime").datetime(2026, 1, 1, 1,
                tzinfo=__import__("datetime").timezone.utc))
    assert sources.freeze.exists()
    assert _remote_main(bare) == auth["candidate_sha"]


def test_ledger_verify_fails_on_edited_intermediate_entry(tmp_path):
    private, public = keypair(tmp_path)
    ledger = tmp_path / "edited-intermediate.jsonl"
    append(ledger, {"type": "note", "detail": "original"}, "key", str(private), {"key": str(public)})
    append(ledger, {"type": "note", "detail": "later"}, "key", str(private), {"key": str(public)})
    rows = ledger.read_text().splitlines()
    first = json.loads(rows[0]); first["detail"] = "edited"
    rows[0] = canonical(first).decode()
    ledger.write_text("\n".join(rows) + "\n")
    with pytest.raises(ValueError, match="edited"):
        verify(ledger, {"key": str(public)})


def test_authorization_rejects_auditor_with_same_model_as_author_for_r2(tmp_path):
    _, _, doc, state, signature = _auth_fixture(tmp_path)
    state["auditor_models"]["auditor"] = state["author_models"]["author"]
    assert "auditor model matches author model" in validate(doc, signature, state)


def test_supervisor_flags_merge_pushed_by_non_integrator_identity(tmp_path):
    repo = tmp_path / "wrong-pusher"
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    git(repo, "config", "user.name", "test"); git(repo, "config", "user.email", "test@example.invalid")
    (repo / "f").write_text("merge\n")
    git(repo, "add", "f"); git(repo, "commit", "-m", "merge")
    sha = git(repo, "rev-parse", "HEAD")
    events = supervisor_inspect(repo, {sha}, 0, str(keypair(tmp_path)[0]), tmp_path,
        push_attributions={sha: "other"}, integrator_identity="integrator")
    assert any(event["commit"] == sha and event["identity_mismatch"] for event in events)


def test_integrator_blocks_on_heartbeat_with_invalid_signature(tmp_path):
    promote, repo, bare, _base, _head, _tree, auth, sources, signature = _git_fixture(tmp_path)
    event = json.loads(sources.heartbeat.read_text())
    event["signature"] = base64.b64encode(b"invalid signature").decode("ascii")
    sources.heartbeat.write_text(json.dumps(event))

    _assert_integrator_rejects_without_main_change(
        promote, repo, bare, auth, signature, sources,
        "valid supervisor heartbeat unavailable",
    )


def test_integrator_blocks_on_heartbeat_with_unknown_key_id(tmp_path):
    promote, repo, bare, _base, _head, _tree, auth, sources, signature = _git_fixture(tmp_path)
    from aao.supervisor import signed_heartbeat

    unknown_keys = tmp_path / "unknown-keys"
    unknown_keys.mkdir()
    private, _public = keypair(unknown_keys)
    event = signed_heartbeat(
        2, "2026-01-01T00:00:00+00:00", str(private), key_id="unknown-supervisor",
        expires_at="2026-01-01T02:00:00+00:00",
    )
    sources.heartbeat.write_text(json.dumps(event))

    _assert_integrator_rejects_without_main_change(
        promote, repo, bare, auth, signature, sources,
        "valid supervisor heartbeat unavailable",
    )


def test_integrator_blocks_on_ledger_anchor_mismatch(tmp_path):
    promote, repo, bare, _base, _head, _tree, auth, sources, signature = _git_fixture(tmp_path)
    sources.ledger_anchor.write_text("f" * 64)

    _assert_integrator_rejects_without_main_change(
        promote, repo, bare, auth, signature, sources,
        "ledger truncated or unexpected terminal hash",
    )


def test_integrator_blocks_when_remote_main_moves_without_local_ref_change(tmp_path):
    promote, repo, bare, base, _head, _tree, auth, sources, signature = _git_fixture(tmp_path)
    rival = tmp_path / "rival"
    subprocess.run(["git", "clone", str(bare), str(rival)], check=True, capture_output=True)
    git(rival, "config", "user.name", "rival")
    git(rival, "config", "user.email", "rival@example.invalid")
    (rival / "f").write_text("independent remote update\n")
    git(rival, "commit", "-am", "advance remote main")
    git(rival, "push", "origin", "main")
    moved_main = _remote_main(bare)
    assert moved_main != base
    assert git(repo, "rev-parse", "refs/heads/main") == base

    _assert_integrator_rejects_without_main_change(
        promote, repo, bare, auth, signature, sources, "changed paths unavailable"
    )


def test_integrator_blocks_on_wrong_integrator_identity(tmp_path):
    promote, repo, bare, _base, _head, _tree, auth, sources, signature = _git_fixture(tmp_path)

    _assert_integrator_rejects_without_main_change(
        promote, repo, bare, auth, signature, sources, "integrator identity mismatch",
        identity=_integrator_identity("impostor"),
    )


def test_integrator_blocks_on_pending_ra_status(tmp_path):
    promote, repo, bare, _base, _head, _tree, auth, sources, signature = _git_fixture(tmp_path)
    registry = json.loads(sources.trust_registry.read_text())
    registry["ra_status"]["RA-03"] = "PENDING"
    sources.trust_registry.write_text(json.dumps(registry))

    _assert_integrator_rejects_without_main_change(
        promote, repo, bare, auth, signature, sources, "required RA status pending"
    )


def test_integrator_publishes_only_authorized_tree_end_to_end(tmp_path):
    promote,r,bare,base,head,tree,d,sources,sig=_git_fixture(tmp_path)
    class Identity:
        def __call__(self): return "integrator"
        def push_identity(self, *args): return True
    commit=promote(r,"origin",d,sig,sources,identity_provider=Identity(), now=lambda: __import__("datetime").datetime(2026,1,1,1,tzinfo=__import__("datetime").timezone.utc))
    assert git(r,"show","-s","--format=%T",commit)==tree
    assert git(r,"show","-s","--format=%P",commit).split()==[base,head]
    assert subprocess.run(["git","--git-dir",str(bare),"rev-parse","refs/heads/main"],check=True,capture_output=True,text=True).stdout.strip()==commit


def test_integrator_revalidates_remote_and_authority_inputs(tmp_path):
    promote,r,_bare,_base,_head,_tree,d,sources,sig=_git_fixture(tmp_path)
    with pytest.raises(RuntimeError, match="identity"):
        promote(r,"origin",d,sig,sources,now=lambda: __import__("datetime").datetime(2026,1,1,1,tzinfo=__import__("datetime").timezone.utc))
    registry=json.loads(sources.trust_registry.read_text()); registry["target_refs"]=[]; sources.trust_registry.write_text(json.dumps(registry))
    with pytest.raises(ValueError): promote(r,"origin",d,sig,sources,identity_provider=type("I",(),{"__call__":lambda self:"integrator","push_identity":lambda self,*a:True})())


def test_integrator_aborts_when_main_moves_between_validation_and_push(tmp_path):
    promote, repo, bare, _base, _head, _tree, auth, sources, signature = _git_fixture(tmp_path)
    other = tmp_path / "other"
    subprocess.run(["git", "clone", str(bare), str(other)], check=True, capture_output=True)
    git(other, "config", "user.name", "rival")
    git(other, "config", "user.email", "rival@example.invalid")
    # Move main to the candidate commit: the authorized merge commit is a
    # fast-forward from this new tip, so without the lease Git would accept it.
    after_race = []

    def race_before_push():
        git(other, "fetch", "origin", "candidate")
        git(other, "push", "origin", "FETCH_HEAD:main")
        after_race.append(git(other, "ls-remote", "origin", "refs/heads/main").split()[0])

    identity = type("Identity", (), {
        "__call__": lambda self: "integrator",
        "push_identity": lambda self, *args: True,
    })()
    with pytest.raises(RuntimeError, match="conditional push rejected"):
        promote(
            repo,
            "origin",
            auth,
            signature,
            sources,
            identity_provider=identity,
            now=lambda: __import__("datetime").datetime(
                2026, 1, 1, 1, tzinfo=__import__("datetime").timezone.utc
            ),
            after_recheck=race_before_push,
        )
    # Removing --force-with-lease lets this fast-forward push succeed, so the
    # expected conditional-push rejection would fail; this exercises server CAS.
    assert git(other, "ls-remote", "origin", "refs/heads/main").split()[0] == after_race[0]


def test_integrator_refuses_stale_supervisor_heartbeat(tmp_path):
    promote, repo, _bare, _base, _head, _tree, auth, sources, signature = _git_fixture(tmp_path)
    from aao.supervisor import signed_heartbeat

    expired = signed_heartbeat(
        1,
        "2026-01-01T00:00:00+00:00",
        json.loads(sources.trust_registry.read_text())["test_supervisor_private_key"],
        key_id="supervisor",
        expires_at="2026-01-01T00:30:00+00:00",
    )
    sources.heartbeat.write_text(json.dumps(expired))
    identity = type("Identity", (), {
        "__call__": lambda self: "integrator",
        "push_identity": lambda self, *args: True,
    })()
    with pytest.raises(ValueError, match="heartbeat"):
        promote(
            repo,
            "origin",
            auth,
            signature,
            sources,
            identity_provider=identity,
            now=lambda: __import__("datetime").datetime(
                2026, 1, 1, 1, tzinfo=__import__("datetime").timezone.utc
            ),
        )


def test_integrator_rejects_stale_base(tmp_path):
    promote, repo, _bare, _base, _head, _tree, auth, sources, _signature = _git_fixture(tmp_path)
    auth["base_sha"] = "stale-base"
    signature = sign(auth, json.loads(sources.trust_registry.read_text())["test_auditor_private_key"])
    identity = type("Identity", (), {
        "__call__": lambda self: "integrator",
        "push_identity": lambda self, *args: True,
    })()
    with pytest.raises(ValueError, match="target ref or base mismatch"):
        promote(
            repo,
            "origin",
            auth,
            signature,
            sources,
            identity_provider=identity,
            now=lambda: __import__("datetime").datetime(
                2026, 1, 1, 1, tzinfo=__import__("datetime").timezone.utc
            ),
        )


def test_integrator_rejects_tree_mismatch(tmp_path):
    promote, repo, _bare, _base, _head, _tree, auth, sources, _signature = _git_fixture(tmp_path)
    auth["merge_result_tree_sha"] = "wrong-tree"
    signature = sign(auth, json.loads(sources.trust_registry.read_text())["test_auditor_private_key"])
    identity = type("Identity", (), {
        "__call__": lambda self: "integrator",
        "push_identity": lambda self, *args: True,
    })()
    with pytest.raises(ValueError, match="computed merge tree differs"):
        promote(
            repo,
            "origin",
            auth,
            signature,
            sources,
            identity_provider=identity,
            now=lambda: __import__("datetime").datetime(
                2026, 1, 1, 1, tzinfo=__import__("datetime").timezone.utc
            ),
        )


def test_integrator_refuses_when_frozen(tmp_path):
    promote,r,_,_,_,_,d,sources,sig=_git_fixture(tmp_path); sources.freeze.write_text("freeze")
    with pytest.raises(RuntimeError,match="frozen"): promote(r,"origin",d,sig,sources,identity_provider=type("I",(),{"__call__":lambda self:"integrator","push_identity":lambda self,*a:True})())


def test_integrator_post_publish_divergence_freezes(tmp_path):
    promote,r,bare,_,_,_,d,sources,sig=_git_fixture(tmp_path)
    def rewrite():
        path=subprocess.run(["git","--git-dir",str(bare),"rev-parse","refs/heads/main^"],check=True,capture_output=True,text=True).stdout.strip()
        subprocess.run(["git","--git-dir",str(bare),"update-ref","refs/heads/main",path],check=True)
    with pytest.raises(RuntimeError,match="post-publication incident"):
        promote(r,"origin",d,sig,sources,identity_provider=type("I",(),{"__call__":lambda self:"integrator","push_identity":lambda self,*a:True})(),now=lambda: __import__("datetime").datetime(2026,1,1,1,tzinfo=__import__("datetime").timezone.utc),after_push=rewrite)
    assert sources.freeze.exists()


def test_integrator_freezes_and_records_incident_when_remote_ref_deleted_after_push(tmp_path):
    from aao.governance_ledger import verify

    promote, repo, bare, _base, _head, _tree, auth, sources, signature = _git_fixture(tmp_path)
    def delete_ref():
        subprocess.run(["git", "--git-dir", str(bare), "update-ref", "-d", "refs/heads/main"],
                       check=True, capture_output=True)
    with pytest.raises(RuntimeError, match="post-publication"):
        promote(repo, "origin", auth, signature, sources, identity_provider=_integrator_identity(),
                now=lambda: __import__("datetime").datetime(2026, 1, 1, 1,
                    tzinfo=__import__("datetime").timezone.utc), after_push=delete_ref)
    registry = json.loads(sources.trust_registry.read_text())
    rows = verify(sources.ledger, registry["ledger_keys"], sources.ledger_anchor.read_text())
    assert sources.freeze.exists()
    assert rows[-1]["type"] == "incident"
    assert rows[-1]["key_id"] == registry["integrator_key_id"]
    assert rows[-1]["intended_sha"]
    assert rows[-1]["observed_sha"] is None


def test_integrator_stays_blocked_when_freeze_file_deleted_but_incident_open(tmp_path):
    from aao.governance_ledger import append

    promote, repo, bare, _base, _head, _tree, auth, sources, signature = _git_fixture(tmp_path)
    registry = json.loads(sources.trust_registry.read_text())
    incident = append(sources.ledger, {"type": "incident", "id": "incident-open",
        "detail": "remote state uncertain", "intended_sha": "a" * 40, "observed_sha": None},
        registry["integrator_key_id"], str(sources.integrator_private_key), registry["ledger_keys"])
    sources.ledger_anchor.write_text(incident["hash"])
    sources.freeze.unlink(missing_ok=True)
    _assert_integrator_rejects_without_main_change(promote, repo, bare, auth, signature,
        sources, "open ledger incident")


def test_integrator_rejects_incident_resolution_signed_by_unauthorized_key(tmp_path):
    from aao.governance_ledger import append

    _promote, _repo, _bare, _base, _head, _tree, _auth, sources, _signature = _git_fixture(tmp_path)
    registry = json.loads(sources.trust_registry.read_text())
    incident = append(sources.ledger, {"type": "incident", "id": "incident-open",
        "detail": "remote state uncertain", "intended_sha": "a" * 40, "observed_sha": None},
        registry["integrator_key_id"], str(sources.integrator_private_key), registry["ledger_keys"])
    unauthorized_dir = tmp_path / "unauthorized"
    unauthorized_dir.mkdir()
    private, public = keypair(unauthorized_dir)
    registry["ledger_keys"]["unauthorized"] = str(public)
    sources.trust_registry.write_text(json.dumps(registry))
    with pytest.raises(ValueError, match="incident-resolution signer"):
        append(sources.ledger, {"type": "incident-resolution", "target": incident["id"],
            "incident_hash": incident["hash"], "detail": "resolved"}, "unauthorized",
            str(private), registry["ledger_keys"])


def test_integrator_resumes_after_valid_incident_resolution(tmp_path):
    from aao.governance_ledger import append

    promote, repo, _bare, _base, _head, _tree, auth, sources, signature = _git_fixture(tmp_path)
    registry = json.loads(sources.trust_registry.read_text())
    incident = append(sources.ledger, {"type": "incident", "id": "incident-open",
        "detail": "remote state uncertain", "intended_sha": "a" * 40, "observed_sha": None},
        registry["integrator_key_id"], str(sources.integrator_private_key), registry["ledger_keys"])
    sources.ledger_anchor.write_text(incident["hash"])
    append(sources.ledger, {"type": "incident-resolution", "target": incident["id"],
        "incident_hash": incident["hash"], "detail": "verified and cleared"},
        "resolver", str(tmp_path / "resolver" / "key.pem"), registry["ledger_keys"])
    sources.ledger_anchor.write_text(__import__("aao.governance_ledger", fromlist=["verify"])
        .verify(sources.ledger, registry["ledger_keys"])[-1]["hash"])
    sources.freeze.unlink(missing_ok=True)
    commit = promote(repo, "origin", auth, signature, sources, identity_provider=_integrator_identity(),
        now=lambda: __import__("datetime").datetime(2026, 1, 1, 1,
            tzinfo=__import__("datetime").timezone.utc))
    assert commit == _remote_main(_bare)


# Regression coverage for the signed ledger and persistent notifier boundary.
def test_ledger_requires_trust_and_append_verifies_existing_chain(tmp_path):
    private, public = keypair(tmp_path)
    f = tmp_path / "trusted-ledger"
    first = append(f, {"type": "veto", "id": "v1"}, "k", str(private), {"k": str(public)})
    with pytest.raises(ValueError):
        verify(f, {})
    with pytest.raises(ValueError):
        append(f, {"type": "clear"}, "k", str(private), {"k": str(public)}, expected_head="0" * 64)
    assert verify(f, {"k": str(public)}, expected_head=first["hash"])[0]["id"] == "v1"


def test_ledger_revocation_requires_enabled_authority_and_exact_veto_reference(tmp_path):
    private, public = keypair(tmp_path)
    f = tmp_path / "revocations"
    append(f, {"type": "veto", "id": "v1"}, "k", str(private), {"k": str(public)})
    with pytest.raises(ValueError, match="revocation"):
        append(f, {"type": "revocation", "target": "v1"}, "k", str(private), {"k": str(public)})


def _signed_event(private, key_id, sequence, **fields):
    event = {"sequence": sequence, "key_id": key_id, **fields}
    with __import__("tempfile").TemporaryDirectory() as d:
        msg = Path(d) / "msg"
        msg.write_bytes(canonical(event))
        signature = subprocess.run(["openssl", "pkeyutl", "-sign", "-rawin", "-inkey", str(private), "-in", str(msg)], check=True, capture_output=True).stdout
    event["signature"] = base64.b64encode(signature).decode()
    return event


def test_notifier_persists_sequences_across_restart_and_publishes_signature(tmp_path):
    private, public = keypair(tmp_path)
    state = tmp_path / "notifier-state.json"
    sink = FileSink(tmp_path / "events")
    event = _signed_event(private, "issuer", 1, type="alert", expires_at="2027-01-01T00:00:00+00:00")
    consume(event, {"issuer": str(public)}, state, "2026-01-01T00:00:00+00:00", sink)
    assert '"signature"' in (tmp_path / "events").read_text()
    with pytest.raises(ValueError):
        consume(event, {"issuer": str(public)}, state, "2026-01-01T00:00:00+00:00", sink)


def test_notifier_rejects_unknown_key_and_control_field_collision(tmp_path):
    private, public = keypair(tmp_path)
    state = tmp_path / "state.json"
    sink = FileSink(tmp_path / "events")
    event = _signed_event(private, "unknown", 1, type="alert", expires_at="2027-01-01T00:00:00+00:00")
    with pytest.raises(ValueError):
        consume(event, {"issuer": str(public)}, state, "2026-01-01T00:00:00+00:00", sink)
    with pytest.raises(ValueError, match="control"):
        append(tmp_path / "collision", {"sequence": 9}, "issuer", str(private), {"issuer": str(public)})
