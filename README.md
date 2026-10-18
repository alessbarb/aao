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
