# Principal authorization matrix

**Scope:** current development API and internal execution/reconciliation
operations at revision `a99b223f515931de5b0dc90b6e3cec28700bf8b3`. This is an
engineering inventory, not a production authorization policy or independent
security review. The PostgreSQL API and its internal helpers are not a claim of
M2 acceptance.

## External HTTP operations

| Operation | Authenticated identity / authority | Project capability and transaction check | Effect and known boundary |
| --- | --- | --- | --- |
| `GET /`, `GET /health` | None | None | Static workboard shell / service status only; health reports autonomous execution disabled. |
| `POST /v1/principals/credentials`, `/v1/principals/{id}/rotate`, `/revoke` | Static `AAO_CEO_TOKEN` bearer, compared before DB transaction | No project grant; lifecycle writes and audit event share a DB transaction | Development credential administration; no constitutional signature, multi-party confirmation, or production identity. |
| `POST /v1/mandates`, `/v1/mandates/{id}/confirm`, `/v1/projects` | Static CEO bearer | No project grant; mandate/project row checked or locked within transaction | Draft/confirm mandate and create project. CEO identity is a development bearer, not a verified constitutional actor. |
| `POST /v1/projects/{id}/grants` | Static CEO bearer | No project grant; only project existence is checked | Inserts arbitrary supplied principal/capability (subject to request allowlist); no principal-kind/existence check, revoke endpoint, or self-grant prevention. Conflict no-op still emits a grant-created event. |
| `GET /v1/projects` | CEO bearer, individual AGENT bearer, or transitional shared worker bearer | CEO receives all projects; other readers need unexpired `project.read`. Individual credential kind/enabled is rechecked under `FOR SHARE` in the same transaction. Grant row is not locked. | Project list is scoped for non-CEO readers. Shared worker identity is enabled by default in development/test unless explicitly disabled. |
| `GET /v1/projects/{id}/board` | Same read-principal resolver | CEO bypasses grant; others pass `require_grant(project.read)` inside transaction. Individual credential is rechecked under `FOR SHARE`; grant read is unlocked. | Project-scoped board read. No DB RLS/role isolation is established by this application check. |
| `POST /v1/projects/{id}/work` | Individual AGENT bearer or transitional shared worker bearer | `work.create`; individual credential rechecked under `FOR SHARE` in transaction; grant read is unlocked | Persists authenticated principal as author; ignores client `author_id`. Shared worker maps to fixed development identity. |
| `POST /v1/work/{id}/admit` | Individual AGENT or transitional shared worker | `work.admit`; credential recheck under `FOR SHARE`; grant read unlocked | Deterministic admission call uses simulated capacity, budget, risk and emergency-stop inputs; not real resource admission. |
| `POST /v1/work/{id}/progress` | Individual AGENT or transitional shared worker | `work.progress`; credential recheck under `FOR SHARE`; grant read unlocked | Advances allowed states; VERIFIED-to-DONE checks for any approval but does not establish independent evidence validation. |
| `POST /v1/work/{id}/reviews` | Individual AUDITOR bearer or transitional shared reviewer bearer | `work.review`; individual AUDITOR credential rechecked under `FOR SHARE`; grant read unlocked | Rejects same principal as author; does not establish independence from executor/approver or validate evidence references. Shared reviewer is a fixed development identity. |
| `POST /v1/work/{id}/stage-inert` | Individual AGENT or transitional shared worker | Checks `work.admit`, not `execution.claim`; credential recheck under `FOR SHARE`; grant read unlocked | Feature-flagged staging of fixed inert payload only. No model/tool/external action. Capability mismatch should be resolved before use as an execution boundary. |

The shared worker/reviewer fallbacks are controlled by
`AAO_ALLOW_SHARED_DEV_TOKENS`; the application defaults the setting to enabled
in `development` and `test`, and rejects them in production. Individual bearer
authentication initially resolves identity outside the protected transaction;
protected API operations then recheck the credential row inside their
transaction. The CEO credential is still a single static bearer.

## Internal PostgreSQL operations (not HTTP authorization boundaries)

| Operation | Identity / capability check | Transaction boundary | Known boundary |
| --- | --- | --- | --- |
| `execution_queue.claim()` / `complete()` | Individual AGENT credential **or** legacy `worker_registrations`; requires unexpired `execution.claim` project grant | Credential is checked with `FOR SHARE`; queue/project rows are locked. Grant lookup is not locked. | Two credential registries remain. Completion captures caller-side `now` before lock acquisition; grant revocation/expiry and delayed completion races are not yet covered by integration tests. |
| `execution_reconciliation.reconcile()` | Caller-supplied `reviewer_id`; unexpired `execution.reconcile` grant; rejects former worker ID | Locks queue/project rows, but neither reviewer identity nor grant row is authenticated/locked | No HTTP endpoint. Identity-string inequality is not proof of auditor identity; evidence references are not verified. Retry-vs-effect-proposal race is not serialized. |
| `external_effect_registry.propose()` | No principal authentication or project grant check in this helper | Idempotency-key row is locked; execution existence is checked without a lock | Records proposals only; does not execute. It is not safe to treat as an authorization boundary. |
| `external_effect_reconciliation.reject_unexecuted_proposal()` | Caller-supplied reviewer ID; unexpired `effect.reconcile` grant; rejects current worker ID | Locks effect and queue rows, but not reviewer identity or grant row | No trusted reviewer binding or verified evidence; internal helper only. No external effect is executed. |

## Cross-cutting gaps and test status

- Grant checks in API, execution, and reconciliation paths are plain reads;
  concurrent grant revocation and expiry do not have a demonstrated
  serialization contract.
- Sequential credential revocation tests and unit mocks that assert SQL text
  do not prove real PostgreSQL lock behavior. Required next evidence includes
  two-connection races for credential and grant revocation against protected
  reads/writes, claims and completion.
- Existing PostgreSQL concurrency coverage tests distinct queue claims, not
  adversarial revocation, lease expiry during lock wait, quarantine/completion
  ordering, or effect-proposal/retry races.
- Normal GitHub CI does not configure the disposable PostgreSQL service, so
  guarded PostgreSQL integration tests can be skipped there. The locally
  recorded 51-test run on `d080da58d4a8a41749a932d8fdf2c1caec5ac652` passed
  under the explicit disposable-database gate; it is not independent review or
  M2 acceptance.
- External execution remains inert. No real model, tool, external effect,
  production identity, or autonomous operation is authorized by this matrix.

## Source map

- HTTP routes and auth helpers: `src/aao/work_management_api.py`
- Credential resolution: `src/aao/principal_credentials.py`
- Execution claims/completion: `src/aao/execution_queue.py`
- Legacy worker credential authority: `src/aao/legacy_worker_authentication.py`
- Execution reconciliation: `src/aao/execution_reconciliation.py`
- Effect proposal/reconciliation: `src/aao/external_effect_registry.py`,
  `src/aao/external_effect_reconciliation.py`
- Relevant integration suites: `tests/test_project_workflow_integration.py`,
  `tests/test_execution_leases_integration.py`,
  `tests/test_execution_reconciliation_integration.py`,
  `tests/test_principal_credential_lifecycle_integration.py`
