"""Local Git history monitor. Events are signed; it is not GitHub supervision."""

from __future__ import annotations

import base64
import subprocess
from pathlib import Path
from typing import Any

from aao.integration_authorization import canonical


def inspect(
    repository: Path, authorization_shas: set[str], sequence: int, private_key: str
) -> list[dict[str, Any]]:
    commits = subprocess.run(
        ["git", "-C", str(repository), "rev-list", "--first-parent", "main"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    events = []
    for sha in commits:
        paths = subprocess.run(
            ["git", "-C", str(repository), "diff-tree", "--no-commit-id", "--name-only", "-r", "--root", sha],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        if sha not in authorization_shas or any(p.startswith(".github/workflows/") for p in paths):
            events.append(
                {
                    "sequence": sequence + len(events) + 1,
                    "commit": sha,
                    "unauthorized": sha not in authorization_shas,
                    "workflow_change": any(p.startswith(".github/workflows/") for p in paths),
                }
            )
    return events


def signed_heartbeat(sequence: int, issued_at: str, private_key: str) -> dict[str, str | int]:
    import tempfile

    event = {"sequence": sequence, "issued_at": issued_at, "type": "heartbeat"}
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "msg"
        f.write_bytes(canonical(event))
        sig = subprocess.run(
            ["openssl", "pkeyutl", "-sign", "-rawin", "-inkey", private_key, "-in", str(f)],
            check=True,
            capture_output=True,
        ).stdout
    return {**event, "signature": base64.b64encode(sig).decode()}
