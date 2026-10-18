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
