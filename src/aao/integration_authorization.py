"""Signed, canonical integration authorizations and fail-closed validation."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta
from typing import Any

FIELDS = (
    "repo",
    "pr_number",
    "candidate_sha",
    "base_sha",
    "target_ref",
    "merge_method",
    "merge_result_tree_sha",
    "risk_class",
    "assurance_level",
    "policy_id",
    "policy_sha256",
    "protected_paths_sha256",
    "expected_parents",
    "git_version",
    "auditor_id",
    "auditor_key_id",
    "auditor_code_revision",
    "attribution",
    "checks_executed",
    "scope",
    "known_limitations",
    "residual_risks",
    "permitted_operations",
    "prohibited_operations",
    "findings",
    "expediente_sha256",
    "verdict",
    "issued_at",
    "expires_at",
)


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sign(document: dict[str, Any], private_key: str) -> str:
    """Return base64 Ed25519 signature for the canonical document via OpenSSL."""
    import base64
    import tempfile
    from pathlib import Path

    payload = {key: document[key] for key in FIELDS}
    with tempfile.TemporaryDirectory() as directory:
        message = Path(directory) / "message"
        message.write_bytes(canonical(payload))
        signature = subprocess.run(
            ["openssl", "pkeyutl", "-sign", "-rawin", "-inkey", private_key, "-in", str(message)],
            check=True,
            capture_output=True,
        ).stdout
    return base64.b64encode(signature).decode()


def verify_signature(document: dict[str, Any], signature: str, public_key: str) -> bool:
    import base64
    import tempfile

    try:
        with tempfile.TemporaryDirectory() as directory:
            from pathlib import Path

            sig, msg = Path(directory) / "sig", Path(directory) / "msg"
            sig.write_bytes(base64.b64decode(signature, validate=True))
            msg.write_bytes(canonical({key: document[key] for key in FIELDS}))
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
        return True
    except (KeyError, ValueError, OSError, subprocess.CalledProcessError):
        return False


def validate(document: dict[str, Any], signature: str, state: dict[str, Any]) -> list[str]:
    """Pure decision over supplied snapshot; missing evidence always rejects."""
    reasons: list[str] = []
    if any(field not in document for field in FIELDS):
        reasons.append("authorization fields missing")
    trusted_identities = state.get("trusted_auditors")
    key_ids = trusted_identities.get(document.get("auditor_id")) if isinstance(trusted_identities, dict) else None
    key_id = document.get("auditor_key_id")
    key = state.get("trusted_keys", {}).get(key_id) if isinstance(key_id, str) else None
    if not isinstance(key_ids, (list, tuple, set)) or key_id not in key_ids:
        reasons.append("auditor key does not belong to auditor")
    if not key or document.get("auditor_key_id") in state.get("revoked_keys", []):
        reasons.append("untrusted or revoked key")
    elif not verify_signature(document, signature, key):
        reasons.append("invalid signature")
    if document.get("repo") != state.get("repo") or document.get("pr_number") != state.get(
        "pr_number"
    ):
        reasons.append("repository or PR mismatch")
    if document.get("candidate_sha") != state.get("pr_head"):
        reasons.append("PR head mismatch")
    if document.get("target_ref") != state.get("target_ref") or document.get(
        "base_sha"
    ) != state.get("target_sha"):
        reasons.append("target ref or base mismatch")
    if document.get("merge_result_tree_sha") != state.get("merge_tree_sha"):
        reasons.append("merge tree mismatch")
    if document.get("policy_sha256") != state.get("policy_sha256"):
        reasons.append("policy mismatch")
    attribution = document.get("attribution")
    authors = {entry.get("principal") for entry in attribution if isinstance(entry, dict)} if isinstance(attribution, list) else set()
    if document.get("auditor_id") in authors or document.get("auditor_id") in state.get("recused_auditors", []):
        reasons.append("auditor recused")
    if document.get("risk_class") == "R2" and any(
        state.get("auditor_models", {}).get(document.get("auditor_id"))
        == state.get("author_models", {}).get(author)
        for author in authors
    ):
        reasons.append("auditor model matches author model")
    if document.get("auditor_code_revision") not in state.get("trusted_auditor_revisions", []):
        reasons.append("auditor revision untrusted")
    enabled = state.get("enabled_risk_classes")
    if not isinstance(enabled, (list, tuple, set)) or document.get("risk_class") not in enabled:
        reasons.append("auditor not enabled for risk class")
    if not isinstance(state.get("policy_id"), str) or document.get("policy_id") != state.get("policy_id"):
        reasons.append("policy id mismatch")
    checks_value = document.get("checks_executed")
    checks = {c.get("name") for c in checks_value if isinstance(c, dict) and c.get("result") == "PASS" and c.get("evidence_sha256")} if isinstance(checks_value, list) else set()
    if not set(state.get("required_checks", [])).issubset(checks):
        reasons.append("required checks/evidence missing")
    try:
        now = datetime.fromisoformat(state["now"])
        issued = datetime.fromisoformat(document["issued_at"])
        expires = datetime.fromisoformat(document["expires_at"])
        if now.tzinfo is None or issued.tzinfo is None or expires.tzinfo is None:
            raise ValueError("timezone required")
        if document.get("verdict") != "APPROVE" or now >= expires:
            reasons.append("verdict not APPROVE or expired")
        if expires - issued > timedelta(hours=72):
            reasons.append("authorization validity exceeds 72 hours")
    except (KeyError, ValueError, TypeError):
        reasons.append("invalid expiration")
    ledger = state.get("ledger", {})
    if ledger.get("suspended") or ledger.get("veto"):
        reasons.append("suspended or vetoed")
    if not state.get("heartbeat_valid"):
        reasons.append("valid supervisor heartbeat unavailable")
    if not state.get("ra03_pass") or not state.get("ra09_pass"):
        reasons.append("RA-03/RA-09 evidence absent")
    if state.get("attribution_resolved") is not True:
        reasons.append("actor attribution inconclusive")
    if state.get("ci_candidate_sha") != document.get("candidate_sha"):
        reasons.append("CI evidence is for another candidate")
    if state.get("protected_paths_match") is not True:
        reasons.append("protected paths digest mismatch")
    try:
        if now < issued:
            reasons.append("authorization issued in the future")
    except (UnboundLocalError, TypeError):
        reasons.append("invalid issue time")
    if type(document.get("pr_number")) is not int:
        reasons.append("invalid PR number")
    return reasons
