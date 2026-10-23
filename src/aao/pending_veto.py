"""Verification for F4-02 pending-veto marker directories."""
from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path
from typing import Any


class PendingVetoError(ValueError):
    """A pending-veto marker or its custody cannot be verified."""


def _check_parents(path: Path, owner_uid: int) -> None:
    for parent in Path(os.path.abspath(path)).parents:
        info = os.lstat(parent)
        if stat.S_ISLNK(info.st_mode):
            raise PendingVetoError(f"{parent} is a symlink")
        writable = info.st_mode & 0o022
        sticky_root = info.st_mode & stat.S_ISVTX and info.st_uid == 0
        if (writable and not sticky_root) or info.st_uid not in (0, owner_uid):
            raise PendingVetoError(f"{parent} allows the protected path to be replaced")


def _read_marker(path: Path, owner_uid: int) -> bytes:
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError as error:
        raise PendingVetoError(f"{path} is missing or is a symlink") from error
    with os.fdopen(descriptor, "rb") as handle:
        info = os.fstat(handle.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != owner_uid or
                stat.S_IMODE(info.st_mode) not in (0o600, 0o640)):
            raise PendingVetoError(f"{path} is not a mode-0600/0640 regular file owned by the ledger uid")
        _check_parents(path, owner_uid)
        return handle.read()


def pending_vetoes(directory: Path, candidate_sha: str, owner_uid: int) -> list[str]:
    """Return verified marker digests for a candidate; absent directory means no markers."""
    try:
        info = os.lstat(directory)
    except FileNotFoundError:
        return []
    except OSError as error:
        raise PendingVetoError(f"cannot inspect pending-veto directory: {error}") from error
    if (stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode) or
            info.st_uid != owner_uid or stat.S_IMODE(info.st_mode) not in (0o700, 0o750)):
        raise PendingVetoError("pending-veto directory must be mode 0700/0750 and owned by the ledger uid")
    _check_parents(directory / "x", owner_uid)
    digests = []
    try:
        paths = sorted(directory.iterdir())
    except OSError as error:
        raise PendingVetoError(f"cannot list pending-veto directory: {error}") from error
    for path in paths:
        if not path.name.startswith(candidate_sha + "-"):
            continue
        data = _read_marker(path, owner_uid)
        try:
            marker: Any = json.loads(data)
        except (ValueError, UnicodeDecodeError) as error:
            raise PendingVetoError(f"pending-veto marker {path.name} is invalid JSON") from error
        digest = hashlib.sha256(data).hexdigest()
        if (not isinstance(marker, dict) or marker.get("schema") != "aao.pending-veto.v1" or
                marker.get("candidate_sha") != candidate_sha or
                path.name != f"{candidate_sha}-{digest}.json"):
            raise PendingVetoError(f"pending-veto marker {path.name} is inconsistent")
        digests.append(digest)
    return digests


def all_pending_vetoes(directory: Path, owner_uid: int) -> dict[str, list[str]]:
    """Return every verified candidate marker currently present in the directory."""
    try:
        info = os.lstat(directory)
    except FileNotFoundError:
        return {}
    if (stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode) or info.st_uid != owner_uid or
            stat.S_IMODE(info.st_mode) not in (0o700, 0o750)):
        raise PendingVetoError("pending-veto directory must be mode 0700/0750 and owned by the ledger uid")
    _check_parents(directory / "x", owner_uid)
    candidates: dict[str, list[str]] = {}
    for marker_path in sorted(directory.iterdir()):
        candidate = marker_path.name.split("-", 1)[0]
        if not candidate:
            raise PendingVetoError(f"invalid pending-veto marker name: {marker_path.name}")
        digest = pending_vetoes(directory, candidate, owner_uid)
        if digest:
            candidates[candidate] = digest
    return candidates
