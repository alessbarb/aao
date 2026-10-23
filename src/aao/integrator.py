"""Fail-closed governed promotion using locally provisioned trust sources."""
from __future__ import annotations

import base64
import json
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aao.git_paths import changed_paths as git_changed_paths
from aao.governance_ledger import active_vetoes, append, open_incidents, verify
from aao.integration_authorization import canonical, validate
from aao.pending_veto import PendingVetoError, pending_vetoes


@dataclass(frozen=True)
class TrustSources:
    trust_registry: Path
    ledger: Path
    ledger_anchor: Path
    heartbeat: Path
    freeze: Path
    integrator_private_key: Path


def _public_key_der(public_key: str) -> bytes:
    result = subprocess.run(
        ["openssl", "pkey", "-pubin", "-in", public_key, "-outform", "DER"],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise ValueError("trust registry contains an unreadable public key")
    return result.stdout


def _validate_integrator_key_separation(registry: dict[str, Any]) -> None:
    keys = registry.get("ledger_keys")
    key_id = registry.get("integrator_key_id")
    if not isinstance(keys, dict) or not isinstance(key_id, str):
        raise TypeError("integrator trust registry is incomplete")
    integrator = keys.get(key_id)
    if not isinstance(integrator, dict) or not integrator.get("public_key"):
        raise ValueError("integrator trust registry key is missing")
    if integrator.get("can_resolve_pending") is True or integrator.get("can_authorize") is True:
        raise ValueError("integrator key has a reserved ledger capability")
    integrator_key = _public_key_der(integrator["public_key"])
    for other_id, entry in keys.items():
        if other_id == key_id or not isinstance(entry, dict):
            continue
        if ((entry.get("can_resolve_pending") is True or entry.get("can_authorize") is True)
                and entry.get("public_key")
                and _public_key_der(entry["public_key"]) == integrator_key):
            raise ValueError("integrator public key is shared with a reserved ledger authority")


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


def _heartbeat(path: Path, registry: dict[str, Any], now: datetime) -> dict[str, Any] | None:
    event = json.loads(path.read_text())
    key_id = registry["supervisor_key_id"]
    if event.get("key_id") != key_id or event.get("type") != "heartbeat":
        return None
    if not isinstance(event.get("state_sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", event["state_sha256"]):
        return None
    expiry = datetime.fromisoformat(event["expires_at"])
    issued = datetime.fromisoformat(event["issued_at"])
    sequence_path = path.with_suffix(path.suffix + ".sequence")
    prior = int(sequence_path.read_text()) if sequence_path.exists() else 0
    if (event.get("sequence", 0) <= prior or now >= expiry or issued > now.replace(microsecond=0) + __import__("datetime").timedelta(seconds=60)
            or (now - issued).total_seconds() > min(3600, registry.get("heartbeat_max_age_seconds", 3600))):
        return None
    signature = base64.b64decode(event["signature"], validate=True)
    signed = {k: v for k, v in event.items() if k != "signature"}
    import tempfile
    with tempfile.TemporaryDirectory() as directory:
        sig, msg = Path(directory) / "sig", Path(directory) / "msg"
        sig.write_bytes(signature); msg.write_bytes(canonical(signed))
        valid = subprocess.run(["openssl", "pkeyutl", "-verify", "-pubin", "-inkey",
            registry["supervisor_public_key"], "-sigfile", str(sig), "-in", str(msg), "-rawin"],
            check=False, capture_output=True).returncode == 0
    if valid:
        sequence_path.write_text(str(event["sequence"]))
    return event if valid else None


def promote(repo: Path, remote: str, auth: dict[str, Any], signature: str,
            trust_sources: TrustSources, message: str = "Governed integration",
            before_push=None, identity_provider=None, after_push=None,
            after_recheck=None,
            observed_repo: str | None = None, observed_pr_number: int | None = None,
            staged_commit: str | None = None,
            candidate_ref: str | None = None,
            now: Callable[[], datetime] = lambda: datetime.now(UTC)) -> str:
    if identity_provider is None:
        raise RuntimeError("identity provider is mandatory")
    if trust_sources.freeze.exists() or (repo / ".aao-freeze").exists():
        raise RuntimeError("integrator frozen")
    registry = json.loads(trust_sources.trust_registry.read_text())
    if not isinstance(observed_repo, str) or not observed_repo or not isinstance(observed_pr_number, int):
        raise ValueError("observed repository and PR number are required")
    ledger_keys = registry["ledger_keys"]
    _validate_integrator_key_separation(registry)
    rows = verify(trust_sources.ledger, ledger_keys)
    current_time = now()
    if current_time.tzinfo is None:
        raise ValueError("clock must return timezone-aware datetime")
    heartbeat = _heartbeat(trust_sources.heartbeat, registry, current_time)
    if heartbeat is None:
        raise ValueError("valid supervisor heartbeat unavailable")
    heartbeat_ok = True
    supervisor_head = heartbeat.get("ledger_head")
    supervisor_markers = heartbeat.get("pending_markers")
    if (not isinstance(supervisor_head, str) or not isinstance(supervisor_markers, dict) or
            any(not isinstance(candidate, str) or not isinstance(digests, list) or
                any(not isinstance(digest, str) for digest in digests)
                for candidate, digests in supervisor_markers.items())):
        raise ValueError("valid supervisor heartbeat unavailable: missing ledger custody state")
    terminal = rows[-1]["hash"] if rows else "0" * 64
    if terminal != supervisor_head:
        if supervisor_head == "0" * 64 or supervisor_head in {row["hash"] for row in rows}:
            raise ValueError("ledger not yet anchored")
        raise ValueError("ledger truncated or rewritten")
    try:
        markers = pending_vetoes(Path(str(trust_sources.ledger) + ".pending-vetoes"), auth["candidate_sha"],
                                 trust_sources.ledger.stat().st_uid)
    except (PendingVetoError, OSError, ValueError) as error:
        raise ValueError(f"pending vetoes cannot be verified: {error}") from error
    resolved: set[str] = set()
    for row in rows:
        if "resolves_pending" in row:
            values = row["resolves_pending"]
            if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
                raise ValueError("pending vetoes cannot be verified: malformed resolves_pending ledger field")
            key_entry = ledger_keys.get(row.get("key_id"))
            if not isinstance(key_entry, dict) or key_entry.get("can_resolve_pending") is not True:
                raise ValueError("resolves_pending signer is not an enabled authority")
            resolved.update(values)
    seen = set(supervisor_markers.get(auth["candidate_sha"], []))
    present = set(markers)
    deleted = seen - present - resolved
    if deleted:
        raise ValueError("pending veto marker deleted")
    if seen - resolved:
        raise ValueError("candidate has an unresolved pending veto")
    if any(digest not in resolved for digest in markers):
        raise ValueError("candidate has an unresolved pending veto")
    incident_resolvers = registry.get("incident_resolvers")
    if not isinstance(incident_resolvers, list) or any(
        row.get("type") == "incident-resolution" and row.get("key_id") not in incident_resolvers
        for row in rows
    ):
        raise ValueError("incident-resolution signer is not enabled in trust registry")
    if active_vetoes(rows, ledger_keys):
        raise ValueError("active ledger veto")
    if open_incidents(rows):
        raise RuntimeError("open ledger incident")
    ra = registry["ra_status"]
    ra01 = ra.get("RA-01") == "PASS"
    ra02 = ra.get("RA-02") == "PASS"
    ra03 = ra.get("RA-03") == "PASS"
    ra07 = ra.get("RA-07") == "PASS"
    ra09 = ra.get("RA-09") == "PASS"
    ref = auth["target_ref"]
    if ref not in registry["target_refs"]:
        raise ValueError("target ref not permitted")
    identity = identity_provider() if callable(identity_provider) else identity_provider
    if identity != registry["integrator_identity"]:
        raise RuntimeError("integrator identity mismatch")
    # R1 callers pass the authoritative remote URL directly. Legacy callers may
    # still pass a configured remote name; resolve only that form through the
    # repository config so a mirror's implicit `origin` is never substituted.
    is_explicit_url = (Path(remote).is_absolute() or "://" in remote or remote.startswith("git@"))
    remote_url = remote if is_explicit_url else _git(repo, "remote", "get-url", remote)
    remote_refs = subprocess.run(["git", "ls-remote", remote_url, ref],
                                 check=True, capture_output=True, text=True).stdout.splitlines()
    base = next((parts[0] for line in remote_refs
                 if len(parts := line.split()) == 2 and parts[1] == ref), None)
    head_ref = candidate_ref or auth.get("candidate_ref") or "refs/heads/candidate"
    candidates = subprocess.run(["git", "ls-remote", remote_url, head_ref], check=True,
                                capture_output=True, text=True).stdout.splitlines()
    head = next((line.split()[0] for line in candidates if len(line.split()) == 2 and line.split()[1] == head_ref), None)
    # Candidate is identified by signed SHA; require that object to be present locally and reachable remotely.
    if not base or not head:
        raise ValueError("remote base or candidate unavailable")
    try:
        subprocess.run(["git", "-C", str(repo), "cat-file", "-e", f"{head}^{{commit}}"],
                       check=True, capture_output=True)
    except (subprocess.CalledProcessError, OSError) as error:
        raise ValueError("changed paths unavailable: local head commit missing") from error
    version = _git(repo, "--version").removeprefix("git version ")
    has_base = subprocess.run(["git", "-C", str(repo), "cat-file", "-e", f"{base}^{{commit}}"],
                              check=False, capture_output=True).returncode == 0
    if not has_base:
        raise ValueError("changed paths unavailable: local base commit missing")
    try:
        changed = git_changed_paths(repo, base, head)
    except (subprocess.CalledProcessError, OSError) as error:
        raise ValueError(f"changed paths unavailable: {error}") from error
    state = {**registry, "repo": observed_repo, "pr_number": observed_pr_number,
        "pr_head": head, "target_ref": ref, "target_sha": base,
        "merge_tree_sha": auth["merge_result_tree_sha"], "now": current_time.isoformat(),
        "heartbeat_valid": heartbeat_ok, "ra03_pass": ra03, "ra09_pass": ra09,
        "ra02_pass": ra02, "ledger": {"veto": bool(active_vetoes(rows, ledger_keys))},
        "git_version": version, "changed_paths": changed}
    reasons = validate(auth, signature, state)
    if not all((ra01, ra02, ra03, ra07, ra09)):
        reasons.append("required RA status pending")
    if reasons:
        raise ValueError("authorization rejected: " + "; ".join(reasons))
    tree = _git(repo, "merge-tree", "--write-tree", base, head).splitlines()[0]
    if tree != auth["merge_result_tree_sha"]:
        raise ValueError("computed merge tree differs from authorization")
    expected_parents = auth["expected_parents"]
    if staged_commit is None:
        commit = subprocess.run(["git", "-C", str(repo), "commit-tree", tree,
            *[arg for parent in expected_parents for arg in ("-p", parent)]],
            input=message + "\n", check=True, capture_output=True, text=True).stdout.strip()
    else:
        try:
            staged_tree = _git(repo, "show", "-s", "--format=%T", staged_commit)
            staged_parents = _git(repo, "show", "-s", "--format=%P", staged_commit).split()
        except (subprocess.CalledProcessError, OSError) as error:
            raise ValueError("staged commit is unavailable") from error
        if staged_tree != tree:
            raise ValueError("staged commit tree differs from authorized merge tree")
        if staged_parents != expected_parents:
            raise ValueError("staged commit parents differ from authorized parents")
        commit = staged_commit
    if not identity_provider.push_identity(ref, base, commit):
        raise RuntimeError("unattributed push")
    if before_push:
        before_push()
    # Re-read the remote immediately before the conditional push.
    latest_lines = subprocess.run(["git", "ls-remote", remote_url, ref], check=True,
                                  capture_output=True, text=True).stdout.splitlines()
    latest = next((parts[0] for line in latest_lines
                   if len(parts := line.split()) == 2 and parts[1] == ref), None)
    if latest is None:
        raise RuntimeError("remote base ref unavailable")
    if latest != base:
        raise RuntimeError("remote base moved")
    if after_recheck:
        after_recheck()
    result = subprocess.run(["git", "-C", str(repo), "push", "--atomic",
        f"--force-with-lease={ref}:{base}", remote_url, f"{commit}:{ref}"], check=False, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError("conditional push rejected; no fallback: " + result.stderr)
    expected_tree = auth["merge_result_tree_sha"]
    observed: dict[str, Any] = {"sha": None, "tree_sha": None, "parents": None}
    try:
        if after_push:
            after_push()
        listing = subprocess.run(["git", "ls-remote", remote_url, ref], check=True,
                                 capture_output=True, text=True).stdout.splitlines()
        observed["sha"] = next((parts[0] for line in listing
                                 if len(parts := line.split()) == 2 and parts[1] == ref), None)
        if observed["sha"] is None:
            raise RuntimeError("published remote ref is missing")
        _git(repo, "cat-file", "-e", f"{observed['sha']}^{{commit}}")
        observed["tree_sha"] = _git(repo, "show", "-s", "--format=%T", observed["sha"])
        observed["parents"] = _git(repo, "show", "-s", "--format=%P", observed["sha"]).split()
        if (observed["sha"] != commit or observed["tree_sha"] != expected_tree or
                observed["parents"] != expected_parents):
            raise RuntimeError("published ref SHA, tree, or parents differ from authorized promotion")
    except Exception as error:
        detail = f"post-push verification failed: {type(error).__name__}: {error}"
        trust_sources.freeze.write_text(
            f"{detail}; intended_sha={commit}; observed_sha={observed['sha']}\n"
        )
        try:
            incident = append(trust_sources.ledger, {
                "type": "incident",
                "id": f"post-push-{commit}",
                "target_ref": ref,
                "detail": detail,
                "intended_sha": commit,
                "observed_sha": observed["sha"],
                "intended_tree_sha": expected_tree,
                "observed_tree_sha": observed["tree_sha"],
                "intended_parents": expected_parents,
                "observed_parents": observed["parents"],
            }, registry["integrator_key_id"], str(trust_sources.integrator_private_key), ledger_keys,
                rows[-1]["hash"] if rows else "0" * 64)
            trust_sources.ledger_anchor.write_text(incident["hash"])
        except Exception as ledger_error:  # noqa: BLE001 - preserve freeze if recording itself fails.
            raise RuntimeError(f"post-publication incident; frozen; ledger recording failed: {ledger_error}") from error
        raise RuntimeError("post-publication incident; integrator frozen") from error
    return commit
