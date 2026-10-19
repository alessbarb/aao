# M2 — Principal authority and revocation boundaries

## Current status

Project-list and board reads revalidate the individual credential and lock
the matching project grant under `FOR SHARE`. CEO grant deletion is audited in
the same transaction and waits for protected transactions holding the grant
row lock. Integration tests demonstrate revocation serialization, expiry
while blocked behind a row update, and auditor credential locking. Shared
worker/reviewer authentication is no longer accepted by the PostgreSQL API;
execution migration 006 removed the legacy worker registration table. These
are bounded engineering results, not a complete concurrency proof. Provisional
CEO bearer, absent independent security review and recovery/concurrency gates
remain open. M2 is not accepted.

## Implemented behavior (not accepted as M2)

Individual bearer credentials are initially authenticated before the PostgreSQL work transaction. Previously, project grants only verified the resolved principal identifier and grant, allowing authorization to outlive a concurrent credential revocation.

The `require_grant` function verifies the individual credential's enabled
state and kind, then holds the matching grant row under `SELECT ... FOR SHARE`
inside the protected transaction. Execution claim/completion and internal
reconciliation checks also lock their grant rows. CEO grant deletion is the
current revocation operation and serializes behind those locks. Grant expiry
checks use database `clock_timestamp()` rather than transaction-start `now()`.
Review and reconciliation require AUDITOR; other currently implemented grant
capabilities require AGENT. SQLite prototype shared tokens do not authenticate
the PostgreSQL API.

## Boundaries and remaining risks

- A PostgreSQL race test verifies that CEO grant deletion waits for an open
  transaction after `require_grant`, and that subsequent protected work is
  denied. Another test verifies denial when a grant expires while the check is
  blocked behind a row lock. These tests are single controlled schedules, not
  repeated adversarial stress tests.
- Migration 006 removes the legacy worker registration table after transferring
  its identities. The migration and identity handoff still warrant independent
  review and collision/recovery testing.
- Concurrent credential rotation/revocation, grant revocation against queue
  claim/completion, expiry across long-running operations, and repeated
  adversarial schedules remain to be tested.
- CEO authentication remains provisional. No production identity provider, privileged token management, or independent security approval exists.
- PostgreSQL role isolation, adverse concurrency, audit guarantees and cold-restart recovery remain acceptance gates.
- External execution and effects remain disabled.

## Historical evidence classification

Three additional unit tests check nonexistent, inactive, wrong-kind, active,
and shared development principal behavior. The validation-pending note is
historical: the full disposable PostgreSQL suite and Ruff were later executed
on the project-read increment. See the exact revision and results above and
in the evidence register. These changes are neither independent security
review nor acceptance of M2.

## Transactional project-list read authorization (historical checkpoint)

Project-list reads for individual agents now revalidate an active AGENT credential under `FOR SHARE` within the same database transaction as the project-scoped listing query. Shared development readers are rechecked against the development-only feature gate. An inactive, missing, or AUDITOR-kind credential is denied before project data is queried. A new isolated unit test covers these states and the SQL boundary. Direct board reads already route through `require_grant`, which checks individual credential state inside its transaction.

The local verification pending at the time of this increment was completed at
the revision recorded above. This historical project-read checkpoint is
superseded by the grant-row locking increment cited in the current status. The
CEO development token remains provisional; M2 remains open.
