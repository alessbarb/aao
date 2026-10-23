"""Disposable bare-remote identity hook and future authenticated provider seam."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class IdentityProvider(Protocol):
    def push_identity(self, ref: str, old: str, new: str) -> str: ...


class GitHubIdentityProvider:
    """Attribute pushes only after verifying the App and repository installation."""

    def __init__(self, identity: str, github: object | None = None, repository: str | None = None):
        if not isinstance(identity, str) or not identity:
            raise ValueError("integrator identity is required")
        self.identity = identity
        self.github = github
        self.repository = repository

    def __call__(self) -> str:
        return self.identity

    def push_identity(self, ref: str, old: str, new: str) -> str:
        if self.github is None or not isinstance(self.repository, str) or self.repository.count("/") != 1:
            return ""
        request = getattr(self.github, "app_request", None)
        installation_id = getattr(self.github, "_installation_id", None)
        if not callable(request) or not isinstance(installation_id, int):
            return ""
        try:
            app_response = request("GET", "/app")
            repo_response = request("GET", f"/repos/{self.repository}/installation")
            app = getattr(app_response, "body", app_response)
            installation = getattr(repo_response, "body", repo_response)
            if getattr(app_response, "status", 200) != 200 or not isinstance(app, dict):
                return ""
            if getattr(repo_response, "status", 200) != 200 or not isinstance(installation, dict):
                return ""
            if app.get("slug") != self.identity or installation.get("id") != installation_id:
                return ""
            return self.identity
        except (OSError, RuntimeError, ValueError, TypeError, KeyError):
            return ""


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
