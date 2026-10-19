# M2 — Worker identity and external-effect ledger (candidate)

> **Current-state note (2026-10-19):** early sections below record historical
> transitions and are not a description of current authentication. Migration
> 006 removed `worker_registrations`; queue claims/completions use individual
> AGENT credentials. Current operation scope and evidence boundaries are in
> [`PRINCIPAL_AUTHORIZATION_MATRIX.md`](PRINCIPAL_AUTHORIZATION_MATRIX.md).

## What exists
Migration 004 provides an explicit worker registration record (disabled by
default) and an external-effect ledger with unique idempotency keys.
`worker_auth.py` verifies registered worker credentials and provides an
explicit opt-in development bootstrap. `external_effect_registry.py` can
**record only** PROPOSED effects, and only while the referenced queue row is
`RUNNING`; it contains no execution or approval operation. Proposal admission
locks that queue row, serializing it with reconciliation/retry decisions.

## Safety boundaries
- Worker registration is now checked on queue claims, but completion still uses only the lease token and worker ID. The claim check does not establish mTLS/OIDC or secure worker attestation.
- Token hashes are SHA-256 development placeholders, not suitable for low-entropy
  human passwords. Production must use stronger credentials (mTLS/OIDC) and
  protected secrets.
- The ledger guarantees key uniqueness at the database level, **not**
  exactly-once behavior of third-party systems.
- Capability approval, authorization snapshots, fencing at external effects,
  and reconciliation must precede any external execution.
- No worker services are started and no agent/model calls are enabled.

## Next integration
Verify worker credentials in completion and renewal as well, add transactional project-state locking, and test suspension races before attaching even inert autonomous workers.
Only then attach inert workers, leaving real effect adapters disabled.

## Increment: credential-bound completion and project lock

Worker `claim()` now rechecks the project state under a row lock before marking a queued execution RUNNING. `complete()` requires the authenticated registered worker credential, a matching live lease, and an ACTIVE project locked in the same transaction. This prevents a completed state being committed concurrently with a project suspension transaction that acquires the same project row lock (subject to transaction ordering).

Migration `007_fence_leases_across_project_state_changes` adds a database-owned
project state generation. A claim records that generation; completion and
effect proposal require it still to match. Pausing and later resuming therefore
does not revive an old lease. The generation trigger increments only when the
state actually changes and overwrites caller-supplied generation values. A
stale lease remains `RUNNING` until its lease expires and the existing explicit
quarantine moves it to `UNCERTAIN`; pause is not an automatic retry or effect
cancellation mechanism. This fence is defense-in-depth, not proof that an
external action did not occur.

Migration rollback policy is forward-only after deployment: preserve lease and
journal evidence, fix defects with a new migration, and do not remove the
generation columns/trigger while claims may depend on them. A disposable test
database may be recreated from migrations 001 onward.

Opt-in PostgreSQL integration tests cover invalid credentials, suspended-project completion, and the pause-resume stale-lease fence. Lease expiry still leads to UNCERTAIN through explicit quarantine; project suspension does not automatically quarantine ongoing work or cancel external effects. A production stop controller and credential-rotation policy remain future gates.

## Reconciliation candidate

See [M2 reconciliation](EXECUTION_RECOVERY_AND_RECONCILIATION.md). The
reconciliation functions are intentionally not exposed via HTTP. They resolve
the reviewer from an active individual AUDITOR credential and require an
explicit persisted project grant inside the transaction. This does not prove
distinct human auditor identity. No worker is restarted automatically.
