# Principal authorization matrix

**Scope:** current development API and internal execution/reconciliation
operations, updated through `22f7310822c2ca3bfe59b8e2ccbb9d8dbc856b0d`.
This is an engineering inventory, not a production authorization policy or
independent security review. The PostgreSQL API and its internal helpers are
not a claim of M2 acceptance.

## External HTTP operations

| Operation | Authenticated identity / authority | Project capability and transaction check | Effect and known boundary |
| --- | --- | --- | --- |
| `GET /`, `GET /health` | None | None | Static workboard shell / service status only; health reports autonomous execution disabled. |
| `POST /v1/principals/credentials`, `/v1/principals/{id}/rotate`, `/revoke` | Static `AAO_CEO_TOKEN` bearer, compared before DB transaction | No project grant; lifecycle writes and audit event share a DB transaction | Development credential administration; no constitutional signature, multi-party confirmation, or production identity. |
| `POST /v1/mandates`, `/v1/mandates/{id}/confirm`, `/v1/projects` | Static CEO bearer | No project grant; mandate/project row checked or locked within transaction | Draft/confirm mandate and create project. CEO identity is a development bearer, not a verified constitutional actor. |
| `POST /v1/projects/{id}/grants` | Static CEO bearer | No project grant; project, active principal identity and capability-compatible principal kind are checked in the transaction; credential row is locked under `FOR SHARE` | Rejects unknown/disabled principals and Agent/Auditor capability mismatches before persisting the grant. Conflict no-op still emits a grant-created event. |
| `DELETE /v1/projects/{id}/grants/{principal}/{capability}` | Static CEO bearer | Deletes the exact matching grant inside a DB transaction | Returns 404 if project/grant is absent; writes `grant.revoked` event atomically with deletion. Protected operations hold `FOR SHARE` on the grant row, so deletion waits for their transaction. |
| `GET /v1/projects` | CEO bearer or individual AGENT bearer | CEO receives all projects; other readers need unexpired `project.read`. Individual credential and project grant rows are rechecked/locked under `FOR SHARE` in the transaction. | Project list is scoped for non-CEO readers. Shared worker/reviewer tokens are not accepted by this API. |
| `GET /v1/projects/{id}/board` | Same read-principal resolver | CEO bypasses grant; others pass `require_grant(project.read)` inside transaction. Individual credential and grant rows are locked under `FOR SHARE`. | Project-scoped board read. No DB RLS/role isolation is established by this application check. |
| `POST /v1/projects/{id}/work` | Individual AGENT bearer | `work.create`; individual credential and grant rows locked under `FOR SHARE` in transaction | Persists authenticated principal as author; ignores client `author_id`. |
| `POST /v1/work/{id}/admit` | Individual AGENT bearer | `work.admit`; credential and grant recheck under `FOR SHARE` | Deterministic admission call uses simulated capacity, budget, risk and emergency-stop inputs; not real resource admission. |
| `POST /v1/work/{id}/progress` | Individual AGENT bearer | `work.progress`; credential and grant recheck under `FOR SHARE` | Advances allowed states; VERIFIED-to-DONE checks for any approval but does not establish independent evidence validation. |
| `POST /v1/work/{id}/reviews` | Individual AUDITOR bearer | `work.review`; individual AUDITOR credential and grant rows locked under `FOR SHARE` | Rejects same principal as author; does not establish independence from executor/approver or validate evidence references. |
| `POST /v1/work/{id}/stage-inert` | Individual AGENT bearer | Requires both `work.admit` and `execution.claim`; credential and grant rows locked under `FOR SHARE` | Feature-flagged staging of fixed inert payload only. No model/tool/external action. A negative integration case rejects an admitted agent without the execution capability. |

The PostgreSQL API no longer accepts shared worker/reviewer tokens. SQLite
prototype tokens are a separate path. Individual bearer authentication first
resolves identity and protected API operations recheck the credential row
inside their transaction. The CEO credential is still a single static bearer.

## Internal PostgreSQL operations (not HTTP authorization boundaries)

| Operation | Identity / capability check | Transaction boundary | Known boundary |
| --- | --- | --- | --- |
| `execution_queue.claim()` / `complete()` | Individual AGENT credential; requires unexpired `execution.claim` project grant | Credential and grant are checked with `FOR SHARE`; queue/project rows are locked. | Migration 006 transfers legacy identities and drops the old registry. Lease expiry is computed and checked with PostgreSQL `clock_timestamp()`; a real database-lock-wait test covers delayed completion. Other lease/revocation schedules remain open. |
| `execution_reconciliation.reconcile()` | Active AUDITOR bearer credential resolves reviewer in-transaction; unexpired `execution.reconcile` grant; AGENT credentials denied | Locks credential, queue/project and grant rows | No HTTP endpoint. Evidence references are not verified; `MARK_FAILED`/auditor-credential revocation has one controlled schedule, but `RETRY_CONFIRMED_SAFE`/revocation remains untested. |
| `external_effect_registry.propose()` | Active individual AGENT credential must match `worker_id`; requires `effect.propose` grant | In one transaction, locks credential, execution/project, then grant; requires active project, `RUNNING`, matching worker and lease token, and a lease not expired by DB clock | Records only; never executes. Appends `effect.proposed` journal event with proposer identity and request digest. No external adapter is enabled. |
| `external_effect_reconciliation.reject_unexecuted_proposal()` | Active AUDITOR bearer credential resolves reviewer in-transaction; unexpired `effect.reconcile` grant; AGENT credentials denied | Locks credential, effect/queue and grant rows | Evidence references are not verified; internal helper only. No external effect is executed. |

## Cross-cutting gaps and test status

- API, queue and reconciliation authorization checks hold matching grant
  tuples under `FOR SHARE`; CEO grant deletion serializes behind in-flight
  protected transactions. PostgreSQL schedules cover an HTTP work-creation
  transaction, queue claim, and queue completion each holding authorization
  while grant deletion waits. Queue completion has also been observed holding
  the AGENT credential row while credential revocation waits; after the
  operation commits, the revocation succeeds and subsequent completion is
  denied. A separate AUDITOR auth/revocation schedule and AGENT auth/rotation
  schedule exercise credential row locks. These are selected controlled lock
  schedules; a queue-claim/credential-revocation schedule now also observes
  credential revocation wait until claim commits, then denies later claims.
  Reconciliation's `MARK_FAILED` disposition has also been observed committing
  before an in-flight auditor credential revocation; the revoked auditor is
  denied on a subsequent attempt. Effect proposal now requires the worker's
  active credential, explicit `effect.propose` grant and live lease. Three
  local focused reruns exercised a controlled execution-row-lock schedule: the
  test observed proposal blocked while completion competed; completion
  succeeded, and proposal either committed before it or was denied after
  completion. This is selected controlled coverage, not exhaustive or
  adversarial race coverage.
- Sequential credential revocation tests and unit mocks that assert SQL text
  do not prove real PostgreSQL lock behavior. Several real lock schedules now
  cover work creation, queue claim/completion against grant deletion, and
  queue completion against credential revocation. Other business writes,
  alternative operation/revocation orderings, retry reconciliation against
  credential revocation, and hostile schedules remain untested.
- The current full local suite has 60 tests, including grant-row, auditor
  credential-lock, and completion-after-lease-expiry-during-row-lock-wait
  coverage, AGENT authentication/rotation, and selected protected-operation
  revocation schedules. Three
  controlled races between completion and quarantine after
  expiry also finish in `UNCERTAIN`; this is not a broad adversarial schedule
  proof. Proposal and retry do not form a meaningful valid-operation race
  because proposals require a live RUNNING lease while retry requires
  UNCERTAIN; a prior test purported to exercise that schedule and has been
  replaced with proposal/completion coverage. A cold PostgreSQL
  restart has been manually verified for one expired lease; broad restart and
  crash-recovery schedules remain open.
- GitHub CI configures a fresh disposable PostgreSQL service and runs the
  guarded integration suite; runs `39258084851` and `39258576394` passed on code SHAs
  `424016daabda4f2cb0cd337be449b71d687d4cac` and
  `22f7310822c2ca3bfe59b8e2ccbb9d8dbc856b0d`, respectively. Current exact local results and
  prior candidate SHA-specific CI runs are recorded in the evidence register;
  this is not independent review or M2 acceptance.
- Grant expiry uses `clock_timestamp()` when the locked authorization query is
  evaluated, avoiding PostgreSQL transaction-start `now()` semantics. This
  does not itself prove every long-running operation stops exactly at expiry;
  authorization is held through transaction end and that contract needs
  separate review.
- External execution remains inert. No real model, tool, external effect,
  production identity, or autonomous operation is authorized by this matrix.

## Source map

- HTTP routes and auth helpers: `src/aao/work_management_api.py`
- Credential resolution: `src/aao/principal_credentials.py`
- Reconciliation credentials are verified and locked via
  `authenticate_in_transaction()` in the operation's database transaction.
- Execution claims/completion: `src/aao/execution_queue.py`
- Legacy worker rows are transferred by `db/postgres/006_unified_execution_identity.sql`; no legacy runtime verifier remains.
- Execution reconciliation: `src/aao/execution_reconciliation.py`
- Effect proposal/reconciliation: `src/aao/external_effect_registry.py`,
  `src/aao/external_effect_reconciliation.py`
- Relevant integration suites: `tests/test_project_workflow_integration.py`,
  `tests/test_execution_leases_integration.py`,
  `tests/test_execution_reconciliation_integration.py`,
  `tests/test_principal_credential_lifecycle_integration.py`
