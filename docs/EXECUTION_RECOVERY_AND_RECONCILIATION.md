# M2 — Uncertain execution reconciliation

An execution whose lease expires is quarantined in `UNCERTAIN`.
`execution_reconciliation.reconcile()` allows two dispositions only:
`MARK_FAILED` or `RETRY_CONFIRMED_SAFE`. It never invokes a worker or tool.

The reviewer must present an active individual `AUDITOR` credential and have
an unexpired project-scoped `execution.reconcile` grant; the reviewer ID is
derived from that credential inside the same transaction. AGENT credentials
are rejected. Evidence references are mandatory.
Retry is refused when the project is paused or cancelled, or when any external
effect exists except one explicitly rejected. That restriction errs on the
side of refusing potentially unsafe duplicate effects.

An external-effect proposal is a ledger record only. `propose()` now requires
an active individual AGENT credential matching the current worker, the
project-scoped `effect.propose` grant, an active project, and the matching
unexpired lease token on a `RUNNING` execution. The credential, execution,
project, and grant checks and proposal+journal writes occur in one transaction.
This does not authorize or execute any external action; no effect adapter is
enabled.

**Important caveats:** evidence references are not cryptographically verified.
The function remains intentionally **not exposed as an HTTP endpoint**. A
caller with direct database/code execution privileges can bypass this Python
policy; database roles/permissions must also be secured. Dedicated concurrent
auditor-credential-revocation tests are still required.
Tests of database-level reconciliation require an isolated PostgreSQL instance.

## Next gates
- Concurrent auditor-credential revocation schedules now cover both
  `MARK_FAILED` and `RETRY_CONFIRMED_SAFE`; grant-revocation races remain open.
- Credential/grant revocation schedules and hostile ordering tests for effect
  proposal; current proposal checks have selected non-concurrent denial cases
  and three focused runs of a controlled execution-row-lock proposal/completion
  schedule only.
- Immutable verification of evidence and signed disposition.
- Recovery of paused/running work and explicit in-flight effects reconciliation.
- Repeated crash/credential rotation and concurrent-worker integration tests.
