#!/usr/bin/env python3
"""Exchange a GitHub App manifest code for the App credentials, as the role account (P2).

Run ONLY as the role that will own the App, e.g.:
    sudo -u aao-integrator -H python3 /opt/aao-p2/exchange_manifest_code.py aao-integrator <code>
Stores the private key in ~/.config/aao/<app>.pem (0600, created exclusively) and
non-secret metadata in ~/.config/aao/<app>.json. Never prints the key, the client
secret or the webhook secret. Refuses to run as the CEO or as root.
"""
import json
import os
import pwd
import sys
import urllib.request
from pathlib import Path

API = os.environ.get("AAO_GITHUB_API", "https://api.github.com")
# Reviewed manifests, installed root-owned next to this script (procedure step 0).
MANIFESTS = Path(__file__).resolve().parent / "github-apps"
ROLE_FOR_APP = {"aao-integrator": "aao-integrator", "aao-auditor": "aao-auditor",
                "aao-auditor-alt": "aao-auditor-alt", "aao-supervisor": "aao-supervisor",
                "aao-notifier": "aao-notifier", "aao-pm": "aao-pm", "aao-impl-codex": "aao-impl-codex",
                "aao-impl-claude": "aao-impl-claude", "aao-impl-ag": "aao-impl-ag",
                # Disposable A-14 probe: its own uid, created by the CEO only for the trial.
                "aao-probe-noworkflows": "aao-probe-noworkflows"}


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    app, code = sys.argv[1], sys.argv[2]
    user = pwd.getpwuid(os.geteuid()).pw_name
    if os.geteuid() == 0 or ROLE_FOR_APP.get(app) != user:
        print(f"refusing: {app} must be exchanged by its role account, not {user}", file=sys.stderr)
        return 1
    # Read the reviewed manifest BEFORE using the single-use code, so a missing manifest never burns it.
    try:
        expected = json.loads((MANIFESTS / f"{app}.json").read_text(encoding="utf-8"))["default_permissions"]
    except (OSError, ValueError, KeyError) as error:
        print(f"refusing: reviewed manifest for {app} unavailable in {MANIFESTS} ({error}); code not used",
              file=sys.stderr)
        return 1
    request = urllib.request.Request(f"{API}/app-manifests/{code}/conversions", method="POST",
                                     headers={"Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.loads(response.read())
    if data.get("slug") != app and data.get("name") != app:
        print(f"refusing: GitHub returned app {data.get('slug')!r}, expected {app!r}", file=sys.stderr)
        return 1
    if data.get("permissions") != expected:
        # The form is a local file and could have been altered: never keep a key for an App whose
        # permissions differ from the reviewed manifest. The App must be deleted and recreated.
        print(f"refusing: App permissions {data.get('permissions')} differ from the reviewed manifest "
              f"{expected}; key NOT stored. Delete the App on GitHub and recreate it.", file=sys.stderr)
        return 1
    directory = Path.home() / ".config" / "aao"
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    directory.chmod(0o700)
    key = directory / f"{app}.pem"
    descriptor = os.open(key, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="ascii") as handle:
        handle.write(data["pem"])
    meta = {k: data.get(k) for k in ("id", "slug", "name", "owner", "html_url", "permissions")}
    meta["owner"] = (data.get("owner") or {}).get("login")
    (directory / f"{app}.json").write_text(json.dumps(meta, indent=1) + "\n", encoding="utf-8")
    print(f"stored key for {app} (app id {data.get('id')}) at {key} (0600); secrets not printed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
