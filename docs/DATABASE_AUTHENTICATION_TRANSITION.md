# M1 PostgreSQL and project authorization — candidate

## PostgreSQL foundation

`db/postgres/001_foundation.sql` defines an isolated, initial PostgreSQL schema using UUID primary keys, JSONB evidence, indexed task states, separate principals and project grants. It is not yet connected to the FastAPI runtime. The existing SQLite store remains the **only active backend**.

The migration is intended for an **empty development database**. It does not migrate SQLite data and is not a production cutover.

To check manually on an isolated PostgreSQL database:

```sh
psql "$AAO_DEV_DATABASE_URL" -v ON_ERROR_STOP=1 -f db/postgres/001_foundation.sql
```

No credentials should be stored in source control.

## Authorization semantics

The pure `has_capability()` function requires exact principal, project, and capability matches, checks account active state and expiry, and fails closed. Independent review requires a distinct principal of kind AUDITOR with a project-specific work.review grant.

**Not yet wired:** trusted identity provider or session authentication, lookup of grants from PostgreSQL, route-level permission enforcement, expiry/revocation invalidation, protected database roles, RLS, durable events, Alembic revision tracking or signature-based CEO approvals.

No claim of production security or reviewed deployment is made.
