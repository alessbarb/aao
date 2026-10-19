"""Bounded patch-proposal validation never changes the source checkout."""

import subprocess

import pytest

from aao.patch_proposals import PatchProposalError, inspect_patch, validate_patch


def _git(path, *args):
    return subprocess.run(
        ["git", "-C", str(path), *args], check=True, capture_output=True, text=True,
    ).stdout.strip()


def _repository(tmp_path):
    repository = tmp_path / "source"
    repository.mkdir()
    _git(repository, "init", "--quiet")
    (repository / "src/aao").mkdir(parents=True)
    target = repository / "src/aao/sample.py"
    target.write_text("VALUE = 1\n", encoding="utf-8")
    _git(repository, "add", "src/aao/sample.py")
    _git(repository, "-c", "user.name=AAO test", "-c", "user.email=test@example.invalid",
         "commit", "--quiet", "-m", "base")
    return repository, target, _git(repository, "rev-parse", "HEAD")


def test_valid_patch_is_checked_in_disposable_clone_without_source_changes(tmp_path):
    repository, target, sha = _repository(tmp_path)
    patch = (
        "diff --git a/src/aao/sample.py b/src/aao/sample.py\n"
        "index 2c2b30a..981f5f4 100644\n"
        "--- a/src/aao/sample.py\n+++ b/src/aao/sample.py\n"
        "@@ -1 +1 @@\n-VALUE = 1\n+VALUE = 2\n"
    )
    result = validate_patch(repository, sha, patch)
    assert result["base_sha"] == sha
    assert result["changed_paths"] == ["src/aao/sample.py"]
    assert result["validated_in_disposable_clone"] is True
    assert result["applied_to_canonical_checkout"] is False
    assert len(result["candidate_tree"]) == 40
    assert target.read_text(encoding="utf-8") == "VALUE = 1\n"
    assert _git(repository, "status", "--porcelain") == ""


def test_proposal_inspection_does_not_claim_applicability_validation():
    patch = (
        "diff --git a/src/aao/sample.py b/src/aao/sample.py\n"
        "--- a/src/aao/sample.py\n+++ b/src/aao/sample.py\n"
        "@@ -1 +1 @@\n-old\n+new\n"
    )
    assert inspect_patch(patch)["changed_paths"] == ["src/aao/sample.py"]


@pytest.mark.parametrize("path", ["README.md", "../outside.py", ".git/config"])
def test_patch_rejects_paths_outside_allowed_roots(tmp_path, path):
    header = f"diff --git a/{path} b/{path}\n"
    with pytest.raises(PatchProposalError):
        validate_patch(tmp_path, "a" * 40, header)


def test_patch_rejects_invalid_base_and_unapplicable_changes(tmp_path):
    repository, _, sha = _repository(tmp_path)
    with pytest.raises(PatchProposalError, match="full base commit SHA"):
        validate_patch(repository, "bad", "diff --git a/src/aao/x.py b/src/aao/x.py\n")
    invalid = (
        "diff --git a/src/aao/sample.py b/src/aao/sample.py\n"
        "--- a/src/aao/sample.py\n+++ b/src/aao/sample.py\n"
        "@@ -1 +1 @@\n-VALUE = wrong\n+VALUE = 2\n"
    )
    with pytest.raises(PatchProposalError, match="does not apply cleanly"):
        validate_patch(repository, sha, invalid)


def test_patch_rejects_binary_and_executable_content(tmp_path):
    repository, _, sha = _repository(tmp_path)
    for extra in ("GIT binary patch\n", "new file mode 100755\n"):
        patch = "diff --git a/src/aao/sample.py b/src/aao/sample.py\n" + extra
        with pytest.raises(PatchProposalError):
            validate_patch(repository, sha, patch)
