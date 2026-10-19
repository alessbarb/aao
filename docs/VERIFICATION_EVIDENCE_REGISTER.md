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

## Incremento de restricción de tokens compartidos — pendiente de validación

Tras las 43 pruebas confirmadas, se incorporaron las rutas individuales de
lectura de proyectos/tableros y el bloqueo de tokens compartidos de workers y
auditores fuera de desarrollo o al establecer
`AAO_ALLOW_SHARED_DEV_TOKENS=false`. Se añadieron pruebas negativas.
**No se ha ejecutado todavía la nueva suite en el ordenador del operador.**

## Validación de autenticación transitoria — 2026-10-19

El operador actualizó mediante `git pull --ff-only` hasta `cb65222` y ejecutó `AAO_ENV=test AAO_ENV_FILE=.env.test python -m pytest -v -rs` con Python 3.12.13: **46 passed, 0 failed, 0 skipped, 1 warning** en 2.45 s. Las tres pruebas negativas nuevas de tokens compartidos y credenciales individuales superaron la suite, así como la integración ampliada de lectura de proyectos/tableros. La advertencia sigue siendo Starlette/httpx. Esta evidencia procede del operador y no sustituye auditoría independiente ni aprobación de M2.

## M2 ciclo gobernado de credenciales — pendiente de validación

Se añadieron rutas de desarrollo de emisión, rotación y revocación de
credenciales individuales protegidas por el token CEO provisional. Los tokens
se generan aleatoriamente y solo se persisten como resúmenes; hay pruebas de
control de autoridad, duplicados, invalidación por rotación, revocación y
registros de eventos. **No hay todavía salida de ejecución local para esta
revisión.** La referencia verificada continúa siendo la suite de 46 pruebas.

## Validación del ciclo de credenciales — 2026-10-19

El operador actualizó hasta la revisión `1006902` y ejecutó `AAO_ENV=test AAO_ENV_FILE=.env.test python -m pytest -v -rs`: **47 passed, 0 failed, 0 skipped, 1 warning** en 2.58 segundos, Python 3.12.13. Pasó `test_ceo_governed_principal_issue_rotate_revoke`, que verifica emisión, rotación, revocación y eventos. Advertencia de deprecación Starlette/httpx. Evidencia local comunicada por el operador; no constituye revisión independiente ni aceptación final de M2.

## Naming refactor — 2026-10-19 (structural changes only)

- Branch: `feat/aao-m0-foundation`; original inspected HEAD: `a58f0f643db82350bcbbc477ac2bb1fae3bdf26a`.
- Updated the configuration test import and runtime/documentation references to existing responsibility-based names. No applied SQL migration was changed and no external executor was enabled.
- Repository-level comparison verified that these changes affect the README, the configuration test and operational documentation only.
- **Validation not yet executed on the amended branch:** pytest collection, full PostgreSQL suite, static analysis, import/link checks and runtime smoke test. The previous `47 passed` result is historical and belongs to commit `1006902c2184fc7fed0f76c677c64ab6599f4669`, not these edits.
- The large `tests/test_postgresql_workflow_integration.py` suite still groups distinct responsibilities; splitting it safely remains pending and must preserve the disposable database gate.
- **Acceptance blocked** until local test evidence, inspection of any remaining obsolete references, independent review and competent M2 approval. This note is not an acceptance record.

## PostgreSQL test responsibility split — 2026-10-19

- The 12 previously passing PostgreSQL integration scenarios were redistributed without deliberate behavioral changes into `test_project_workflow_integration.py` (4), `test_execution_leases_integration.py` (3), `test_execution_reconciliation_integration.py` (1), and `test_principal_credential_lifecycle_integration.py` (4).
- Each scenario retains its individual opt-in disposable PostgreSQL database guard. The original monolithic file has been removed; its historical test evidence remains associated with the previous revision.
- **Validation on the resulting HEAD is pending:** full pytest suite and Ruff lint. No new proof of passing tests is asserted by this split.

## Verified structural baseline and HTTPX2 deprecation resolution — 2026-10-19

Operator supplied terminal output for commit `5fe0b4b86d999b020e928e0bd4e8375e5c0dc7c9` on Python 3.12.13. Local `python -m pip install -e '.[dev,postgres]'` installed `httpx2==2.14.0`; `python -m pip check` reported no broken requirements, `python -m ruff check src tests` passed, and `AAO_ENV=test AAO_ENV_FILE=.env.test python -m pytest -v -rs -W error` completed **47 passed, 0 failed, 0 skipped, 0 warnings in 3.30 seconds**. Thus the naming restructure and test-suite split have a verified local functional/static baseline, and the previous Starlette HTTPX deprecation no longer occurs under warnings-as-errors. This is operator-reported evidence only; no independent architecture/security review was performed, and M2 is not accepted.
