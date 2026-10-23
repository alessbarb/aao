"""Disposable bare-remote identity hook and future authenticated provider seam."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class IdentityProvider(Protocol):
    def push_identity(self, ref: str, old: str, new: str) -> str: ...


class GitHubIdentityProvider:
    """P2: GitHub events/API required; local hook identity is not GitHub attribution."""

    def push_identity(self, ref: str, old: str, new: str) -> str:
        raise NotImplementedError("RA-02 GitHub provider pending P2")


def install_uid_hook(bare: Path, log: Path) -> None:
    hook = bare / "hooks" / "pre-receive"
    hook.write_text(
        '#!/bin/sh\n'
        'set -eu\n'
        'uid=$(id -u)\n'
        'while read old new ref; do\n'
        '  printf "%s %s %s %s\\n" "$uid" "$old" "$new" "$ref" >> '
        + repr(str(log))
        + '\n'
        'done\n'
    )
    hook.chmod(0o755)
