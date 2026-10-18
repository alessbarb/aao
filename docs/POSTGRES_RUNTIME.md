# PostgreSQL development runtime (M1)

AAO now includes a **separate, actually PostgreSQL-backed API** at
`aao.pg_work:app`. The original `aao.main:app` remains SQLite-based.

This is a deliberate incremental cutover. It is not a transparent or complete
migration: use the PostgreSQL endpoint only for development mandates, projects,
grants, work creation and work admission. No real agents or external effects.

## Isolated setup

Requires a development PostgreSQL database.

```sh
python -m pip install -e '.[postgres]'
psql "$AAO_POSTGRES_URL" -v ON_ERROR_STOP=1 -f db/postgres/001_foundation.sql
psql "$AAO_POSTGRES_URL" -v ON_ERROR_STOP=1 -f db/postgres/002_dev_identity.sql
export AAO_CEO_TOKEN='locally-generated-secret'
export AAO_WORK_TOKEN='different-locally-generated-secret'
uvicorn aao.pg_work:app --host 127.0.0.1 --port 8001
```

**Do not expose port 8001 beyond loopback.** Both secrets are development
credentials, not a production identity system. PostgreSQL permissions,
RLS, authenticated agent IDs, independent reviews and true resource/risk checks
are not yet established. `work.admit` presently uses development-only
assumptions for low risk and sufficient resources; it does not authorize
real execution.

The original schema includes UUID principals and FK constraints. The second
migration relaxes those to text development identities. Do not reuse these
migrations unchanged for production.

## Review and work progression (incremental)

The PostgreSQL service now exposes `POST /v1/work/{id}/progress` and
`POST /v1/work/{id}/reviews`. Progression follows
`READY -> IN_PROGRESS -> IN_REVIEW -> VERIFIED -> DONE`.
Only the review endpoint can reach VERIFIED. A rejected review returns the
task to IN_PROGRESS; completion requires an accepted review record.
Review identity derives from the dedicated development review token, not from
the request body. The work author is also bound to the development worker
credential rather than trusting a caller-supplied author ID.

Grant checks use exact principal/project/capability matching and honor
`expires_at`. Test coverage is included for a disposable PostgreSQL database.

**Security limits:** development credentials still authenticate entire shared
roles; all approved evidence strings are references, not cryptographically
verified artifacts. No OAuth/OIDC identities, signed approvals, reviewer
qualification/independence assessment, project-scoped read authorization,
migration/rollback system, worker integration, dynamic risk assessment or
production-grade audit integrity exists yet. AAO remains development-only.
