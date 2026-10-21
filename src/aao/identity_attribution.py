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
        '#!/bin/sh\nwhile read old new ref; do printf \'%s %s %s %s\\n\' "$(id -u)" "$old" "$new" "$ref" >> "'
        + str(log)
        + '"; done\n'
    )
    hook.chmod(0o755)
