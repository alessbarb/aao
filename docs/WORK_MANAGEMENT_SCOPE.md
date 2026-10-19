# AAO M1 implementation boundary

M1 provides incremental project-state controls and a first independent review decision record. It is **not** production authorization.

- Projects may be paused through a development worker gate; cancellation requires a separate development CEO credential.
- Reviewers use a separate dev review credential and distinct declared reviewer identity.
- Accepted work requires an author identity and evidence references. This is a testable procedural safeguard, not cryptographic proof of identity or proof that evidence contents are correct.
- All review transitions are recorded transactionally with work status.
- Historical SQLite environments use additive initialization rather than schema migrations. Replace with PostgreSQL/Alembic before real deployment.
- No unauthenticated endpoints should be exposed on public networks. Read operations currently lack project-level scoping.

## Required before genuine autonomy
- Verified authentication and real project-scoped authorization.
- Proper evidence verification and independent review approval credentials.
- Durable execution, idempotency/reconciliation, audit integrity and emergency stop.
- Validated deployments and longitudinal recovery tests.
