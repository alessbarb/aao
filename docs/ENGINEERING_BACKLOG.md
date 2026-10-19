# AAO implementation backlog — initial internal planning seed

**Status update — 2026-10-19:** this file began as a planning seed, not an
authoritative issue tracker. The PostgreSQL API, individual development
credentials, project-scoped API grants, durable inert queue, lease quarantine
and effect proposal/reconciliation helpers have since been implemented in
part. The current authorization inventory is
[`PRINCIPAL_AUTHORIZATION_MATRIX.md`](PRINCIPAL_AUTHORIZATION_MATRIX.md); the
latest exact local baseline is in
[`VERIFICATION_EVIDENCE_REGISTER.md`](VERIFICATION_EVIDENCE_REGISTER.md).
M2 remains in progress and is not accepted. Do not interpret old `[candidate]`
or `[BLOCKED]` labels below as live issue statuses.

## Current M2 engineering priorities

1. **Implemented in candidate code:** execution authenticates only through
   individual AGENT credentials. Migration `006_unified_execution_identity`
   transfers legacy worker identities (aborting on collisions) and removes
   `worker_registrations`. Transitional shared worker/reviewer credentials and
   runtime validation of migration on a disposable database remain.
2. **Partially implemented and locally validated:** CEO grant revocation is
   audited transactionally; API, execution and reconciliation authorization
   checks lock the matched grant row. PostgreSQL tests cover revocation waiting
   behind a protected authorization transaction and expiry during lock wait.
   Still required: repeated/adversarial schedules, real operation mutation and
   queue claim/completion races, credential rotation races, and review of
   long-running transaction expiry semantics.
3. **Implemented in candidate code and locally validated:** execution/effect
   reconciliation derives the reviewer from a locked individual AUDITOR
   credential inside the transaction, then checks the project grant. Tests
   cover AGENT denial, authorized AUDITOR paths and serialization between
   credential authentication and revocation. HTTP exposure still requires
   further design, evidence verification, and review.
4. Verify lease expiry, credential/grant revocation, effect proposal/retry,
   quarantine/completion ordering, and cold-restart recovery with repeated
   PostgreSQL concurrency tests.
5. Make PostgreSQL integration tests part of CI with a fresh disposable
   database and migrations; ordinary CI currently can skip those tests.
6. Obtain adversarial independent security/architecture review and competent
   acceptance. Codex cannot substitute for either.

This document is a repository bootstrap artifact. **It is not GitHub Issues or GitHub Projects as the operational Kanban.** On M1, import the work definitions into AAO's own database and manage all status transitions there.

## M0 · Constitutional foundation
- M0-01 [candidate] Policy engine for reserved/forbidden operations.
- M0-02 [candidate] CEO mandate draft and confirmation.
- M0-03 [candidate] Project creation gate.
- M0-04 [candidate] Internal work items and event record.
- M0-05 [BLOCKED] Production authentication, project-scoped roles, encrypted CEO approval channel.
- M0-06 [BLOCKED] Independent auditor decisions and appeals, evidence and audit integrity.

## M1 · Core work management
- M1-01 PostgreSQL migrations; transactional outbox and immutable audit hashes.
- M1-02 Project lifecycle with PAUSE and CEO-only CANCEL.
- M1-03 Task intake, triage, READY planner gate and dependency graph.
- M1-04 Evidence and independent review, risk-dependent acceptance.
- M1-05 React Kanban and portfolio dashboards, API auth and optimistic locking.
- M1-06 Confirmed mandates bound to exact immutable snapshots, with expiry/revocation.

## M2 · Durable execution
- M2-01 Evaluate Temporal against database-backed execution.
- M2-02 Workers, signed leases, fencing tokens and checkpoints.
- M2-03 External effects ledger with reconciliation and idempotency.
- M2-04 Sandbox runners with operation-scoped capabilities.
- M2-05 Stop controls independent of AI runtime.
- M2-06 Crash recovery, repeated event delivery and denied-action test suite.

## M3 · First autonomous crew
- M3-01 Persistent COO/planner, engineering agent and independent auditor identities.
- M3-02 Structured agent/job/tool contracts and provider-neutral adapters.
- M3-03 LLM/task routing with quotas and fallback.
- M3-04 Complete one isolated issue-equivalent workflow without CEO intervention.
- M3-05 Longitudinal test and independent safety review.

## M4+ · Growth
- M4 multiproject reservations, cross-project work and shared specialists.
- M5 knowledge isolation, publication, evaluation and agent version promotion.
- M6 contextual executive office, conversations, voice, Kanban/3D visual states.
- M7 24/7 reliability, autonomous rollout gates and real project onboarding.

## Hard gates
1. Production effects disabled until authenticated authorizations are deployed.
2. Review and DONE fail closed until independent evidence validation exists.
3. Self-evolution cannot modify or deploy the constitutional kernel.
4. External access restricted to approved workspaces and tool capabilities.
5. Any high residual risk or constitutionally reserved action waits for CEO confirmation.
6. No actual Biopeia project execution before CEO confirms an exact deployment mandate.
