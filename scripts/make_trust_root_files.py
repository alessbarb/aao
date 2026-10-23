#!/usr/bin/python3 -I
"""Generate the trust anchor, the pinned policy and the supervisor config for one auditor revision.

Writes into --out (a fresh directory); the CEO then installs each file with the owner/mode in
docs/procedures/TRUST_ROOT_HOST_INSTALL.md. Pure: reads only the public keys and the policy template.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pwd
import re
from pathlib import Path

INTAKE_SOCKET = "/run/aao-veto-intake/veto.sock"
HEARTBEAT = "/var/lib/aao-heartbeat/heartbeat.json"
POLICY_PATH = "/var/lib/aao-auditor/policy.json"
LEDGER = "/var/lib/aao-auditor/ledger/governance.jsonl"


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def build(revision: str, template: dict, auditor_pub: str, supervisor_pub: str, auditor_uid: int,
          developer_users: list[str], supervisor_key_id: str = "aao-supervisor") -> dict[str, dict]:
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("revision must be a full lowercase SHA")
    policy = {**template, "auditor_id": "aao-auditor", "auditor_os_user": "aao-auditor",
              "developer_os_users": sorted(set(developer_users)), "trusted_auditor_revisions": [revision]}
    if "aao-auditor" in policy["developer_os_users"]:
        raise ValueError("the auditor account cannot be a developer account")
    anchor = {"schema": "aao.audit-trust-anchor.v1", "policy_path": POLICY_PATH,
              "policy_sha256": hashlib.sha256(canonical(policy)).hexdigest(), "auditor_uid": auditor_uid,
              "auditor_public_key": auditor_pub, "ledger_path": LEDGER,
              "ledger_anchor_path": "/etc/aao-audit/ledger.anchor", "attribution_path": "/etc/aao-audit/attribution.json",
              "supervisor_public_key": supervisor_pub, "supervisor_key_id": supervisor_key_id,
              "supervisor_heartbeat_path": HEARTBEAT, "supervisor_intake_socket": INTAKE_SOCKET}
    config = {"schema": "aao.supervisor-config.v1", "auditor_uid": auditor_uid, "ledger_path": LEDGER,
              "state_path": "/var/lib/aao-supervisor/state.json", "heartbeat_path": HEARTBEAT,
              "intake_socket": INTAKE_SOCKET, "private_key": "/var/lib/aao-supervisor/keys/supervisor-ed25519.pem",
              "key_id": supervisor_key_id, "trust_registry": "/srv/aao/trust/registry.json", "validity_seconds": 600}
    return {"policy.json": policy, "trust-anchor.json": anchor, "supervisor-config.json": config}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--revision", required=True)
    parser.add_argument("--policy-template", type=Path, required=True)
    parser.add_argument("--auditor-public-key", type=Path, default=Path("/srv/aao/trust/keys/aao-auditor-ed25519.pub"))
    parser.add_argument("--supervisor-public-key", type=Path,
                        default=Path("/srv/aao/trust/keys/aao-supervisor-ed25519.pub"))
    parser.add_argument("--developer", action="append", default=["alessbarb", "aao-impl-codex", "aao-impl-claude",
                                                                 "aao-impl-ag", "aao-pm"])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    files = build(args.revision, json.loads(args.policy_template.read_text()), args.auditor_public_key.read_text(),
                  args.supervisor_public_key.read_text(), pwd.getpwnam("aao-auditor").pw_uid, args.developer)
    args.out.mkdir(mode=0o700)
    for name, value in files.items():
        (args.out / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
        print(f"{name} sha256={hashlib.sha256((args.out / name).read_bytes()).hexdigest()}")
    print(f"policy canonical sha256 (pinned in the anchor) = {files['trust-anchor.json']['policy_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
