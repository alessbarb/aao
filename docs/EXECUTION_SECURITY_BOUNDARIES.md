# M2 candidate: execution-state machinery

This module deliberately implements only an **inert durable queue** and journal,
not an agent runtime or distributed service.

## Guarantees demonstrated by code (subject to test execution)

- One stored execution per work item.
- Atomic SQLite claim with one active lease.
- Lease token and worker identity required to complete.
- Expired leases quarantined into UNCERTAIN instead of automatically executing twice.
- Explicit reconciliation decision required before retry.
- No model calls, shell commands, network tools, or external side effects.

## Non-guarantees

- SQLite is not the planned PostgreSQL execution backend.
- No worker attestation or real identities.
- Lease tokens alone cannot prevent a crashed worker from completing an
  already issued external side effect: external adapters must use fencing,
  idempotency keys, or reconciliation.
- Reconciler trust is not enforced by this library.
- No task admission integration, authorization middleware, distributed scheduler,
  operation budgets or checkpoint payloads.
- Does not satisfy production 24/7 or longitudinal acceptance.

M2 remains OPEN until the service has integrated project authorizations,
durable PostgreSQL storage, real workers and external-effect verification.
