"""Minimal independent audit emitter and promotion decision (GOV-REV-001 v1.1).

The emitter clones a candidate at an exact SHA into a fresh directory, runs
policy-defined Python checks in a read-only, network-less bubblewrap sandbox,
applies adversarial diff rules defined only in the trusted policy, writes
content-addressed evidence, signs the report with an Ed25519 key, and appends
the decision to a hash-chained ledger. ``promotion_decision`` combines the
existing ``pr_conformity.evaluate`` gate with the ledger so a recorded veto or a
newer decision overrides an older approval.

Independence is not established by this code. It is established only when the
policy, key, ledger and evidence directory are owned by a dedicated auditor OS
account that the implementer cannot control. Outside that custody the emitter
records a ``provisional`` verdict and does not sign, which the gate rejects.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import pwd
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aao.pr_conformity import GateResult, _canonical, _sha, evaluate, fetch_github_pr_checks

POLICY_VERSION = "GOV-REV-001/v1.1"
_GIT_ENV = {
    "PATH": "/usr/bin:/bin",
    "HOME": "/nonexistent",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_TERMINAL_PROMPT": "0",
    "LANG": "C.UTF-8",
}
_OUTPUT_LIMIT = 12_000
_SANDBOX_SYSTEM_PATHS = ("/usr", "/bin", "/lib", "/lib64", "/etc")
_LIMITATIONS = (
    ("Auditor checks run only Python argv defined by the trusted policy; PostgreSQL integration tests are skipped "
     "inside the network-less sandbox and are covered only by implementer-controlled CI."),
    "CI check-runs are recorded as implementer-controlled inputs, not as independent evidence.",
    "Adversarial rules are deterministic path and test-weakening heuristics, not a semantic security review.",
    ("The ledger hash chain is unkeyed: it detects accidental corruption only; protection against anyone able "
     "to write the file (for example to drop a veto) comes solely from auditor-account file custody."),
    ("The gate's implementer identity comes from the caller; it must be supplied by the merge authority, "
     "not by the implementer."),
)


class AuditError(RuntimeError):
    """The audit could not be performed safely; no verdict was recorded."""


def _is_sha(value: object) -> bool:
    return isinstance(value, str) and len(value) == 40 and all(c in "0123456789abcdef" for c in value)


def _git(repository: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", "-C", str(repository), *args],
        check=True, capture_output=True, text=True, env=_GIT_ENV, timeout=300,
    ).stdout


def load_policy(path: Path) -> tuple[dict[str, Any], str]:
    try:
        data = path.read_bytes()
    except OSError as error:
        raise AuditError(f"trusted policy is invalid: {error}") from error
    return parse_policy(data)


def parse_policy(data: bytes) -> tuple[dict[str, Any], str]:
    try:
        policy = json.loads(data)
        if not isinstance(policy, dict) or policy.get("version") != POLICY_VERSION:
            raise ValueError("unsupported policy version")
        for key, kind in (("auditor_id", str), ("auditor_os_user", str), ("developer_os_users", list),
                          ("required_checks", list), ("auditors", dict), ("audit_checks", dict),
                          ("protected_paths", list), ("dispositions", dict),
                          ("trusted_auditor_revisions", list)):
            if not isinstance(policy.get(key), kind):
                raise TypeError(f"policy field {key} is missing or malformed")
        if not policy["audit_checks"] or any(
            not isinstance(argv, list) or not argv or not all(isinstance(a, str) for a in argv)
            for argv in policy["audit_checks"].values()
        ):
            raise ValueError("audit_checks must map names to non-empty argv lists")
        if policy["auditor_id"] not in policy["auditors"]:
            raise ValueError("auditor_id must be a trusted auditor in the policy")
    except (ValueError, TypeError) as error:
        raise AuditError(f"trusted policy is invalid: {error}") from error
    return policy, _sha(_canonical(policy))


def fetch_candidate(source: str, candidate_sha: str, base_sha: str, destination: Path) -> Path:
    """Clone ``source`` and detach at the exact candidate SHA; never reuse a working checkout."""
    if not _is_sha(candidate_sha) or not _is_sha(base_sha):
        raise AuditError("candidate and base must be full lowercase commit SHAs")
    try:
        subprocess.run(["git", "clone", "--quiet", "--no-checkout", "--no-hardlinks", source, str(destination)],
                       check=True, capture_output=True, env=_GIT_ENV, timeout=600)
        for sha in (candidate_sha, base_sha):
            if subprocess.run(["git", "-C", str(destination), "cat-file", "-e", f"{sha}^{{commit}}"],
                              check=False, capture_output=True, env=_GIT_ENV).returncode:
                _git(destination, "fetch", "--quiet", "--no-tags", "origin", sha)
        _git(destination, "checkout", "--quiet", "--detach", candidate_sha)
        if _git(destination, "rev-parse", "HEAD").strip() != candidate_sha:
            raise AuditError("candidate checkout does not match the requested SHA")
        if _git(destination, "status", "--porcelain", "--untracked-files=all").strip():
            raise AuditError("candidate checkout is not clean")
    except (OSError, subprocess.SubprocessError) as error:
        raise AuditError("candidate revision could not be fetched by exact SHA") from error
    return destination


def adversarial_findings(clone: Path, base_sha: str, candidate_sha: str, policy: dict[str, Any]) -> list[dict[str, str]]:
    """Rules live in the auditor's code and trusted policy, never in the candidate."""
    findings: list[dict[str, str]] = []
    protected = tuple(policy["protected_paths"])
    for line in _git(clone, "diff", "--no-renames", "--name-status", base_sha, candidate_sha).splitlines():
        status, path = line.split("\t", 1)
        if path.startswith(protected):
            findings.append({"id": f"protected-path:{path}", "path": path,
                             "detail": "change to audit, governance or CI control requires disposition by separate authority"})
        if status == "D" and path.startswith("tests/"):
            findings.append({"id": f"deleted-test:{path}", "path": path, "detail": "test file deleted"})
    asserts: dict[str, list[int]] = {}
    current, line_number = "", 0
    for line in _git(clone, "diff", "--no-renames", "-U0", base_sha, candidate_sha, "--", "tests").splitlines():
        if line.startswith("+++ "):
            current = line[6:] if line.startswith("+++ b/") else ""
            continue
        if line.startswith("@@"):
            line_number = int(line.split("+", 1)[1].split(" ", 1)[0].split(",", 1)[0])
            continue
        if line.startswith("--- ") or not current:
            continue
        if line.startswith("+") and any(m in line for m in ("pytest.skip", "mark.skip", "xfail", "importorskip")):
            findings.append({"id": f"added-skip:{current}:{line_number}", "path": current,
                             "detail": f"test skip or expected failure added: {line[1:].strip()[:120]}"})
        if line.startswith("+"):
            line_number += 1
        if line[:1] in "+-" and line[1:].lstrip().startswith("assert"):
            asserts.setdefault(current, [0, 0])[line[0] == "-"] += 1
    for path, (added, removed) in sorted(asserts.items()):
        if removed > added:
            findings.append({"id": f"removed-asserts:{path}", "path": path,
                             "detail": f"{removed} assertions removed, {added} added"})
    return list({item["id"]: item for item in findings}.values())


def _sandbox_runtimes() -> list[str]:
    return sorted({str(Path(sys.base_prefix).resolve()), os.path.abspath(sys.prefix)})


def _visible_in_sandbox(path: Path) -> bool:
    resolved = path.resolve()
    return any(resolved.is_relative_to(root) for root in (*_SANDBOX_SYSTEM_PATHS, *_sandbox_runtimes()))


def _interpreter_links(executable: str, mounted: list[str]) -> list[str]:
    """Recreate symlink hops (venv -> shim -> real interpreter) without mounting their parent directories."""
    args, path = [], os.path.abspath(executable)
    for _ in range(40):
        parts = Path(path).parts
        for index in range(2, len(parts) + 1):
            prefix = os.path.join(*parts[:index])
            if os.path.islink(prefix):
                target = os.readlink(prefix)
                if not any(prefix == m or prefix.startswith(m + "/") for m in mounted):
                    args += ["--symlink", target, prefix]
                path = os.path.normpath(os.path.join(os.path.dirname(prefix), target, *parts[index:]))
                break
        else:
            return args
    raise AuditError("interpreter symlink chain is too deep")


def run_sandboxed(clone: Path, argv: list[str], timeout_seconds: int = 600) -> tuple[int, str, str]:
    """Run trusted-policy Python argv against a read-only candidate with no network or secrets."""
    bwrap, timeout, prlimit = shutil.which("bwrap"), shutil.which("timeout"), shutil.which("prlimit")
    if sys.platform != "linux" or not bwrap or not timeout or not prlimit:
        raise AuditError("bubblewrap, timeout and prlimit are required for audit checks")
    # Interpreter and environment keep their host paths so nested tools (ruff binary, sandboxed tests) resolve alike.
    runtimes = _sandbox_runtimes()
    command = [
        bwrap, "--unshare-all", "--die-with-parent", "--new-session",
        *[arg for path in _SANDBOX_SYSTEM_PATHS if Path(path).exists()
          for arg in ("--ro-bind", path, path)],
        "--proc", "/proc", "--dev", "/dev", "--size", "268435456", "--tmpfs", "/tmp", "--dir", "/tmp/home",
        *[arg for path in runtimes for arg in ("--ro-bind", path, path)],
        *_interpreter_links(sys.executable, runtimes),
        "--ro-bind", str(clone), "/workspace", "--chdir", "/workspace",
        "--setenv", "HOME", "/tmp/home", "--setenv", "TMPDIR", "/tmp", "--setenv", "PATH", "/usr/bin:/bin",
        "--setenv", "PYTHONPATH", "/workspace/src",
        "--setenv", "PYTHONDONTWRITEBYTECODE", "1", "--setenv", "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1",
        timeout, "--signal=TERM", "--kill-after=5", f"{timeout_seconds}s",
        prlimit, "--as=2147483648", "--fsize=16777216", "--nproc=128", "--nofile=256", "--",
        os.path.abspath(sys.executable), "-B", *argv,
    ]
    result = subprocess.run(command, check=False, stdin=subprocess.DEVNULL, capture_output=True, text=True, errors="replace",
                            cwd="/", env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"}, timeout=timeout_seconds + 30)
    return result.returncode, result.stdout[-_OUTPUT_LIMIT:], result.stderr[-_OUTPUT_LIMIT:]


def auditor_revision() -> str:
    """The auditor's own committed revision; a dirty tree never matches a reviewed revision."""
    root = Path(__file__).resolve().parents[2]
    try:
        sha = _git(root, "rev-parse", "HEAD").strip()
        dirty = _git(root, "status", "--porcelain", "--untracked-files=all").strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return f"{sha}-dirty" if dirty else sha


def custody_problems(policy: dict[str, Any], key_path: Path | None) -> list[str]:
    """Signing is valid only from reviewed auditor code, run by the auditor account with a private key."""
    user = pwd.getpwuid(os.geteuid()).pw_name
    problems = []
    if auditor_revision() not in policy["trusted_auditor_revisions"]:
        problems.append("auditor code revision is not an independently reviewed revision")
    if user != policy["auditor_os_user"]:
        problems.append(f"audit is not running as the designated auditor account ({user})")
    if user in policy["developer_os_users"] or policy["auditor_os_user"] in policy["developer_os_users"]:
        problems.append("auditor account is also a developer account")
    if key_path is None:
        problems.append("no auditor signing key was provided")
    else:
        try:
            info = key_path.stat()
            if info.st_uid != os.geteuid() or info.st_mode & 0o077:
                problems.append("signing key is not private to the auditor account")
        except OSError:
            problems.append("signing key is unavailable")
    return problems


def _write_evidence(directory: Path, name: str, content: dict[str, Any]) -> tuple[str, str]:
    path = directory / f"{name}.json"
    data = _canonical(content)
    path.write_bytes(data)
    path.chmod(0o444)
    return _sha(data), str(path.resolve())


def _ledger_entries(ledger: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    previous = "0" * 64
    if not ledger.exists():
        return entries
    for line in ledger.read_text(encoding="utf-8").splitlines():
        entry = json.loads(line)
        body = {k: v for k, v in entry.items() if k != "entry_sha256"}
        if body.get("prev_sha256") != previous or entry.get("entry_sha256") != _sha(_canonical(body)):
            raise AuditError("audit ledger chain is broken")
        previous = entry["entry_sha256"]
        entries.append(entry)
    return entries


def _append_ledger(ledger: Path, report: dict[str, Any], report_sha256: str) -> None:
    with ledger.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        entries = _ledger_entries(ledger)
        body = {
            "seq": len(entries), "prev_sha256": entries[-1]["entry_sha256"] if entries else "0" * 64,
            "candidate_sha": report["candidate_sha"], "report_sha256": report_sha256,
            "verdict": report["verdict"], "veto": report["veto"], "auditor_id": report["auditor_id"],
            "recorded_at": report["created_at"],
        }
        handle.write(json.dumps({**body, "entry_sha256": _sha(_canonical(body))}, sort_keys=True) + "\n")


LEGACY_RETIRED = ("legacy audit path retired: caller-supplied policy/key/ledger cannot approve or promote; "
                  "use manifest_audit with the fixed trust anchor and the F3a integrator")


def audit_candidate(
    *, source: str, candidate_sha: str, base_sha: str, policy_path: Path, output: Path, ledger: Path,
    key_path: Path | None, implementer_ids: list[str], ci_checks: dict[str, Any] | None = None,
    veto_reason: str | None = None, current_head: Callable[[], str] | None = None,
    current_base: Callable[[], str] | None = None,
    runner: Callable[[Path, list[str]], tuple[int, str, str]] = run_sandboxed,
) -> dict[str, Any]:
    policy, policy_digest = load_policy(policy_path)
    for secret in (key_path, output, ledger, policy_path):
        if secret is not None and _visible_in_sandbox(secret):
            raise AuditError(f"{secret} would be readable by candidate code inside the sandbox")
    output.mkdir(parents=True, exist_ok=False)
    evidence_dir = output / "evidence"
    evidence_dir.mkdir()
    evidence: dict[str, str] = {}
    with tempfile.TemporaryDirectory(prefix="aao-audit-candidate-") as temporary:
        clone = fetch_candidate(source, candidate_sha, base_sha, Path(temporary) / "candidate")
        findings = adversarial_findings(clone, base_sha, candidate_sha, policy)
        checks: dict[str, dict[str, Any]] = {}
        for name, argv in sorted(policy["audit_checks"].items()):
            code, stdout, stderr = runner(clone, argv)
            checks[name] = {"conclusion": "success" if code == 0 else "failure", "exit_code": code}
            digest, path = _write_evidence(evidence_dir, f"check-{name}", {
                "candidate_sha": candidate_sha, "check": name, "argv": argv, "exit_code": code,
                "stdout_tail": stdout, "stderr_tail": stderr,
                "sandbox": "bwrap: read-only candidate, unshared network, no home or credentials",
            })
            evidence[digest] = path
        if _git(clone, "rev-parse", "HEAD").strip() != candidate_sha or _git(clone, "status", "--porcelain").strip():
            raise AuditError("candidate changed during the audit")
    digest, path = _write_evidence(evidence_dir, "adversarial-findings", {
        "candidate_sha": candidate_sha, "base_sha": base_sha, "findings": findings})
    evidence[digest] = path
    ci = ci_checks or {}
    digest, path = _write_evidence(evidence_dir, "ci-checks-implementer-controlled", {
        "candidate_sha": candidate_sha, "check_runs": ci})
    evidence[digest] = path

    blocking = [f["id"] for f in findings if f"{candidate_sha}:{f['id']}" not in policy["dispositions"]]
    blocking += [f"audit-check-failed:{n}" for n, c in checks.items() if c["conclusion"] != "success"]
    blocking += [f"ci-check-not-successful:{n}" for n in policy["required_checks"]
                 if not isinstance(ci.get(n), dict) or ci[n].get("conclusion") != "success"
                 or ci[n].get("head_sha") != candidate_sha]
    if policy["auditor_id"] in implementer_ids or not implementer_ids:
        blocking.append("auditor-is-implementer-or-implementer-unknown")
    custody = custody_problems(policy, key_path)
    # SL-01: this legacy path takes policy, key and ledger from its caller, so it can never approve or sign.
    # Promotion goes only through manifest_audit (fixed trust anchor) and the F3a integrator.
    custody.append(LEGACY_RETIRED)
    verdict = "veto" if veto_reason else "reject" if blocking else "provisional"
    report = {
        "schema": "aao.audit-report.v1", "candidate_sha": candidate_sha, "base_sha": base_sha,
        "policy_version": POLICY_VERSION, "policy_sha256": policy_digest, "auditor_id": policy["auditor_id"],
        "auditor_revision": auditor_revision(),
        "implementer_ids": sorted(set(implementer_ids)), "verdict": verdict, "veto": bool(veto_reason),
        "veto_reason": veto_reason or "", "blocking_findings": blocking, "findings": findings,
        "dispositions_applied": sorted(f["id"] for f in findings if f["id"] not in blocking),
        "audit_checks": checks, "custody_problems": custody, "evidence_files": evidence,
        "assurance_level": "A", "scope": "exact candidate tree against base; local, inert, disposable",
        "limitations": list(_LIMITATIONS),
        "residual_risks": ["independence holds only while auditor account custody holds"],
        "permitted_operations": ["promotion decision by a separate merge authority"] if verdict == "approve" else [],
        "prohibited_operations": ["self-merge by implementer", "deployment", "external effects"],
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    if current_head is not None and current_head() != candidate_sha:
        raise AuditError("candidate head moved before the verdict was recorded")
    if current_base is not None and current_base() != base_sha:
        raise AuditError("pull request base moved before the verdict was recorded")
    report_bytes = _canonical(report)
    (output / "report.json").write_bytes(report_bytes)
    _append_ledger(ledger, report, _sha(report_bytes))
    return report


def promotion_decision(
    repository: Path, policy_path: Path, report_path: Path | None, signature_path: Path | None,
    check_results: dict[str, Any], implementer_id: str, ledger: Path, *, current_base_sha: str,
) -> GateResult:
    """Retired (SL-01): always denies. Kept so old callers fail closed instead of breaking silently."""
    result = evaluate(repository, policy_path, report_path, signature_path, check_results, implementer_id)
    reasons = [LEGACY_RETIRED, *result.reasons]
    try:
        policy, _ = load_policy(policy_path)
        report = json.loads(report_path.read_text(encoding="utf-8")) if report_path else {}
        if report.get("base_sha") != current_base_sha:
            reasons.append("audit report targets a different base than the current pull request base")
        if report.get("auditor_revision") not in policy["trusted_auditor_revisions"]:
            reasons.append("audit report was produced by an auditor revision the policy does not trust")
    except (OSError, ValueError, AuditError):
        reasons.append("audit report or policy is unreadable")
    try:
        entries = [e for e in _ledger_entries(ledger) if e.get("candidate_sha") == result.candidate_sha]
        if any(e.get("veto") for e in entries):
            reasons.append("candidate has a recorded audit veto")
        report_digest = None
        if report_path is not None and report_path.is_file():
            report_digest = _sha(_canonical(json.loads(report_path.read_text(encoding="utf-8"))))
        if not entries or entries[-1].get("report_sha256") != report_digest:
            reasons.append("audit report is not the latest recorded decision for this candidate")
    except (OSError, ValueError, AuditError):
        reasons.append("audit ledger is missing or invalid")
    return GateResult(not reasons, tuple(dict.fromkeys(reasons)), result.candidate_sha)


def _gh_json(path: str) -> Any:
    return json.loads(subprocess.run(["gh", "api", path], check=True, capture_output=True, text=True).stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description="AAO independent audit emitter and promotion decision")
    commands = parser.add_subparsers(dest="command", required=True)
    audit = commands.add_parser("audit", help="audit an open GitHub PR at its exact head SHA (read-only)")
    audit.add_argument("--github-pr", nargs=2, metavar=("REPOSITORY", "NUMBER"), required=True)
    audit.add_argument("--policy", type=Path, required=True)
    audit.add_argument("--output", type=Path, required=True)
    audit.add_argument("--ledger", type=Path, required=True)
    audit.add_argument("--key", type=Path)
    audit.add_argument("--veto", metavar="REASON")
    audit.add_argument("--source", help="clone source; defaults to the PR head repository URL")
    gate = commands.add_parser("gate", help="promotion decision for a checkout at the candidate SHA")
    for name in ("--repository", "--policy", "--report", "--signature", "--ledger"):
        gate.add_argument(name, type=Path, required=name != "--signature")
    gate.add_argument("--github-pr", nargs=2, metavar=("REPOSITORY", "NUMBER"), required=True)
    gate.add_argument("--implementer", required=True, help="implementer supplied by the merge authority")
    args = parser.parse_args()
    slug, number = args.github_pr[0], int(args.github_pr[1])
    try:
        if args.command == "gate":
            _, checks = fetch_github_pr_checks(slug, number)
            base = _gh_json(f"repos/{slug}/pulls/{number}")["base"]["sha"]
            result = promotion_decision(args.repository, args.policy, args.report, args.signature, checks,
                                        args.implementer, args.ledger, current_base_sha=base)
            print(json.dumps({"conformant": result.conformant, "candidate_sha": result.candidate_sha,
                              "reasons": result.reasons}, sort_keys=True))
            return 0 if result.conformant else 1
        pull = _gh_json(f"repos/{slug}/pulls/{number}")
        if pull.get("state") != "open":
            raise AuditError("pull request is not open")
        candidate = pull["head"]["sha"]
        commits = _gh_json(f"repos/{slug}/pulls/{number}/commits?per_page=100")
        implementers = [pull["user"]["login"]] + [
            item for c in commits for item in ((c.get("author") or {}).get("login"), c["commit"]["author"]["email"]) if item
        ]
        _, ci = fetch_github_pr_checks(slug, number)
        report = audit_candidate(
            source=args.source or pull["head"]["repo"]["clone_url"], candidate_sha=candidate, base_sha=pull["base"]["sha"],
            policy_path=args.policy, output=args.output, ledger=args.ledger, key_path=args.key,
            implementer_ids=implementers, ci_checks=ci, veto_reason=args.veto,
            current_head=lambda: _gh_json(f"repos/{slug}/pulls/{number}")["head"]["sha"],
            current_base=lambda: _gh_json(f"repos/{slug}/pulls/{number}")["base"]["sha"],
        )
    except (AuditError, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(json.dumps({"error": str(error)}))
        return 2
    print(json.dumps({k: report[k] for k in ("candidate_sha", "verdict", "veto", "blocking_findings",
                                             "custody_problems")}, sort_keys=True))
    return 0 if report["verdict"] == "approve" else 1


if __name__ == "__main__":
    raise SystemExit(main())
