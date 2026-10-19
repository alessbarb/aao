#!/usr/bin/env python3
"""One-shot local CEO bootstrap for a narrowly scoped Self Development agent.

The CEO bearer is entered through a no-echo terminal prompt, used only for
loopback API requests, and never written or printed. The newly issued agent
bearer is written only to the user's private runtime directory.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import secrets
import stat
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

PROJECT_NAME = "AAO Self Development"
GRANTS = ("project.read", "work.admit", "execution.claim")
GRANT_LIFETIME = timedelta(hours=8)


class BootstrapError(RuntimeError):
    pass


def request_json(base_url: str, path: str, *, method: str = "GET",
                 ceo_token: str | None = None, agent_token: str | None = None,
                 body: dict | None = None) -> dict | list:
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if ceo_token is not None:
        headers["X-CEO-Token"] = ceo_token
    if agent_token is not None:
        headers["X-Agent-Token"] = agent_token
    payload = None if body is None else json.dumps(body).encode()
    request = Request(
        f"{base_url}{path}",
        data=payload,
        method=method,
        headers=headers,
    )
    try:
        with urlopen(request, timeout=5) as response:
            return json.loads(response.read())
    except HTTPError as exc:
        raise BootstrapError(f"AAO API rejected the bootstrap request (HTTP {exc.code})") from None
    except (URLError, TimeoutError, OSError, json.JSONDecodeError):
        raise BootstrapError("AAO API is unavailable or returned invalid data") from None


def private_runtime_file() -> Path:
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if not runtime:
        raise BootstrapError("XDG_RUNTIME_DIR is required; no persistent fallback is used")
    directory = Path(runtime).resolve()
    try:
        mode = stat.S_IMODE(directory.stat().st_mode)
    except OSError:
        raise BootstrapError("XDG_RUNTIME_DIR is unavailable") from None
    if directory.stat().st_uid != os.getuid() or mode & 0o077:
        raise BootstrapError("XDG_RUNTIME_DIR must be owned by this user and private")
    target = directory / "aao-self-development-agent.token"
    if target.exists():
        raise BootstrapError("agent token file already exists; refusing to overwrite it")
    return target


def write_private_token(path: Path, token: str) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(token)
            stream.write("\n")
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def bootstrap(base_url: str) -> tuple[str, str, datetime, Path]:
    parsed = urlparse(base_url)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise BootstrapError("bootstrap is restricted to the local HTTP API")
    if parsed.path or parsed.query or parsed.fragment:
        raise BootstrapError("base URL must not contain a path, query, or fragment")
    token_path = private_runtime_file()
    ceo_token = getpass.getpass("CEO development token (hidden): ")
    if not ceo_token:
        raise BootstrapError("CEO credential is required")

    projects = request_json(base_url, "/v1/projects", ceo_token=ceo_token)
    if not isinstance(projects, list):
        raise BootstrapError("project listing response is invalid")
    matches = [p for p in projects if p.get("name") == PROJECT_NAME]
    if len(matches) != 1 or matches[0].get("state") != "ACTIVE":
        raise BootstrapError("exactly one active AAO Self Development project is required")
    project = matches[0]
    # Inspect the currently authorized inventory before creating any new identity.
    # The endpoint is CEO-only and returns metadata only, never credential material.
    existing_grants = request_json(
        base_url, f"/v1/projects/{project['id']}/grants", ceo_token=ceo_token,
    )
    if not isinstance(existing_grants, list):
        raise BootstrapError("project grant inventory response is invalid")
    now = datetime.now(UTC)
    active_agents = {
        row.get("principal_id")
        for row in existing_grants
        if isinstance(row, dict)
        and row.get("kind") == "AGENT"
        and row.get("credential_enabled") is True
        and isinstance(row.get("principal_id"), str)
        and (
            row.get("expires_at") is None
            or datetime.fromisoformat(row["expires_at"]) > now
        )
    }
    if active_agents:
        raise BootstrapError(
            "an active AGENT grant already exists for this project; refusing to provision a duplicate"
        )
    principal_id = f"aao-selfdev-{secrets.token_hex(6)}"
    credential = request_json(
        base_url,
        "/v1/principals/credentials",
        method="POST",
        ceo_token=ceo_token,
        body={"principal_id": principal_id, "kind": "AGENT"},
    )
    if not isinstance(credential, dict) or credential.get("principal_id") != principal_id:
        raise BootstrapError("credential issuance response is invalid")
    agent_token = credential.get("token")
    if not isinstance(agent_token, str) or not agent_token:
        raise BootstrapError("credential issuance response omitted the agent token")

    expiry = datetime.now(UTC) + GRANT_LIFETIME
    grant_body = {"principal_id": principal_id, "expires_at": expiry.isoformat()}
    try:
        for capability in GRANTS:
            response = request_json(
                base_url,
                f"/v1/projects/{project['id']}/grants",
                method="POST",
                ceo_token=ceo_token,
                body={**grant_body, "capability": capability},
            )
            if not isinstance(response, dict) or response.get("created") is not True:
                raise BootstrapError("a narrowly scoped project grant was not created")
        visible_projects = request_json(
            base_url, "/v1/projects", agent_token=agent_token,
        )
        if not isinstance(visible_projects, list) or not any(
            item.get("id") == project["id"] for item in visible_projects
        ):
            raise BootstrapError("the issued AGENT identity failed its scoped read check")
        write_private_token(token_path, agent_token)
    except BaseException:
        try:
            request_json(
                base_url,
                f"/v1/principals/{principal_id}/revoke",
                method="POST",
                ceo_token=ceo_token,
                body={},
            )
        except BootstrapError:
            pass
        token_path.unlink(missing_ok=True)
        raise
    finally:
        del ceo_token
        del agent_token

    return principal_id, project["id"], expiry, token_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    arguments = parser.parse_args()
    try:
        principal, project, expiry, token_file = bootstrap(arguments.base_url)
    except BootstrapError as exc:
        print(f"Bootstrap not completed: {exc}", file=sys.stderr)
        return 1
    print(f"AGENT provisioned: {principal}")
    print(f"Project: {PROJECT_NAME} ({project})")
    print(f"Grants: {', '.join(GRANTS)}")
    print(f"Grant expiry (UTC): {expiry.isoformat()}")
    print(f"Agent token file (mode 0600): {token_file}")
    print("No CEO or AGENT credential was printed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
