import os
import stat

import pytest

from scripts import run_self_development_worker as worker


def make_runtime(tmp_path, *, mode=0o700, token_mode=0o600):
    runtime = tmp_path / "runtime"
    runtime.mkdir(mode=mode)
    runtime.chmod(mode)
    token_path = runtime / worker.AGENT_TOKEN_NAME
    token_path.write_text("agent-token-fixture\n", encoding="utf-8")
    token_path.chmod(token_mode)
    return runtime, token_path


def test_worker_reads_agent_token_only_from_private_runtime_file(tmp_path, monkeypatch):
    runtime, _ = make_runtime(tmp_path)
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(runtime))
    monkeypatch.setattr(worker.os, "getuid", lambda: os.stat(runtime).st_uid)

    assert worker._read_agent_token() == "agent-token-fixture"


@pytest.mark.parametrize("runtime_mode,token_mode", [(0o750, 0o600), (0o700, 0o640)])
def test_worker_rejects_non_private_runtime_or_token(tmp_path, monkeypatch,
                                                    runtime_mode, token_mode):
    runtime, _ = make_runtime(tmp_path, mode=runtime_mode, token_mode=token_mode)
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(runtime))
    monkeypatch.setattr(worker.os, "getuid", lambda: os.stat(runtime).st_uid)

    with pytest.raises(worker.WorkerError, match="private|mode 0600"):
        worker._read_agent_token()


def test_worker_runs_one_authorized_queue_item_without_logging_token(tmp_path, monkeypatch,
                                                                     capsys):
    runtime, _ = make_runtime(tmp_path)
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(runtime))
    monkeypatch.setattr(worker.os, "getuid", lambda: os.stat(runtime).st_uid)
    monkeypatch.setattr(
        "aao.inert_execution_worker.run_one",
        lambda principal, token, *, project_id, seconds: (
            {"status": "SUCCEEDED", "execution_id": "exec-1"}
            if (principal, token, project_id, seconds)
            == ("agent-1", "agent-token-fixture", "project-1", worker.MAX_LEASE_SECONDS)
            else pytest.fail("worker arguments did not match the scoped invocation")
        ),
    )
    monkeypatch.setattr(worker.sys, "argv", ["worker", "--project-id", "project-1",
                                             "--principal-id", "agent-1"])

    assert worker.main() == 0
    output = capsys.readouterr().out
    assert "Execution exec-1: SUCCEEDED" in output
    assert "agent-token-fixture" not in output


def test_worker_token_file_must_be_regular_and_owned(tmp_path, monkeypatch):
    runtime, token_path = make_runtime(tmp_path)
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(runtime))
    monkeypatch.setattr(worker.os, "getuid", lambda: os.stat(runtime).st_uid)
    assert stat.S_ISREG(token_path.stat().st_mode)
    token_path.unlink()
    token_path.symlink_to(runtime / "missing")

    with pytest.raises(worker.WorkerError, match="symbolic link"):
        worker._read_agent_token()


def test_worker_error_output_does_not_include_exception_details(tmp_path, monkeypatch, capsys):
    runtime, _ = make_runtime(tmp_path)
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(runtime))
    monkeypatch.setattr(worker.os, "getuid", lambda: os.stat(runtime).st_uid)
    monkeypatch.setattr(
        "aao.inert_execution_worker.run_one",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("sensitive detail")),
    )
    monkeypatch.setattr(worker.sys, "argv", ["worker", "--project-id", "p",
                                             "--principal-id", "a"])

    assert worker.main() == 1
    output = capsys.readouterr().err
    assert "RuntimeError" in output
    assert "sensitive detail" not in output
