"""Fail-closed conformity gate for an immutable Git revision.

This module verifies audit attestations signed by a configured key; it does not establish auditor identities,
review code, or grant promotion authority. Trust roots and reports must be supplied
outside the candidate checkout by an independently controlled process.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class GateResult:
    conformant: bool
    reasons: tuple[str, ...]
    candidate_sha: str


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def current_commit(repository: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "--verify", "HEAD^{commit}"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def aggregate_github_check_runs(candidate_sha: str, check_runs: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    """Aggregate GitHub check-runs; duplicate names pass only if every run passes this SHA."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in check_runs:
        name = item.get("name")
        if isinstance(name, str):
            grouped.setdefault(name, []).append(item)
    aggregated: dict[str, dict[str, str]] = {}
    for name, runs in grouped.items():
        exact = all(item.get("head_sha") == candidate_sha for item in runs)
        passed = exact and all(item.get("conclusion") == "success" for item in runs)
        aggregated[name] = {
            "head_sha": candidate_sha if exact else "mismatch",
            "conclusion": "success" if passed else "failure",
        }
    return aggregated


def fetch_github_pr_checks(repository_slug: str, pull_request_number: int) -> tuple[str, dict[str, dict[str, str]]]:
    """Read a PR and its check-runs via gh; performs no GitHub writes."""
    if not repository_slug or "/" not in repository_slug or pull_request_number <= 0:
        raise ValueError("repository and PR number are invalid")
    try:
        pull = subprocess.run(
            ["gh", "api", f"repos/{repository_slug}/pulls/{pull_request_number}"],
            check=True, capture_output=True, text=True,
        )
        pull_data = json.loads(pull.stdout)
        if pull_data.get("state") != "open":
            raise ValueError("pull request is not open")
        sha = pull_data["head"]["sha"]
        response = subprocess.run(
            ["gh", "api", f"repos/{repository_slug}/commits/{sha}/check-runs"],
            check=True, capture_output=True, text=True,
        )
        check_runs = json.loads(response.stdout)["check_runs"]
        if not isinstance(check_runs, list):
            raise TypeError("GitHub check-run response is malformed")
        return sha, aggregate_github_check_runs(sha, check_runs)
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError) as error:
        raise ValueError("could not obtain a valid read-only GitHub PR snapshot") from error


def evaluate(
    repository: Path,
    policy_path: Path,
    report_path: Path | None,
    signature_path: Path | None,
    check_results: dict[str, Any],
    implementer_id: str,
) -> GateResult:
    """Evaluate trusted policy, mandatory checks and a signed audit report."""
    sha = current_commit(repository)
    reasons: list[str] = []
    repository_root = repository.resolve()
    if policy_path.resolve().is_relative_to(repository_root):
        return GateResult(False, ("trusted policy must be outside the candidate checkout",), sha)
    if report_path is not None and report_path.resolve().is_relative_to(repository_root):
        return GateResult(False, ("audit report must be outside the candidate checkout",), sha)
    if signature_path is not None and signature_path.resolve().is_relative_to(repository_root):
        return GateResult(False, ("audit signature must be outside the candidate checkout",), sha)
    try:
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        if policy.get("version") != "GOV-REV-001/v1.1":
            reasons.append("unsupported or missing policy version")
        required = policy["required_checks"]
        reviewers = policy["auditors"]
        if not isinstance(required, list) or not required or any(not isinstance(item, str) for item in required):
            raise ValueError("required_checks must be a non-empty string list")
        if not isinstance(reviewers, dict) or not reviewers:
            raise ValueError("auditors must be a non-empty trust map")
        policy_digest = _sha(_canonical(policy))
    except (OSError, ValueError, KeyError, TypeError):
        return GateResult(False, ("trusted policy is missing or malformed",), sha)

    for check in required:
        result = check_results.get(check)
        if not isinstance(result, dict) or result.get("conclusion") != "success":
            reasons.append(f"required check not successful: {check}")
        elif result.get("head_sha") != sha:
            reasons.append(f"required check targets a different candidate SHA: {check}")

    if report_path is None or signature_path is None:
        reasons.append("signed audit report is absent")
        return GateResult(False, tuple(reasons), sha)
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        signature = base64.b64decode(signature_path.read_text(encoding="ascii").strip(), validate=True)
        auditor_id = report["auditor_id"]
        public_key = Path(reviewers[auditor_id]).resolve()
        if public_key.is_relative_to(repository_root):
            reasons.append("auditor trust key must be outside the candidate checkout")
        if auditor_id == implementer_id:
            reasons.append("implementer cannot audit their own change")
        if report.get("candidate_sha") != sha:
            reasons.append("audit report targets a different candidate SHA")
        if report.get("policy_sha256") != policy_digest:
            reasons.append("audit report targets a different policy")
        if report.get("verdict") != "approve":
            reasons.append("audit verdict is not approve")
        if report.get("blocking_findings"):
            reasons.append("blocking audit findings remain")
        if report.get("veto") is not False:
            reasons.append("audit veto is active or unspecified")
        evidence = report.get("evidence_files")
        if not isinstance(evidence, dict) or not evidence:
            reasons.append("audit evidence files are absent or malformed")
        else:
            for expected_digest, evidence_path in evidence.items():
                if (
                    not isinstance(expected_digest, str)
                    or len(expected_digest) != 64
                    or any(character not in "0123456789abcdef" for character in expected_digest)
                    or not isinstance(evidence_path, str)
                ):
                    reasons.append("audit evidence reference is malformed")
                    continue
                resolved_evidence = Path(evidence_path).resolve()
                if resolved_evidence.is_relative_to(repository_root):
                    reasons.append("audit evidence must be outside the candidate checkout")
                    continue
                try:
                    if _sha(resolved_evidence.read_bytes()) != expected_digest:
                        reasons.append("audit evidence content does not match its digest")
                except OSError:
                    reasons.append("audit evidence file is unavailable")
        with tempfile.TemporaryDirectory(prefix="aao-pr-gate-") as temporary_directory:
            detached = Path(temporary_directory) / "report.sig"
            payload = Path(temporary_directory) / "report.json"
            detached.write_bytes(signature)
            payload.write_bytes(_canonical(report))
            verify = subprocess.run(
                ["openssl", "pkeyutl", "-verify", "-pubin", "-inkey", str(public_key), "-rawin", "-in", str(payload), "-sigfile", str(detached)],
                check=False,
                capture_output=True,
            )
        if verify.returncode != 0:
            reasons.append("audit report signature is invalid")
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        reasons.append("audit report, signature, or auditor trust entry is invalid")
    return GateResult(not reasons, tuple(reasons), sha)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail-closed gate for a signed PR audit")
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True, help="trusted policy outside the candidate checkout")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--signature", type=Path)
    check_source = parser.add_mutually_exclusive_group(required=True)
    check_source.add_argument("--checks", type=Path, help="JSON object of check name to conclusion and SHA")
    check_source.add_argument("--github-pr", nargs=2, metavar=("REPOSITORY", "NUMBER"), help="fetch read-only PR checks through gh")
    parser.add_argument("--implementer", required=True, help="implementer principal from trusted CI context")
    args = parser.parse_args()
    try:
        if args.github_pr:
            _, check_results = fetch_github_pr_checks(args.github_pr[0], int(args.github_pr[1]))
        else:
            check_results = json.loads(args.checks.read_text(encoding="utf-8"))
        if not isinstance(check_results, dict) or any(
            not isinstance(name, str) or not isinstance(item, dict)
            or not isinstance(item.get("conclusion"), str) or not isinstance(item.get("head_sha"), str)
            for name, item in check_results.items()
        ):
            raise ValueError("check results must map names to conclusion and head_sha records")
    except (OSError, ValueError):
        print(json.dumps({"conformant": False, "reasons": ["check results are missing, malformed, or unavailable"]}))
        return 1
    result = evaluate(args.repository, args.policy, args.report, args.signature, check_results, args.implementer)
    print(json.dumps({"conformant": result.conformant, "candidate_sha": result.candidate_sha, "reasons": result.reasons}, sort_keys=True))
    return 0 if result.conformant else 1


if __name__ == "__main__":
    raise SystemExit(main())
