#!/usr/bin/env python3
"""Rotate the local development CEO bearer, restart AAO, then bootstrap its agent.

This is for an interactive local development terminal only. It never prints,
logs, or puts the CEO bearer in a command-line argument. The existing local
dotenv file is the authoritative source; an inherited token override is refused.
"""

from __future__ import annotations

import getpass
import json
import os
import re
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
ENV_FILE = ROOT / ".env.local"
BASE_URL = "http://127.0.0.1:8001"
CEO_KEY = b"AAO_CEO_TOKEN"
TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{43,}$")


class RotationError(RuntimeError):
    pass


def _has_key(line: bytes) -> bool:
    match = re.match(rb"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=", line)
    return bool(match and match.group(1) == CEO_KEY)


def replace_dotenv_token(path: Path, token: str) -> None:
    """Replace only the named setting atomically, without displaying old values."""
    if path.is_symlink():
        raise RotationError("configuration file must not be a symbolic link")
    if path.exists():
        info = path.stat()
        if info.st_uid != os.getuid():
            raise RotationError("configuration file must be owned by the current user")
        mode = stat.S_IMODE(info.st_mode)
        if mode & 0o077:
            raise RotationError("configuration file permissions must be private (0600 or stricter)")
        old_lines = path.read_bytes().splitlines(keepends=True)
    else:
        mode = 0o600
        old_lines = []

    matches = [index for index, line in enumerate(old_lines) if _has_key(line)]
    if len(matches) > 1:
        raise RotationError("configuration contains duplicate CEO token settings; resolve them locally first")

    replacement = b"AAO_CEO_TOKEN=" + token.encode("ascii") + b"\n"
    if matches:
        old_lines[matches[0]] = replacement
    else:
        if old_lines and not old_lines[-1].endswith((b"\n", b"\r")):
            old_lines[-1] += b"\n"
        old_lines.append(replacement)

    fd, temporary_name = tempfile.mkstemp(prefix=".env.local.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb") as stream:
            stream.writelines(old_lines)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def validate_dotenv_file(path: Path) -> None:
    """Validate configuration metadata and key cardinality before prompting."""
    if path.is_symlink() or not path.is_file():
        raise RotationError("configuration must be a regular, non-symlink file")
    info = path.stat()
    if info.st_uid != os.getuid():
        raise RotationError("configuration file must be owned by the current user")
    if stat.S_IMODE(info.st_mode) & 0o077:
        raise RotationError("configuration file permissions must be private (0600 or stricter)")
    try:
        lines = path.read_bytes().splitlines()
    except OSError:
        raise RotationError("configuration file cannot be read") from None
    if sum(_has_key(line) for line in lines) > 1:
        raise RotationError("configuration contains duplicate CEO token settings; resolve them locally first")


def _candidate_server_pids() -> list[int]:
    pids = []
    proc_root = Path("/proc")
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            if entry.stat().st_uid != os.getuid():
                continue
            args = (entry / "cmdline").read_bytes().split(b"\0")
            cwd = (entry / "cwd").resolve()
        except (OSError, PermissionError):
            continue
        host_index = args.index(b"--host") if b"--host" in args else -1
        port_index = args.index(b"--port") if b"--port" in args else -1
        if (
            cwd == ROOT
            and b"uvicorn" in args
            and b"aao.work_management_api:app" in args
            and host_index >= 0
            and host_index + 1 < len(args)
            and args[host_index + 1] == b"127.0.0.1"
            and port_index >= 0
            and port_index + 1 < len(args)
            and args[port_index + 1] == b"8001"
        ):
            pids.append(int(entry.name))
    return pids


def _port_is_open() -> bool:
    with socket.socket() as client:
        client.settimeout(0.25)
        return client.connect_ex(("127.0.0.1", 8001)) == 0


def preflight_current_service() -> None:
    if not _port_is_open():
        raise RotationError("AAO is not listening on 127.0.0.1:8001")
    pids = _candidate_server_pids()
    if len(pids) != 1:
        raise RotationError("port 8001 is not owned by exactly one verified loopback AAO process")
    try:
        with urlopen(f"{BASE_URL}/ready", timeout=2) as response:
            readiness = json.loads(response.read())
        with urlopen(f"{BASE_URL}/openapi.json", timeout=2) as response:
            api_schema = json.loads(response.read())
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError):
        raise RotationError("current AAO service or PostgreSQL readiness check failed") from None
    mandate_methods = api_schema.get("paths", {}).get("/v1/mandates", {})
    if readiness.get("status") != "ready":
        raise RotationError("PostgreSQL is not ready; no token was changed")
    if "get" not in mandate_methods:
        raise RotationError("current API is stale; restart from the current checkout before rotating")


def stop_current_server() -> None:
    pids = _candidate_server_pids()
    if len(pids) > 1:
        raise RotationError("multiple matching local AAO API processes found; stop them manually")
    if not pids:
        if _port_is_open():
            raise RotationError("port 8001 is occupied by an unverified process; refusing to stop it")
        return

    pid = pids[0]
    os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.1)
    else:
        raise RotationError("the existing AAO API did not stop cleanly; refusing to force-kill it")


def start_server() -> subprocess.Popen[bytes]:
    environment = os.environ.copy()
    environment.pop("AAO_CEO_TOKEN", None)
    environment["AAO_ENV"] = "development"
    environment["AAO_ENV_FILE"] = ".env.local"
    # Enable only the already-implemented fixed repository-check sandbox. It
    # does not enable general shell, model, network, or external-effect tools.
    environment["AAO_SANDBOX_QUEUE_ENABLED"] = "true"
    environment["AAO_SELF_DEV_REPOSITORY"] = str(ROOT)
    command = [
        sys.executable, "-m", "uvicorn", "aao.work_management_api:app",
        "--host", "127.0.0.1", "--port", "8001", "--no-access-log",
    ]
    return subprocess.Popen(
        command,
        cwd=ROOT,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def verify_ceo_auth(token: str, process: subprocess.Popen[bytes]) -> None:
    deadline = time.monotonic() + 20
    last_error = ""
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RotationError("AAO API exited during restart; no credential was logged")
        try:
            request = Request(
                f"{BASE_URL}/v1/mandates",
                headers={"Accept": "application/json", "X-CEO-Token": token},
            )
            with urlopen(request, timeout=2) as response:
                if response.status == 200:
                    return
                last_error = "unexpected HTTP response"
        except HTTPError as exc:
            last_error = f"HTTP {exc.code}"
        except (URLError, TimeoutError, OSError):
            last_error = "API not ready"
        time.sleep(0.25)
    raise RotationError(f"CEO authentication did not verify ({last_error}); no credential was logged")


def main() -> int:
    from scripts import bootstrap_self_dev_agent

    new_token: str | None = None
    try:
        if os.name != "posix" or not Path("/proc").is_dir():
            raise RotationError("this safe restart procedure requires the local Linux development host")
        if "AAO_CEO_TOKEN" in os.environ:
            raise RotationError(
                "AAO_CEO_TOKEN is already set in the process environment, which overrides .env.local; "
                "remove that override from its source and rerun"
            )
        # The existing bootstrap requires a private, ephemeral destination for
        # the new AGENT token; validate it before changing CEO configuration.
        bootstrap_self_dev_agent.private_runtime_file()
        if not ENV_FILE.is_file():
            raise RotationError(".env.local is missing; create it privately from .env.example first")
        validate_dotenv_file(ENV_FILE)
        if not sys.stdin.isatty() or not sys.stderr.isatty():
            raise RotationError("run this command in an interactive terminal so input remains hidden")
        preflight_current_service()

        new_token = getpass.getpass("New CEO development token (hidden): ")
        if not TOKEN_PATTERN.fullmatch(new_token):
            raise RotationError("token must be at least 43 URL-safe characters; no value was displayed")

        replace_dotenv_token(ENV_FILE, new_token)
        stop_current_server()
        server = start_server()
        verify_ceo_auth(new_token, server)
        # Reuse the same in-memory credential, so bootstrap does not prompt for
        # or copy the CEO token again. The bootstrap only prints non-secret IDs.
        principal, mandate, project, expiry, token_path = bootstrap_self_dev_agent.bootstrap(
            BASE_URL, ceo_token=new_token,
        )
        print(f"CEO token rotated; authorized API check passed. PID: {server.pid}")
        print(f"AGENT provisioned: {principal}; mandate: {mandate}; project: {project}")
        print(f"Grant expiry (UTC): {expiry.isoformat()}; private AGENT token file: {token_path}")
        print("No CEO or AGENT credential was printed.")
        return 0
    except (RotationError, bootstrap_self_dev_agent.BootstrapError, OSError, EOFError) as exc:
        print(f"CEO rotation/bootstrap not completed: {exc}", file=sys.stderr)
        return 1
    finally:
        new_token = None


if __name__ == "__main__":
    raise SystemExit(main())
