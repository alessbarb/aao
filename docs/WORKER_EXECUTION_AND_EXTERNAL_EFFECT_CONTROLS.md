# M2 — Worker identity and external-effect ledger (candidate)

## What exists
Migration 004 provides an explicit worker registration record (disabled by
default) and an external-effect ledger with unique idempotency keys.
`worker_auth.py` verifies registered worker credentials and provides an
explicit opt-in development bootstrap. `pg_effects.py` can **record only**
PROPOSED effects; it contains no execution or approval operation.

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

An opt-in PostgreSQL integration test covers invalid credentials and suspended-project completion. No PostgreSQL server run was observed in this session. Lease expiry still leads to UNCERTAIN through explicit quarantine; project suspension **does not yet** automatically quarantine ongoing work or cancel external effects. A production stop controller and credential-rotation policy remain future gates.

## Reconciliation candidate

See [M2 reconciliation](M2_RECONCILIATION.md). The candidate function is intentionally not exposed via API: it currently accepts a caller-supplied reviewer identity and cannot be treated as production authorization. The `execution.reconcile` capability requires an explicit persisted project grant, and no worker is restarted automatically.
