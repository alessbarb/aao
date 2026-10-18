# M2 — Worker identity and external-effect ledger (candidate)

## What exists
Migration 004 provides an explicit worker registration record (disabled by
default) and an external-effect ledger with unique idempotency keys.
`worker_auth.py` verifies registered worker credentials and provides an
explicit opt-in development bootstrap. `pg_effects.py` can **record only**
PROPOSED effects; it contains no execution or approval operation.

## Safety boundaries
- Worker registration does not yet authenticate the queue's claim/complete APIs.
- Token hashes are SHA-256 development placeholders, not suitable for low-entropy
  human passwords. Production must use stronger credentials (mTLS/OIDC) and
  protected secrets.
- The ledger guarantees key uniqueness at the database level, **not**
  exactly-once behavior of third-party systems.
- Capability approval, authorization snapshots, fencing at external effects,
  and reconciliation must precede any external execution.
- No worker services are started and no agent/model calls are enabled.

## Next integration
Bind verified worker registrations to queue claims, ensure project ACTIVE
status under transaction, and add a test for project suspension during claim.
Only then attach inert workers, leaving real effect adapters disabled.
