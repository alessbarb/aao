"""Fail-closed integrator tick for the R1 pull-request pipeline.

The GitHub object may expose the small method protocol used below or a
GitHubAppClient-compatible ``request`` method. Persistent state and inbox files
are content-addressed and replaced atomically; they never carry credentials.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import quote

from aao.integrator import TrustSources, promote


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(_canonical(value)); stream.flush(); os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def _body(response: Any) -> Any:
    return getattr(response, "body", response)


def _request(client: Any, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
    response = client.request(method, path, body=body)
    status = getattr(response, "status", 200)
    if status < 200 or status >= 300:
        raise RuntimeError(f"GitHub API {method} failed with HTTP {status}")
    return _body(response)


def _pulls(client: Any, repository: str) -> list[dict[str, Any]]:
    if hasattr(client, "list_open_pull_requests"):
        values = client.list_open_pull_requests(repository, base="main")
    else:
        values = _request(client, "GET", f"/repos/{quote(repository, safe='/')}/pulls?state=open&base=main")
    if not isinstance(values, list):
        raise TypeError("GitHub returned malformed pull request list")
    return [p for p in values if isinstance(p, dict) and p.get("state", "open") == "open"
            and (p.get("base", {}).get("ref", "main") == "main")]


def _check_passed(client: Any, repository: str, sha: str, name: str) -> bool:
    if hasattr(client, "check_conclusion"):
        return client.check_conclusion(repository, sha, name) == "success"
    owner, repo = repository.split("/", 1)
    checks = _request(client, "GET", f"/repos/{quote(owner, safe='')}/{quote(repo, safe='')}/commits/{sha}/check-runs")
    runs = [run for run in checks.get("check_runs", []) if isinstance(run, dict) and run.get("name") == name] \
        if isinstance(checks, dict) else []
    if not runs:
        return False
    latest = max(runs, key=lambda run: (run.get("id", 0) if isinstance(run.get("id", 0), int) else 0,
                                        run.get("run_attempt", 0) if isinstance(run.get("run_attempt", 0), int) else 0))
    return latest.get("status") == "completed" and latest.get("conclusion") == "success"


def _sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 40 and all(c in "0123456789abcdef" for c in value)


def integrator_tick(github: Any, git_remote: str, mirror: str | Path, inbox: str | Path,
                    reports: str | Path, state_dir: str | Path, trust_sources: TrustSources,
                    identity_provider: Any, now: Any) -> list[dict[str, Any]]:
    """Advance each open main-targeting PR at most one safely evidenced step."""
    mirror, inbox, reports, state_dir = map(Path, (mirror, inbox, reports, state_dir))
    for path in (inbox, reports, state_dir):
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        owner_repo = getattr(github, "repository", None) or os.environ.get("AAO_GITHUB_REPOSITORY")
        if not isinstance(owner_repo, str) or owner_repo.count("/") != 1:
            raise ValueError("GitHub client must identify repository as owner/name")
        pulls = _pulls(github, owner_repo)
        _git(mirror, "fetch", "--prune", git_remote, "+refs/heads/main:refs/remotes/aao/main")
        base = _git(mirror, "rev-parse", "refs/remotes/aao/main")
        # Auditors verify the manifest target_ref inside this mirror. Keep that
        # local branch aligned with the fetched remote tip before creating manifests.
        _git(mirror, "update-ref", "refs/heads/main", base)
    except (OSError, ValueError, TypeError, RuntimeError, KeyError, subprocess.SubprocessError) as error:
        return [{"status": "failed", "reason": str(error)}]

    results: list[dict[str, Any]] = []
    for pr in pulls:
        number = pr.get("number")
        head = pr.get("head", {}).get("sha") if isinstance(pr.get("head"), dict) else None
        if not isinstance(number, int) or number <= 0 or not _sha(head):
            results.append({"status": "failed", "reason": "malformed pull request identity"}); continue
        # Base is part of audit identity: authorization for an older main tip
        # must never be reused when main moves.
        key = hashlib.sha256(_canonical([owner_repo, number, head, base])).hexdigest()
        state_path = state_dir / f"{key}.json"
        try:
            state = json.loads(state_path.read_text()) if state_path.exists() else {
                "schema": "aao.r1-integrator-state.v1", "id": key, "repo": owner_repo,
                "pr_number": number, "head_sha": head, "base_sha": base, "status": "queued"}
            if state.get("head_sha") != head or state.get("base_sha") != base:
                state = {"schema": "aao.r1-integrator-state.v1", "id": key, "repo": owner_repo,
                         "pr_number": number, "head_sha": head, "base_sha": base, "status": "queued"}
            if state["status"] in ("promoted", "failed"):
                results.append(state); continue
            pr_ref = f"refs/pull/{number}/head"
            _git(mirror, "fetch", git_remote, f"+{pr_ref}:refs/remotes/aao/pr/{number}")
            candidate = _git(mirror, "rev-parse", f"refs/remotes/aao/pr/{number}")
            if candidate != head:
                raise ValueError("fetched pull request head differs from observed API head")
            manifest = {"schema": "aao.candidate-manifest.v1", "repository": str(mirror.resolve()),
                        "target_ref": "refs/heads/main", "target_sha": base,
                        "candidate_sha": candidate,
                        "candidate_tree": _git(mirror, "rev-parse", f"{candidate}^{{tree}}"),
                        "result_tree": _git(mirror, "merge-tree", "--write-tree", base, candidate).splitlines()[0],
                        "producer": "aao-integrator:r1-pipeline"}
            report_dir = reports / key
            auth_path = report_dir / "authorization.json"
            sig_path = report_dir / "authorization.sig"
            verdict_path = report_dir / "audit" / "report.json"
            if auth_path.is_file() != sig_path.is_file():
                raise ValueError("authorization document/signature pair is incomplete")
            if verdict_path.is_file() and not auth_path.is_file():
                verdict = json.loads(verdict_path.read_text())
                if verdict.get("verdict") != "approve":
                    state.update(status="failed", reason=f"audit verdict: {verdict.get('verdict', 'unknown')}")
                    _atomic_json(state_path, state); results.append(state); continue
            if not auth_path.is_file() or not sig_path.is_file():
                request = {"schema": "aao.audit-request.v1", "type": "audit", "repo": owner_repo,
                           "pr_number": number, "manifest": manifest}
                _atomic_json(inbox / f"{key}.json", request)
                state.update(status="queued", audit_request=key)
                _atomic_json(state_path, state); results.append(state); continue
            auth = json.loads(auth_path.read_text())
            state.update(status="audited", authorization_sha256=hashlib.sha256(auth_path.read_bytes()).hexdigest())
            _atomic_json(state_path, state)
            staged = state.get("staged_commit")
            if not staged:
                staged = subprocess.run(["git", "-C", str(mirror), "commit-tree", manifest["result_tree"],
                                         "-p", base, "-p", candidate], input="R1 staged merge\n",
                                        check=True, capture_output=True, text=True,
                                        env={**os.environ,
                                             "GIT_AUTHOR_NAME": "aao-integrator",
                                             "GIT_AUTHOR_EMAIL": "aao-integrator@users.noreply.github.com",
                                             "GIT_COMMITTER_NAME": "aao-integrator",
                                             "GIT_COMMITTER_EMAIL": "aao-integrator@users.noreply.github.com"}).stdout.strip()
                staged_ref = f"refs/heads/aao-staging/{number}-{staged}"
                _git(mirror, "push", git_remote, f"{staged}:{staged_ref}")
                state.update(status="staged", staged_commit=staged, staged_ref=staged_ref)
            gate_id = hashlib.sha256(_canonical([key, "gate", staged])).hexdigest()
            gate_path = reports / gate_id / "gate.json"
            if not gate_path.is_file():
                _atomic_json(inbox / f"{gate_id}.json", {"schema": "aao.audit-request.v1", "type": "gate",
                            "id": key, "promoted_sha": staged, "repo": owner_repo, "pr_number": number})
                _atomic_json(state_path, state); results.append(state); continue
            gate = json.loads(gate_path.read_text())
            if gate.get("conformant") is not True:
                raise ValueError("auditor gate is non-conformant")
            state.update(status="gated", gate_id=gate_id)
            _atomic_json(state_path, state)
            if not _check_passed(github, owner_repo, staged, "test") or not _check_passed(github, owner_repo, staged, "aao-audit"):
                state.update(status="gated", reason="required checks are not successful on staged commit")
                _atomic_json(state_path, state); results.append(state); continue
            signature = sig_path.read_text(encoding="ascii").strip()
            clock = now if callable(now) else lambda: now
            promoted = promote(mirror, git_remote, auth, signature, trust_sources,
                               identity_provider=identity_provider, observed_repo=owner_repo,
                               observed_pr_number=number, staged_commit=staged,
                               ci_verified_sha=staged,
                               candidate_ref=f"refs/pull/{number}/head", now=clock)
            state.update(status="promoted", promoted_sha=promoted)
        except (OSError, ValueError, TypeError, RuntimeError, KeyError, subprocess.SubprocessError) as error:
            moved = isinstance(error, RuntimeError) and str(error) == "remote base moved"
            if (isinstance(error, RuntimeError)
                    and str(error).startswith("conditional push rejected; no fallback:")):
                try:
                    latest = subprocess.run(["git", "-C", str(mirror), "ls-remote", git_remote,
                                             "refs/heads/main"], check=True, capture_output=True,
                                            text=True).stdout.split()
                    moved = bool(latest and latest[0] != base)
                except (OSError, subprocess.SubprocessError):
                    moved = False
            if moved:
                state.update(status="queued", reason="remote base moved during promotion; re-audit new base")
            else:
                state.update(status="failed", reason=f"{type(error).__name__}: {error}")
        _atomic_json(state_path, state)
        results.append(state)
    return results
