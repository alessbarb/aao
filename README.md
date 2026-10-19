# Autonomous AI Organization (AAO)

An independently governed, private, multi-project AI organization. AAO is **not** Biopeia-specific; Biopeia is intended to be its first authorized project.

## Current milestone

**M0 foundation candidate** — not a deployed autonomous agent system. This branch implements:
- deterministic constitutional gates for reserved actions;
- CEO-confirmed draft mandates (local development token only);
- project creation against confirmed mandates;
- internal Kanban work records and event history;
- fail-closed verification (no premature DONE);
- automated tests and CI.

Not implemented: independent review, production authentication, distributed workers, model adapters, durable engine, PostgreSQL deployment, office UI, and autonomous scheduling. No external effects are enabled.

## Current PostgreSQL development path (19 October 2026)

The sections below preserve the incremental history of the prototype; they must not be read as the present acceptance status. The PostgreSQL-backed development API is `aao.work_management_api:app`, while the separate SQLite prototype remains at `aao.sqlite_api:app`. The PostgreSQL integration suite is `tests/test_project_workflow_integration.py`, `tests/test_execution_leases_integration.py`, `tests/test_execution_reconciliation_integration.py`, and `tests/test_principal_credential_lifecycle_integration.py`. Schema migrations `001` through `005` are immutable historical artifacts.

For the local disposable test database, after configuring the private `.env.test` file and applying the existing migrations:

```sh
AAO_ENV=test AAO_ENV_FILE=.env.test python -m pytest -v -rs
python -m uvicorn aao.work_management_api:app --host 127.0.0.1 --port 8001
```

The 47 passing tests were recorded against commit `1006902c2184fc7fed0f76c677c64ab6599f4669` **before** the naming refactor. They have not been rerun on the current branch by this documentation change. Individual development credentials and a deliberately inert execution worker are present, but M2 remains open and external effects remain disabled. This is not production authentication, independent security acceptance, or permission to enable autonomous operations.

## Local development

Requires Python 3.12+.

```bash
python -m pip install -e '.[dev]'
export AAO_CEO_TOKEN='local-dev-only-change-me'
export AAO_WORK_TOKEN='local-worker-only-change-me'
export AAO_REVIEW_TOKEN='local-review-only-change-me'
uvicorn aao.sqlite_api:app --reload
pytest -q
```

Open `http://127.0.0.1:8000/docs` to examine the draft API.

Do not expose this dev server publicly; the development token headers are not sufficient for production authentication. All mutating endpoints require a token in the development API; read endpoints remain unauthenticated and must not be exposed to untrusted networks.

## Design principles

- CEO mandates are explicit and confirmed.
- All ordinary operations are delegated, but every effect must be authorized.
- Kanban belongs to AAO, not GitHub Issues/Projects.
- Workers and language models are replaceable.
- Projects own their isolated memory and reserved capacity.
- Evidence and independent audit gate completion.
- Autonomous rollout is gradual and begins in an isolated environment.

See [Constitution](docs/CONSTITUTION.md).

## M1 candidate (development only)

This branch adds declared work author identity, separate reviewer token, review decision records, and gated transitions into VERIFIED/DONE. Pause/resume is available to the development worker credential; cancellation requires CEO credentials. None of these tokens establish real actor identity or independent auditor authority. Read APIs are still unscoped and must remain on a trusted development network.

The SQLite schema uses additive prototype initialization; PostgreSQL migrations, verified authN/authZ, actual evidence checking, independent audit, distributed execution and a UI remain necessary. See [M1 scope](docs/WORK_MANAGEMENT_SCOPE.md).

## Latest increment: M1/M2 engineering candidates

The branch also contains:
- a PostgreSQL foundation schema (NOT wired to the API yet);
- pure project-scoped grant checks with expiry;
- a deterministic admission policy with resource/risk gates;
- a development-only reviewer workflow and project pause/resume/cancel;
- an **inert SQLite-backed durable execution queue** with lease quarantine and explicit reconciliation.

The execution queue is intentionally not callable by AI models, does not perform external effects, and is not a production distributed workflow engine.

Critical remaining gates: database cutover, trusted identities, DB-scoped permissions and read isolation, independent reviewer attestation, effect ledger, external tool authorization, real worker runtime, evaluation suite and deployment controls.

See [M1 scope](docs/WORK_MANAGEMENT_SCOPE.md), [PostgreSQL/authorization](docs/DATABASE_AUTHENTICATION_TRANSITION.md) and [M2 execution boundary](docs/EXECUTION_SECURITY_BOUNDARIES.md).

## Read-only workboard and inert queue prototype

The FastAPI root route `/` now serves a **read-only HTML Kanban** based on the actual
`/v1/projects` and `/v1/projects/{id}/board` API endpoints. No demo data or
background animations are presented as actual work.

The optional `/v1/work/{id}/sandbox-queue` endpoint bridges the existing work
board and execution queue. It is disabled by default. For **local isolated
development only**, set `AAO_SANDBOX_QUEUE_ENABLED=true` before starting the API.
Its admission check only accepts a task already marked READY in an active
project with a confirmed mandate and enqueues a constant inert payload.
It does **not** execute tools, models or arbitrary user-specified commands.
It is not a substitute for trusted identity, resources, risks and project
permissions. Never enable it on a public or shared network.

The initial project workboard and the queue have automated test cases committed
but **their execution remains unverified in this session**. Do not promote or
deploy until runtime verification and independent security review.

## PostgreSQL development service (M1 next slice)

A separate API `aao.work_management_api:app` now uses PostgreSQL transactions for actual
mandate, project, project grant, work-item and READY-admission writes. This is
**not** yet a cutover of the original SQLite application, and it has no
agent execution, external integrations, secure production authentication,
independent-review endpoint or full workflows.

Read [PostgreSQL runtime setup](docs/POSTGRESQL_RUNTIME_OPERATIONS.md). It requires applying
`001_foundation.sql` and `002_dev_identity.sql` to a **fresh isolated development**
database, then running on localhost. The development identity migration relaxes
principal FK enforcement and is **not a production schema**.

An opt-in integration test exists in `tests/test_project_workflow_integration.py`, `tests/test_execution_leases_integration.py`, `tests/test_execution_reconciliation_integration.py`, and `tests/test_principal_credential_lifecycle_integration.py`.
Use it only on an explicitly disposable database:
```sh
export AAO_TEST_POSTGRES_URL='postgresql://...disposable-test-database'
export AAO_TEST_DB_DISPOSABLE=yes
pytest -q tests/test_project_workflow_integration.py tests/test_execution_leases_integration.py tests/test_execution_reconciliation_integration.py tests/test_principal_credential_lifecycle_integration.py
```
The test creates records and does not delete the database afterwards.

**Tests and actual PostgreSQL server execution have not been verified here.**

## M2 recovery increment

Added a one-shot **inert** worker, a restricted effect-proposal rejection function,
and an opt-in PostgreSQL concurrency test. See [M2 inert worker](docs/INERT_WORKER_BEHAVIOR.md).

The worker is not scheduled automatically, no AI models are connected, and no
external effect is performed. Database-backed tests still require a disposable
PostgreSQL instance. No verified test run or operational acceptance is claimed.

## Local configuration (development-only)

See [Configuration](docs/ENVIRONMENT_CONFIGURATION.md). Copy the sanitized
[environment template](.env.example) to `.env.local` and replace placeholders.
The Python services now load `.env.local` automatically without overriding
already-exported process environment variables. To choose `.env.test`, run
`AAO_ENV=test AAO_ENV_FILE=.env.test python -m pytest -q`.

Docker Compose needs its explicit loader:
`docker compose --env-file .env.local -f compose.dev.yaml up -d`.
All local dotenv variants are Git-ignored; only `.env.example` is tracked.

Do not create a fresh database password for an existing Docker volume without
also rotating it in PostgreSQL. Shared development tokens and dotenv files
are not suitable for production.
