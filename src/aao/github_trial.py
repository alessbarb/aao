"""Run one bounded P2/P3 GitHub trial and write a redacted evidence record."""

from __future__ import annotations

import argparse
import base64
import json
import os
import pwd
import re
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .github_app_auth import ROLE_NAMES, GitHubAppClient, GitHubAuthError

NOT_RUN = {
    "A-07": "Manual CEO step: with the CEO token, push a commit to the canonical repository; verify governance-violation records the real actor.",
    "A-08": "Manual supervisor/CEO step: generate attribution.json from actual push and PR-author events; verify App identities and provisional status when events are absent.",
    "A-11": "Manual organization/fork step: install implementer App only on the organization fork, open a fork PR, and verify no canonical-repository push permission.",
    "P3-10": "Manual Actions step: open an unapproved fork PR changing .github/workflows; verify Actions does not run and GITHUB_TOKEN is read-only.",
    "P3-11": "Manual CEO step: disable ruleset A in the trial repository; verify GitHub audit log and supervisor alert.",
}

EXPECTED_PERMISSIONS = {
    "aao-integrator": {"contents": "write", "pull_requests": "write", "checks": "read", "statuses": "read", "workflows": "write", "metadata": "read"},
    "aao-auditor": {"contents": "read", "pull_requests": "read", "checks": "write", "metadata": "read"},
    "aao-auditor-alt": {"contents": "read", "pull_requests": "read", "checks": "write", "metadata": "read"},
    "aao-supervisor": {"contents": "read", "pull_requests": "read", "checks": "read", "actions": "read", "metadata": "read"},
    "aao-notifier": {"issues": "write", "metadata": "read"},
    "aao-pm": {"issues": "write", "pull_requests": "write", "contents": "read", "metadata": "read"},
    "aao-impl-codex": {"contents": "write", "pull_requests": "write", "workflows": "write", "metadata": "read"},
    "aao-impl-claude": {"contents": "write", "pull_requests": "write", "workflows": "write", "metadata": "read"},
    "aao-impl-ag": {"contents": "write", "pull_requests": "write", "workflows": "write", "metadata": "read"},
}
CANONICAL_REPO = "alessbarb/aao"
CHECK_WAIT_SECONDS = 300
CHECK_POLL_SECONDS = 5


def validate_role_uid(role: str) -> None:
    if role == "ceo":
        try:
            expected = pwd.getpwnam("alessbarb").pw_uid
        except KeyError as exc:
            raise GitHubAuthError("CEO account alessbarb does not exist") from exc
        if expected != os.getuid():
            raise GitHubAuthError(f"uid {os.getuid()} does not match CEO uid {expected}")
        return
    if role not in ROLE_NAMES:
        raise GitHubAuthError("unknown app role")
    try:
        expected = pwd.getpwnam(role).pw_uid
    except KeyError as exc:
        raise GitHubAuthError(f"role account {role} does not exist") from exc
    if expected != os.getuid():
        raise GitHubAuthError(f"uid {os.getuid()} does not match role {role} uid {expected}")


def validate_ceo_gh_identity(repo: str) -> None:
    """Require the gh CLI token to identify the CEO and be admin on this trial repo."""
    user = subprocess.run(["gh", "api", "--hostname", "github.com", "user", "--jq", ".login"], check=True, capture_output=True,
                          text=True, timeout=10, stdin=subprocess.DEVNULL).stdout.strip()
    if user.lower() != "alessbarb":
        raise GitHubAuthError("gh authenticated user is not alessbarb")
    admin = subprocess.run(["gh", "api", "--hostname", "github.com", f"repos/{repo}", "--jq", ".permissions.admin"], check=True,
                          capture_output=True, text=True, timeout=10, stdin=subprocess.DEVNULL).stdout.strip()
    if admin.lower() != "true":
        raise GitHubAuthError("CEO GitHub account lacks admin permission on the trial repository")


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: ("[REDACTED]" if re.search(r"token|authorization|private.?key", k, re.IGNORECASE) else _redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def _api(client: GitHubAppClient, method: str, path: str, body: dict | None = None) -> dict:
    response = client.request(method, path, body=body)
    return {"method": method, "path": path, "body": body, "status": response.status, "response": _redact(response.body)}


def _git_push(client: GitHubAppClient, repo: str, refspec: str, *, force_with_lease: str | None = None, force: bool = False) -> dict:
    """Use HTTPS auth only in process environment; never put token in URL or output."""
    token = client._installation_token
    if not token:
        raise GitHubAuthError("installation token missing")
    credential = base64.b64encode(f"x-access-token:{token}".encode()).decode("ascii")
    config = [("http.extraheader", f"AUTHORIZATION: basic {credential}")]
    env = os.environ.copy()
    for key in list(env):
        if key.startswith(("GIT_TRACE", "GIT_CURL_VERBOSE")):
            env.pop(key, None)
    env["GIT_TRACE_REDACT"] = "1"
    env["GIT_CONFIG_COUNT"] = str(len(config))
    for i, (key, value) in enumerate(config):
        env[f"GIT_CONFIG_KEY_{i}"] = key
        env[f"GIT_CONFIG_VALUE_{i}"] = value
    remote = f"https://github.com/{repo}.git"
    args = ["git", "-c", "credential.helper=", "push"]
    if force_with_lease is not None:
        args.append(f"--force-with-lease=refs/heads/main:{force_with_lease}")
    elif force:
        args.append("--force")
    args.extend([remote, refspec])
    try:
        result = subprocess.run(args, env=env, stdin=subprocess.DEVNULL, capture_output=True, timeout=90, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"method": "git push", "remote": remote, "refspec": refspec, "status": None, "response": type(exc).__name__}
    stderr = result.stderr.decode("utf-8", errors="replace")[:4000]
    stderr = re.sub(r"(Authorization:\s*(?:Basic|Bearer)\s+)\S+", r"\1[REDACTED]", stderr, flags=re.IGNORECASE)
    stderr = stderr.replace(token, "[REDACTED]")
    server_rejected = bool(re.search(r"remote:.*(?:protected branch|permission to .* denied|not permitted|GH\d+:)|\[rejected\].*(?:stale info|protected branch|permission|non-fast-forward)", stderr, re.IGNORECASE))
    return {"method": "git push", "remote": remote, "refspec": refspec,
            "exit_code": result.returncode, "status": 0 if result.returncode == 0 else 1,
            "server_rejected": server_rejected, "response": stderr}


def _trial_repo_allowed(owner: str, repo: str) -> bool:
    target = f"{owner}/{repo}".lower()
    if target == CANONICAL_REPO:
        return False
    allowed = {item.strip().lower() for item in os.environ.get("AAO_GITHUB_TRIAL_REPOS", "").split(",") if item.strip()}
    return bool(allowed) and target in allowed


def _main_sha(client: GitHubAppClient, base: str, evidence: list[dict]) -> str | None:
    record = _api(client, "GET", f"{base}/git/ref/heads/main")
    evidence.append(record)
    if record["status"] != 200 or not isinstance(record["response"], dict):
        return None
    return record["response"].get("object", {}).get("sha")


def _verify_unchanged(client: GitHubAppClient, base: str, before: str, evidence: list[dict]) -> bool:
    after = _main_sha(client, base, evidence)
    return bool(after and after == before)


def _push_rejection_pass(item: dict, unchanged: bool, expected: str = "protected branch") -> bool:
    response = item.get("response", "").lower()
    reason_matches = expected.lower() in response or (expected == "protected branch" and "permission to " in response and " denied" in response)
    return item.get("exit_code", 0) != 0 and item.get("server_rejected") is True and reason_matches and unchanged


def _merge_trial_pr(client: GitHubAppClient, base: str, evidence: list[dict]) -> tuple[str, str, list[dict]]:
    if base.lower() == "/repos/alessbarb/aao":
        return "NOT RUN", "refusing to promote on the canonical repository; use the disposable trial", evidence
    pull_list = _api(client, "GET", f"{base}/pulls?state=open&per_page=100")
    evidence.append(pull_list)
    authorized_number = os.environ.get("AAO_GITHUB_TRIAL_PR")
    authorized_head = os.environ.get("AAO_GITHUB_TRIAL_PR_HEAD", "")
    if not authorized_number or not authorized_number.isdigit() or not re.fullmatch(r"[0-9a-f]{40,64}", authorized_head):
        return "NOT RUN", "Set AAO_GITHUB_TRIAL_PR and AAO_GITHUB_TRIAL_PR_HEAD to the explicitly authorized disposable PR and exact head SHA.", evidence
    if pull_list["status"] != 200 or not pull_list["response"]:
        return "NOT RUN", "Create an open trial PR with the exact authorized commit and required checks, then rerun.", evidence
    matches = [item for item in pull_list["response"] if item.get("number") == int(authorized_number)]
    if not matches:
        return "NOT RUN", "The authorized disposable PR is not among open trial PRs.", evidence
    pr = matches[0]
    number = pr.get("number")
    candidate = pr.get("head", {}).get("sha")
    if not isinstance(number, int) or not candidate:
        return "FAIL", "trial PR response lacks number or head SHA", evidence
    if candidate != authorized_head:
        return "FAIL", "authorized trial PR head SHA does not match AAO_GITHUB_TRIAL_PR_HEAD", evidence
    detail = _api(client, "GET", f"{base}/pulls/{number}")
    evidence.append(detail)
    if detail["status"] != 200 or not isinstance(detail["response"], dict):
        return "FAIL", "could not read trial PR details", evidence
    pr = detail["response"]
    candidate = pr.get("head", {}).get("sha")
    base_branch = pr.get("base", {}).get("ref")
    if not candidate or base_branch != "main":
        return "FAIL", "trial PR must have a head SHA and target main", evidence
    base_ref = _api(client, "GET", f"{base}/git/ref/heads/main")
    evidence.append(base_ref)
    base_sha = base_ref.get("response", {}).get("object", {}).get("sha") if isinstance(base_ref.get("response"), dict) else None
    if base_ref["status"] != 200 or not base_sha:
        return "FAIL", "could not read main base SHA", evidence

    # Resolve the auditor App's canonical ID, then require that exact source for aao-audit.
    auditor = _api(client, "GET", "/apps/aao-auditor")
    evidence.append(auditor)
    auditor_id = auditor.get("response", {}).get("id") if isinstance(auditor.get("response"), dict) else None
    auditor_owner = auditor.get("response", {}).get("owner", {}).get("login", "").lower() if isinstance(auditor.get("response"), dict) else ""
    if auditor["status"] != 200 or not isinstance(auditor_id, int) or auditor_owner != "alessbarb":
        return "FAIL", "could not resolve aao-auditor App id", evidence

    try:
        tree = subprocess.run(["git", "merge-tree", "--write-tree", base_sha, candidate], check=True,
                              capture_output=True, text=True, timeout=60).stdout.splitlines()[0].strip()
        merge_sha = subprocess.run(["git", "-c", "user.name=AAO Integrator", "-c",
                                    "user.email=aao-integrator@users.noreply.github.com", "commit-tree",
                                    tree, "-p", base_sha, "-p", candidate], check=True, capture_output=True,
                                   text=True, timeout=30).stdout.strip()
    except (OSError, subprocess.SubprocessError, IndexError) as exc:
        evidence.append({"method": "git merge-tree/commit-tree", "status": "error", "response": type(exc).__name__})
        return "FAIL", "could not construct local merge commit", evidence
    evidence.append({"method": "git merge-tree --write-tree + git commit-tree", "tree": tree,
                     "parents": [base_sha, candidate], "sha": merge_sha})
    if not re.fullmatch(r"[0-9a-f]{40,64}", tree) or not re.fullmatch(r"[0-9a-f]{40,64}", merge_sha):
        return "FAIL", "local merge tree or commit returned an invalid object id", evidence
    staging = f"refs/heads/aao-staging/{number}-{candidate[:8]}"
    push = _git_push(client, f"{owner_repo(base)}", f"{merge_sha}:{staging}")
    evidence.append(push)
    if push["status"] != 0:
        return "FAIL", "integrator could not push merge commit to staging", evidence

    deadline = time.monotonic() + CHECK_WAIT_SECONDS
    checks_ok = False
    while time.monotonic() < deadline:
        checks = _api(client, "GET", f"{base}/commits/{merge_sha}/check-runs?per_page=100")
        evidence.append(checks)
        runs = checks.get("response", {}).get("check_runs", []) if isinstance(checks.get("response"), dict) else []
        selected = {}
        for run in runs:
            name = run.get("name")
            if name == "aao-audit" and run.get("app", {}).get("id") != auditor_id:
                return "FAIL", f"aao-audit check came from app_id {run.get('app', {}).get('id')}, expected {auditor_id}", evidence
            if name in ("aao-audit", "test"):
                selected[name] = run
        if checks["status"] != 200:
            return "FAIL", f"check-runs query returned HTTP {checks['status']}", evidence
        if all(name in selected and selected[name].get("status") == "completed" and selected[name].get("conclusion") == "success" for name in ("aao-audit", "test")):
            checks_ok = True
            break
        time.sleep(min(CHECK_POLL_SECONDS, max(0, deadline - time.monotonic())))
    if not checks_ok:
        return "FAIL", f"required checks did not become green within {CHECK_WAIT_SECONDS}s", evidence

    query = {"query": "mutation($input: UpdateRefsInput!) { updateRefs(input: $input) { refs { name } } }",
             "variables": {"input": {"refUpdates": [{"name": "refs/heads/main", "oid": merge_sha,
                                                        "beforeOid": base_sha}]}}}
    update = _api(client, "POST", "/graphql", query)
    evidence.append(update)
    errors = update["status"] >= 400 or (isinstance(update["response"], dict) and bool(update["response"].get("errors")))
    if errors:
        return "FAIL", "GraphQL updateRefs promotion failed", evidence
    main_after = _api(client, "GET", f"{base}/git/ref/heads/main")
    commit_after = _api(client, "GET", f"{base}/git/commits/{merge_sha}")
    pr_after = _api(client, "GET", f"{base}/pulls/{number}")
    evidence.extend([main_after, commit_after, pr_after])
    actual_main = main_after.get("response", {}).get("object", {}).get("sha") if isinstance(main_after.get("response"), dict) else None
    commit = commit_after.get("response", {})
    parents = [item.get("sha") for item in commit.get("parents", [])] if isinstance(commit, dict) else []
    actual_tree = commit.get("tree", {}).get("sha") if isinstance(commit, dict) else None
    merged = isinstance(pr_after.get("response"), dict) and pr_after["response"].get("merged") is True
    if actual_main == merge_sha and actual_tree == tree and parents == [base_sha, candidate] and merged:
        return "PASS", f"main promoted to verified merge commit {merge_sha}; PR {number} is merged", evidence
    return "FAIL", "promotion verification failed: main, tree, parents, or PR merged state differs", evidence


def owner_repo(base: str) -> str:
    return base.removeprefix("/repos/")


def run_test(test_id: str, owner: str, repo: str, role: str, client: GitHubAppClient) -> tuple[str, str, list[dict]]:
    base = f"/repos/{owner}/{repo}"
    evidence: list[dict] = []
    if not _trial_repo_allowed(owner, repo):
        return "NOT RUN", "Repository is not explicitly listed in AAO_GITHUB_TRIAL_REPOS or is the canonical repository; no operation performed.", evidence
    implementers = {"aao-impl-codex", "aao-impl-claude", "aao-impl-ag"}
    required_roles = {
        "A-01": implementers, "A-02": implementers, "A-03": {"aao-integrator"},
        "A-04": {"aao-integrator"}, "A-05": {"aao-integrator"}, "A-09": {"aao-notifier"},
        "P3-02": implementers, "P3-03": {"aao-integrator"}, "P3-05": {"aao-integrator"},
        "P3-06": {"aao-integrator"}, "P3-12": {"aao-integrator"},
    }
    if test_id in required_roles and role not in required_roles[test_id]:
        names = ", ".join(sorted(required_roles[test_id]))
        return "NOT RUN", f"This test must run with role: {names}.", evidence
    if test_id in NOT_RUN:
        return "NOT RUN", NOT_RUN[test_id], evidence
    if test_id == "A-01":
        before = _main_sha(client, base, evidence)
        if not before:
            return "FAIL", "could not read main before push attempt", evidence
        item = _git_push(client, f"{owner}/{repo}", "HEAD:refs/heads/main")
        evidence.append(item)
        unchanged = _verify_unchanged(client, base, before, evidence)
        return ("PASS", "server denied push to protected branch; main unchanged", evidence) if _push_rejection_pass(item, unchanged, "protected branch") else ("FAIL", "push failed for an unproven cause, changed main, or was accepted", evidence)
    if test_id == "A-04":
        ref = _api(client, "GET", f"{base}/git/ref/heads/main")
        evidence.append(ref)
        if ref["status"] != 200 or not isinstance(ref["response"], dict):
            return "FAIL", "could not read main SHA for stale lease trial", evidence
        actual = ref["response"].get("object", {}).get("sha")
        if not actual:
            return "FAIL", "main response has no SHA", evidence
        # First move main to a distinct, real commit, then use its actual prior SHA as the lease.
        try:
            local = subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True, timeout=10).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return "NOT RUN", "local candidate commit unavailable for stale-lease trial", evidence
        if not re.fullmatch(r"[0-9a-f]{40,64}", local) or local == actual:
            return "NOT RUN", "trial needs a distinct local commit to move main before stale-lease attempt", evidence
        stage = f"refs/heads/aao-trial/stale-lease-{local[:8]}"
        staged = _git_push(client, f"{owner}/{repo}", f"{local}:{stage}")
        evidence.append(staged)
        if staged.get("exit_code") != 0:
            return "FAIL", "could not stage the distinct candidate commit", evidence
        moved = _api(client, "POST", "/graphql", {"query": "mutation($input: UpdateRefsInput!) { updateRefs(input: $input) { refs { name } } }", "variables": {"input": {"refUpdates": [{"name": "refs/heads/main", "oid": local, "beforeOid": actual}]}}})
        evidence.append(moved)
        moved_ok = moved["status"] == 200 and isinstance(moved["response"], dict) and not moved["response"].get("errors")
        if not moved_ok or _main_sha(client, base, evidence) != local:
            return "FAIL", "could not move main to distinct candidate before stale lease", evidence
        item = _git_push(client, f"{owner}/{repo}", f"{actual}:refs/heads/main", force_with_lease=actual)
        evidence.append(item)
        unchanged = _verify_unchanged(client, base, local, evidence)
        response = item.get("response", "").lower()
        valid_server_reject = item.get("exit_code", 0) != 0 and item.get("server_rejected") and ("stale" in response or "rejected" in response)
        return ("PASS", "server rejected stale force-with-lease; moved main unchanged", evidence) if valid_server_reject and unchanged else ("FAIL", "stale lease was not rejected by server for the expected reason or main changed", evidence)
    if test_id == "A-09":
        item = _api(client, "POST", f"{base}/issues", {"title": "AAO P2/P3 trial notification", "body": "Disposable trial harness check."})
        evidence.append(item)
        if item["status"] not in (200, 201):
            return "FAIL", f"issue creation returned HTTP {item['status']}", evidence
        before = _main_sha(client, base, evidence)
        if not before:
            return "FAIL", "issue created but could not read main before push", evidence
        push = _git_push(client, f"{owner}/{repo}", "HEAD:refs/heads/main")
        evidence.append(push)
        unchanged = _verify_unchanged(client, base, before, evidence)
        return ("PASS", "issue created; server denied protected-branch push; main unchanged", evidence) if _push_rejection_pass(push, unchanged) else ("FAIL", "issue created but push failure cause or remote state did not match", evidence)
    if test_id == "A-10":
        item = _api(client, "GET", "/installation")
        evidence.append(item)
        actual = item["response"].get("permissions", {}) if isinstance(item["response"], dict) else {}
        expected = EXPECTED_PERMISSIONS[role]
        is_canonical = f"{owner}/{repo}".lower() == CANONICAL_REPO
        if role.startswith("aao-impl-") and is_canonical:
            expected = {"pull_requests": "write", "contents": "read", "metadata": "read"}
        elif not is_canonical:
            if role in ("aao-auditor", "aao-auditor-alt"):
                expected = {"contents": "read", "metadata": "read"}
            elif not role.startswith("aao-impl-"):
                return "NOT RUN", "this App role is specified only for the canonical repository", evidence
        clean = {k: v for k, v in actual.items() if v not in (None, "none")}
        return ("PASS", "installation permissions match role manifest", evidence) if clean == expected else ("FAIL", f"installation permissions differ from expected table: expected {expected}, got {clean}", evidence)
    if test_id == "A-12":
        item = client.revoke()
        evidence.append({"method": "DELETE", "path": "/installation/token", "body": None,
                         "status": item.status if item else None, "response": _redact(item.body) if item else None})
        return ("NOT RUN", "current token revocation was exercised; full A-12 still requires deleting this App key or suspending its installation, then proving new token issuance fails", evidence) if item and item.status in (200, 204) else ("FAIL", "installation token revocation failed", evidence)
    if test_id == "A-13":
        return "NOT RUN", "Manual expiry step: use an installation token after its expires_at time (or revoke it), then verify GitHub returns HTTP 401; harness cannot wait an hour within one-test invocation.", evidence
    if test_id == "A-14":
        if not role.startswith("aao-impl-") or f"{owner}/{repo}".lower() == CANONICAL_REPO:
            return "NOT RUN", "A-14 must run with an implementer App installed on its disposable fork; no canonical-repository App is valid.", evidence
        fork_parent = os.environ.get("AAO_GITHUB_TRIAL_FORK_PARENT", "").lower()
        if not fork_parent or fork_parent == CANONICAL_REPO:
            return "NOT RUN", "Set AAO_GITHUB_TRIAL_FORK_PARENT to the explicit disposable trial parent repository.", evidence
        fork_info = _api(client, "GET", base)
        evidence.append(fork_info)
        parent = fork_info.get("response", {}).get("parent", {}).get("full_name", "").lower() if isinstance(fork_info.get("response"), dict) else ""
        if fork_info["status"] != 200 or not isinstance(fork_info["response"], dict) or fork_info["response"].get("fork") is not True or parent != fork_parent:
            return "NOT RUN", "Target is not the explicitly configured disposable fork of the trial repository.", evidence
        try:
            changed = subprocess.run(["git", "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", "HEAD"],
                                     check=True, capture_output=True, text=True, timeout=10).stdout.splitlines()
        except (OSError, subprocess.SubprocessError):
            return "NOT RUN", "Run from a local disposable clone containing the test commit.", evidence
        if not any(path.startswith(".github/workflows/") for path in changed):
            return "NOT RUN", "Prepare a disposable local commit changing .github/workflows/ and rerun; the harness will attempt that commit's push to main.", evidence
        before = _main_sha(client, base, evidence)
        if not before:
            return "FAIL", "could not read fork main before workflow push", evidence
        item = _git_push(client, f"{owner}/{repo}", "HEAD:refs/heads/main")
        evidence.append(item)
        message = item.get("response", "").lower()
        expected = item.get("exit_code", 0) != 0 and item.get("server_rejected") and ("workflow" in message or "workflows" in message or "permission" in message)
        unchanged = _verify_unchanged(client, base, before, evidence)
        return ("PASS", "server denied workflow-changing push for missing workflow permission; fork main unchanged", evidence) if expected and unchanged else ("FAIL", "workflow push was not rejected for the expected permission or fork main changed", evidence)
    if test_id == "P3-09":
        if role != "ceo":
            return "NOT RUN", "Run explicitly with --role ceo to test the CEO identity.", evidence
        pulls = _api(client, "GET", f"{base}/pulls?state=open&per_page=100")
        evidence.append(pulls)
        if pulls["status"] != 200 or not pulls["response"]:
            return "NOT RUN", "Create an open disposable PR, then rerun this test.", evidence
        number = pulls["response"][0].get("number")
        if not isinstance(number, int):
            return "FAIL", "open PR response lacks a number", evidence
        item = _api(client, "PUT", f"{base}/pulls/{number}/merge", {"merge_method": "merge"})
        evidence.append(item)
        after = _api(client, "GET", f"{base}/pulls/{number}")
        evidence.append(after)
        expected = item["status"] == 403 and isinstance(item["response"], dict) and "resource not accessible" in item["response"].get("message", "").lower()
        unchanged = after["status"] == 200 and after["response"].get("merged") is False and after["response"].get("state") == "open"
        return ("PASS", "CEO merge denied with HTTP 403 permission reason; PR remains open", evidence) if expected and unchanged else ("FAIL", "CEO merge attempt was not denied for the expected permission or PR state changed", evidence)
    if test_id == "A-02":
        pulls = _api(client, "GET", f"{base}/pulls?state=open&per_page=1")
        evidence.append(pulls)
        if pulls["status"] != 200 or not pulls["response"]:
            return "NOT RUN", "Create an open disposable PR, then rerun this test.", evidence
        number = pulls["response"][0]["number"]
        item = _api(client, "PUT", f"{base}/pulls/{number}/merge", {"merge_method": "merge"})
        evidence.append(item)
        after = _api(client, "GET", f"{base}/pulls/{number}")
        evidence.append(after)
        rejected = item["status"] == 403 and isinstance(item["response"], dict) and "resource not accessible" in item["response"].get("message", "").lower()
        unchanged = after["status"] == 200 and after["response"].get("merged") is False and after["response"].get("state") == "open"
        return ("PASS", "merge denied with HTTP 403 permission reason; PR remains open", evidence) if rejected and unchanged else ("FAIL", "merge was not denied for the expected permission reason or PR state changed", evidence)
    if test_id in ("A-03", "P3-05"):
        # Make a real distinct update, then exercise CAS with the previous actual OID.
        sha = _main_sha(client, base, evidence)
        if not sha:
            return "NOT RUN", "main ref unavailable; prepare the disposable trial repository", evidence
        try:
            candidate = subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True, timeout=10).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return "NOT RUN", "local candidate commit unavailable for stale updateRefs trial", evidence
        if not re.fullmatch(r"[0-9a-f]{40,64}", candidate) or candidate == sha:
            return "NOT RUN", "trial needs a distinct local commit to move main before stale updateRefs", evidence
        staged = _git_push(client, f"{owner}/{repo}", f"{candidate}:refs/heads/aao-trial/stale-ref-{candidate[:8]}")
        evidence.append(staged)
        if staged.get("exit_code") != 0:
            return "FAIL", "could not stage distinct candidate commit", evidence
        query = {"query": "mutation($input: UpdateRefsInput!) { updateRefs(input: $input) { refs { name } } }", "variables": {"input": {"refUpdates": [{"name": "refs/heads/main", "oid": candidate, "beforeOid": sha}]}}}
        moved = _api(client, "POST", "/graphql", query)
        evidence.append(moved)
        moved_ok = moved["status"] == 200 and isinstance(moved["response"], dict) and not moved["response"].get("errors")
        if not moved_ok or _main_sha(client, base, evidence) != candidate:
            return "FAIL", "could not move main to distinct candidate before stale updateRefs attempt", evidence
        query = {"query": "mutation($input: UpdateRefsInput!) { updateRefs(input: $input) { refs { name } } }",
                 "variables": {"input": {"refUpdates": [{"name": "refs/heads/main", "oid": sha, "beforeOid": sha}]}}}
        item = _api(client, "POST", "/graphql", query)
        evidence.append(item)
        errors = item["status"] == 200 and isinstance(item["response"], dict) and any("before" in e.get("message", "").lower() or "stale" in e.get("message", "").lower() for e in item["response"].get("errors", []))
        unchanged = _verify_unchanged(client, base, candidate, evidence)
        return ("PASS", "updateRefs rejected stale beforeOid; moved main unchanged", evidence) if errors and unchanged else ("FAIL", "updateRefs did not report expected stale precondition rejection or main changed", evidence)
    if test_id in ("P3-01", "P3-02", "P3-07", "P3-12"):
        if test_id == "P3-01":
            if role != "ceo":
                return "NOT RUN", "Run explicitly with --role ceo to test the CEO identity.", evidence
            item = _git_push(client, f"{owner}/{repo}", "HEAD:refs/heads/main")
            evidence.append(item)
            return ("PASS", "CEO push to protected main was rejected", evidence) if item["status"] == 1 else ("FAIL", "CEO push to protected main was accepted", evidence)
        if test_id == "P3-02" and role not in ("aao-impl-codex", "aao-impl-claude", "aao-impl-ag"):
            return "NOT RUN", "Run with one of the implementer App roles to test its denial on canonical main.", evidence
        if test_id == "P3-12" and role != "aao-integrator":
            return "NOT RUN", "Run as aao-integrator with a non-fast-forward candidate on the disposable trial main.", evidence
        before = _main_sha(client, base, evidence)
        if not before:
            return "FAIL", "could not read main before protected push attempt", evidence
        item = _git_push(client, f"{owner}/{repo}", "HEAD:refs/heads/main", force=test_id == "P3-07")
        evidence.append(item)
        unchanged = _verify_unchanged(client, base, before, evidence)
        expected = "non-fast-forward" if test_id == "P3-12" else "protected branch"
        return ("PASS", f"server denied {test_id} push for expected reason; main unchanged", evidence) if _push_rejection_pass(item, unchanged, expected) else ("FAIL", "push was not rejected by the server for the expected reason or main changed", evidence)
    if test_id == "P3-08":
        return "NOT RUN", "Default-branch deletion is not a meaningful ruleset test: GitHub forbids deleting the default branch independently of rulesets. Configure a protected non-default trial branch and rerun.", evidence
    if test_id in ("A-05", "P3-06"):
        if role != "aao-integrator":
            return "NOT RUN", "Run as aao-integrator on the disposable trial repository after authorization and all required checks are present.", evidence
        try:
            return _merge_trial_pr(client, base, evidence)
        except (GitHubAuthError, OSError, subprocess.SubprocessError, ValueError) as exc:
            evidence.append({"method": "promotion flow", "status": "error", "response": type(exc).__name__})
            return "FAIL", f"promotion flow failed: {type(exc).__name__}", evidence
    if test_id == "A-06":
        head = _api(client, "GET", f"{base}/commits/HEAD")
        evidence.append(head)
        if head["status"] != 200:
            return "FAIL", "could not read HEAD SHA", evidence
        sha = head["response"].get("sha") if isinstance(head["response"], dict) else None
        if not sha:
            return "FAIL", "HEAD response has no SHA", evidence
        item = _api(client, "POST", f"{base}/check-runs", {"name": "aao-audit", "head_sha": sha, "status": "completed", "conclusion": "success"})
        evidence.append(item)
        if role == "aao-auditor":
            actual_app = item["response"].get("app", {}).get("id") if isinstance(item["response"], dict) else None
            return ("PASS", "aao-audit check was accepted from the configured auditor app_id", evidence) if item["status"] in (200, 201) and actual_app == client.app_id else ("FAIL", "auditor check run rejected or returned a different app_id", evidence)
        if role not in ("aao-impl-codex", "aao-impl-claude", "aao-impl-ag"):
            return "NOT RUN", "Use aao-auditor for the positive source-attribution check or an implementer for the expected 403.", evidence
        denied = item["status"] == 403 and isinstance(item["response"], dict) and "resource not accessible" in item["response"].get("message", "").lower()
        return ("PASS", "implementer check-run publication denied with HTTP 403 permission reason", evidence) if denied else ("FAIL", "check-run publication was not denied for the expected permission reason", evidence)
    if test_id == "P3-03":
        try:
            sha = subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True, timeout=10).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return "NOT RUN", "Run from a disposable local clone containing a candidate commit without aao-audit.", evidence
        staged = _git_push(client, f"{owner}/{repo}", f"{sha}:refs/heads/aao-trial/no-audit-{sha[:8]}")
        evidence.append(staged)
        if staged.get("exit_code") != 0:
            return "FAIL", "candidate without required check could not be staged on the trial repository", evidence
        before = _main_sha(client, base, evidence)
        if not before:
            return "FAIL", "could not read main before required-check update attempt", evidence
        item = _api(client, "PATCH", f"{base}/git/refs/heads/main", {"sha": sha, "force": True})
        evidence.append(item)
        message = item["response"].get("message", "").lower() if isinstance(item["response"], dict) else ""
        expected = item["status"] == 403 and ("protected branch" in message or "required status check" in message or "required check" in message)
        unchanged = _verify_unchanged(client, base, before, evidence)
        return ("PASS", "protected branch denied missing-check update with HTTP 403; main unchanged", evidence) if expected and unchanged else ("FAIL", "update was not rejected for required-check protection or main changed", evidence)
    if test_id == "P3-04":
        return "NOT RUN", "Prepare a candidate whose aao-audit check/status was published by a non-auditor App, then run as aao-integrator and attempt the candidate ref update; the auditor app_id is not available cross-uid to this invocation.", evidence
    raise ValueError(f"unsupported test id: {test_id}")


def write_evidence(test_id: str, status: str, reason: str, repo: str, role: str, app_id: int, evidence: list[dict]) -> Path:
    timestamp = datetime.now(UTC).isoformat(timespec="seconds")
    safe_ts = timestamp.replace(":", "").replace("+00:00", "Z")
    directory = Path.home() / "aao-trial-evidence"
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(directory, 0o700)
    shas: set[str] = set()

    def collect(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {"sha", "oid", "beforeOid"} and isinstance(item, str) and re.fullmatch(r"[0-9a-f]{40,64}", item):
                    shas.add(item)
                collect(item)
        elif isinstance(value, list):
            for item in value:
                collect(item)

    collect(evidence)
    if os.environ.get("GITHUB_SHA"):
        shas.add(os.environ["GITHUB_SHA"])
    payload = {"test_id": test_id, "status": status, "reason": reason, "repo": repo, "role": role,
               "app_id": app_id, "timestamp": timestamp, "shas": sorted(shas),
               "evidence": _redact(evidence)}
    fd, name = tempfile.mkstemp(prefix=f".{test_id}-", suffix=".tmp", dir=directory)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True)
            stream.write("\n")
        target = directory / f"{test_id}-{safe_ts}.json"
        os.replace(name, target)
        os.chmod(target, 0o600)
        return target
    except BaseException:
        try:
            os.unlink(name)
        except OSError:
            pass
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("test_id", choices=[*(f"A-{i:02}" for i in range(1, 15)), *(f"P3-{i:02}" for i in range(1, 13))])
    parser.add_argument("--repo", required=True, help="OWNER/REPO disposable trial repository")
    parser.add_argument("--role", required=True, choices=[*sorted(ROLE_NAMES), "ceo"])
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repo):
        parser.error("--repo must be OWNER/REPO")
    try:
        validate_role_uid(args.role)
        if not _trial_repo_allowed(*args.repo.split("/", 1)):
            raise GitHubAuthError("--repo must be explicitly listed in AAO_GITHUB_TRIAL_REPOS and cannot be alessbarb/aao")
        if args.role == "ceo":
            if args.test_id not in ("P3-01", "P3-09"):
                raise GitHubAuthError("--role ceo is allowed only for P3-01 and P3-09")
            token_result = subprocess.run(["gh", "auth", "token", "--hostname", "github.com"], check=True, capture_output=True,
                                          text=True, timeout=10, stdin=subprocess.DEVNULL)
            token = token_result.stdout.strip()
            if not token:
                raise GitHubAuthError("gh auth token returned no token")
            validate_ceo_gh_identity(args.repo)
            client = object.__new__(GitHubAppClient)
            client.app_id, client._installation_token = 0, token
            client.api_base, client.timeout = "https://api.github.com", 15.0
            client.close = lambda: None
        else:
            client = GitHubAppClient(args.role)
        owner, repo = args.repo.split("/", 1)
        # Manual tests require no API call and do not need private credentials.
        if args.role == "ceo":
            status, reason, records = run_test(args.test_id, owner, repo, args.role, client)
        else:
            client.installation_token(owner, repo)
            status, reason, records = run_test(args.test_id, owner, repo, args.role, client)
        output = write_evidence(args.test_id, status, reason, args.repo, args.role, client.app_id, records)
        print(f"{status}: {reason}\nEvidence: {output}")
        return 0 if status == "PASS" else (1 if status == "FAIL" else 2)
    except (GitHubAuthError, OSError, ValueError, subprocess.SubprocessError,
            KeyError, TypeError, IndexError, StopIteration) as exc:
        message = str(exc) if isinstance(exc, GitHubAuthError) else type(exc).__name__
        try:
            output = write_evidence(args.test_id, "NOT RUN", message, args.repo, args.role,
                                    getattr(locals().get("client"), "app_id", 0),
                                    [{"method": "harness", "status": "error", "response": type(exc).__name__}])
            print(f"NOT RUN: {message}\nEvidence: {output}")
        except OSError:
            print(f"NOT RUN: {message}")
        return 2
    finally:
        if "client" in locals():
            try:
                client.close()
            except GitHubAuthError:
                pass


if __name__ == "__main__":
    sys.exit(main())
