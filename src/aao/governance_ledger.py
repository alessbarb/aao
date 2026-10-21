"""Append-only signed hash-chain ledger (file custody remains external)."""

from __future__ import annotations

import base64
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from aao.integration_authorization import canonical


def _verify(entry: dict[str, Any], public_key: str) -> bool:
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        sig, msg = Path(d) / "sig", Path(d) / "msg"
        sig.write_bytes(base64.b64decode(entry["signature"], validate=True))
        payload = {k: v for k, v in entry.items() if k not in {"signature", "hash"}}
        msg.write_bytes(canonical(payload))
        return (
            subprocess.run(
                [
                    "openssl",
                    "pkeyutl",
                    "-verify",
                    "-pubin",
                    "-inkey",
                    public_key,
                    "-sigfile",
                    str(sig),
                    "-in",
                    str(msg),
                    "-rawin",
                ],
                check=False,
                capture_output=True,
            ).returncode
            == 0
        )


def append(path: Path, payload: dict[str, Any], key_id: str, private_key: str) -> dict[str, Any]:
    rows = verify(path, {}) if path.exists() else []
    entry = {
        "sequence": len(rows) + 1,
        "previous_hash": rows[-1]["hash"] if rows else "0" * 64,
        "key_id": key_id,
        **payload,
    }
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        msg = Path(d) / "msg"
        msg.write_bytes(canonical(entry))
        sig = subprocess.run(
            ["openssl", "pkeyutl", "-sign", "-rawin", "-inkey", private_key, "-in", str(msg)],
            check=True,
            capture_output=True,
        ).stdout
    entry["signature"] = base64.b64encode(sig).decode()
    entry["hash"] = hashlib.sha256(canonical(entry)).hexdigest()
    with path.open("ab") as stream:
        stream.write(canonical(entry) + b"\n")
    return entry


def verify(
    path: Path, trusted_keys: dict[str, str], expected_head: str | None = None
) -> list[dict[str, Any]]:
    rows = []
    previous = "0" * 64
    for number, line in enumerate(path.read_bytes().splitlines(), 1):
        e = json.loads(line)
        digest = e.pop("hash", None)
        if e.get("sequence") != number or e.get("previous_hash") != previous:
            raise ValueError("ledger reordered/truncated/chain mismatch")
        if digest != hashlib.sha256(canonical(e)).hexdigest():
            raise ValueError("ledger edited")
        key = trusted_keys.get(e.get("key_id"))
        if trusted_keys and (not key or not _verify(e, key)):
            raise ValueError("ledger signature invalid or key unknown")
        e["hash"] = digest
        previous = digest
        rows.append(e)
    if expected_head is not None and previous != expected_head:
        raise ValueError("ledger truncated or unexpected terminal hash")
    return rows


def active_vetoes(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    revoked = {r.get("target") for r in rows if r.get("type") == "revocation"}
    return [r for r in rows if r.get("type") == "veto" and r.get("id") not in revoked]
