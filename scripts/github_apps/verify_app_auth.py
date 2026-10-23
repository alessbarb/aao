#!/usr/bin/python3 -I
"""Verify one GitHub App's API authentication as its own Linux account (P2). Read-only on GitHub.

Run once per App, as the App's uid, from the root-owned copy installed in /opt/aao-p2:
    sudo -u <linux_uid> -H /usr/bin/python3 -I /opt/aao-p2/verify_app_auth.py <app>
Reads app_id, installation_id, linux_uid and key_file from the reviewed registry next to this script,
and the expected permissions from the reviewed manifest in ./github-apps/. Prints one JSON record.
Never prints the private key, the JWT or the installation token; the token is revoked before exit.
Exit 0 only if every check passes.
"""
from __future__ import annotations

import base64
import json
import os
import pwd
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.github.com"
HERE = Path(__file__).resolve().parent
REGISTRY = HERE / "aao-github-apps-registry.json"
MANIFESTS = HERE / "github-apps"
# Where each App may be installed (P2 design): implementers only on their forks, never on the canonical repo.
CANONICAL_ONLY = {"aao-integrator", "aao-auditor", "aao-auditor-alt", "aao-supervisor", "aao-notifier", "aao-pm"}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # never forward a bearer credential


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _jwt(app_id: int, key: bytes) -> str:
    now = int(time.time())
    head = _b64(b'{"alg":"RS256","typ":"JWT"}')
    body = _b64(json.dumps({"iat": now - 60, "exp": now + 300, "iss": str(app_id)}).encode())
    signing = f"{head}.{body}".encode()
    # Key goes to openssl via an inherited pipe fd, never via argv or a temp file.
    r, w = os.pipe()
    os.write(w, key)
    os.close(w)
    try:
        sig = subprocess.run(["openssl", "dgst", "-sha256", "-sign", f"/dev/fd/{r}"], input=signing,
                             capture_output=True, check=True, pass_fds=(r,)).stdout
    finally:
        os.close(r)
    return f"{signing.decode()}.{_b64(sig)}"


def _call(method: str, path: str, token: str) -> tuple[int, object]:
    req = urllib.request.Request(API + path, method=method, headers={
        "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"})
    try:
        with urllib.request.build_opener(_NoRedirect()).open(req, timeout=20) as res:
            raw, status = res.read(), res.status
    except urllib.error.HTTPError as exc:
        raw, status = exc.read(), exc.code
    try:
        return status, json.loads(raw) if raw else None
    except ValueError:
        return status, None


def _err(status: int, body: object) -> str:
    return f"HTTP {status}"  # GitHub's message is not echoed: the output must hold only our own fields


def _trusted(path: Path) -> bool:
    """Registry and manifests decide which key is read and what is expected: root-owned, not group/other-writable."""
    st = os.stat(path, follow_symlinks=False)
    return st.st_uid == 0 and not st.st_mode & 0o022 and not stat.S_ISLNK(st.st_mode)


def _read_key(path: Path, uid: int, home: Path) -> bytes:
    if path.parent.resolve() != (home / ".config" / "aao").resolve() or path.parent.resolve() != path.parent:
        raise ValueError("key_file is not directly under the role's ~/.config/aao")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid != uid or st.st_mode & 0o777 != 0o600:
            raise ValueError("key_file must be a regular file owned by the role uid with mode 0600")
        with os.fdopen(fd, "rb", closefd=False) as handle:
            return handle.read()
    finally:
        os.close(fd)


def verify(app: str) -> tuple[bool, dict]:
    manifest = MANIFESTS / f"{app}.json"
    if not all(_trusted(p) for p in (HERE, REGISTRY, MANIFESTS, manifest)):
        return False, {"app": app, "error": "registry/manifests must be root-owned and not group/other-writable"}
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    entry = next((a for a in registry["apps"] if a["name"] == app), None)
    if entry is None:
        return False, {"app": app, "error": "app not in registry"}
    me = pwd.getpwuid(os.getuid())
    rec: dict = {"app": app, "app_id": entry["app_id"], "installation_id": entry["installation_id"],
                 "linux_uid": me.pw_name, "checks": {}}
    checks = rec["checks"]
    if os.getuid() == 0 or me.pw_name != entry["linux_uid"]:
        return False, rec | {"error": f"must run as {entry['linux_uid']}, not {me.pw_name}"}
    if Path(entry["key_file"]).name != f"{app}.pem":
        return False, rec | {"error": f"key_file must be named {app}.pem"}
    try:
        key = _read_key(Path(entry["key_file"]), me.pw_uid, Path(me.pw_dir))
        jwt = _jwt(int(entry["app_id"]), key)
        del key
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        return False, rec | {"error": f"key/JWT: {type(exc).__name__}: {exc}" if isinstance(exc, ValueError)
                             else f"key/JWT: {type(exc).__name__}"}
    want = json.loads(manifest.read_text(encoding="utf-8"))["default_permissions"]

    status, body = _call("GET", "/app", jwt)
    if status != 200 or not isinstance(body, dict):
        return False, rec | {"error": "GET /app " + _err(status, body)}
    rec |= {"slug": body.get("slug"), "owner": (body.get("owner") or {}).get("login"),
            "app_permissions": body.get("permissions"), "events": body.get("events")}
    checks["jwt_app_id"] = body.get("id") == entry["app_id"]
    checks["slug_equals_name"] = body.get("slug") == app
    checks["app_permissions_match_manifest"] = body.get("permissions") == want

    iid = entry["installation_id"]
    status, inst = _call("GET", f"/app/installations/{iid}", jwt)
    if status != 200 or not isinstance(inst, dict):
        return False, rec | {"error": f"GET installation {_err(status, inst)}"}
    rec |= {"account": (inst.get("account") or {}).get("login"),
            "repository_selection": inst.get("repository_selection"),
            "installation_permissions": inst.get("permissions"), "suspended_at": inst.get("suspended_at")}
    checks["installation_belongs_to_app"] = inst.get("app_id") == entry["app_id"]
    checks["installation_not_suspended"] = inst.get("suspended_at") is None
    checks["installation_permissions_match_manifest"] = inst.get("permissions") == want

    status, tok = _call("POST", f"/app/installations/{iid}/access_tokens", jwt)
    token = tok.pop("token", None) if isinstance(tok, dict) else None
    checks["installation_token_issued"] = status == 201 and bool(token)
    if not token:
        return False, rec | {"error": "access_tokens " + _err(status, tok)}
    repos: list[str] = []
    canonical = registry["canonical_repository"]
    forks_of_canonical: list[bool] = []
    try:
        page = 1
        while True:
            status, body = _call("GET", f"/installation/repositories?per_page=100&page={page}", token)
            if status != 200 or not isinstance(body, dict) or not isinstance(body.get("total_count"), int) \
                    or not isinstance(body.get("repositories"), list):
                rec["error"] = "GET /installation/repositories " + _err(status, body)
                break
            repos += [r["full_name"] for r in body["repositories"]]
            if len(repos) == body["total_count"]:
                break
            if not body["repositories"] or len(repos) > body["total_count"]:
                rec["error"] = "repository listing inconsistent with total_count"
                break
            page += 1
        if app not in CANONICAL_ONLY and "error" not in rec:
            for name in repos:  # each implementer repo must be a fork whose parent is the canonical repo
                status, body = _call("GET", f"/repos/{name}", token)
                forks_of_canonical.append(status == 200 and isinstance(body, dict) and body.get("fork") is True
                                          and (body.get("parent") or {}).get("full_name") == canonical)
    finally:
        revoke, _ = _call("DELETE", "/installation/token", token)
        del token
    rec["accessible_repositories"] = sorted(repos)
    checks["token_revoked"] = revoke == 204
    if app in CANONICAL_ONLY:
        checks["access_is_canonical_only"] = rec["accessible_repositories"] == [canonical] \
            and rec["repository_selection"] == "selected"
    else:
        checks["implementer_cannot_reach_canonical"] = canonical not in rec["accessible_repositories"]
        checks["implementer_only_forks_of_canonical"] = bool(repos) and rec["repository_selection"] == "selected" \
            and all(forks_of_canonical) and len(forks_of_canonical) == len(repos)
    return "error" not in rec and all(checks.values()), rec


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    ok, rec = verify(sys.argv[1])
    rec["result"] = "PASS" if ok else "FAIL"
    rec["checked_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    print(json.dumps(rec, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
