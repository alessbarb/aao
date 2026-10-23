from __future__ import annotations

import base64
import json
import os
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import ClassVar
from urllib.parse import urlparse

import pytest

from aao import github_app_auth as auth
from aao import github_trial as trial


class FakeGitHub(BaseHTTPRequestHandler):
    calls: ClassVar[list] = []
    responses: ClassVar[dict] = {}

    def log_message(self, *_args):
        return

    def do_GET(self):
        self._reply("GET", self.path)

    def do_POST(self):
        self._reply("POST", self.path)

    def do_PUT(self):
        self._reply("PUT", self.path)

    def do_PATCH(self):
        self._reply("PATCH", self.path)

    def do_DELETE(self):
        self._reply("DELETE", self.path)

    def _reply(self, method, path):
        body = self.rfile.read(int(self.headers.get("Content-Length", "0"))) if self.headers.get("Content-Length") else b""
        FakeGitHub.calls.append((method, path, bool(self.headers.get("Authorization")), body))
        status, payload = FakeGitHub.responses.get((method, path), (404, {"message": "not found"}))
        raw = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


@pytest.fixture
def api_server(monkeypatch):
    FakeGitHub.calls = []
    FakeGitHub.responses = {
        ("GET", "/repos/org/trial/installation"): (200, {"id": 901}),
        ("POST", "/app/installations/901/access_tokens"): (201, {"token": "never-store-this-token", "expires_at": "2030-01-01T00:00:00Z"}),
        ("GET", "/installation"): (200, {"id": 901}),
        ("DELETE", "/installation/token"): (204, {}),
    }
    try:
        server = ThreadingHTTPServer(("127.0.0.1", 0), FakeGitHub)
    except PermissionError:
        # Keep the auth flow testable in network-restricted sandboxes that deny bind().
        class FakeResponse:
            def __init__(self, status, payload):
                self.status, self.headers = status, {}
                self._body = json.dumps(payload).encode()

            def read(self):
                return self._body

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

        def fake_urlopen(request, timeout=None):
            method, path = request.get_method(), urlparse(request.full_url).path
            FakeGitHub.calls.append((method, path, bool(request.get_header("Authorization")), request.data or b""))
            status, payload = FakeGitHub.responses[(method, path)]
            return FakeResponse(status, payload)

        monkeypatch.setattr(auth.urllib.request, "urlopen", fake_urlopen)
        yield "http://mock.invalid"
        return
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    thread.join()
    server.server_close()


def test_jwt_well_formed_and_signature_verifies(tmp_path):
    key = tmp_path / "private.pem"
    pub = tmp_path / "public.pem"
    subprocess.run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(key)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["openssl", "pkey", "-in", str(key), "-pubout", "-out", str(pub)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    jwt = auth.create_jwt(12345, key, now=1_800_000_000)
    header, payload, signature = jwt.split(".")
    pad = lambda x: x + "=" * (-len(x) % 4)
    assert json.loads(base64.urlsafe_b64decode(pad(header))) == {"alg": "RS256", "typ": "JWT"}
    claims = json.loads(base64.urlsafe_b64decode(pad(payload)))
    assert claims == {"iat": 1_799_999_940, "exp": 1_800_000_540, "iss": "12345"}
    signed, sig = tmp_path / "signed", tmp_path / "sig"
    signed.write_text(f"{header}.{payload}", encoding="ascii")
    sig.write_bytes(base64.urlsafe_b64decode(pad(signature)))
    subprocess.run(["openssl", "dgst", "-sha256", "-verify", str(pub), "-signature", str(sig), str(signed)], check=True, capture_output=True)


def test_token_is_memory_only_and_not_printed(tmp_path, monkeypatch, api_server, capsys):
    key = tmp_path / "app.pem"
    key.write_text("not used for this API token test")
    client = object.__new__(auth.GitHubAppClient)
    client.app_id, client._key_path, client.api_base, client.timeout = 77, key, api_server, 5
    client._installation_token = None
    monkeypatch.setattr(auth, "create_jwt", lambda *_: "jwt-for-test")
    token = client.installation_token("org", "trial")
    assert token == "never-store-this-token"
    assert client.request("GET", "/installation").status == 200
    client.close()
    assert capsys.readouterr().out == ""
    assert not list(tmp_path.glob("*token*"))
    assert all("never-store-this-token" not in str(call) for call in FakeGitHub.calls)
    assert all(call[2] for call in FakeGitHub.calls)
    assert FakeGitHub.calls[-1][1] == "/installation/token"


def test_rejects_wrong_uid(monkeypatch):
    monkeypatch.setattr(trial, "ROLE_NAMES", {"aao-impl-codex"})
    monkeypatch.setattr(trial.pwd, "getpwnam", lambda _role: type("Entry", (), {"pw_uid": os.getuid() + 1000})())
    with pytest.raises(auth.GitHubAuthError, match="does not match role"):
        trial.validate_role_uid("aao-impl-codex")


class DummyClient:
    _installation_token = "test"

    def __init__(self, replies):
        self.replies = iter(replies)
        self.calls = []

    def request(self, method, path, body=None):
        self.calls.append((method, path, body))
        response = next(self.replies)
        return auth.APIResponse(response[0], response[1], {})


def _promotion_replies(*, audit_app_id=77):
    base, head, tree, merge = "a" * 40, "b" * 40, "c" * 40, "d" * 40
    return [
        (200, [{"number": 8, "head": {"sha": head}}]),
        (200, {"number": 8, "head": {"sha": head}, "base": {"ref": "main"}}),
        (200, {"object": {"sha": base}}),
        (200, {"id": 77}),
        (200, {"check_runs": [
            {"name": "aao-audit", "app": {"id": audit_app_id}, "status": "completed", "conclusion": "success"},
            {"name": "test", "app": {"id": 1}, "status": "completed", "conclusion": "success"},
        ]}),
        (200, {"data": {"updateRefs": {"refs": [{"name": "refs/heads/main"}]}}}),
        (200, {"object": {"sha": merge}}),
        (200, {"sha": merge, "tree": {"sha": tree}, "parents": [{"sha": base}, {"sha": head}]}),
        (200, {"merged": True}),
    ]


def _fake_git(monkeypatch):
    tree, merge = "c" * 40, "d" * 40

    def run(args, **_kwargs):
        return type("Result", (), {"stdout": tree + "\n" if "merge-tree" in args else merge + "\n"})()

    monkeypatch.setattr(trial.subprocess, "run", run)
    monkeypatch.setattr(trial, "_git_push", lambda *_args, **_kwargs: {"status": 0, "response": "push accepted"})


@pytest.mark.parametrize("test_id", ["A-05", "P3-06"])
def test_authorized_promotion_uses_update_refs_never_merge_endpoint(monkeypatch, test_id):
    _fake_git(monkeypatch)
    monkeypatch.setattr(trial, "CHECK_WAIT_SECONDS", 1)
    client = DummyClient(_promotion_replies())
    status, _, evidence = trial.run_test(test_id, "org", "trial", "aao-integrator", client)
    assert status == "PASS"
    assert not any(method == "PUT" and path.endswith("/merge") for method, path, _ in client.calls)
    update = next(body for method, path, body in client.calls if method == "POST" and path == "/graphql")
    ref_update = update["variables"]["input"]["refUpdates"][0]
    assert ref_update["beforeOid"] == "a" * 40
    assert ref_update["oid"] == "d" * 40
    assert any(item.get("method", "").startswith("git merge-tree") for item in evidence)


def test_authorized_promotion_fails_for_wrong_audit_app(monkeypatch):
    _fake_git(monkeypatch)
    monkeypatch.setattr(trial, "CHECK_WAIT_SECONDS", 1)
    client = DummyClient(_promotion_replies(audit_app_id=999))
    status, reason, _ = trial.run_test("A-05", "org", "trial", "aao-integrator", client)
    assert status == "FAIL"
    assert "app_id 999" in reason
    assert not any(path == "/graphql" for _, path, _ in client.calls)


def test_a01_rejected_git_push_is_pass(monkeypatch):
    monkeypatch.setattr(trial, "_git_push", lambda *_args, **_kwargs: {"status": 1, "response": "rejected"})
    status, _, _ = trial.run_test("A-01", "org", "trial", "aao-impl-codex", DummyClient([]))
    assert status == "PASS"


def test_a03_stale_update_refs_rejection_is_pass():
    client = DummyClient([(200, {"object": {"sha": "a" * 40}}), (200, {"errors": [{"message": "stale"}]})])
    status, _, evidence = trial.run_test("A-03", "org", "trial", "aao-integrator", client)
    assert status == "PASS"
    assert evidence[-1]["path"] == "/graphql"


def test_p3_03_missing_required_check_rejection_is_pass(monkeypatch):
    monkeypatch.setattr(trial.subprocess, "run", lambda *_args, **_kwargs: type("Result", (), {"stdout": "b" * 40})())
    client = DummyClient([(403, {"message": "required check missing"})])
    status, _, _ = trial.run_test("P3-03", "org", "trial", "aao-integrator", client)
    assert status == "PASS"


def test_a10_wrong_installation_permissions_is_fail():
    client = DummyClient([(200, {"permissions": {"contents": "write", "metadata": "read", "administration": "write"}})])
    status, _, _ = trial.run_test("A-10", "org", "trial", "aao-impl-codex", client)
    assert status == "FAIL"


def test_evidence_mode_and_redaction(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    dest = trial.write_evidence("A-01", "PASS", "ok", "org/trial", "aao-impl-codex", 17,
                                [{"request": {"token": "hide"}, "response": {"ok": True}}])
    assert dest.stat().st_mode & 0o777 == 0o600
    assert "hide" not in dest.read_text()
