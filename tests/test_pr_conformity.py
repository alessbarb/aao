import base64
import hashlib
import json
import shutil
import subprocess

import pytest

from aao.pr_conformity import evaluate


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


@pytest.fixture
def trust_bundle(tmp_path):
    if not shutil.which("openssl"):
        pytest.skip("openssl is required to verify detached auditor signatures")
    private = tmp_path / "auditor-private.pem"
    public = tmp_path / "auditor-public.pem"
    subprocess.run(["openssl", "genpkey", "-algorithm", "ED25519", "-out", str(private)], check=True)
    subprocess.run(["openssl", "pkey", "-in", str(private), "-pubout", "-out", str(public)], check=True)
    policy = {"version": "GOV-REV-001/v1.1", "required_checks": ["tests", "lint"], "auditors": {"audit-principal": str(public)}}
    policy_path = tmp_path / "trusted-policy.json"
    policy_path.write_text(json.dumps(policy), encoding="utf-8")
    return private, policy_path, hashlib.sha256(canonical(policy)).hexdigest()


def successful_checks(repository):
    sha = subprocess.run(["git", "-C", str(repository), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    return {name: {"conclusion": "success", "head_sha": sha} for name in ("tests", "lint")}


@pytest.fixture
def candidate_repo(tmp_path):
    repository = tmp_path / "candidate"
    repository.mkdir()
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    subprocess.run(["git", "-C", str(repository), "config", "user.name", "candidate-test"], check=True)
    subprocess.run(["git", "-C", str(repository), "config", "user.email", "candidate@example.invalid"], check=True)
    (repository / "candidate.txt").write_text("candidate", encoding="utf-8")
    subprocess.run(["git", "-C", str(repository), "add", "candidate.txt"], check=True)
    subprocess.run(["git", "-C", str(repository), "commit", "-qm", "candidate"], check=True)
    return repository


def sign(report, private, report_path, signature_path):
    report_path.write_bytes(canonical(report))
    payload = report_path.with_suffix(".payload")
    payload.write_bytes(canonical(report))
    signature = subprocess.run(
        ["openssl", "pkeyutl", "-sign", "-inkey", str(private), "-rawin", "-in", str(payload)],
        check=True, capture_output=True,
    ).stdout
    signature_path.write_text(base64.b64encode(signature).decode("ascii"), encoding="ascii")


def make_report(repository, policy_digest, auditor="audit-principal", evidence_path=None):
    commit = subprocess.run(["git", "-C", str(repository), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    if evidence_path is None:
        raise AssertionError("tests must provide evidence outside the candidate checkout")
    evidence_path.write_bytes(b"test evidence")
    digest = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
    return {"candidate_sha": commit, "policy_sha256": policy_digest, "auditor_id": auditor,
            "verdict": "approve", "blocking_findings": [], "veto": False,
            "evidence_files": {digest: str(evidence_path)}}


def test_signed_independent_audit_and_required_checks_allow_conformity(tmp_path, trust_bundle, candidate_repo):
    private, policy, policy_digest = trust_bundle
    report_path, signature_path = tmp_path / "audit.json", tmp_path / "audit.sig"
    report = make_report(candidate_repo, policy_digest, evidence_path=tmp_path / "evidence.json")
    sign(report, private, report_path, signature_path)
    result = evaluate(candidate_repo, policy, report_path, signature_path,
                     successful_checks(candidate_repo), "implementer")
    assert result.conformant
    assert not result.reasons


def test_implementer_cannot_self_approve(tmp_path, trust_bundle, candidate_repo):
    private, policy, digest = trust_bundle
    report_path, signature_path = tmp_path / "audit.json", tmp_path / "audit.sig"
    sign(make_report(candidate_repo, digest, evidence_path=tmp_path / "evidence.json"), private, report_path, signature_path)
    result = evaluate(candidate_repo, policy, report_path, signature_path,
                      successful_checks(candidate_repo), "audit-principal")
    assert not result.conformant
    assert "implementer cannot audit their own change" in result.reasons


def test_stale_or_tampered_sha_and_missing_check_fail_closed(tmp_path, trust_bundle, candidate_repo):
    private, policy, digest = trust_bundle
    report_path, signature_path = tmp_path / "audit.json", tmp_path / "audit.sig"
    report = make_report(candidate_repo, digest, evidence_path=tmp_path / "evidence.json")
    report["candidate_sha"] = "0" * 40
    sign(report, private, report_path, signature_path)
    result = evaluate(candidate_repo, policy, report_path, signature_path,
                      {"tests": {"conclusion": "success", "head_sha": "0" * 40}}, "implementer")
    assert not result.conformant
    assert "audit report targets a different candidate SHA" in result.reasons
    assert "required check not successful: lint" in result.reasons


def test_report_modification_after_signing_is_rejected(tmp_path, trust_bundle, candidate_repo):
    private, policy, digest = trust_bundle
    report_path, signature_path = tmp_path / "audit.json", tmp_path / "audit.sig"
    report = make_report(candidate_repo, digest, evidence_path=tmp_path / "evidence.json")
    sign(report, private, report_path, signature_path)
    report["veto"] = True
    report_path.write_bytes(canonical(report))
    result = evaluate(candidate_repo, policy, report_path, signature_path,
                      successful_checks(candidate_repo), "implementer")
    assert not result.conformant
    assert "audit report signature is invalid" in result.reasons


def test_absent_auditor_blocks(tmp_path, trust_bundle, candidate_repo):
    _, policy, _ = trust_bundle
    result = evaluate(candidate_repo, policy, None, None,
                      successful_checks(candidate_repo), "implementer")
    assert not result.conformant
    assert "signed audit report is absent" in result.reasons


def test_new_commit_invalidates_prior_signed_report(tmp_path, trust_bundle):
    private, policy, digest = trust_bundle
    repository = tmp_path / "candidate"
    repository.mkdir()
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    subprocess.run(["git", "-C", str(repository), "config", "user.name", "test"], check=True)
    subprocess.run(["git", "-C", str(repository), "config", "user.email", "test@example.invalid"], check=True)
    candidate_file = repository / "candidate.txt"
    candidate_file.write_text("first", encoding="utf-8")
    subprocess.run(["git", "-C", str(repository), "add", "candidate.txt"], check=True)
    subprocess.run(["git", "-C", str(repository), "commit", "-qm", "first"], check=True)
    report_path, signature_path = tmp_path / "audit.json", tmp_path / "audit.sig"
    report = make_report(repository, digest, evidence_path=tmp_path / "evidence.json")
    sign(report, private, report_path, signature_path)
    candidate_file.write_text("changed after audit", encoding="utf-8")
    subprocess.run(["git", "-C", str(repository), "commit", "-qam", "changed"], check=True)
    result = evaluate(repository, policy, report_path, signature_path,
                      successful_checks(repository), "implementer")
    assert not result.conformant
    assert "audit report targets a different candidate SHA" in result.reasons


@pytest.mark.nt("NT-02-4")
def test_github_duplicate_checks_require_all_runs_to_pass_same_sha():
    from aao.pr_conformity import aggregate_github_check_runs

    sha = "a" * 40
    runs = [
        {"name": "test", "head_sha": sha, "conclusion": "success"},
        {"name": "test", "head_sha": sha, "conclusion": "failure"},
        {"name": "lint", "head_sha": "b" * 40, "conclusion": "success"},
    ]
    result = aggregate_github_check_runs(sha, runs)
    assert result["test"] == {"head_sha": sha, "conclusion": "failure"}
    assert result["lint"] == {"head_sha": "mismatch", "conclusion": "failure"}


@pytest.mark.parametrize("change", ["tracked", "untracked"])
def test_dirty_candidate_checkout_blocks_conformity(tmp_path, trust_bundle, candidate_repo, change):
    private, policy, digest = trust_bundle
    report_path, signature_path = tmp_path / "audit.json", tmp_path / "audit.sig"
    report = make_report(candidate_repo, digest, evidence_path=tmp_path / "evidence.json")
    sign(report, private, report_path, signature_path)
    if change == "tracked":
        (candidate_repo / "candidate.txt").write_text("modified", encoding="utf-8")
    else:
        (candidate_repo / "untracked.txt").write_text("untracked", encoding="utf-8")
    result = evaluate(candidate_repo, policy, report_path, signature_path,
                      successful_checks(candidate_repo), "implementer")
    assert not result.conformant
    assert "candidate checkout is dirty; audit must target the exact committed tree" in result.reasons
