"""Local Git history monitor. Events are signed; it is not GitHub supervision."""

from __future__ import annotations

import base64
import subprocess
from pathlib import Path
from typing import Any

from aao.integration_authorization import canonical


def inspect(
    repository: Path, authorization_shas: set[str], sequence: int, private_key: str,
    *, push_attributions: dict[str, str] | None = None,
    integrator_identity: str | None = None,
    protected_path_registry: dict[str, str] | None = None,
    authorized_classes: dict[str, str] | None = None,
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
        protected = protected_path_registry or {".github/workflows/": "R2"}
        protected_changes = [p for p in paths if any(p == prefix or p.startswith(prefix.rstrip("*") ) for prefix in protected)]
        missing_class = any(
            path in protected_changes and (authorized_classes or {}).get(sha) != required
            for path, required in protected.items()
        )
        attribution_mismatch = (
            sha in authorization_shas and integrator_identity is not None
            and (push_attributions or {}).get(sha) != integrator_identity
        )
        if sha not in authorization_shas or missing_class or attribution_mismatch:
            events.append(
                {
                    "sequence": sequence + len(events) + 1,
                    "commit": sha,
                    "unauthorized": sha not in authorization_shas,
                    "workflow_change": bool(protected_changes),
                    "protected_path_change": bool(protected_changes),
                    "protected_path_unauthorized": missing_class,
                    "identity_mismatch": attribution_mismatch,
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
