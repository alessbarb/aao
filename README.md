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

## Local development

Requires Python 3.12+.

```bash
python -m pip install -e '.[dev]'
export AAO_CEO_TOKEN='local-dev-only-change-me'
export AAO_WORK_TOKEN='local-worker-only-change-me'
export AAO_REVIEW_TOKEN='local-review-only-change-me'
uvicorn aao.main:app --reload
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

The SQLite schema uses additive prototype initialization; PostgreSQL migrations, verified authN/authZ, actual evidence checking, independent audit, distributed execution and a UI remain necessary. See [M1 scope](docs/M1_SCOPE.md).

## Latest increment: M1/M2 engineering candidates

The branch also contains:
- a PostgreSQL foundation schema (NOT wired to the API yet);
- pure project-scoped grant checks with expiry;
- a deterministic admission policy with resource/risk gates;
- a development-only reviewer workflow and project pause/resume/cancel;
- an **inert SQLite-backed durable execution queue** with lease quarantine and explicit reconciliation.

The execution queue is intentionally not callable by AI models, does not perform external effects, and is not a production distributed workflow engine.

Critical remaining gates: database cutover, trusted identities, DB-scoped permissions and read isolation, independent reviewer attestation, effect ledger, external tool authorization, real worker runtime, evaluation suite and deployment controls.

See [M1 scope](docs/M1_SCOPE.md), [PostgreSQL/authorization](docs/POSTGRES_AUTH_MIGRATION.md) and [M2 execution boundary](docs/M2_EXECUTION_BOUNDARY.md).

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
