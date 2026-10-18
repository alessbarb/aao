# M1 next gate — PostgreSQL and trusted project-scoped identity

## Current reality
The FastAPI application still uses SQLite. The PostgreSQL module is a connectivity probe,
not a database adapter. PostgreSQL schema 001 is not applied automatically. No
production identity provider is configured.

## Introduced
- Dedicated development service-token verification maps a verified credential to a fixed
  identity; callers cannot choose the mapped identity.
- Exact project capability matching is available as a pure decision helper.
- PostgreSQL connectivity and schema version probes are explicit; no implicit DB cutover.

## Required before connection to external systems
1. Replace shared development tokens with OIDC/mTLS-authenticated principals.
2. Store grants in PostgreSQL and enforce them on both reads and mutations.
3. Use transactional outbox and database migrations with rollback plans.
4. Add evidence provenance, independent review and authorization at every side-effect boundary.
5. Validate durable execution across process crashes and project suspension.
6. Demonstrate no cross-project data reads or writes under adversarial tests.

The next slice must wire grant persistence into the API rather than merely defining grant types.
