# AAO verification evidence register — append-only snapshots

Each entry records evidence and status at its stated revision/time. Earlier
"pending" or "not verified" statements describe those checkpoints only and
are superseded where a later entry says validation was completed. Current
acceptance remains unproven unless explicitly supported by competent review;
the latest local engineering run is not independent review or M2 acceptance.

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

## Shared-token retirement increment — validation

The validation status described below is historical. After `a47c853`, the
PostgreSQL API shared-auth fallback was removed and integration scenarios were
migrated to individual credentials. On `ca1857e8fa387f6834540b70f21bf11202cfc8e3`,
compileall, Ruff, pip check, diff check and the full suite ran against the
explicitly disposable database configured by `.env.test`: **52 passed, 0
skipped, 0 warnings**. Ruff reported `All checks passed!`, pip check reported
`No broken requirements found`, and `git diff --check` exited successfully.
GitHub Actions run `39252871118` completed successfully for commit
`7f7fd63483f5dc467a464db67ef87022e7254dff`. CI covers compileall, Ruff,
migrations against disposable PostgreSQL, integration tests and pip check.
This is not independent review or M2 acceptance.

## PostgreSQL-clock lease expiry and delayed completion

At `02603d680520e034dce2908f575038411c6e73df`, lease issue, completion
expiry validation, and quarantine compare against PostgreSQL `clock_timestamp()`;
the API no longer accepts caller-supplied timestamps for these decisions. The
full local disposable-database suite passed **52 tests, 0 skipped, 0
warnings**. The delayed-completion integration scenario was also run three
additional times individually and passed each time. Compileall, Ruff, pip
check, and diff check passed. GitHub Actions run `39253290548` completed
successfully on the same SHA. This covers one controlled lock-wait schedule,
not repeated adversarial race testing or M2 acceptance.

## Completion/quarantine ordering after lease expiry

Commit `9f24450e45f44f128e0de320809b7e6b9f47955b` adds a lease integration
scenario competing
completion with `quarantine_expired()` for the same queue row after the
database-clock deadline. Three consecutive local reruns passed, each asserting
expired completion is denied and final state is `UNCERTAIN`. The full local
disposable PostgreSQL suite passed **52 tests** with compileall, Ruff, pip
check and diff check clean. GitHub Actions run `39253753026` passed on the same
SHA. This is a bounded controlled schedule, not proof of all
possible orderings or independent review.

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

## M2 transaction-time principal guard — candidate (not yet validated)

The work API now rechecks principal credential state and principal kind under a PostgreSQL row lock inside `require_grant` before checking a project grant. The earlier separate authentication could otherwise allow a revoked credential to keep using its resolved identity in a subsequent transaction. Three unit test cases cover inactive/missing/wrong-kind principals, allowed identities and disallowed shared fallback. See `PRINCIPAL_AUTHORITY_AND_REVOCATION_BOUNDARIES.md` for scope and remaining unprotected read routes. No local tests have been run on this change; the previous 47 passing tests belong to `5fe0b4b86d999b020e928e0bd4e8375e5c0dc7c9`. Independent security review and M2 acceptance remain pending.

## M2 grant-boundary validation — 2026-10-19

Operator ran at `87779b5d8422d33e7f8befbe87c4e4ff307cee52` with Python 3.12.13 and pytest 9.1.1: `python -m compileall -q src tests` succeeded, `python -m ruff check src tests` reported `All checks passed!`, and `AAO_ENV=test AAO_ENV_FILE=.env.test python -m pytest -v -rs -W error` collected and passed **50/50 tests**, 0 failures, 0 skipped, and 0 warnings in **2.43 seconds**. This is a local operator-reported result, including the three additional grant-boundary tests. It demonstrates the implemented test scope only, not an adversarial revocation race or independent security audit. M2 remains open.

## M2 project-read revalidation — superseded by validation below

After the 50-test baseline at `87779b5d8422d33e7f8befbe87c4e4ff307cee52`, the project listing route was changed to recheck individual AGENT credential status with `SELECT ... FOR SHARE` in its database transaction, before reading project grants. One unit test covers inactive, absent, wrong-kind, and active principals with a stubbed transaction. The pending local validation stated here has since been completed; see the B023 baseline repair entry below. No actual concurrent credential revoke/read race is proven, and M2 remains unaccepted.

## B023 baseline repair and local validation — 2026-10-19

- Validated revision: `d080da58d4a8a41749a932d8fdf2c1caec5ac652` on `feat/aao-m0-foundation`.
- Fixed `B023` in `test_project_listing_rechecks_active_reader_in_transaction` by using a transaction-context-manager factory that binds each loop's selected database instance; no suppression was added.
- Local checks on that exact revision: `python -m compileall -q src tests` succeeded; `python -m ruff check src tests` passed; `AAO_ENV=test AAO_ENV_FILE=.env.test AAO_TEST_DB_DISPOSABLE=yes python -m pytest -q -rs -W error` completed **51 passed**; `python -m pip check` reported no broken requirements; `git diff --check` passed. Pytest reported no skips or warnings.
- The PostgreSQL integration cases ran under the explicit disposable-database gate. This is local engineering evidence only; it is not independent security review or M2 acceptance. This run does not demonstrate an actual concurrent revocation race.
- PR #1 is merged and the branch currently contains this commit beyond its remote-tracking branch. CI for the prior revision `60de4cb7792a3e7a8229f1e9487bdac49f828294` failed; this revision has not yet been pushed and therefore has no CI result here.

## Grant revocation serialization — 2026-10-19

- Revision: `78fd000e65388dbee9fc0aefaa58391ba9541d7c` on
  `feat/aao-m0-foundation`.
- Added CEO-only exact grant deletion with an atomic `grant.revoked` event.
  Protected API reads/writes, queue claim/completion, and reconciliation checks
  now hold the matched grant tuple under `FOR SHARE`. Grant validity predicates
  use `clock_timestamp()` rather than PostgreSQL transaction-start `now()`.
- Added disposable-PostgreSQL tests demonstrating that deletion blocks behind
  a transaction after `require_grant`, subsequent protected work is denied,
  and a grant expiring while the check waits behind a row update is denied.
- Local validation on this exact source tree: `python -m compileall -q src
  tests`; `python -m ruff check src tests` (**All checks passed**);
  `AAO_ENV=test AAO_ENV_FILE=.env.test AAO_TEST_DB_DISPOSABLE=yes python -m
  pytest -q -rs -W error` (**53 passed, 0 skipped, 0 warnings**, 3.66 s);
  `python -m pip check` (**No broken requirements found**); `git diff --check`
  passed. These PostgreSQL tests ran under the explicit disposable-database
  gate.
- GitHub Actions run `39250603339` completed successfully on commit
  `a56fcca70f872b07734ddf98785bc753d6daf948`, including migrations, compile,
  Ruff, disposable PostgreSQL tests with warnings as errors and `pip check`.
- A read-only agent engineering review found no critical lock defect, while
  noting that the test covers a grant-check transaction rather than a complete
  business mutation, and that repeated adversarial schedules remain absent.
  This is not independent formal security review, auditor acceptance or M2
  closure.

## Unified execution identity — 2026-10-19

- Source revision: `db7494b7e155bb50740d05a6c9c11484445cec43`; CI workflow
  correction: `585b422eebd9fa55e0bb7ed93f0cd281bad9233b`.
- Execution claim/completion and the inert worker now require individual AGENT
  credentials. The legacy verifier and its test have been removed. Migration
  `006_unified_execution_identity.sql` moves legacy rows to the AGENT
  credential registry, aborting on principal/digest collisions, then drops
  `worker_registrations`. CI seeds a fixed non-secret legacy fixture before
  applying migration 006 and verifies the transferred identity in the
  disposable PostgreSQL integration suite.
- Local validation after applying migration 006 to the explicitly designated
  `aao_test` database: **52 passed**, zero skips/warnings; Ruff, compileall,
  pip check and `git diff --check` passed. This local database had no seeded
  legacy row, so data transfer is specifically exercised by CI instead.
- CI run `39251426719` failed because the fixture was initially seeded after
  migration 006. The workflow ordering was corrected; run `39251540849` passed
  on `585b422eebd9fa55e0bb7ed93f0cd281bad9233b`, including the legacy-row
  transfer fixture, migrations, Ruff, compileall, PostgreSQL tests (**52
  passed**) and pip check.
- This proves the migration path for the fixed fixture and the engineering
  checks at the listed revisions. It is not adversarial security review,
  broad collision-case testing, production migration approval, or M2
  acceptance.

## Authenticated execution and effect reconciliation — 2026-10-19

- Revision: `d8a87cb75f392a66e5366547acff2094b817fd6e` on
  `feat/aao-m0-foundation`.
- Both PostgreSQL reconciliation helpers now accept an AUDITOR bearer
  credential, resolve it to an enabled AUDITOR principal under `FOR SHARE`
  inside the same transaction, then check the project grant. Caller-supplied
  reviewer IDs are no longer accepted. CEO grant schema now admits the two
  reconciliation capabilities and associates them with AUDITOR principals.
- The disposable-PostgreSQL integration suite exercises rejected ungranted
  auditors, AGENT denial, successful execution retry reconciliation, effect
  proposal rejection, and a real separate-connection lock wait proving
  revocation blocks behind the authenticated transaction. After revocation,
  the old credential is denied.
- Local exact-tree checks: `python -m compileall -q src tests`, Ruff, full
  PostgreSQL-gated pytest (**53 passed, 0 skipped, 0 warnings**), `pip check`
  and `git diff --check` passed.
- CI run `39252195117` passed its disposable PostgreSQL migrations, static
  checks, full integration suite (**53 passed**) and `pip check` on this SHA.
- Remaining limitations: evidence references are not verified; reconciliation
  has no HTTP endpoint; only one lock schedule is covered; grant/lease/effect
  retry races, independent security review and competent M2 acceptance remain
  open. This is not M2 closure.

## Effect proposal/retry serialization

Commit `62ef676a67851d976f6d327800d46b247bdea956` locks the execution row
before checking/inserting an effect proposal and accepts a new proposal only
while that execution is `RUNNING`. This serializes proposal admission against
the retry transaction's execution-row lock: a prior proposal is visible to the
retry check; a retry that commits first leaves a queued execution, for which a
new proposal is denied. Local disposable PostgreSQL validation passed **52
tests** with compileall, Ruff, pip check and diff check clean. GitHub Actions
run `39253994700` passed on the same code SHA. This verifies the implemented
admission boundary, not every possible proposal/retry schedule and not any
external effect execution.

## Concurrent effect proposal versus safe retry

Commit `919ce2118a37dd65763516748979494ce6f96e61` adds a barrier-started
PostgreSQL race between `propose()` and `RETRY_CONFIRMED_SAFE`. The test asserts
the serialized outcomes: if proposal admission wins, retry is denied because
an effect exists; if retry wins, the execution is queued and proposal is denied.
The race scenario passed ten consecutive local reruns, and the full disposable
PostgreSQL suite passed **52 tests** with compileall, Ruff, pip check and diff
check clean. GitHub Actions run `39254352077` passed on the same code SHA.
These are bounded controlled tests, not exhaustive scheduling or adversarial
review; no external effect was executed.

## Cold PostgreSQL restart with an expired execution lease

On the current code checkpoint `5d64de31429748d3150a919dedc10ae27428b640`,
I created a separate disposable `postgres:16-alpine` container, applied
migrations 001-006, staged and claimed one inert execution with a one-second
lease, then restarted that PostgreSQL container. The database retained the
execution as `RUNNING` with one attempt. After reconnecting, one call to
`quarantine_expired()` moved it to `UNCERTAIN`; the persisted journal contained
`claimed` then `quarantined`, and the attempt count remained one. The temporary
container was removed afterward. This demonstrates single-instance database
restart persistence and explicit expired-lease quarantine, not automatic
recovery, a process crash during transaction commit, failover, or repeated
restart schedules. No production database or external effect was used.

## Inert queue staging requires execution authority

Commit `9f6f3e3dc80967e794104ca8c97e347cb50637bd` changes
`POST /v1/work/{id}/stage-inert` to require both `work.admit` and
`execution.claim`, with both active AGENT credential and grant checks held in
the staging transaction. The PostgreSQL integration test confirms an otherwise
admitted agent without `execution.claim` receives 403, then succeeds after the
grant is added; staging remains fixed/inert and feature-flagged. Local full
suite: **52 passed**, no skips/warnings; compileall, Ruff, pip check and diff
check clean. GitHub Actions run `39254714699` passed on the same code SHA.

## Agent credential rotation serializes with in-transaction authentication

Commit `627a3cdd5fd3bd5936f956e2caa9e8a3ddf511b6` adds a PostgreSQL
integration schedule that resolves an AGENT token through
`authenticate_in_transaction()` (holding its credential row `FOR SHARE`), then
starts a concurrent digest rotation on a separate connection. The test checks
PostgreSQL reports the rotation blocked until the authenticated transaction
commits; afterward the old token is rejected and the new token resolves to the
same principal. Five consecutive local reruns passed; full local validation
passed **53 tests** with compileall, Ruff, pip check and diff check clean.
GitHub Actions run `39254963905` passed on the same code SHA. This validates
credential-row serialization, not a complete queue-claim/completion business
operation racing rotation or all revoke/rotate schedules.

## Project-grant revocation versus a protected HTTP write

Commit `3168ec3ba14cd7093dc34c435db7bdcc466bb32f` adds an integration test
that deliberately blocks an HTTP work-creation request at its final INSERT
using a table lock, after the request has authenticated and acquired its
project grant `FOR SHARE`. It then starts the actual grant-revocation HTTP
route on another thread and verifies PostgreSQL reports revocation blocked by
the work request's backend. Releasing the table lock allows the work write to
commit first; revocation then succeeds, and the test verifies both the durable
work row and absent grant. Five consecutive local reruns passed; full local
validation passed **54 tests**, with compileall, Ruff, pip check and diff check
clean. GitHub Actions run `39255217942` passed on the same code SHA. This is
one controlled HTTP mutation/revocation ordering, not broad coverage of all
protected routes, claim/completion, or adversarial schedules.

## Execution claim versus grant revocation

Commit `4df66bb35a55a20c47a991e5edb13977c9faf8f3` adds a separate PostgreSQL schedule for
`execution_queue.claim()`: a table lock stalls the claim after it has verified
and locked `execution.claim` `FOR SHARE`; concurrent deletion through the CEO
grant-revocation HTTP route is observed waiting on that transaction. Releasing
the lock lets the claim commit first and the revocation finish second. The test
then verifies the execution is RUNNING and another claim is denied. Five
consecutive local reruns passed; the full local suite passed **55 tests** with
compileall, Ruff, `pip check`, and `git diff --check` clean. GitHub Actions run
`39255590963` passed on the same code SHA. This validates one claim/revocation schedule only; it does
not establish behavior for every queue operation, credential revocation, or
hostile production concurrency.

## Execution completion versus grant revocation

The new integration schedule claims an inert execution, then holds an
`ACCESS EXCLUSIVE` lock on `execution_journal` so completion pauses at its
journal insert after locking the execution, active project, AGENT credential,
and `execution.claim` grant. The actual CEO grant-revocation route is observed
waiting on that transaction. Releasing the lock allows completion to commit
before revocation; afterward, the test confirms `SUCCEEDED` and verifies another
completion attempt is denied for the missing grant. Five consecutive local
reruns passed; the full suite passed **56 tests**, and compileall, Ruff,
`pip check`, and `git diff --check` were clean. CI has not yet run for this
change. This is one controlled claim-completion/revocation ordering and does
not prove credential revocation races, all queue operations, or hostile
production schedules.

CI run `39255841351` passed for code commit `773a5270cd25ec812db6272a4a26026d50f7d598`, including PostgreSQL integration tests, compilation, Ruff, and dependency checks.
