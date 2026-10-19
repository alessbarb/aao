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


## Increment: PostgreSQL workboard on the same origin

The PostgreSQL API now serves the **read-only** workboard at its root
(`http://127.0.0.1:8001/`). It fetches `/v1/projects` and each
`/v1/projects/{id}/board` from the **same PostgreSQL API**, not from
the SQLite API on port 8000. No CORS proxy and no data synchronization
between SQLite and PostgreSQL is involved.

Project reads continue to require the development CEO token. On an
initial 403, the browser prompts for the development CEO token and holds
it only in the current tab's JavaScript memory, not localStorage or URL.
This is a **local development workflow only**; entering privileged tokens
in browser prompts is not an acceptable production authentication method.

SQLite remains available separately at port 8000 for backward inspection,
but it is no longer required to view the PostgreSQL workboard. The runtime
is **not fully unified**: CEO/project auth, work submission, effects,
and lifecycle still need a single hardened PostgreSQL application.

A test was added to verify same-origin page delivery and fail-closed
project listing without valid CEO credentials. It has not yet been run
against the operator's PostgreSQL instance.


## Project-scoped reader integration

The PostgreSQL development API accepts either the configured CEO token or
the configured worker token on project and board reads. The CEO development
credential can see all projects; the worker identity sees only projects with
an explicit unexpired `project.read` grant, enforced for both listing and
direct board URLs. Ungranted project IDs cannot be read with the worker token.

This **does not** implement strong identity authentication: there is still one
shared worker development credential and the browser presently prompts only for
the CEO credential. Production read isolation requires distinct principals,
role separation, server-enforced session identity, least-privilege database
roles and adversarial security review.

An isolated integration regression test demonstrates worker visibility for
one granted project and denial for another. This test is not yet verified
against the operator's PostgreSQL database.
