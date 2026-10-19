"""Local, fail-closed candidate integration checks for AAO development.

This controller records immutable Git revisions, tests their merge in a disposable
worktree, and writes content-addressed local evidence. It cannot promote or push.
It is an engineering tool, not the independent audit/conformity authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aao import sandboxed_repository_checks
from aao.sandboxed_repository_checks import RepositoryCheckError, run_repository_check

_SHA = re.compile(r"^[0-9a-f]{40}$")
_SCHEMA = "aao.local-candidate.v2"
_MANIFEST_SCHEMA = "aao.candidate-manifest.v1"
_EVIDENCE_SCHEMA = "aao.local-integration-evidence.v3"
PROMOTION_ENABLED = False


class CandidateControllerError(RuntimeError):
    """Candidate registration or isolated integration failed closed."""


def _git(repository: Path, *args: str, timeout: int = 30) -> str:
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": "/nonexistent",
        "LANG": "C.UTF-8",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_TERMINAL_PROMPT": "0",
    }
    try:
        result = subprocess.run(
            ["git", "-C", str(repository), *args],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            cwd="/",
            env=env,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise CandidateControllerError("Git candidate operation unavailable") from exc
    if result.returncode:
        raise CandidateControllerError("Git candidate operation failed")
    return result.stdout.strip()


def _resolve_commit(repository: Path, revision: str) -> str:
    if not isinstance(revision, str) or not _SHA.fullmatch(revision):
        raise CandidateControllerError("full immutable commit SHA required")
    resolved = _git(repository, "rev-parse", "--verify", f"{revision}^{{commit}}")
    if resolved != revision:
        raise CandidateControllerError("revision did not resolve to the declared commit")
    return resolved


def _resolve_target_ref(repository: Path, target_ref: str, target_sha: str) -> str:
    if not isinstance(target_ref, str) or not target_ref.startswith("refs/heads/"):
        raise CandidateControllerError("full refs/heads ref required")
    try:
        _git(repository, "check-ref-format", target_ref)
        resolved = _git(repository, "rev-parse", "--verify", f"{target_ref}^{{commit}}")
    except CandidateControllerError as exc:
        raise CandidateControllerError("target ref is invalid or unavailable") from exc
    if resolved != target_sha:
        raise CandidateControllerError("target ref moved or does not resolve to target SHA")
    return target_ref


def _candidate_trees(repository: Path, target_sha: str, candidate_sha: str) -> tuple[str, str]:
    candidate_tree = _git(repository, "rev-parse", "--verify", f"{candidate_sha}^{{tree}}")
    merge_output = _git(repository, "merge-tree", "--write-tree", target_sha, candidate_sha)
    result_tree = merge_output.splitlines()[0] if merge_output else ""
    if not _SHA.fullmatch(candidate_tree) or not _SHA.fullmatch(result_tree):
        raise CandidateControllerError("Git did not produce valid candidate and result trees")
    return candidate_tree, result_tree


def _state_path(repository: Path, state_directory: str | Path, *, create: bool) -> Path:
    state = Path(state_directory).expanduser().resolve()
    if state == repository or state.is_relative_to(repository):
        raise CandidateControllerError("candidate state must be outside the repository")
    if create:
        state.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not state.is_dir():
        raise CandidateControllerError("candidate state directory is unavailable")
    if stat.S_IMODE(state.stat().st_mode) & 0o077:
        raise CandidateControllerError("candidate state directory must be private to its owner")
    return state


def _write_json(path: Path, value: dict[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    digest = hashlib.sha256(payload).hexdigest()
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)
    return digest


def _record_digest(value: dict[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(payload).hexdigest()


def _source_digest(source: str | Path) -> str:
    try:
        return hashlib.sha256(Path(source).read_bytes()).hexdigest()
    except OSError as exc:
        raise CandidateControllerError("candidate controller source evidence unavailable") from exc


def _candidate_identifier(target_ref: str, target_sha: str, candidate_sha: str) -> str:
    return hashlib.sha256(f"{target_ref}:{target_sha}:{candidate_sha}".encode()).hexdigest()


def register_candidate(
    repository: str | Path,
    target_sha: str,
    candidate_sha: str,
    state_directory: str | Path,
    *,
    target_ref: str,
) -> dict[str, Any]:
    """Register a target/candidate pair without changing refs or worktrees."""
    root = Path(repository).resolve()
    if not root.is_dir():
        raise CandidateControllerError("Git repository unavailable")
    target = _resolve_commit(root, target_sha)
    candidate = _resolve_commit(root, candidate_sha)
    resolved_target_ref = _resolve_target_ref(root, target_ref, target)
    candidate_tree, result_tree = _candidate_trees(root, target, candidate)
    state = _state_path(root, state_directory, create=True)
    candidate_id = _candidate_identifier(resolved_target_ref, target, candidate)
    manifest = {
        "schema": _MANIFEST_SCHEMA,
        "repository": str(root),
        "target_ref": resolved_target_ref,
        "target_sha": target,
        "candidate_sha": candidate,
        "candidate_tree": candidate_tree,
        "result_tree": result_tree,
        "producer": f"aao.local_candidate_controller:uid:{os.geteuid()}",
    }
    manifest_path = state / f"{candidate_id}.manifest.json"
    path = state / f"{candidate_id}.json"
    if path.exists():
        raise CandidateControllerError("candidate pair already registered; refusing overwrite")
    if manifest_path.exists():
        raise CandidateControllerError("candidate manifest already exists; refusing overwrite")
    manifest_digest = _write_json(manifest_path, manifest)
    record = {
        "schema": _SCHEMA,
        "candidate_id": candidate_id,
        "repository": str(root),
        "target_ref": resolved_target_ref,
        "target_sha": target,
        "candidate_sha": candidate,
        "candidate_tree": candidate_tree,
        "result_tree": result_tree,
        "manifest_path": str(manifest_path),
        "manifest_sha256": manifest_digest,
        "registered_at": datetime.now(UTC).isoformat(),
        "promotion": "disabled",
    }
    record["record_sha256"] = _record_digest(record)
    _write_json(path, record)
    return record


def _load_record(repository: Path, candidate_id: str, state: Path) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{64}", candidate_id):
        raise CandidateControllerError("invalid candidate identifier")
    path = state / f"{candidate_id}.json"
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CandidateControllerError("candidate record unavailable or malformed") from exc
    expected_digest = record.pop("record_sha256", None)
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    if expected_digest != hashlib.sha256(canonical).hexdigest():
        raise CandidateControllerError("candidate record integrity check failed")
    if record.get("schema") != _SCHEMA or record.get("repository") != str(repository):
        raise CandidateControllerError("candidate record belongs to another repository")
    if record.get("candidate_id") != candidate_id:
        raise CandidateControllerError("candidate record identifier mismatch")
    if candidate_id != _candidate_identifier(
        record.get("target_ref", ""), record.get("target_sha", ""), record.get("candidate_sha", "")
    ):
        raise CandidateControllerError("candidate record tuple does not match identifier")
    manifest_path = state / f"{candidate_id}.manifest.json"
    if record.get("manifest_path") != str(manifest_path):
        raise CandidateControllerError("candidate manifest path mismatch")
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise CandidateControllerError("candidate manifest is not a regular file")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CandidateControllerError("candidate manifest unavailable or malformed") from exc
    if (
        manifest.get("schema") != _MANIFEST_SCHEMA
        or _record_digest(manifest) != record.get("manifest_sha256")
        or manifest.get("repository") != str(repository)
        or manifest.get("target_ref") != record.get("target_ref")
        or manifest.get("target_sha") != record.get("target_sha")
        or manifest.get("candidate_sha") != record.get("candidate_sha")
        or manifest.get("candidate_tree") != record.get("candidate_tree")
        or manifest.get("result_tree") != record.get("result_tree")
    ):
        raise CandidateControllerError("candidate manifest integrity check failed")
    return record


def run_integration_check(
    repository: str | Path,
    candidate_id: str,
    state_directory: str | Path,
    *,
    check_id: str = "core-unit",
) -> dict[str, Any]:
    """Create an ephemeral two-parent integration commit, run fixed sandbox checks.

    No branch/ref is created or moved. The source checkout is not modified.
    """
    if check_id != "core-unit":
        raise CandidateControllerError("only the fixed core-unit check is supported")
    root = Path(repository).resolve()
    state = _state_path(root, state_directory, create=False)
    record = _load_record(root, candidate_id, state)
    evidence_path = state / f"{candidate_id}.integration.json"
    if evidence_path.exists():
        raise CandidateControllerError("integration evidence already exists; refusing overwrite")
    target = _resolve_commit(root, record["target_sha"])
    candidate = _resolve_commit(root, record["candidate_sha"])
    _resolve_target_ref(root, record["target_ref"], target)
    candidate_tree, result_tree = _candidate_trees(root, target, candidate)
    if candidate_tree != record["candidate_tree"] or result_tree != record["result_tree"]:
        raise CandidateControllerError("candidate manifest tree does not match repository")
    commit_env = {
            "PATH": "/usr/bin:/bin",
            "HOME": "/nonexistent",
            "LANG": "C.UTF-8",
            "GIT_AUTHOR_NAME": "AAO Local Integration Check",
            "GIT_AUTHOR_EMAIL": "aao-local-check@invalid",
            "GIT_COMMITTER_NAME": "AAO Local Integration Check",
            "GIT_COMMITTER_EMAIL": "aao-local-check@invalid",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null",
        }
    try:
        synthetic = subprocess.run(
            ["git", "-C", str(root), "commit-tree", result_tree, "-p", target, "-p", candidate],
            input=f"AAO disposable integration {candidate_id}\n",
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            cwd="/",
            env=commit_env,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise CandidateControllerError("could not create isolated integration commit") from exc
    integrated_sha = synthetic.stdout.strip()
    if synthetic.returncode or not _SHA.fullmatch(integrated_sha):
        raise CandidateControllerError("could not create isolated integration commit")

    result: dict[str, Any]
    verifier_sources = {
        "candidate_controller_sha256": _source_digest(__file__),
        "sandbox_check_runner_sha256": _source_digest(sandboxed_repository_checks.__file__),
    }
    worktree_added = False
    with tempfile.TemporaryDirectory(prefix="aao-integration-") as temporary:
        checkout = Path(temporary) / "worktree"
        try:
            _git(root, "worktree", "add", "--detach", str(checkout), integrated_sha)
            worktree_added = True
            check = run_repository_check(checkout, check_id)
            result = {
                "schema": _EVIDENCE_SCHEMA,
                "candidate_id": candidate_id,
                "target_sha": target,
                "candidate_sha": candidate,
                "candidate_tree": candidate_tree,
                "result_tree": result_tree,
                "manifest_sha256": record["manifest_sha256"],
                "integration_sha": integrated_sha,
                "check_id": check_id,
                "verifier_sources_sha256": verifier_sources,
                "check": check,
                "conclusion": check["conclusion"],
                "promotion": "disabled",
                "independent_audit": "not_provided_by_this_controller",
                "created_at": datetime.now(UTC).isoformat(),
            }
        except RepositoryCheckError as exc:
            result = {
                "schema": _EVIDENCE_SCHEMA,
                "candidate_id": candidate_id,
                "target_sha": target,
                "candidate_sha": candidate,
                "candidate_tree": candidate_tree,
                "result_tree": result_tree,
                "manifest_sha256": record["manifest_sha256"],
                "integration_sha": integrated_sha,
                "check_id": check_id,
                "verifier_sources_sha256": verifier_sources,
                "conclusion": "unavailable",
                "reason": str(exc),
                "promotion": "disabled",
                "independent_audit": "not_provided_by_this_controller",
                "created_at": datetime.now(UTC).isoformat(),
            }
        finally:
            if worktree_added:
                try:
                    _git(root, "worktree", "remove", "--force", str(checkout))
                except CandidateControllerError as exc:
                    raise CandidateControllerError(
                        "integration check finished but disposable worktree cleanup failed"
                    ) from exc
    result["evidence_sha256"] = _record_digest(result)
    _write_json(evidence_path, result)
    return result


def request_promotion(*_args: object, **_kwargs: object) -> None:
    """Promotion is intentionally unavailable in this transition phase."""
    if not PROMOTION_ENABLED:
        raise CandidateControllerError("promotion is disabled by local transition policy")
    raise CandidateControllerError("no promotion implementation is configured")


def main() -> int:
    parser = argparse.ArgumentParser(description="Local-only AAO candidate integration controller")
    commands = parser.add_subparsers(dest="operation", required=True)
    register = commands.add_parser("register", help="record immutable target/candidate commits")
    register.add_argument("--repository", type=Path, required=True)
    register.add_argument("--target-sha", required=True)
    register.add_argument("--target-ref", required=True)
    register.add_argument("--candidate-sha", required=True)
    register.add_argument("--state-directory", type=Path, required=True)
    check = commands.add_parser("check", help="test the exact pair in a disposable worktree")
    check.add_argument("--repository", type=Path, required=True)
    check.add_argument("--candidate-id", required=True)
    check.add_argument("--state-directory", type=Path, required=True)
    check.add_argument("--check-id", choices=("core-unit",), default="core-unit")
    commands.add_parser("promote", help="promotion is disabled in local transition mode")
    args = parser.parse_args()
    try:
        if args.operation == "register":
            result = register_candidate(
                args.repository,
                args.target_sha,
                args.candidate_sha,
                args.state_directory,
                target_ref=args.target_ref,
            )
        elif args.operation == "check":
            result = run_integration_check(
                args.repository,
                args.candidate_id,
                args.state_directory,
                check_id=args.check_id,
            )
        else:
            request_promotion()
            return 1
    except CandidateControllerError as exc:
        print(json.dumps({"ok": False, "reason": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
