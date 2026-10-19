# M2 — Uncertain execution reconciliation

An execution whose lease expires is quarantined in `UNCERTAIN`.
`pg_reconciliation.reconcile()` allows two dispositions only:
`MARK_FAILED` or `RETRY_CONFIRMED_SAFE`. It never invokes a worker or tool.

The reviewer must have an unexpired project-scoped `execution.reconcile`
grant and cannot be the former worker. Evidence references are mandatory.
Retry is refused when the project is paused or cancelled, or when any external
effect exists except one explicitly rejected. That restriction errs on the
side of refusing potentially unsafe duplicate effects.

**Important caveats:** evidence references are not cryptographically verified;
the caller's reviewer_id is not yet bound to a trusted authenticated principal.
The function is intentionally **not exposed as an HTTP endpoint** until this
is fixed. A caller with direct database/code execution privileges can bypass
this Python policy; database roles/permissions must also be secured.
Tests of database-level reconciliation require an isolated PostgreSQL instance.

## Next gates
- Trusted auditor identity and project grants from authenticated session.
- Immutable verification of evidence and signed disposition.
- Recovery of paused/running work and explicit in-flight effects reconciliation.
- Repeated crash/credential rotation and concurrent-worker integration tests.
