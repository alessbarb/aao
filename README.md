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
uvicorn aao.main:app --reload
pytest -q
```

Open `http://127.0.0.1:8000/docs` to examine the draft API.

Do not expose this dev server publicly; the token header is not sufficient for production authentication.

## Design principles

- CEO mandates are explicit and confirmed.
- All ordinary operations are delegated, but every effect must be authorized.
- Kanban belongs to AAO, not GitHub Issues/Projects.
- Workers and language models are replaceable.
- Projects own their isolated memory and reserved capacity.
- Evidence and independent audit gate completion.
- Autonomous rollout is gradual and begins in an isolated environment.

See [Constitution](docs/CONSTITUTION.md).
