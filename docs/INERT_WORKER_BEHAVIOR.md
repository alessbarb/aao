# M2 — Inert worker and effect proposal reconciliation

- `inert_worker.run_one()` performs one atomic claim and one completion.
- It intentionally cannot execute models, programs, tools or network calls.
- It requires the worker to have an enabled database registration and secret.
- It operates on the PostgreSQL queue and leaves interrupted leases UNCERTAIN.
- `external_effect_reconciliation.reject_unexecuted_proposal()` only rejects a
  PROPOSED record after an explicit project-scoped reviewer grant.
- Effect and execution reconciliation are separate, explicit operations.

The reconciler remains a Python-only function; its caller-supplied reviewer
identity is not cryptographically authenticated. No external effect execution
is enabled. This is not production-safe.

Next mandatory tests: multiple workers concurrently claiming a queue,
project pause/claim races, simulated crash and credential revocation, and
reconciliation of ambiguous effects. Do not call M2 accepted before actual
PostgreSQL integration tests pass.
