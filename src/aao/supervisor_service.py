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
from urllib.parse import quote

from aao.supervisor import _sequence, serve_veto_intake, signed_heartbeat

CONFIG_PATH = Path("/etc/aao-supervisor/config.json")
CONFIG_SCHEMA = "aao.supervisor-config.v1"
_FIELDS = {"schema", "auditor_uid", "ledger_path", "state_path", "heartbeat_path", "intake_socket",
           "private_key", "key_id", "trust_registry", "validity_seconds", "repository", "attribution_path"}


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
    push_principals = registry.get("push_principals")
    if not isinstance(push_principals, dict) or not push_principals or any(
            not isinstance(principal, str) or not principal or not isinstance(implementer, str) or not implementer
            for principal, implementer in push_principals.items()):
        raise ValueError("trust registry lacks push_principals")
    if len(set(push_principals.values())) != len(push_principals):
        raise ValueError("push principal attribution is ambiguous")
    return {**config, "trusted_keys": keys, "integrator_key_id": integrator,
            "push_principals": push_principals}


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


def attribution(config: dict[str, Any], client: Any | None = None) -> int:
    """Record only GitHub-sourced push actors and PR authors; API failure writes nothing."""
    from aao.github_app_auth import GitHubAppClient
    from aao.supervisor import record_attribution

    repo = config["repository"]
    if not isinstance(repo, str) or repo.count("/") != 1 or not all(repo.split("/")):
        raise ValueError("supervisor repository must be configured as owner/name")
    github = client if client is not None else GitHubAppClient("aao-supervisor")
    owner, name = repo.split("/", 1)
    if hasattr(github, "installation_token"):
        github.installation_token(owner, name)
    escaped = f"{quote(owner, safe='')}/{quote(name, safe='')}"

    def get(path: str) -> Any:
        response = github.request("GET", path)
        status = getattr(response, "status", 200)
        body = getattr(response, "body", response)
        if not 200 <= status < 300 or not isinstance(body, list):
            raise RuntimeError(f"GitHub attribution API failed (HTTP {status})")
        return body

    attributed: dict[str, set[str]] = {}
    push_principals = config["push_principals"]
    # Only authenticated push events are eligible. PR author logins are not push authentication.
    events = get(f"/repos/{escaped}/events?per_page=100")
    for event in events:
        if not isinstance(event, dict):
            raise TypeError("malformed GitHub repository event")
        if event.get("type") == "PushEvent":
            actor = event.get("actor")
            commits = event.get("payload", {}).get("commits") if isinstance(event.get("payload"), dict) else None
            if not isinstance(actor, dict) or not isinstance(actor.get("login"), str) or not isinstance(commits, list):
                raise ValueError("malformed GitHub push event")
            for commit in commits:
                sha = commit.get("sha") if isinstance(commit, dict) else None
                if not isinstance(sha, str) or len(sha) != 40 or any(ch not in "0123456789abcdef" for ch in sha):
                    raise ValueError("malformed commit in GitHub push event")
                attributed.setdefault(sha, set()).add(actor["login"])
    for sha, principals in sorted(attributed.items()):
        record_attribution(Path(config["attribution_path"]), sha, sorted(principals))
    return len(attributed)


def main() -> int:
    parser = argparse.ArgumentParser(description="AAO supervisor service (config path is fixed)")
    parser.add_argument("command", choices=("serve", "heartbeat", "attribution"))
    args = parser.parse_args()
    config = load_config()
    if args.command == "heartbeat":
        event = heartbeat(config)
        print(json.dumps({"sequence": event["sequence"], "ledger_head": event["ledger_head"]}))
        return 0
    if args.command == "attribution":
        count = attribution(config)
        print(json.dumps({"status": "recorded", "candidates": count}))
        return 0
    serve_veto_intake(Path(config["intake_socket"]), auditor_uid=config["auditor_uid"],
                      validity_seconds=config["validity_seconds"], **_custody(config))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
