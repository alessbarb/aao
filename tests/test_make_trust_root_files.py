import importlib.util
import json
import os
import subprocess
from pathlib import Path

from aao.manifest_audit import load_anchor
from aao.supervisor_service import load_config

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("maker", ROOT / "scripts/make_trust_root_files.py")
maker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(maker)
REV = "97ad4f13655aae2b736c7ba6b3d8d666e51d4680"


def _pub(tmp_path, name):
    key = tmp_path / f"{name}.pem"
    subprocess.run(["openssl", "genpkey", "-algorithm", "ed25519", "-out", str(key)], check=True)
    return subprocess.run(["openssl", "pkey", "-in", str(key), "-pubout"], check=True,
                          capture_output=True, text=True).stdout


def test_generated_anchor_loads_with_the_real_loader(tmp_path):
    template = json.loads((ROOT / "docs/audit-runs/20261019-provisional/policy.json").read_text())
    files = maker.build(REV, template, _pub(tmp_path, "a"), _pub(tmp_path, "s"), os.getuid(), ["alessbarb"])
    trust = tmp_path / "trust"
    trust.mkdir(mode=0o755)
    policy = trust / "policy.json"
    policy.write_text(json.dumps(files["policy.json"]))
    policy.chmod(0o644)
    anchor = {**files["trust-anchor.json"], "policy_path": str(policy)}
    anchor_path = trust / "anchor.json"
    anchor_path.write_text(json.dumps(anchor))
    anchor_path.chmod(0o644)
    loaded = load_anchor(anchor_path, (os.getuid(),))
    assert loaded["policy"]["trusted_auditor_revisions"] == [REV]
    assert loaded["supervisor_intake_socket"] == "/run/aao-veto-intake/veto.sock"


def test_generated_supervisor_config_loads(tmp_path):
    files = maker.build(REV, {"version": "x"}, "A", "S", 1005, [])
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps({"ledger_keys": {"k": {}}, "integrator_key_id": "k"}))
    registry.chmod(0o644)
    config = tmp_path / "config.json"
    config.write_text(json.dumps({**files["supervisor-config.json"], "trust_registry": str(registry)}))
    config.chmod(0o644)
    assert load_config(config, (os.getuid(),), (os.getuid(),))["integrator_key_id"] == "k"


def test_auditor_cannot_be_developer():
    try:
        maker.build(REV, {}, "A", "S", 1005, ["aao-auditor"])
    except ValueError:
        return
    raise AssertionError("auditor accepted as developer")
