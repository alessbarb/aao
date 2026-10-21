"""Sign local Git-history alerts and heartbeats; this is not GitHub supervision."""

from __future__ import annotations

import base64
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from aao.governance_ledger import verify
from aao.integration_authorization import canonical


def _sign(event: dict[str, Any], private_key: str) -> dict[str, Any]:
    import tempfile

    with tempfile.TemporaryDirectory() as directory:
        message = Path(directory) / "message"
        message.write_bytes(canonical(event))
        signature = subprocess.run(
            ["openssl", "pkeyutl", "-sign", "-rawin", "-inkey", private_key, "-in", str(message)],
            check=True, capture_output=True,
        ).stdout
    return {**event, "signature": base64.b64encode(signature).decode()}


def _sequence(path: Path) -> int:
    state = json.loads(path.read_text()) if path.exists() else {}
    return int(state.get("sequence", 0))


def _persist_sequence(path: Path, sequence: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps({"sequence": sequence}))
    temporary.replace(path)


def inspect(
    repository: Path,
    authorization_shas: set[str],
    sequence: int,
    private_key: str,
    *,
    key_id: str,
    state_path: Path,
    ledger_path: Path,
    trusted_keys: dict[str, str],
    push_attributions: dict[str, str] | None = None,
    integrator_identity: str | None = None,
    protected_path_registry: dict[str, str] | None = None,
    authorized_classes: dict[str, str] | None = None,
    now: str | None = None,
) -> list[dict[str, Any]]:
    """Return signed alerts for unauthorized, misattributed, or under-classed commits.

    Authorizations are derived only from the signature-verified ledger. ``sequence``
    is retained for call compatibility; persistent state is the sequence authority.
    """
    rows = verify(ledger_path, trusted_keys)
    ledger_authorizations = {
        row["commit"]: row for row in rows
        if row.get("type") == "authorization" and isinstance(row.get("commit"), str)
    }
    authorized = set(ledger_authorizations)
    commits = subprocess.run(
        ["git", "-C", str(repository), "rev-list", "--first-parent", "main"],
        check=True, capture_output=True, text=True,
    ).stdout.splitlines()
    protected = protected_path_registry or {".github/workflows/": "R2"}
    order = {"R1": 1, "R2": 2, "R3": 3}
    events = []
    seq = max(sequence, _sequence(state_path))
    timestamp = now or datetime.now().astimezone().isoformat()
    expiry = (datetime.fromisoformat(timestamp.replace("Z", "+00:00")) + timedelta(minutes=5)).isoformat()  # noqa: FURB162
    for sha in commits:
        parents = subprocess.run(
            ["git", "-C", str(repository), "show", "-s", "--format=%P", sha],
            check=True, capture_output=True, text=True,
        ).stdout.split()
        if parents:
            paths = subprocess.run(
                ["git", "-C", str(repository), "diff-tree", "-r", "--no-commit-id", "--name-only",
                 parents[0], sha], check=True, capture_output=True, text=True,
            ).stdout.splitlines()
        else:
            paths = subprocess.run(
                ["git", "-C", str(repository), "diff-tree", "--root", "-r", "--no-commit-id",
                 "--name-only", sha], check=True, capture_output=True, text=True,
            ).stdout.splitlines()
        changed_rules = [(path, level) for path in paths for rule, level in protected.items()
                         if path == rule or (rule.endswith("/") and path.startswith(rule))]
        ledger_row = ledger_authorizations.get(sha)
        attestation = (authorized_classes or {}).get(sha) or (ledger_row or {}).get("risk_class")
        insufficient = any(order.get(attestation, 0) < order.get(level, 4) for _, level in changed_rules)
        mismatch = bool(ledger_row and integrator_identity is not None and
                        (push_attributions or {}).get(sha) != integrator_identity)
        if sha not in authorized or insufficient or mismatch:
            seq += 1
            events.append(_sign({
                "sequence": seq, "key_id": key_id, "issued_at": timestamp, "expires_at": expiry,
                "type": "alert", "commit": sha, "unauthorized": sha not in authorized,
                "workflow_change": any(path.startswith(".github/workflows/") for path, _ in changed_rules),
                "protected_path_change": bool(changed_rules),
                "protected_path_unauthorized": insufficient, "identity_mismatch": mismatch,
            }, private_key))
    _persist_sequence(state_path, seq)
    return events


def signed_heartbeat(sequence: int, issued_at: str, private_key: str, *, key_id: str,
                     expires_at: str) -> dict[str, Any]:
    event = {"sequence": sequence, "key_id": key_id, "issued_at": issued_at,
             "expires_at": expires_at, "type": "heartbeat"}
    return _sign(event, private_key)
