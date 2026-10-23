#!/usr/bin/env python3
"""Write a local HTML form that registers one AAO GitHub App from its manifest (P2).

Run as the CEO (it only writes an HTML file; no credentials involved):
    python3 scripts/github_apps/create_app_form.py aao-integrator
Open the printed file in the browser and click "Create GitHub App".
GitHub then redirects to http://127.0.0.1:9/?code=...  (nothing listens there):
copy the `code` value from the address bar and give it to the role account:
    sudo -u aao-integrator -H python3 /opt/aao-p2/exchange_manifest_code.py aao-integrator <code>
The private key is returned only to that call, so it never touches the CEO account.
The code expires after one hour and can be used once.
"""
import html
import json
import secrets
import sys
from pathlib import Path

MANIFESTS = Path(__file__).resolve().parents[2] / "docs" / "proposals" / "github-apps"


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    name = sys.argv[1]
    manifest = json.loads((MANIFESTS / f"{name}.json").read_text(encoding="utf-8"))
    manifest["redirect_url"] = "http://127.0.0.1:9/"
    state = secrets.token_urlsafe(16)
    page = Path(f"/tmp/aao-create-{name}.html")
    page.write_text(
        "<!doctype html><meta charset=utf-8><title>Create " + html.escape(name) + "</title>"
        "<p>Creating GitHub App <b>" + html.escape(name) + "</b> under your account. State: "
        + state + "</p>"
        '<form action="https://github.com/settings/apps/new?state=' + state + '" method="post">'
        '<input type="hidden" name="manifest" value="' + html.escape(json.dumps(manifest)) + '">'
        '<button type="submit">Create GitHub App</button></form>',
        encoding="utf-8",
    )
    page.chmod(0o600)
    print(f"Open {page} and check the redirect carries state={state}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
