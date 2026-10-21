"""Deterministic local-Git promotion prototype; GitHub RA-09 remains unproven."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from aao.integration_authorization import validate


def promote(
    repo: Path,
    remote: str,
    auth: dict[str, Any],
    signature: str,
    snapshot: dict[str, Any],
    message: str = "Governed integration",
    before_push=None,
    identity_provider=None,
) -> str:
    if Path(repo / ".aao-freeze").exists():
        raise RuntimeError("integrator frozen")
    reasons = validate(auth, signature, snapshot)
    if reasons:
        raise ValueError("authorization rejected: " + "; ".join(reasons))
    base = snapshot["target_sha"]
    head = snapshot["pr_head"]
    if auth["merge_method"] != "merge-commit":
        raise ValueError("only merge-commit supported")
    tree = subprocess.run(
        ["git", "-C", str(repo), "merge-tree", "--write-tree", base, head],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()[0]
    if tree != auth["merge_result_tree_sha"]:
        raise ValueError("computed merge tree differs from authorization")
    if (
        subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "refs/heads/main"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        != base
    ):
        raise ValueError("base moved")
    if snapshot.get("pr_head_current") != head:
        raise ValueError("PR head moved")
    commit = subprocess.run(
        ["git", "-C", str(repo), "commit-tree", tree, "-p", base, "-p", head],
        input=message + "\n",
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if identity_provider is not None and not identity_provider.push_identity(
        "refs/heads/main", base, commit
    ):
        raise RuntimeError("unattributed push")
    if before_push is not None:
        before_push()
    result = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "push",
            "--atomic",
            f"--force-with-lease=refs/heads/main:{base}",
            remote,
            f"{commit}:refs/heads/main",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError("conditional push rejected; no fallback: " + result.stderr)
    actual = subprocess.run(
        ["git", "-C", str(repo), "ls-remote", remote, "refs/heads/main"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()[0]
    remote_tree = subprocess.run(
        ["git", "-C", str(repo), "show", "-s", "--format=%T", actual],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if actual != commit or remote_tree != tree:
        (Path(repo) / ".aao-freeze").write_text(
            f"published ref divergence {actual} {remote_tree}\n"
        )
        raise RuntimeError("post-publication divergence; integrator frozen")
    return commit
