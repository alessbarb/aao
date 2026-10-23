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


@pytest.fixture(autouse=True)
def trial_env(monkeypatch):
    monkeypatch.setenv("AAO_GITHUB_TRIAL_REPOS", "org/trial")
    monkeypatch.setenv("AAO_GITHUB_API_ALLOW_TEST", "1")


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
        class FakeOpener:
            def open(self, request, timeout=None):
                return fake_urlopen(request, timeout)
        monkeypatch.setattr(auth.urllib.request, "build_opener", lambda *_handlers: FakeOpener())
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
    assert json.loads(FakeGitHub.calls[1][3]) == {"repository_names": ["trial"]}
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
        (200, {"id": 77, "owner": {"login": "alessbarb"}}),
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
    monkeypatch.setenv("AAO_GITHUB_TRIAL_PR", "8")
    monkeypatch.setenv("AAO_GITHUB_TRIAL_PR_HEAD", "b" * 40)
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
    monkeypatch.setenv("AAO_GITHUB_TRIAL_PR", "8")
    monkeypatch.setenv("AAO_GITHUB_TRIAL_PR_HEAD", "b" * 40)
    monkeypatch.setattr(trial, "CHECK_WAIT_SECONDS", 1)
    client = DummyClient(_promotion_replies(audit_app_id=999))
    status, reason, _ = trial.run_test("A-05", "org", "trial", "aao-integrator", client)
    assert status == "FAIL"
    assert "app_id 999" in reason
    assert not any(path == "/graphql" for _, path, _ in client.calls)


def test_push_client_failure_is_not_misreported_as_permission_rejection(monkeypatch):
    client = DummyClient([(200, {"object": {"sha": "a" * 40}}), (200, {"object": {"sha": "a" * 40}})])
    monkeypatch.setattr(trial, "_git_push", lambda *_args, **_kwargs: {"status": 1, "exit_code": 128, "server_rejected": False, "response": "Could not resolve host"})
    status, _, _ = trial.run_test("A-01", "org", "trial", "aao-impl-codex", client)
    assert status == "FAIL"


def test_a03_rejects_unrelated_graphql_error(monkeypatch):
    monkeypatch.setattr(trial.subprocess, "run", lambda *_args, **_kwargs: type("Result", (), {"stdout": "b" * 40})())
    monkeypatch.setattr(trial, "_git_push", lambda *_args, **_kwargs: {"exit_code": 0, "status": 0})
    client = DummyClient([
        (200, {"object": {"sha": "a" * 40}}),
        (200, {"data": {"updateRefs": {"refs": [{"name": "main"}]}}}),
        (200, {"object": {"sha": "b" * 40}}),
        (200, {"errors": [{"message": "internal server error"}]}),
        (200, {"object": {"sha": "b" * 40}}),
    ])
    status, _, _ = trial.run_test("A-03", "org", "trial", "aao-integrator", client)
    assert status == "FAIL"


def test_p3_03_wrong_http_reason_is_fail(monkeypatch):
    monkeypatch.setattr(trial.subprocess, "run", lambda *_args, **_kwargs: type("Result", (), {"stdout": "b" * 40})())
    monkeypatch.setattr(trial, "_git_push", lambda *_args, **_kwargs: {"exit_code": 0, "status": 0})
    client = DummyClient([(200, {"object": {"sha": "a" * 40}}), (403, {"message": "Resource not accessible"}), (200, {"object": {"sha": "a" * 40}})])
    status, _, _ = trial.run_test("P3-03", "org", "trial", "aao-integrator", client)
    assert status == "FAIL"


def test_a10_wrong_installation_permissions_is_fail():
    client = DummyClient([(200, {"fork": False}),
                          (200, {"permissions": {"contents": "write", "metadata": "read", "administration": "write"}})])
    status, _, _ = trial.run_test("A-10", "org", "trial", "aao-impl-codex", client)
    assert status == "FAIL"


def test_permission_tables_match_p2_manifest_values():
    """Pin corrected P2 manifest defaults and the narrower implementer fork scope offline."""
    assert trial.EXPECTED_PERMISSIONS["aao-auditor"] == {
        "contents": "read", "pull_requests": "read", "checks": "write",
        "statuses": "write", "metadata": "read",
    }
    assert trial.EXPECTED_PERMISSIONS["aao-auditor-alt"] == trial.EXPECTED_PERMISSIONS["aao-auditor"]
    assert trial.EXPECTED_PERMISSIONS["aao-pm"] == {
        "issues": "write", "pull_requests": "write", "contents": "read", "metadata": "read",
    }
    expected_fork = {"contents": "write", "workflows": "write", "metadata": "read"}
    for role in ("aao-impl-codex", "aao-impl-claude", "aao-impl-agy"):
        assert trial.EXPECTED_PERMISSIONS[role] == {
            "contents": "write", "pull_requests": "write", "workflows": "write", "metadata": "read",
        }
        assert trial.FORK_PERMISSIONS[role] == expected_fork
        assert "pull_requests" not in trial.FORK_PERMISSIONS[role]


def test_a10_implementer_on_trial_canonical_fails_even_with_read_only_permissions():
    """P2 §4 makes the trial repo canonical: implementers must be absent, not merely read-only."""
    client = DummyClient([(200, {"fork": False})])
    status, _, _ = trial.run_test("A-10", "org", "trial", "aao-impl-codex", client)
    assert status == "FAIL"
    assert [call[1] for call in client.calls] == ["/repos/org/trial"]


def test_default_branch_delete_is_not_run():
    status, reason, evidence = trial.run_test("P3-08", "org", "trial", "aao-integrator", DummyClient([]))
    assert status == "NOT RUN"
    assert "Default-branch" in reason
    assert not evidence


def test_a14_requires_implementer_on_fork():
    status, reason, _ = trial.run_test("A-14", "org", "trial", "aao-notifier", DummyClient([]))
    assert status == "NOT RUN"
    assert "implementer App" in reason


def test_disallowed_repo_has_no_api_or_git_side_effects(monkeypatch):
    monkeypatch.setenv("AAO_GITHUB_TRIAL_REPOS", "org/another")
    client = DummyClient([])
    status, _, evidence = trial.run_test("A-01", "org", "trial", "aao-impl-codex", client)
    assert status == "NOT RUN"
    assert client.calls == []
    assert evidence == []


def test_push_classifier_requires_server_reason_and_unchanged_state():
    assert trial._push_rejection_pass({"exit_code": 1, "server_rejected": True,
                                      "response": "remote: protected branch hook declined"}, True)
    assert not trial._push_rejection_pass({"exit_code": 1, "server_rejected": False,
                                           "response": "fatal: could not resolve host"}, True)
    assert not trial._push_rejection_pass({"exit_code": 1, "server_rejected": True,
                                           "response": "remote: protected branch hook declined"}, False)


@pytest.mark.parametrize(("stderr", "expected"), [
    (" ! [rejected]        HEAD -> main (non-fast-forward)\nerror: failed to push some refs", False),
    (" ! [rejected]        main -> main (stale info)\nerror: failed to push some refs", False),
    (" ! [remote rejected] HEAD -> main (protected branch hook declined)\nerror: failed to push some refs", True),
    ("remote: error: GH013: repository rule violations found for refs/heads/main.\n! [remote rejected] HEAD -> main (push declined)", True),
])
def test_git_push_classifies_real_client_and_server_transcripts(monkeypatch, stderr, expected):
    monkeypatch.setattr(trial.subprocess, "run", lambda *_args, **_kwargs: type("Result", (), {"returncode": 1, "stderr": stderr.encode()})())
    result = trial._git_push(type("Client", (), {"_installation_token": "unique-test-token"})(), "org/trial", "HEAD:refs/heads/main")
    assert result["server_rejected"] is expected


@pytest.mark.parametrize(("stderr", "expected"), [
    (" ! [rejected] main -> main (stale info)\nerror: failed to push some refs", False),
    (" ! [rejected] main -> main (non-fast-forward)\nerror: failed to push some refs", False),
    (" ! [remote rejected] main -> main (protected branch hook declined)\nerror: failed to push some refs", True),
    ("remote: error: GH013: Repository rule violations found for refs/heads/main", True),
])
def test_push_rejection_regex_distinguishes_client_and_server(stderr, expected):
    assert trial._is_server_rejection(stderr) is expected


def _push_record(refspec, response, *, code=1, server=True):
    return {"method": "git push", "refspec": refspec, "exit_code": code,
            "status": 0 if code == 0 else 1, "server_rejected": server, "response": response}


class RefClient(DummyClient):
    def __init__(self, refs):
        super().__init__([])
        self.refs = refs

    def request(self, method, path, body=None):
        self.calls.append((method, path, body))
        status, payload = self.refs[path].pop(0)
        return auth.APIResponse(status, payload, {})


def _ref_reply(sha):
    return (200, {"object": {"sha": sha}})


def test_a01_implementer_passes_only_server_push_denial_and_unchanged_main(monkeypatch):
    before = "a" * 40
    client = RefClient({"/repos/org/trial/git/ref/heads/main": [_ref_reply(before), _ref_reply(before)]})
    monkeypatch.setattr(trial, "_git_push", lambda *_a, **_k: _push_record(
        "HEAD:refs/heads/main", "! [remote rejected] HEAD -> main (protected branch hook declined)"))
    status, _, evidence = trial.run_test("A-01", "org", "trial", "aao-impl-codex", client)
    assert status == "PASS"
    assert evidence[1]["server_rejected"] is True


def test_a04_stale_lease_passes_only_server_rejection_and_moved_main_intact(monkeypatch):
    old, moved = "a" * 40, "b" * 40
    client = RefClient({"/repos/org/trial/git/ref/heads/main": [
        _ref_reply(old), _ref_reply(moved), _ref_reply(moved),
    ]})
    pushes = iter([
        _push_record("local:refs/heads/aao-trial/stale-lease", "To github\n * [new branch]", code=0, server=False),
        _push_record("old:refs/heads/main", "! [remote rejected] old -> main (stale lease rejected)")])
    monkeypatch.setattr(trial.subprocess, "run", lambda args, **_kw: type(
        "Result", (), {"stdout": moved + "\n" if args[1:3] == ["rev-parse", "HEAD"] else ""})())
    monkeypatch.setattr(trial, "_git_push", lambda *_a, **_k: next(pushes))
    original_api = trial._api
    monkeypatch.setattr(trial, "_api", lambda c, m, p, b=None: (
        original_api(c, m, p, b) if m == "GET" else {"method": m, "path": p, "status": 200,
        "response": {"data": {"updateRefs": {"refs": [{"name": "main"}]}}}}))
    status, _, evidence = trial.run_test("A-04", "org", "trial", "aao-integrator", client)
    assert status == "PASS"
    assert evidence[-2]["server_rejected"] is True


def test_p3_01_ceo_pass_requires_restrict_updates_attribution(monkeypatch):
    """Generic GH013 can be caused by required checks; only explicit Restrict updates proves P3-01."""
    before = "a" * 40
    client = RefClient({"/repos/org/trial/git/ref/heads/main": [_ref_reply(before), _ref_reply(before)]})
    monkeypatch.setattr(trial, "_git_push", lambda *_a, **_k: _push_record(
        "HEAD:refs/heads/main", "remote: error: GH013: Restrict updates rule violation"))
    assert trial.run_test("P3-01", "org", "trial", "ceo", client)[0] == "PASS"


def test_p3_01_generic_gh013_is_inconclusive(monkeypatch):
    before = "a" * 40
    client = RefClient({"/repos/org/trial/git/ref/heads/main": [_ref_reply(before), _ref_reply(before)]})
    monkeypatch.setattr(trial, "_git_push", lambda *_a, **_k: _push_record(
        "HEAD:refs/heads/main", "remote: error: GH013: Repository rule violations"))
    assert trial.run_test("P3-01", "org", "trial", "ceo", client)[0] == "INCONCLUSIVE"


def test_p3_01_permission_denied_is_not_ruleset_evidence(monkeypatch):
    before = "a" * 40
    client = RefClient({"/repos/org/trial/git/ref/heads/main": [_ref_reply(before), _ref_reply(before)]})
    monkeypatch.setattr(trial, "_git_push", lambda *_a, **_k: _push_record(
        "HEAD:refs/heads/main", "remote: Permission to org/trial.git denied to app"))
    assert trial.run_test("P3-01", "org", "trial", "ceo", client)[0] == "INCONCLUSIVE"


def test_p3_01_ruleset_name_does_not_override_failed_required_checks(monkeypatch):
    before = "a" * 40
    client = RefClient({"/repos/org/trial/git/ref/heads/main": [_ref_reply(before), _ref_reply(before)]})
    monkeypatch.setattr(trial, "_git_push", lambda *_a, **_k: _push_record(
        "HEAD:refs/heads/main", "remote: GH013: Restrict updates and required status checks aao-audit failed"))
    assert trial.run_test("P3-01", "org", "trial", "ceo", client)[0] == "INCONCLUSIVE"


def test_p3_07_integrator_requires_non_fast_forward_rule_for_both_refs(monkeypatch):
    """P3-07 is PASS only when both server denials name non_fast_forward, not required checks."""
    main, candidate = "a" * 40, "b" * 40
    base = "/repos/org/trial/git/ref/heads/"
    client = RefClient({base + "main": [_ref_reply(main), _ref_reply(main)],
                        base + "aao-staging/" + candidate[:12]: [(404, {"message": "Not Found"}),
                                                                (404, {"message": "Not Found"})]})
    monkeypatch.setattr(trial.subprocess, "run", lambda *_a, **_k: type(
        "Result", (), {"stdout": candidate + "\n", "returncode": 1})())
    pushes = []
    def fake_push(_client, _repo, refspec, **_kwargs):
        pushes.append(refspec)
        return _push_record(refspec, "remote: GH013: non_fast_forward rule violation")
    monkeypatch.setattr(trial, "_git_push", fake_push)
    status, _, _ = trial.run_test("P3-07", "org", "trial", "aao-integrator", client)
    assert status == "PASS"
    assert pushes == [f"+{candidate}:refs/heads/main",
                      f"+{candidate}:refs/heads/aao-staging/{candidate[:12]}"]


def test_p3_07_generic_ruleset_denial_is_inconclusive(monkeypatch):
    main, candidate = "a" * 40, "b" * 40
    base = "/repos/org/trial/git/ref/heads/"
    client = RefClient({base + "main": [_ref_reply(main), _ref_reply(main)],
                        base + "aao-staging/" + candidate[:12]: [(404, {"message": "Not Found"}),
                                                                (404, {"message": "Not Found"})]})
    monkeypatch.setattr(trial.subprocess, "run", lambda *_a, **_k: type(
        "Result", (), {"stdout": candidate + "\n", "returncode": 1})())
    monkeypatch.setattr(trial, "_git_push", lambda *_a, **_k: _push_record(
        "forced", "remote: GH013: Repository rule violations"))
    assert trial.run_test("P3-07", "org", "trial", "aao-integrator", client)[0] == "INCONCLUSIVE"


def test_p3_07_non_fast_forward_name_does_not_override_failed_checks(monkeypatch):
    main, candidate = "a" * 40, "b" * 40
    base = "/repos/org/trial/git/ref/heads/"
    client = RefClient({base + "main": [_ref_reply(main), _ref_reply(main)],
                        base + "aao-staging/" + candidate[:12]: [(404, {"message": "Not Found"}),
                                                                (404, {"message": "Not Found"})]})
    monkeypatch.setattr(trial.subprocess, "run", lambda *_a, **_k: type(
        "Result", (), {"stdout": candidate + "\n", "returncode": 1})())
    monkeypatch.setattr(trial, "_git_push", lambda *_a, **_k: _push_record(
        "forced", "remote: GH013: non_fast_forward; required checks aao-audit failed"))
    assert trial.run_test("P3-07", "org", "trial", "aao-integrator", client)[0] == "INCONCLUSIVE"


def test_p3_07_implementer_uses_a01_not_p3_07():
    client = DummyClient([])
    status, _, evidence = trial.run_test("P3-07", "org", "trial", "aao-impl-codex", client)
    assert status == "NOT RUN"
    assert not client.calls and not evidence


def test_p3_12_forced_non_fast_forward_must_be_server_rejected(monkeypatch):
    main, candidate = "a" * 40, "b" * 40
    client = RefClient({"/repos/org/trial/git/ref/heads/main": [_ref_reply(main), _ref_reply(main)]})
    monkeypatch.setattr(trial.subprocess, "run", lambda *_a, **_k: type(
        "Result", (), {"stdout": candidate + "\n", "returncode": 1})())
    calls = []
    monkeypatch.setattr(trial, "_git_push", lambda _c, _r, spec, **kw: (
        calls.append((spec, kw)) or _push_record(spec,
        "! [remote rejected] HEAD -> main (non-fast-forward update rejected by ruleset)")))
    status, _, _ = trial.run_test("P3-12", "org", "trial", "aao-integrator", client)
    assert status == "PASS"
    assert calls == [("+HEAD:refs/heads/main", {"no_verify": True})]


def test_a14_requires_workflows_permission_denial_and_accepted_control(monkeypatch):
    main, parent = "a" * 40, "b" * 40
    base = "/repos/org/trial"
    client = RefClient({base: [(200, {"fork": True, "parent": {"full_name": "org/parent"}})],
                        base + "/git/ref/heads/main": [_ref_reply(main), _ref_reply(main)]})
    monkeypatch.setenv("AAO_GITHUB_TRIAL_FORK_PARENT", "org/parent")
    monkeypatch.setattr(trial.subprocess, "run", lambda args, **_kw: type(
        "Result", (), {"stdout": ".github/workflows/ci.yml\n" if "diff-tree" in args else parent + "\n"})())
    pushes = []
    def fake_push(_client, _repo, spec, **_kw):
        pushes.append(spec)
        if spec.endswith("main"):
            return _push_record(spec, "remote: refusing to allow an OAuth App to create or update workflow without 'workflows' permission")
        return _push_record(spec, "To github\n * [new branch]", code=0, server=False)
    monkeypatch.setattr(trial, "_git_push", fake_push)
    status, _, _ = trial.run_test("A-14", "org", "trial", "aao-probe-noworkflows", client)
    assert status == "PASS"
    assert pushes == ["HEAD:refs/heads/main", f"{parent}:refs/heads/aao-trial/no-workflows-{parent[:12]}"]


def test_p3_09_ceo_pass_requires_restrict_updates_attribution():
    """A still-open PR plus generic denial is insufficient; the API message must name Restrict updates."""
    client = DummyClient([
        (200, [{"number": 9}]),
        (403, {"message": "Protected branch update failed: Restrict updates rule"}),
        (200, {"merged": False, "state": "open"}),
    ])
    status, _, _ = trial.run_test("P3-09", "org", "trial", "ceo", client)
    assert status == "PASS"


def test_p3_09_generic_rule_violation_is_inconclusive():
    client = DummyClient([
        (200, [{"number": 9}]),
        (403, {"message": "Protected branch update failed: rule violations"}),
        (200, {"merged": False, "state": "open"}),
    ])
    assert trial.run_test("P3-09", "org", "trial", "ceo", client)[0] == "INCONCLUSIVE"


def test_p3_09_rule_name_does_not_override_failed_required_checks():
    client = DummyClient([
        (200, [{"number": 9}]),
        (403, {"message": "Restrict updates and required status checks are failing"}),
        (200, {"merged": False, "state": "open"}),
    ])
    assert trial.run_test("P3-09", "org", "trial", "ceo", client)[0] == "INCONCLUSIVE"


@pytest.mark.parametrize("error", [AttributeError("unexpected API shape"), KeyError("head")])
def test_b6_07_attribute_or_key_error_is_recorded_as_failure(monkeypatch, error):
    monkeypatch.setattr(trial, "_run_test", lambda *_a, **_k: (_ for _ in ()).throw(error))
    status, reason, evidence = trial.run_test("A-01", "org", "trial", "aao-impl-codex", DummyClient([]))
    assert status == "FAIL"
    assert type(error).__name__ in reason
    assert evidence[0]["exception"] == type(error).__name__


def test_a10_auditor_permissions_pass_on_fork_installation(monkeypatch):
    """Fork permissions apply only after API parent identity matches the configured canonical repo."""
    monkeypatch.setenv("AAO_GITHUB_TRIAL_FORK_PARENT", "org/parent")
    permissions = trial.FORK_PERMISSIONS["aao-auditor"]
    client = DummyClient([(200, {"fork": True, "parent": {"full_name": "org/parent"}}),
                          (200, {"permissions": permissions})])
    status, _, _ = trial.run_test("A-10", "org", "trial", "aao-auditor", client)
    assert status == "PASS"


@pytest.mark.parametrize("role", [
    "aao-integrator", "aao-auditor", "aao-auditor-alt", "aao-supervisor",
    "aao-notifier", "aao-pm",
])
def test_a10_non_implementer_roles_are_checked_against_canonical_column(role):
    """Every non-implementer role is evaluated against its explicit P2 permissions."""
    permissions = trial.EXPECTED_PERMISSIONS[role]
    client = DummyClient([(200, {"fork": False}), (200, {"permissions": permissions})])
    status, _, _ = trial.run_test("A-10", "org", "trial", role, client)
    assert status == "PASS"


def test_git_push_discards_trace_settings_and_redacts_stderr(monkeypatch):
    monkeypatch.setenv("GIT_TRACE_CURL", "/tmp/curl-trace.log")
    monkeypatch.setenv("GIT_TRACE_REDACT", "0")
    seen = {}
    def fake_run(args, *, env, **_kwargs):
        seen["args"], seen["env"] = args, env
        return type("Result", (), {"returncode": 1, "stderr": b"remote: permission denied secret-token"})()
    monkeypatch.setattr(trial.subprocess, "run", fake_run)
    client = type("Client", (), {"_installation_token": "secret-token"})()
    result = trial._git_push(client, "org/trial", "HEAD:refs/heads/main")
    assert "secret-token" not in " ".join(seen["args"])
    assert "GIT_TRACE_CURL" not in seen["env"]
    assert seen["env"]["GIT_TRACE_REDACT"] == "1"
    assert "secret-token" not in result["response"]


def test_a02_405_non_permission_rejection_fails():
    client = DummyClient([
        (200, [{"number": 4}]),
        (405, {"message": "Pull request is not mergeable"}),
        (200, {"state": "open", "merged": False}),
    ])
    status, _, _ = trial.run_test("A-02", "org", "trial", "aao-impl-codex", client)
    assert status == "FAIL"


def test_ceo_cli_identity_must_be_exact_user_and_admin(monkeypatch):
    replies = iter(["another-user\n"])
    monkeypatch.setattr(trial.subprocess, "run", lambda *_args, **_kwargs: type("Result", (), {"stdout": next(replies)})())
    with pytest.raises(auth.GitHubAuthError, match="not alessbarb"):
        trial.validate_ceo_gh_identity("org/trial")


def test_custom_api_host_requires_explicit_test_flag(monkeypatch):
    monkeypatch.setattr(auth, "load_app", lambda _role: (7, Path("/unused")))
    monkeypatch.delenv("AAO_GITHUB_API_ALLOW_TEST", raising=False)
    with pytest.raises(auth.GitHubAuthError, match="requires AAO_GITHUB_API_ALLOW_TEST"):
        auth.GitHubAppClient("aao-impl-codex", api_base="https://attacker.invalid")


def test_redirect_handler_never_forwards_credentials():
    handler = auth._NoRedirect()
    assert handler.redirect_request(None, None, 302, "Found", {}, "https://attacker.invalid") is None


def test_evidence_mode_and_redaction(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    dest = trial.write_evidence("A-01", "PASS", "ok", "org/trial", "aao-impl-codex", 17,
                                [{"request": {"token": "hide"}, "response": {"ok": True}}])
    assert dest.stat().st_mode & 0o777 == 0o600
    assert "hide" not in dest.read_text()
