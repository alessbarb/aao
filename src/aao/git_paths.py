"""Shared Git path decoding and policy-prefix matching."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

_GIT_ENV = {
    "PATH": "/usr/bin:/bin",
    "HOME": "/nonexistent",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_NO_REPLACE_OBJECTS": "1",
    "LANG": "C.UTF-8",
}


def path_matches_prefix(path: str, prefix: str) -> bool:
    """Policy prefixes are literal string prefixes, as defined by governance policy."""
    return path.startswith(prefix)


def changed_paths(repository: str | Path, base: str, candidate: str) -> list[str]:
    """Return Git's raw changed path names; renames contribute both old and new names."""
    args = ["git", "-C", str(repository), "diff"]
    result = subprocess.run(
        [*args, "-z", "--name-only", "-M", base, candidate],
        check=True, capture_output=True, env=_GIT_ENV,
    )
    paths = {os.fsdecode(path) for path in result.stdout.split(b"\0") if path}
    statuses = subprocess.run(
        [*args, "-z", "--name-status", "-M", base, candidate],
        check=True, capture_output=True, env=_GIT_ENV,
    ).stdout.split(b"\0")
    index = 0
    while index < len(statuses) and statuses[index]:
        status = statuses[index].decode("ascii")
        count = 2 if status.startswith(("R", "C")) else 1
        paths.update(os.fsdecode(path) for path in statuses[index + 1:index + 1 + count])
        index += count + 1
    return sorted(paths)

