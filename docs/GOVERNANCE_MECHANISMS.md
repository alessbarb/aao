# F3a governance mechanisms (disposable prototype)

This work implements local mechanisms only. It does not activate GOV-REV-002, certify identity, or authorize a merge. GitHub, network, sudo and external publication are out of scope. No claim of independent custody is made.

**F4-01a limitation:** the integrator uses the supervisor's signed heartbeat snapshot to detect veto markers observed by the supervisor and a verified ledger head. On each heartbeat the supervisor requires its prior non-genesis head to remain in the currently verified ledger chain; otherwise it records a continuity incident and refuses to sign. Resolution rows are accepted only from verified `can_resolve_pending` signers, with the integrator key excluded from that authority. A marker deleted before the next heartbeat is not covered; the exposure window is bounded by the heartbeat's validity period. This mitigation depends on exclusive custody of the supervisor uid. It narrows, but does not close, A-2. The manifest gate still uses its older external ledger anchor; F4-01b, which advances that anchor independently, remains pending. P1 having run does not remove these logic limits.

**Supervisor-state migration:** legacy `state.json` files without a valid signature fail closed and are not imported or repaired automatically. An operator must preserve the file for investigation and initialize a new signed state only through an authorized migration procedure; do not delete or rewrite it as an automatic recovery.

| Policy requirement | Prototype / evidence | Status |
|---|---|---|
| §6.1–6.2 signed authorization | `integration_authorization.py`; fail-closed snapshot reasons | Prototype; callers must supply authenticated state |
| §6.3 conditional promotion | `integrator.py`; merge-tree, expected two parents, atomic force-with-lease, readback | Local Git only; RA-09 **PENDING**, GitHub server/config untested |
| §7 supervisor / heartbeat | `supervisor.py` verifies the signed ledger against a trusted-key registry; alerts and heartbeats are Ed25519-signed with key id, issued/expiry times; alert sequences persist locally | Local history only; sequence-file/clock custody and operational monitor remain deployment responsibilities |
| §8 ledger | `governance_ledger.py` signed entries and chain checks | File custody independent only by deployment; not established here |
| RA-02 attribution | `identity_attribution.py` bare pre-receive effective-uid log | GitHub identity PENDING; distinct local UIDs not tested |
| §16.1–16.5 | Tests below cover cryptographic checks and local failure cases | GitHub-only NT-09 cases excluded; do not imply RA-09 PASS |

## §16 / RA acceptance map

| Requested case | Test | Evidence boundary |
|---|---|---|
| §16 authorized promotion / RA-09 | `test_integrator_publishes_only_authorized_tree_end_to_end` | Local bare Git only |
| §16 CAS race | `test_integrator_aborts_when_main_moves_between_validation_and_push` | Local bare Git; server configuration not established |
| §16 tree mismatch, stale base, freeze, heartbeat | `test_integrator_rejects_tree_mismatch`, `test_integrator_rejects_stale_base`, `test_integrator_refuses_when_frozen`, `test_integrator_refuses_stale_supervisor_heartbeat` | Local mechanism tests |
| §16 post-publish divergence | `test_integrator_post_publish_divergence_freezes`, `test_integrator_freezes_when_published_parents_differ` | Local bare Git: callbacks alter `main` after successful push; readback detects a mismatch and records a freeze. The tests do not establish recovery behavior |
| §6 signed authorization predicates | `test_authorization_rejects_other_policy_hash`, `test_authorization_rejects_recused_auditor_by_attributed_identity_not_git_metadata`, `test_authorization_rejects_unknown_or_revoked_key`, `test_authorization_rejects_missing_mandatory_checks_for_class`, `test_authorization_rejects_expired_and_vetoed`, `test_authorization_rejects_other_repo_or_pr` | Local signed snapshot validation |
| §8 ledger tamper/anchor/signing key | `test_ledger_detects_edit_reorder_and_truncation_with_external_anchor`, `test_ledger_rejects_entry_signed_by_unknown_key` | Caller-supplied anchor; independent custody not proven |
| §7 history, integrator identity, protected paths | `test_supervisor_matches_main_history_against_ledger_authorizations`, `test_supervisor_flags_merge_not_made_by_integrator_identity`, `test_supervisor_flags_merge_pushed_by_non_integrator_identity`, `test_supervisor_flags_protected_path_change`, `test_supervisor_detects_protected_change_in_real_merge_using_minimum_class`, `test_supervisor_signs_events_and_heartbeat_for_notifier`, `test_supervisor_ignores_unverified_authorization_rows` | Local first-parent Git history and real bare-repository merge; supplied trust keys are used. Unverified authorization input fails closed; external key custody and GitHub history are not established |
| §7 notification replay/expiry/signature/counter | `test_notifier_rejects_replay_expired_bad_signature_and_counter_gap` | Local signer and sink |
| RA-02 pusher attribution | `test_identity_attribution_hook_records_pusher_uid_and_rejects_unattributed_push` | Local bare Git executes real pushes: pre-receive records server-side effective uid; failed append rejects push. Distinct effective UIDs and GitHub identity provider remain untested |
| NF-05 veto identity | `test_ledger_new_veto_with_reused_id_stays_active_after_old_revocation` | Local signed ledger; a newly appended veto sharing an old ID remains active after an exact-hash revocation |
| NF-06 heartbeat freshness/replay | `test_integrator_rejects_replayed_heartbeat_sequence`, `test_integrator_rejects_heartbeat_older_than_one_hour_even_if_registry_allows_more`, `test_integrator_rejects_heartbeat_issued_in_the_future` | Local signed heartbeat and sequence file; does not establish independent clock or state custody |
| NF-07 pending acceptance gates | `test_integrator_rejects_pending_ra01_or_ra07` | Local registry values; both pending states reject promotion |
| NF-08 protected paths | `test_authorization_rejects_protected_path_change_below_minimum_class`, `test_authorization_rejects_protected_paths_digest_mismatch` | Local signed snapshot validation against caller-supplied path data; no GitHub check-run evidence |
| NF-09 authorization role | `test_ledger_rejects_authorization_row_from_key_without_can_authorize`, `test_supervisor_ignores_unverified_authorization_rows` | Local ledger rejects an authorization row without the configured capability; the supervisor does not accept the invalid ledger |
| FA-07 remote candidate head | `test_integrator_blocks_when_remote_candidate_head_moves` | Local bare Git ref changes between authorization and integration; GitHub PR state is not tested |
| FA-11/16 authorization evidence | `test_authorization_rejects_git_version_mismatch`, `test_authorization_rejects_open_critical_finding_or_empty_expediente` | Local signed document validation; no independent evidence authenticity is established |
| FA-14 promotion, ledger and auditor safeguards | `test_integrator_freezes_when_published_parents_differ`, `test_ledger_verify_fails_on_edited_intermediate_entry`, `test_authorization_rejects_auditor_with_same_model_as_author_for_r2`, `test_supervisor_flags_merge_pushed_by_non_integrator_identity` | Local mechanisms only; does not establish external identity attribution or independent auditor custody |

## Test mapping and limits

The named tests exercise the listed local predicates only. They do not establish RA-01, RA-02, RA-03, RA-07, or RA-09 acceptance beyond the specific local cases described above. Local bare Git can exercise compare-and-swap behavior, but does not prove GitHub atomicity. Distinct effective UIDs and GitHub event/check-run behavior are not claimed. RA-02 and RA-09 remain PENDING for GitHub; real uid isolation also remains PENDING.

Reproduce with the project Python 3.12 environment:

```sh
PYTHONPATH=src /home/alessbarb/workspace/repos/active/aao/.venv/bin/python -m ruff check src tests
PYTHONPATH=src /home/alessbarb/workspace/repos/active/aao/.venv/bin/python -m pytest -q tests/test_governance*.py
```

Merge commits use parents `[base_sha, candidate_sha]`; the `merge-tree --write-tree` tree is used unchanged. Conflicts abort. This prototype is not wired into existing release or audit workflows.
