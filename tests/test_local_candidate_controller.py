from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from aao import local_candidate_controller, sandboxed_repository_checks
from aao.local_candidate_controller import (
    CandidateControllerError,
    RepositoryCheckError,
    register_candidate,
    request_promotion,
    run_integration_check,
)


def _git(repository: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repository), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture
def repository(tmp_path: Path) -> tuple[Path, str, str, str]:
    root = tmp_path / "repo"
    root.mkdir()
    _git(tmp_path, "init", "-q", str(root))
    _git(root, "config", "user.name", "candidate-test")
    _git(root, "config", "user.email", "candidate@example.invalid")
    source = root / "src" / "aao"
    source.mkdir(parents=True)
    (source / "sample.py").write_text("VALUE = 1\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "base")
    target = _git(root, "rev-parse", "HEAD")
    base_branch = _git(root, "branch", "--show-current")
    _git(root, "checkout", "-qb", "candidate")
    (source / "sample.py").write_text("VALUE = 2\n", encoding="utf-8")
    _git(root, "commit", "-qam", "candidate")
    candidate = _git(root, "rev-parse", "HEAD")
    _git(root, "checkout", "-q", base_branch)
    return root, target, candidate, f"refs/heads/{base_branch}"


def test_register_and_check_disposable_integration_without_mutating_checkout(
    tmp_path: Path, repository: tuple[Path, str, str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    root, target, candidate, target_ref = repository
    state = tmp_path / "state"
    record = register_candidate(root, target, candidate, state, target_ref=target_ref)
    manifest_path = Path(record["manifest_path"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert set(manifest) == {
        "schema",
        "repository",
        "target_ref",
        "target_sha",
        "candidate_sha",
        "candidate_tree",
        "result_tree",
        "producer",
    }
    assert manifest["schema"] == "aao.candidate-manifest.v1"
    assert manifest["repository"] == str(root)
    assert manifest["target_ref"] == target_ref
    assert manifest["target_sha"] == target
    assert manifest["candidate_sha"] == candidate
    assert manifest["candidate_tree"] == _git(root, "rev-parse", f"{candidate}^{{tree}}")
    assert manifest["result_tree"] == _git(root, "merge-tree", "--write-tree", target, candidate).splitlines()[0]
    assert manifest["producer"].startswith("aao.local_candidate_controller:uid:")
    assert record["manifest_sha256"] == hashlib.sha256(
        json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    manifest_path.write_text(json.dumps({**manifest, "result_tree": target}), encoding="utf-8")
    with pytest.raises(CandidateControllerError, match="manifest integrity check failed"):
        run_integration_check(root, record["candidate_id"], state)
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
        encoding="utf-8",
    )
    initial_head = _git(root, "rev-parse", "HEAD")
    initial_refs = _git(root, "for-each-ref", "--format=%(refname) %(objectname)")
    seen: dict[str, str] = {}

    def fake_check(path: str | Path, check_id: str) -> dict[str, object]:
        checkout = Path(path)
        seen["sha"] = _git(checkout, "rev-parse", "HEAD")
        seen["parent_count"] = _git(checkout, "rev-list", "--parents", "-n", "1", "HEAD")
        seen["check_id"] = check_id
        assert not _git(checkout, "status", "--porcelain")
        return {"check_id": check_id, "candidate_sha": seen["sha"], "conclusion": "success"}

    monkeypatch.setattr("aao.local_candidate_controller.run_repository_check", fake_check)
    evidence = run_integration_check(root, record["candidate_id"], state)

    assert evidence["schema"] == "aao.local-integration-evidence.v3"
    assert evidence["conclusion"] == "success"
    assert evidence["candidate_sha"] == candidate
    assert evidence["target_sha"] == target
    assert evidence["manifest_sha256"] == record["manifest_sha256"]
    assert evidence["verifier_sources_sha256"] == {
        "candidate_controller_sha256": hashlib.sha256(
            Path(local_candidate_controller.__file__).read_bytes()
        ).hexdigest(),
        "sandbox_check_runner_sha256": hashlib.sha256(
            Path(sandboxed_repository_checks.__file__).read_bytes()
        ).hexdigest(),
    }
    assert evidence["result_tree"] == manifest["result_tree"]
    assert evidence["integration_sha"] == seen["sha"]
    assert len(seen["parent_count"].split()) == 3
    assert seen["check_id"] == "core-unit"
    assert evidence["promotion"] == "disabled"
    assert evidence["independent_audit"] == "not_provided_by_this_controller"
    assert _git(root, "rev-parse", "HEAD") == initial_head
    assert _git(root, "for-each-ref", "--format=%(refname) %(objectname)") == initial_refs
    assert len(_git(root, "worktree", "list", "--porcelain").split("worktree ")) == 2
    saved = json.loads((state / f"{record['candidate_id']}.integration.json").read_text())
    assert saved["integration_sha"] == evidence["integration_sha"]
    digest_payload = {key: value for key, value in saved.items() if key != "evidence_sha256"}
    canonical = json.dumps(digest_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    assert saved["evidence_sha256"] == hashlib.sha256(canonical).hexdigest()
    with pytest.raises(CandidateControllerError, match="evidence already exists"):
        run_integration_check(root, record["candidate_id"], state)


def test_rejects_short_sha_and_candidate_state_inside_repository(
    tmp_path: Path, repository: tuple[Path, str, str, str]
) -> None:
    root, target, candidate, target_ref = repository
    with pytest.raises(CandidateControllerError, match="full immutable commit SHA"):
        register_candidate(root, target[:8], candidate, tmp_path / "state", target_ref=target_ref)
    with pytest.raises(CandidateControllerError, match="outside the repository"):
        register_candidate(root, target, candidate, root / ".aao-state", target_ref=target_ref)
    with pytest.raises(CandidateControllerError, match="full refs/heads ref"):
        register_candidate(root, target, candidate, tmp_path / "invalid-ref-state", target_ref="main")
    with pytest.raises(CandidateControllerError, match="does not resolve to target SHA"):
        register_candidate(
            root,
            candidate,
            candidate,
            tmp_path / "mismatched-ref-state",
            target_ref=target_ref,
        )


def test_rejects_non_private_existing_state_directory(
    tmp_path: Path, repository: tuple[Path, str, str, str]
) -> None:
    root, target, candidate, target_ref = repository
    state = tmp_path / "shared-state"
    state.mkdir(mode=0o755)
    state.chmod(0o755)
    with pytest.raises(CandidateControllerError, match="must be private"):
        register_candidate(root, target, candidate, state, target_ref=target_ref)


def test_candidate_artifact_collision_fails_closed_without_leaving_temp_files(
    tmp_path: Path,
    repository: tuple[Path, str, str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, target, candidate, target_ref = repository
    state = tmp_path / "state"

    def collision(*_args: object, **_kwargs: object) -> None:
        raise FileExistsError("concurrent artifact writer")

    monkeypatch.setattr(local_candidate_controller.os, "link", collision)
    with pytest.raises(CandidateControllerError, match="already exists; refusing overwrite"):
        register_candidate(root, target, candidate, state, target_ref=target_ref)
    assert list(state.iterdir()) == []


def test_rejects_duplicate_record_tampering_and_unallowlisted_check(
    tmp_path: Path, repository: tuple[Path, str, str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    root, target, candidate, target_ref = repository
    state = tmp_path / "state"
    record = register_candidate(root, target, candidate, state, target_ref=target_ref)
    assert record["schema"] == "aao.local-candidate.v2"
    with pytest.raises(CandidateControllerError, match="already registered"):
        register_candidate(root, target, candidate, state, target_ref=target_ref)
    path = state / f"{record['candidate_id']}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["candidate_sha"] = target
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(
        "aao.local_candidate_controller.run_repository_check",
        lambda *_args, **_kwargs: pytest.fail("must reject before running a check"),
    )
    with pytest.raises(CandidateControllerError, match="integrity check failed"):
        run_integration_check(root, record["candidate_id"], state)
    with pytest.raises(CandidateControllerError, match="fixed core-unit"):
        run_integration_check(root, record["candidate_id"], state, check_id="arbitrary")


def test_ref_movement_invalidates_manifest_before_running_checks(
    tmp_path: Path,
    repository: tuple[Path, str, str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, target, candidate, target_ref = repository
    state = tmp_path / "state"
    record = register_candidate(root, target, candidate, state, target_ref=target_ref)
    current_branch = target_ref.removeprefix("refs/heads/")
    _git(root, "checkout", "-q", current_branch)
    (root / "target-change.txt").write_text("moved\n", encoding="utf-8")
    _git(root, "add", "target-change.txt")
    _git(root, "commit", "-qm", "move target ref")
    monkeypatch.setattr(
        "aao.local_candidate_controller.run_repository_check",
        lambda *_args, **_kwargs: pytest.fail("must reject before running checks"),
    )
    with pytest.raises(CandidateControllerError, match="target ref moved"):
        run_integration_check(root, record["candidate_id"], state)


def test_unavailable_sandbox_check_is_persisted_and_worktree_is_cleaned(
    tmp_path: Path,
    repository: tuple[Path, str, str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, target, candidate, target_ref = repository
    state = tmp_path / "state"
    record = register_candidate(root, target, candidate, state, target_ref=target_ref)
    worktrees_before = _git(root, "worktree", "list", "--porcelain")

    def unavailable(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise RepositoryCheckError("sandbox unavailable")

    monkeypatch.setattr("aao.local_candidate_controller.run_repository_check", unavailable)
    evidence = run_integration_check(root, record["candidate_id"], state)

    assert evidence["conclusion"] == "unavailable"
    assert evidence["reason"] == "sandbox unavailable"
    assert evidence["promotion"] == "disabled"
    assert evidence["independent_audit"] == "not_provided_by_this_controller"
    assert _git(root, "worktree", "list", "--porcelain") == worktrees_before
    persisted = json.loads(
        (state / f"{record['candidate_id']}.integration.json").read_text(encoding="utf-8")
    )
    assert persisted["evidence_sha256"] == evidence["evidence_sha256"]


def test_promotion_is_unconditionally_blocked() -> None:
    with pytest.raises(CandidateControllerError, match="promotion is disabled"):
        request_promotion()
