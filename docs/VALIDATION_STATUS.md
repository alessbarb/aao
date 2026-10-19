# AAO local validation evidence — 2026-10-19

## Environment
- Branch: `feat/aao-m0-foundation`
- Revision validated: `d6abac3ba6361094dfda7b1976b4e9741c1cc35c`
- Python: 3.12.13; pytest: 9.1.1
- PostgreSQL: 16-alpine, Docker Compose development configuration; isolated database `aao_test`
- Migrations: 001, 002, 003, 004 completed with COMMIT and 12 tables listed

## Evidence supplied by local operator
- Initial `python -m pytest -q`: 23 passed, 6 skipped, one Starlette/httpx deprecation warning.
- First PostgreSQL integration run: 3 passed / 3 failed (unscoped queue claims).
- Second PostgreSQL integration run: 5 passed / 1 failed (global expired lease quarantine count).
- Final `python -m pytest -v -rs tests/test_postgres_integration.py`: **6 passed**, one deprecation warning, 1.16 s.
- Final `python -m pytest -q`: **29 passed**, one deprecation warning, 1.48 s.
- Development FastAPI application booted and served root and project API HTTP 200; PostgreSQL service itself not yet demonstrated running via Uvicorn.

## Meaning and boundaries
This validates the current **test suite and migrations** in the user's local environment. It does not prove complete recovery under crashes, denial of cross-project reads, real operator/authenticated auditor identities, independent audit signatures, external-effect idempotence, or readiness for autonomous actions. SQLite and PostgreSQL runtime entrypoints remain separate. CI is deferred per owner instruction.

## Next required evidence
1. Real cold-restart of PostgreSQL and rerun selected recovery/concurrency tests.
2. Fail-closed project read isolation and authorization tests.
3. Lifecycle and identity for independently attested auditors and workers.
4. Full PostgreSQL service startup and browser health smoke.
5. Explicit owner acceptance after relevant independent security review.
