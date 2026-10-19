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

## Validación local comunicada — 2026-10-19

Operador ejecutó `AAO_ENV=test AAO_ENV_FILE=.env.test python -m pytest -v -rs` con Python 3.12.13, pytest 9.1.1 y PostgreSQL 16.15: **35 passed, 0 failed, 0 skipped, 1 warning, 1.80 s**. Las 8 pruebas PostgreSQL y las 4 pruebas de configuración se ejecutaron, no fueron omitidas. Advertencia: deprecación Starlette/httpx. La evidencia es la salida facilitada por el operador; no constituye revisión independiente ni prueba de seguridad de producción. M2 continúa abierto.

## Verificación del incremento 005 — 2026-10-19

El operador ejecutó la migración `005_principal_credentials.sql` sobre `aao_dev` y `aao_test`: ambas finalizaron con `COMMIT`. La suite `AAO_ENV=test AAO_ENV_FILE=.env.test python -m pytest -v -rs` obtuvo **40 passed, 0 failed, 0 skipped, 1 warning**, en 1.98 segundos, Python 3.12.13 y PostgreSQL 16. La evidencia procede del registro de terminal facilitado por el operador. La advertencia sigue siendo la deprecación Starlette/httpx. Este resultado no autoriza producción ni cierra M2.

## Validación local adicional — 2026-10-19

El operador comunicó una ejecución completa posterior a la incorporación de identidades individuales de agentes: `AAO_ENV=test AAO_ENV_FILE=.env.test python -m pytest -v -rs`: **41 passed, 0 failed, 0 skipped, 1 warning**, duración 2.10 s. Esto valida el caso de aislamiento y revocación de la API de desarrollo incluido en la revisión `b1b9125`, no una identidad unificada del ejecutor ni garantías de producción.

## Validación del contrato `execution.claim` — 2026-10-19

El operador confirmó `git pull --ff-only` hasta `3de90ea` y la ejecución `AAO_ENV=test AAO_ENV_FILE=.env.test python -m pytest -v -rs`: **43 passed, 0 failed, 0 skipped, 1 warning** en 2.29 s, Python 3.12.13. La prueba `test_individual_agent_claim_and_revocation` pasó junto con la nueva prueba del contrato exacto `execution.claim`. Persiste la advertencia de deprecación Starlette/httpx. Esta evidencia es una prueba local comunicada por el operador y no constituye revisión independiente ni autorización de ejecución externa.
