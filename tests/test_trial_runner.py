from pathlib import Path


RUNNER = Path(__file__).parents[1] / "scripts/trial/run_trial.sh"


def test_runner_binds_evidence_to_unique_run_and_harness_revision():
    source = RUNNER.read_text()
    assert "export AAO_TRIAL_RUN_ID=$TS AAO_TRIAL_HARNESS_REV=$REV" in source
    assert 'get("run_id", "")' in source
    assert "no evidence from this run" in source
    assert "GITHUB_SHA=" not in source


def test_runner_stages_candidate_from_app_clone_and_logs_helpers():
    source = RUNNER.read_text()
    stage = source.index('STAGE-COMMIT --repo')
    stage_context = source[source.rfind('(cd "$clone"', 0, stage):stage]
    assert '(cd "$clone"' in stage_context
    assert "AAO_GITHUB_TRIAL_EXPECTED_SHA=\"$candidate\"" in stage_context
    assert '"$LOG/$id-STAGE-COMMIT.out"' in source
    assert '"$LOG/$id-PUBLISH-AUDIT.out"' in source
    assert ">/dev/null 2>&1" not in source


def test_runner_fetch_and_symlink_checks_fail_closed_before_install():
    source = RUNNER.read_text()
    fetch = 'fetch --quiet origin main || {'
    assert fetch in source
    symlink_check = source.index('[[ ! -L /opt/aao-trial ]]')
    install = source.index('install -d -o root -g root -m 0755 /opt/aao-trial')
    assert symlink_check < install


def test_runner_passes_both_implementer_forks_and_runs_a10_for_all_apps():
    source = RUNNER.read_text()
    assert 'AAO_GITHUB_TRIAL_FORKS="autoaiorg/aao-codex,$impl_fork"' in source
    assert 'AAO_GITHUB_TRIAL_FORKS="$production_fork,$impl_fork"' in source
    assert "A10_ROLES=(aao-integrator aao-auditor aao-auditor-alt aao-supervisor aao-notifier aao-pm aao-impl-claude aao-impl-codex aao-impl-agy aao-probe-noworkflows)" in source
    assert "target=autoaiorg/aao-trial-probe" in source
    assert 'impl_uid=${APP_UID[$impl]}' in source
