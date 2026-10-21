"""Signed event consumer with sequence anti-replay and injectable sink."""

from __future__ import annotations

import base64
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


def consume(
    event: dict[str, Any], public_key: str, last_sequence: int, now: str, sink: Sink
) -> int:
    import tempfile

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
    if datetime.fromisoformat(event["expires_at"].replace("Z", "+00:00")) <= datetime.fromisoformat(  # noqa: FURB162
        now.replace("Z", "+00:00")  # noqa: FURB162
    ):
        raise ValueError("expired event")
    sink.publish(payload)
    return event["sequence"]
