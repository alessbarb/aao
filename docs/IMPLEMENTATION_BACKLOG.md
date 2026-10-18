# AAO implementation backlog — initial internal planning seed

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
