# F3a governance mechanisms (disposable prototype)

This work implements local mechanisms only. It does not activate GOV-REV-002, certify identity, or authorize a merge. GitHub, network, sudo and external publication are out of scope. No claim of independent custody is made.

| Policy requirement | Prototype / evidence | Status |
|---|---|---|
| §6.1–6.2 signed authorization | `integration_authorization.py`; fail-closed snapshot reasons | Prototype; callers must supply authenticated state |
| §6.3 conditional promotion | `integrator.py`; merge-tree, expected two parents, atomic force-with-lease, readback | Local Git only; RA-09 **PENDING**, GitHub server/config untested |
| §7 supervisor / heartbeat | `supervisor.py` signed events and heartbeat | Local history only; operational monitor/clock custody pending |
| §8 ledger | `governance_ledger.py` signed entries and chain checks | File custody independent only by deployment; not established here |
| RA-02 attribution | `identity.py` bare pre-receive uid log | GitHub identity PENDING; uid distinction PENDING (no root / separate uid test) |
| §16.1–16.5 | Tests below cover cryptographic checks and local failure cases | GitHub-only NT-09 cases excluded; do not imply RA-09 PASS |

## §16 / RA acceptance map

| Requested case | Test | Evidence boundary |
|---|---|---|
| §16 authorized promotion / RA-09 | `test_integrator_publishes_only_authorized_tree_end_to_end` | Local bare Git only |
| §16 CAS race | `test_integrator_aborts_when_main_moves_between_validation_and_push` | Local bare Git; server configuration not established |
| §16 tree mismatch, stale base, freeze, heartbeat | `test_integrator_rejects_tree_mismatch`, `test_integrator_rejects_stale_base`, `test_integrator_refuses_when_frozen`, `test_integrator_refuses_stale_supervisor_heartbeat` | Local mechanism tests |
| §16 post-publish divergence | `test_integrator_post_publish_divergence_freezes` | PENDING: test does not currently induce a post-publish rewrite |
| §6 signed authorization predicates | `test_authorization_rejects_other_policy_hash`, `test_authorization_rejects_recused_auditor_by_attributed_identity_not_git_metadata`, `test_authorization_rejects_unknown_or_revoked_key`, `test_authorization_rejects_missing_mandatory_checks_for_class`, `test_authorization_rejects_expired_and_vetoed`, `test_authorization_rejects_other_repo_or_pr` | Local signed snapshot validation |
| §8 ledger tamper/anchor/signing key | `test_ledger_detects_edit_reorder_and_truncation_with_external_anchor`, `test_ledger_rejects_entry_signed_by_unknown_key` | Caller-supplied anchor; independent custody not proven |
| §7 history, integrator identity, protected paths | `test_supervisor_matches_main_history_against_ledger_authorizations`, `test_supervisor_flags_merge_not_made_by_integrator_identity`, `test_supervisor_flags_protected_path_change` | Local Git history only; identity attribution is not yet implemented in supervisor |
| §7 notification replay/expiry/signature/counter | `test_notifier_rejects_replay_expired_bad_signature_and_counter_gap` | Local signer and sink |
| RA-02 pusher attribution | `test_identity_attribution_hook_records_pusher_uid_and_rejects_unattributed_push` | **PENDIENTE en entorno real**: distinct effective UIDs and GitHub identity provider; current test only exercises injectable seam/hook installation |

## Test mapping and limits

The test suite exercises signed canonical data, revocation/recusal, missing required checks, veto/expiry, ledger integrity, replay/expiry, and stale-heartbeat rejection. Local bare Git can exercise compare-and-swap behavior, but does not prove GitHub atomicity. NT-02 cases that require distinct effective uids and all GitHub event/check-run cases are intentionally not claimed as passed. RA-02 and RA-09 remain PENDING for GitHub; real uid isolation also remains PENDING.

Reproduce with the project Python 3.12 environment:

```sh
PYTHONPATH=src /home/alessbarb/workspace/repos/active/aao/.venv/bin/python -m ruff check src tests
PYTHONPATH=src /home/alessbarb/workspace/repos/active/aao/.venv/bin/python -m pytest -q tests/test_governance*.py
```

Merge commits use parents `[base_sha, candidate_sha]`; the `merge-tree --write-tree` tree is used unchanged. Conflicts abort. This prototype is not wired into existing release or audit workflows.
