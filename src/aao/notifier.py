"""Signed event consumer with sequence anti-replay and injectable sink."""

from __future__ import annotations

import base64
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from aao.integration_authorization import canonical


class Sink(Protocol):
    def publish(self, event: dict[str, Any]) -> None: ...


class FileSink:
    def __init__(self, path: Path):
        self.path = path

    def publish(self, event: dict[str, Any]) -> None:
        with self.path.open("ab") as f:
            f.write(canonical(event) + b"\n")


class GitHubIssueSink:
    """P2 placeholder: requires authorized GitHub issues:write; deliberately not called in tests."""

    def publish(self, event: dict[str, Any]) -> None:
        raise RuntimeError("GitHub sink requires P2 authorization")


def consume(event: dict[str, Any], trusted_keys: dict[str, str], state_path: Path,
           now: str, sink: Sink) -> int:
    import tempfile

    if not isinstance(trusted_keys, dict) or not trusted_keys:
        raise ValueError("trusted key registry is required")
    key_id = event.get("key_id")
    public_key = trusted_keys.get(key_id)
    if not public_key:
        raise ValueError("unknown signing key")
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    last_sequence = int(state.get(key_id, 0))
    payload = {k: v for k, v in event.items() if k != "signature"}
    with tempfile.TemporaryDirectory() as d:
        sig, msg = Path(d) / "sig", Path(d) / "msg"
        sig.write_bytes(base64.b64decode(event["signature"], validate=True))
        msg.write_bytes(canonical(payload))
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
            check=True,
            capture_output=True,
        )
    if event["sequence"] <= last_sequence:
        raise ValueError("replayed event")
    if event["sequence"] != last_sequence + 1:
        raise ValueError("event sequence gap")
    if datetime.fromisoformat(event["expires_at"].replace("Z", "+00:00")) <= datetime.fromisoformat(  # noqa: FURB162
        now.replace("Z", "+00:00")  # noqa: FURB162
    ):
        raise ValueError("expired event")
    sink.publish(dict(event))
    state[key_id] = event["sequence"]
    state_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = state_path.with_name(state_path.name + ".tmp")
    temporary.write_text(json.dumps(state, sort_keys=True))
    os.replace(temporary, state_path)
    return event["sequence"]
