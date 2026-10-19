# M2 — Inert worker and effect proposal reconciliation

> **Current-state note (2026-10-19):** this page contains historical claims
> that were superseded by migrations 006–009. For current authentication,
> reconciliation, and test scope, see the
> [authorization matrix](PRINCIPAL_AUTHORIZATION_MATRIX.md),
> [reconciliation notes](EXECUTION_RECOVERY_AND_RECONCILIATION.md), and
> [verification register](VERIFICATION_EVIDENCE_REGISTER.md).

- `inert_worker.run_one()` performs one atomic claim and one completion.
- It intentionally cannot execute models, programs, tools or network calls.
- It requires the worker to have an enabled database registration and secret.
- It operates on the PostgreSQL queue and leaves interrupted leases UNCERTAIN.
- `external_effect_reconciliation.reject_unexecuted_proposal()` only rejects a
  PROPOSED record after an explicit project-scoped reviewer grant.
- Effect and execution reconciliation are separate, explicit operations.

Reconciliation remains an internal Python operation; it now authenticates an
individual AUDITOR credential and project-scoped grant in-transaction. This
does not establish independent human identity or production authorization. No
external effect execution is enabled.

Next mandatory tests: multiple workers concurrently claiming a queue,
project pause/claim races, simulated crash and credential revocation, and
reconciliation of ambiguous effects. Do not call M2 accepted before actual
PostgreSQL integration tests pass.
