"""Fail-closed governed promotion using locally provisioned trust sources."""
from __future__ import annotations

import base64
import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aao.governance_ledger import active_vetoes, verify
from aao.integration_authorization import canonical, validate


@dataclass(frozen=True)
class TrustSources:
    trust_registry: Path
    ledger: Path
    ledger_anchor: Path
    heartbeat: Path
    freeze: Path


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


def _heartbeat(path: Path, registry: dict[str, Any], now: datetime) -> bool:
    event = json.loads(path.read_text())
    key_id = registry["supervisor_key_id"]
    if event.get("key_id") != key_id or event.get("type") != "heartbeat":
        return False
    expiry = datetime.fromisoformat(event["expires_at"])
    issued = datetime.fromisoformat(event["issued_at"])
    if now >= expiry or (now - issued).total_seconds() > registry["heartbeat_max_age_seconds"]:
        return False
    signature = base64.b64decode(event["signature"], validate=True)
    signed = {k: v for k, v in event.items() if k != "signature"}
    import tempfile
    with tempfile.TemporaryDirectory() as directory:
        sig, msg = Path(directory) / "sig", Path(directory) / "msg"
        sig.write_bytes(signature); msg.write_bytes(canonical(signed))
        return subprocess.run(["openssl", "pkeyutl", "-verify", "-pubin", "-inkey",
            registry["supervisor_public_key"], "-sigfile", str(sig), "-in", str(msg), "-rawin"],
            check=False, capture_output=True).returncode == 0


def promote(repo: Path, remote: str, auth: dict[str, Any], signature: str,
            trust_sources: TrustSources, message: str = "Governed integration",
            before_push=None, identity_provider=None, after_push=None,
            now: Callable[[], datetime] = lambda: datetime.now(UTC)) -> str:
    if identity_provider is None:
        raise RuntimeError("identity provider is mandatory")
    if trust_sources.freeze.exists() or (repo / ".aao-freeze").exists():
        raise RuntimeError("integrator frozen")
    registry = json.loads(trust_sources.trust_registry.read_text())
    ledger_keys = registry["ledger_keys"]
    anchor = trust_sources.ledger_anchor.read_text().strip()
    rows = verify(trust_sources.ledger, ledger_keys, anchor)
    if active_vetoes(rows, ledger_keys):
        raise ValueError("active ledger veto")
    current_time = now()
    if current_time.tzinfo is None:
        raise ValueError("clock must return timezone-aware datetime")
    heartbeat_ok = _heartbeat(trust_sources.heartbeat, registry, current_time)
    ra = registry["ra_status"]
    ra02 = ra.get("RA-02") == "PASS"
    ra03 = ra.get("RA-03") == "PASS"
    ra09 = ra.get("RA-09") == "PASS"
    ref = auth["target_ref"]
    if ref not in registry["target_refs"]:
        raise ValueError("target ref not permitted")
    identity = identity_provider() if callable(identity_provider) else identity_provider
    if identity != registry["integrator_identity"]:
        raise RuntimeError("integrator identity mismatch")
    remote_url = _git(repo, "remote", "get-url", remote)
    remote_refs = dict(line.split()[:2][::-1] for line in subprocess.run(
        ["git", "ls-remote", remote_url, ref],
        check=True, capture_output=True, text=True).stdout.splitlines())
    base = remote_refs.get(ref)
    head = auth["candidate_sha"]
    # Candidate is identified by signed SHA; require that object to be present locally and reachable remotely.
    if not base or _git(repo, "cat-file", "-e", f"{head}^{{commit}}") is None:
        raise ValueError("remote base or candidate unavailable")
    version = _git(repo, "--version").removeprefix("git version ")
    state = {**registry, "repo": auth["repo"], "pr_number": auth["pr_number"],
        "pr_head": head, "target_ref": ref, "target_sha": base,
        "merge_tree_sha": auth["merge_result_tree_sha"], "now": current_time.isoformat(),
        "heartbeat_valid": heartbeat_ok, "ra03_pass": ra03, "ra09_pass": ra09,
        "ra02_pass": ra02, "ledger": {"veto": bool(active_vetoes(rows, ledger_keys))},
        "git_version": version}
    reasons = validate(auth, signature, state)
    if not ra02 or not ra03 or not ra09:
        reasons.append("required RA status pending")
    if reasons:
        raise ValueError("authorization rejected: " + "; ".join(reasons))
    tree = _git(repo, "merge-tree", "--write-tree", base, head).splitlines()[0]
    if tree != auth["merge_result_tree_sha"]:
        raise ValueError("computed merge tree differs from authorization")
    commit = subprocess.run(["git", "-C", str(repo), "commit-tree", tree, "-p", base, "-p", head],
        input=message + "\n", check=True, capture_output=True, text=True).stdout.strip()
    if not identity_provider.push_identity(ref, base, commit):
        raise RuntimeError("unattributed push")
    if before_push:
        before_push()
    # Re-read the remote immediately before the conditional push.
    latest = subprocess.run(["git", "ls-remote", remote_url, ref], check=True, capture_output=True, text=True).stdout.split()[0]
    if latest != base:
        raise RuntimeError("remote base moved")
    result = subprocess.run(["git", "-C", str(repo), "push", "--atomic",
        f"--force-with-lease={ref}:{base}", remote_url, f"{commit}:{ref}"], check=False, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError("conditional push rejected; no fallback: " + result.stderr)
    if after_push:
        after_push()
    actual = subprocess.run(["git", "ls-remote", remote_url, ref], check=True, capture_output=True, text=True).stdout.split()[0]
    if actual != commit:
        trust_sources.freeze.write_text(f"published ref divergence {actual}\n")
        raise RuntimeError("post-publication divergence; integrator frozen")
    return commit
