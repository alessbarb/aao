import base64
import hashlib
import json
import os
import pwd
import shutil
import subprocess

import pytest

from aao import manifest_audit
from aao.independent_audit import AuditError
from aao.manifest_audit import audit_manifest, verify_promotion
from aao.pr_conformity import _canonical

UID = os.geteuid()
USER = pwd.getpwuid(UID).pw_name
REVIEWED = "b" * 40


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


def commit(repo, files, message):
    for name, content in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", message)
    return git(repo, "rev-parse", "HEAD")


def ok_runner(tree, argv):
    assert (tree / "src" / "app.py").is_file()
    parents = subprocess.run(["git", "-C", str(tree), "rev-list", "--parents", "-n", "1", "HEAD"], check=True,
                             capture_output=True, text=True).stdout.split()
    assert len(parents) == 3  # checks see git metadata of a [target, candidate] merge commit
    return 0, "1 passed", ""


@pytest.fixture
def env(tmp_path, monkeypatch):
    if not shutil.which("openssl"):
        pytest.skip("openssl is required for auditor signatures")
    monkeypatch.setattr(manifest_audit, "auditor_revision", lambda: REVIEWED)
    tmp_path.chmod(0o700)
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.name", "implementer")
    git(repo, "config", "user.email", "implementer@example.invalid")
    commit(repo, {"src/app.py": "X = 1\n", "src/other.py": "Y = 1\n", "tests/test_app.py": "def test():\n    assert 1\n"},
           "base")
    git(repo, "switch", "-q", "-c", "candidate")
    commit(repo, {"src/app.py": "X = 2\n"}, "candidate change")
    git(repo, "switch", "-q", "main")
    commit(repo, {"src/other.py": "Y = 2\n"}, "target moved on")
    trust = tmp_path / "trust"
    state = tmp_path / "state"
    for directory in (trust, state):
        directory.mkdir(mode=0o700)
    key = state / "auditor.pem"
    subprocess.run(["openssl", "genpkey", "-algorithm", "ED25519", "-out", str(key)], check=True)
    key.chmod(0o600)
    public = subprocess.run(["openssl", "pkey", "-in", str(key), "-pubout"], check=True, capture_output=True,
                            text=True).stdout
    policy_path = trust / "policy.json"
    anchor_path = trust / "anchor.json"
    attribution_path = trust / "attribution.json"
    ledger_anchor_path = trust / "ledger.anchor"
    attributed = {}

    def write_private(path, text):
        if path.exists():
            path.chmod(0o600)
        path.write_text(text, encoding="utf-8")
        path.chmod(0o600)

    def attribute(sha, identities=("codex-impl",)):
        attributed[sha] = list(identities)
        write_private(attribution_path, json.dumps({"schema": "aao.implementer-attribution.v1",
                                                    "candidates": attributed}))

    write_private(attribution_path, json.dumps({"schema": "aao.implementer-attribution.v1", "candidates": {}}))
    write_private(ledger_anchor_path, "0" * 64)

    def configure(policy_overrides=None, **anchor_overrides):
        policy = {
            "version": "GOV-REV-001/v1.1", "auditor_id": "aao-auditor", "auditor_os_user": USER,
            "developer_os_users": ["implementer-account"], "required_checks": [],
            "auditors": {"aao-auditor": "anchored"}, "audit_checks": {"unit": ["-m", "pytest"]},
            "protected_paths": ["src/aao/pr_conformity.py"], "dispositions": {},
            "trusted_auditor_revisions": [REVIEWED], **(policy_overrides or {}),
        }
        for path in (policy_path, anchor_path):
            if path.exists():
                path.chmod(0o600)
        policy_path.write_text(json.dumps(policy), encoding="utf-8")
        policy_path.chmod(0o600)
        anchor = {"schema": "aao.audit-trust-anchor.v1", "policy_path": str(policy_path),
                  "policy_sha256": hashlib.sha256(_canonical(policy)).hexdigest(), "auditor_uid": UID,
                  "auditor_public_key": public, "ledger_path": str(state / "ledger.jsonl"),
                  "ledger_anchor_path": str(ledger_anchor_path), "attribution_path": str(attribution_path),
                  **anchor_overrides}
        anchor_path.write_text(json.dumps(anchor), encoding="utf-8")
        anchor_path.chmod(0o600)

    configure()
    return {"tmp": tmp_path, "repo": repo, "key": key, "state": state, "anchor": anchor_path,
            "policy": policy_path, "configure": configure, "attribute": attribute,
            "ledger_anchor": ledger_anchor_path, "write_private": write_private}


def manifest(env, name="manifest.json", candidate="candidate", attribute=True, **overrides):
    repo = env["repo"]
    target = git(repo, "rev-parse", "main")
    sha = git(repo, "rev-parse", candidate)
    if attribute:
        env["attribute"](sha)
    merged = subprocess.run(["git", "-C", str(repo), "merge-tree", "--write-tree", target, sha],
                            capture_output=True, text=True, check=False).stdout.split()
    data = {"schema": "aao.candidate-manifest.v1", "repository": str(repo), "target_ref": "refs/heads/main",
            "target_sha": target, "candidate_sha": sha, "candidate_tree": git(repo, "rev-parse", f"{sha}^{{tree}}"),
            "result_tree": merged[0] if merged else "0" * 40, "producer": "integration-controller", **overrides}
    path = env["tmp"] / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return path, data


def audit(env, path, run="run", **kwargs):
    kwargs.setdefault("key_path", env["key"])
    return audit_manifest(path, env["state"] / run, kwargs.pop("key_path"), anchor_path=env["anchor"],
                          anchor_owner_uids=(UID,), runner=kwargs.pop("runner", ok_runner), **kwargs)


def gate(env, path, run="run", promoted=None):
    out = env["state"] / run
    return verify_promotion(path, out / "report.json", out / "report.sig", promoted,
                            anchor_path=env["anchor"], anchor_owner_uids=(UID,))


def merge_commit(env, data, tree=None, parents=None):
    parents = parents or [data["target_sha"], data["candidate_sha"]]
    args = [arg for parent in parents for arg in ("-p", parent)]
    return git(env["repo"], "commit-tree", tree or data["result_tree"], *args, "-m", "promote")


def test_resulting_tree_is_audited_signed_and_promotable(env):
    path, data = manifest(env)
    report = audit(env, path)
    assert report["verdict"] == "approve", report["custody_problems"] + report["blocking_findings"]
    assert report["result_tree"] == data["result_tree"] != data["candidate_tree"]
    assert gate(env, path) == (True, ())
    assert gate(env, path, promoted=merge_commit(env, data)) == (True, ())


def test_fast_forward_promotion_of_candidate_is_accepted(env):
    git(env["repo"], "switch", "-q", "-c", "ff", "main")
    commit(env["repo"], {"src/app.py": "X = 3\n"}, "ff change")
    git(env["repo"], "switch", "-q", "main")
    path, data = manifest(env, candidate="ff")
    assert data["result_tree"] == data["candidate_tree"]
    audit(env, path)
    assert gate(env, path, promoted=data["candidate_sha"]) == (True, ())


@pytest.mark.parametrize("field", ["candidate_tree", "result_tree"])
def test_tree_claim_that_does_not_match_git_is_refused(env, field):
    path, _ = manifest(env, **{field: "c" * 40})
    with pytest.raises(AuditError, match=field):
        audit(env, path)


def test_conflicting_candidate_is_refused(env):
    git(env["repo"], "switch", "-q", "-c", "conflict", "main~1")
    commit(env["repo"], {"src/other.py": "Y = 99\n"}, "conflict")
    git(env["repo"], "switch", "-q", "main")
    path, _ = manifest(env, candidate="conflict")
    with pytest.raises(AuditError, match="merge cleanly"):
        audit(env, path)


def test_target_moving_after_audit_blocks_the_gate(env):
    path, _ = manifest(env)
    audit(env, path)
    commit(env["repo"], {"src/third.py": "Z = 1\n"}, "concurrent push")
    ok, reasons = gate(env, path)
    assert not ok and "target ref no longer points to the manifest target_sha" in reasons


def test_promoted_commit_must_carry_the_audited_tree_and_parents(env):
    path, data = manifest(env)
    audit(env, path)
    wrong_tree = merge_commit(env, data, tree=data["candidate_tree"])
    assert "promoted commit tree is not the audited result_tree" in gate(env, path, promoted=wrong_tree)[1]
    wrong_parent = merge_commit(env, data, parents=[data["candidate_sha"], data["target_sha"]])
    assert "promoted commit parents are not [target_sha, candidate_sha]" in gate(env, path, promoted=wrong_parent)[1]


@pytest.mark.parametrize("overrides", [
    {"policy_path": "/tmp/attacker-policy.json"},
    {"target_ref": "main"},
    {"candidate_sha": "candidate"},
    {"repository": "relative/path"},
])
def test_malformed_or_overreaching_manifest_is_refused(env, overrides):
    path, _ = manifest(env, **overrides)
    with pytest.raises(AuditError, match="manifest is invalid"):
        audit(env, path)


def test_anchor_must_be_a_private_regular_file_with_safe_parents(env):
    path, _ = manifest(env)
    env["anchor"].chmod(0o660)
    with pytest.raises(AuditError, match="group/other writable"):
        audit(env, path)
    env["anchor"].chmod(0o600)
    link = env["tmp"] / "trust" / "link.json"
    link.symlink_to(env["anchor"])
    with pytest.raises(AuditError, match="symlink"):
        audit_manifest(path, env["state"] / "x", env["key"], anchor_path=link, anchor_owner_uids=(UID,))
    (env["tmp"] / "trust").chmod(0o770)
    with pytest.raises(AuditError, match="replaced"):
        audit(env, path)
    (env["tmp"] / "trust").chmod(0o700)
    with pytest.raises(AuditError, match="missing"):
        audit_manifest(path, env["state"] / "x", env["key"], anchor_path=env["tmp"] / "none.json",
                       anchor_owner_uids=(UID,))
    assert gate(env, path, run="never")[0] is False


def test_policy_must_match_the_anchor_pin_and_owner(env):
    path, _ = manifest(env)
    env["configure"](policy_sha256="d" * 64)
    with pytest.raises(AuditError, match="pinned"):
        audit(env, path)
    env["configure"](auditor_uid=UID + 1)
    with pytest.raises(AuditError, match="trusted uid"):
        audit(env, path)


def test_key_not_pinned_by_anchor_or_developer_account_is_provisional_and_unsigned(env):
    path, _ = manifest(env)
    other = env["state"] / "other.pem"
    subprocess.run(["openssl", "genpkey", "-algorithm", "ED25519", "-out", str(other)], check=True)
    other.chmod(0o600)
    report = audit(env, path, key_path=other)
    assert report["verdict"] == "provisional"
    assert "signing key does not match the anchored auditor public key" in report["custody_problems"]
    assert "signed audit report is absent" in gate(env, path)[1]
    env["configure"]({"developer_os_users": [USER]})
    assert audit(env, path, run="dev")["verdict"] == "provisional"


def test_tampered_evidence_or_report_fails_the_gate(env):
    path, _ = manifest(env)
    report = audit(env, path)
    evidence = next(iter(report["evidence_files"].values()))
    os.chmod(evidence, 0o600)
    with open(evidence, "ab") as handle:
        handle.write(b" ")
    os.chmod(evidence, 0o444)
    assert any("does not match its digest" in r for r in gate(env, path)[1])
    report_path = env["state"] / "run" / "report.json"
    report_path.chmod(0o600)
    report_path.write_bytes(_canonical({**report, "blocking_findings": []}).replace(b'"approve"', b'"approve" '))
    assert not gate(env, path)[0]


def test_veto_after_approval_is_sticky(env):
    path, _ = manifest(env)
    audit(env, path)
    audit(env, path, run="veto", veto_reason="unsafe")
    reasons = gate(env, path)[1]
    assert "candidate has a recorded audit veto" in reasons
    assert "report is not the latest recorded decision for this candidate" in reasons


def test_group_writable_ledger_is_not_trusted(env):
    path, _ = manifest(env)
    audit(env, path)
    (env["state"] / "ledger.jsonl").chmod(0o660)
    assert any("ledger is not trustworthy" in r for r in gate(env, path)[1])


def test_protected_path_in_result_tree_blocks(env):
    git(env["repo"], "switch", "-q", "candidate")
    commit(env["repo"], {"src/aao/pr_conformity.py": "weak = True\n"}, "touch gate")
    git(env["repo"], "switch", "-q", "main")
    path, _ = manifest(env)
    report = audit(env, path)
    assert report["verdict"] == "reject"
    assert "protected-path:src/aao/pr_conformity.py" in report["blocking_findings"]
    assert not gate(env, path)[0]


def test_gate_rejects_report_from_auditor_revision_no_longer_trusted(env):
    path, _ = manifest(env)
    audit(env, path)
    env["configure"]({"trusted_auditor_revisions": ["c" * 40]})
    reasons = gate(env, path)[1]
    assert "report was produced by an auditor revision the anchored policy does not trust" in reasons


# --- Second-line review SL-02/SL-03 (trust root) ------------------------------------------------------------

def test_unattributed_candidate_is_provisional_even_with_valid_custody(env):
    path, _ = manifest(env, attribute=False)
    report = audit(env, path)
    assert report["verdict"] == "provisional"
    assert "implementer attribution is unresolved" in report["custody_problems"]
    assert report["implementer_ids"] == [] and "integration-controller" in report["declared_implementers"]
    assert not gate(env, path)[0]


def test_recusal_uses_attribution_and_declared_identities_only_tighten(env):
    path, data = manifest(env)
    env["attribute"](data["candidate_sha"], ["aao-auditor"])  # authenticated pusher is the auditor itself
    assert "auditor-is-implementer" in audit(env, path)["blocking_findings"]
    path, data = manifest(env, name="declared.json", producer="aao-auditor")
    env["attribute"](data["candidate_sha"], ["codex-impl"])  # a declared match still blocks (stricter only)
    assert "auditor-is-implementer" in audit(env, path, run="declared")["blocking_findings"]


def test_attribution_file_writable_by_others_is_not_trusted(env):
    path, _ = manifest(env)
    attribution = env["tmp"] / "trust" / "attribution.json"
    attribution.chmod(0o660)
    assert "implementer attribution is unresolved" in audit(env, path)["custody_problems"]


def _ledger_lines(env):
    return (env["state"] / "ledger.jsonl").read_bytes().splitlines()


def _rewrite_chain(rows):
    """What an attacker with file access but no auditor key can do: drop rows and recompute the hash chain."""
    previous, out = "0" * 64, []
    for number, row in enumerate(rows, 1):
        row = {k: v for k, v in row.items() if k != "hash"}
        row.update(sequence=number, previous_hash=previous)
        row["hash"] = hashlib.sha256(_canonical(row)).hexdigest()
        previous = row["hash"]
        out.append(_canonical(row))
    return b"\n".join(out) + b"\n"


def test_ledger_rewritten_without_an_intermediate_veto_and_rehashed_is_rejected(env):
    # SL-06: delete a veto in the middle and recompute the hash chain. Later entries change sequence and
    # previous_hash, which are signed, so the rewrite fails without the auditor key.
    path, _ = manifest(env)
    audit(env, path)
    audit(env, path, run="veto", veto_reason="unsafe")
    audit(env, path, run="again")
    rows = [json.loads(line) for line in _ledger_lines(env)]
    assert [r["type"] for r in rows] == ["audit-verdict", "veto", "audit-verdict"]
    (env["state"] / "ledger.jsonl").write_bytes(_rewrite_chain([rows[0], rows[2]]))
    assert any("ledger is not trustworthy" in r for r in gate(env, path, run="again")[1])


def test_ledger_tail_truncation_below_the_external_anchor_is_rejected(env):
    path, _ = manifest(env)
    audit(env, path)
    audit(env, path, run="veto", veto_reason="unsafe")
    lines = _ledger_lines(env)
    env["write_private"](env["ledger_anchor"], json.loads(lines[-1])["hash"])  # custodian anchors the veto
    (env["state"] / "ledger.jsonl").write_bytes(lines[0] + b"\n")  # signed prefix kept, veto truncated
    reasons = gate(env, path)[1]
    assert any("does not contain its external anchor" in r for r in reasons)


def test_ledger_entry_signed_by_another_key_is_rejected(env):
    path, data = manifest(env)
    audit(env, path)
    rogue = env["state"] / "rogue.pem"
    subprocess.run(["openssl", "genpkey", "-algorithm", "ED25519", "-out", str(rogue)], check=True)
    previous = json.loads(_ledger_lines(env)[-1])
    report = (env["state"] / "run" / "report.json").read_bytes()
    entry = {"sequence": 2, "previous_hash": previous["hash"], "key_id": "aao-auditor", "type": "audit-verdict",
             "candidate_sha": data["candidate_sha"], "result_tree": data["result_tree"],
             "report_sha256": hashlib.sha256(report).hexdigest(), "verdict": "approve", "veto": False}
    message = env["state"] / "msg"
    message.write_bytes(_canonical(entry))
    signature = subprocess.run(["openssl", "pkeyutl", "-sign", "-rawin", "-inkey", str(rogue), "-in", str(message)],
                               check=True, capture_output=True).stdout
    entry["signature"] = base64.b64encode(signature).decode()
    entry["hash"] = hashlib.sha256(_canonical(entry)).hexdigest()
    with (env["state"] / "ledger.jsonl").open("ab") as handle:
        handle.write(_canonical(entry) + b"\n")
    assert any("ledger is not trustworthy" in r for r in gate(env, path)[1])
