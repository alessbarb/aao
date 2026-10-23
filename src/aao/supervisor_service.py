"""Supervisor service entry points (run as the aao-supervisor uid by systemd).

Not part of the auditor closure pinned in trusted_auditor_revisions: the auditor's frozen tree stays at its
reviewed commit; this module is deployed only to the supervisor's frozen tree.
"""
from __future__ import annotations

import argparse
import json
import os
import pwd
import stat
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from aao.supervisor import _sequence, serve_veto_intake, signed_heartbeat

CONFIG_PATH = Path("/etc/aao-supervisor/config.json")
CONFIG_SCHEMA = "aao.supervisor-config.v1"
_FIELDS = {"schema", "auditor_uid", "ledger_path", "state_path", "heartbeat_path", "intake_socket",
           "private_key", "key_id", "trust_registry", "validity_seconds"}


def _read_owned(path: Path, owners: tuple[int, ...]) -> bytes:
    """A regular, non-symlink file owned by an allowed uid and not group/other writable."""
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o022 or info.st_uid not in owners:
            raise ValueError(f"{path} is not a protected regular file owned by {owners}")
        return handle.read()


def load_config(path: Path = CONFIG_PATH, owners: tuple[int, ...] = (0,),
                registry_owners: tuple[int, ...] | None = None) -> dict[str, Any]:
    """Config is root-owned; the trust registry is root- or aao-trust-owned (P1 layout)."""
    if registry_owners is None:
        registry_owners = (0, pwd.getpwnam("aao-trust").pw_uid)
    config = json.loads(_read_owned(path, owners))
    if not isinstance(config, dict) or set(config) != _FIELDS or config["schema"] != CONFIG_SCHEMA:
        raise ValueError("supervisor config fields are not the expected set")
    if not isinstance(config["auditor_uid"], int) or not isinstance(config["validity_seconds"], int):
        raise TypeError("auditor_uid and validity_seconds must be integers")
    registry = json.loads(_read_owned(Path(config["trust_registry"]), registry_owners))
    keys, integrator = registry.get("ledger_keys"), registry.get("integrator_key_id")
    if not isinstance(keys, dict) or not keys or not isinstance(integrator, str):
        raise ValueError("trust registry lacks ledger_keys or integrator_key_id")
    return {**config, "trusted_keys": keys, "integrator_key_id": integrator}


def _custody(config: dict[str, Any]) -> dict[str, Any]:
    return {"private_key": config["private_key"], "key_id": config["key_id"],
            "ledger_path": Path(config["ledger_path"]), "state_path": Path(config["state_path"]),
            "trusted_keys": config["trusted_keys"], "integrator_key_id": config["integrator_key_id"],
            "heartbeat_path": Path(config["heartbeat_path"])}


def heartbeat(config: dict[str, Any]) -> dict[str, Any]:
    """One periodic signed heartbeat; the publication guard rejects a stale sequence (timer retries)."""
    custody = _custody(config)
    now = datetime.now(UTC)
    sequence = _sequence(custody["state_path"], custody["private_key"]) + 1
    return signed_heartbeat(sequence, now.isoformat(), expires_at=(now + timedelta(
        seconds=config["validity_seconds"])).isoformat(), **custody)


def main() -> int:
    parser = argparse.ArgumentParser(description="AAO supervisor service (config path is fixed)")
    parser.add_argument("command", choices=("serve", "heartbeat"))
    args = parser.parse_args()
    config = load_config()
    if args.command == "heartbeat":
        event = heartbeat(config)
        print(json.dumps({"sequence": event["sequence"], "ledger_head": event["ledger_head"]}))
        return 0
    serve_veto_intake(Path(config["intake_socket"]), auditor_uid=config["auditor_uid"],
                      validity_seconds=config["validity_seconds"], **_custody(config))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
