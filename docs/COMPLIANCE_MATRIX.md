# M2 candidate compliance matrix

**Purpose:** stage-specific traceability for the M2-A candidate and remaining
M2-B/M2-C work. The CEO's scope decision is recorded in
[`SCOPE_DISPOSITION.md`](SCOPE_DISPOSITION.md). The Constitution remains a
draft; this decision does not ratify it or accept M2-A. `SATISFECHO` below
means only that the bounded behavior is implemented and supported by cited
evidence; it is not formal M2-A acceptance.

**Baseline source revision:** `99760c7339323600368e5dbb145b088d83ad0715`.
**Frozen implementation under PR #2:** `dc084417a2ba683fe4737342f89e9cd1036b38ad`.
**Frozen PR #2 package:** `ef1a6e64ad4d6523cacd6c98a3b25ae7cebf4ad5`.
**Separate corrected implementation candidate:** `31e7397be082394a6da95eadebd0d8ad6bf99c39`.
The corrected candidate has not replaced PR #2. **Verification:** see exact-SHA entries in
[`VERIFICATION_EVIDENCE_REGISTER.md`](VERIFICATION_EVIDENCE_REGISTER.md).

| Requirement / source | Implementation and evidence | Residual risk / limit | Status |
| --- | --- | --- | --- |
| Confirmed CEO mandate before operating a project (Constitution §§1–4; backlog M0-02/03) | Mandate draft/confirm and project creation routes exist in `work_management_api.py`; project workflow integration tests exercise the local path. AAO may be its own first managed project under the same gate. | CEO credential is a static development/test bearer, not verified human identity or constitutional signature; no operational project mandate is recorded. | **SATISFECHO** for the local mandate gate; production authority remains **DIFERIDO** to M2-C and separately authorized. |
| Individual principal identity, roles, project grants, revocation (Constitution §§2–3, 10) | Migrations 005/006 and credential/grant transaction checks; selected PostgreSQL race tests cover grant/credential revocation and stale request contexts. At frozen `dc084417`, credential verification implicitly defaulted to development when `AAO_ENV` was absent. Separate candidate `31e7397` rejects absent, empty, production, and unknown modes before DB access in both authentication paths; explicit `development`/`test` remain allowed. | The frozen PR #2 package retains H-01. Corrected candidate needs a refreshed review/package pin. Coverage is selected, not exhaustive; no RLS/least-privilege role isolation; credentials do not prove human identities. | **SATISFECHO** only for corrected local candidate behavior with test evidence; frozen PR #2 has a **CONFIRMED** defect; human/production identity and DB isolation remain residual gates or **DIFERIDO** to M2-C. |
| Segregation of duties and auditor independence (Constitution §6) | Work author/reviewer principal-ID separation and execution claimant/reviewer ID separation are implemented; positive `APPROVE` remains fail-closed. | Different principal IDs do not establish distinct humans or organizations; auditor appointment, appeal path, and human independence proof are absent. | **SATISFECHO** for fail-closed M2-A denial controls; positive independent approval remains **PENDIENTE** and must not be enabled in M2-A. |
| Project data isolation (Constitution §7) | API reads and grants are scoped to project; evidence artifact primary key and lookups include project ID; tests cover cross-project authorization. | No DB RLS or isolated DB roles; privileged direct SQL/code can bypass application scope. | **SATISFECHO** for application-scoped M2-A paths; production-grade isolation remains **DIFERIDO** to M2-C. |
| M2-01: Evaluate Temporal against database-backed execution (backlog) | [`DURABLE_EXECUTION_EVALUATION.md`](DURABLE_EXECUTION_EVALUATION.md) compares the existing PostgreSQL queue with Temporal's service/database, persisted workflow history and replay model. Recommendation: retain the current DB-backed queue for the inert/local candidate; do not adopt another runtime without an approved operational scope and a measured need. | This is an engineering disposition of the evaluation task, not an acceptance decision. No Temporal prototype or benchmark was needed to decide against adding a second runtime to the current inert candidate. | **SATISFECHO** for the requested evaluation; adoption remains **DIFERIDO** pending a separate scope decision. |
| M2-02: Durable execution, leases, expiry and fencing (Constitution §8; backlog) | PostgreSQL queue, lease ownership/expiry, project state generation in migration 007, atomic claim/completion, `UNCERTAIN` quarantine; controlled integration schedules are registered. | M2-A has no autonomous worker runtime or scheduler/startup quarantine path. Leases are not signed attestations; complete checkpoint protocol and automated crash/restart recovery are not implemented. Historical cold-restart evidence used checkpoint `5d64de3` and migrations 001–006 only. | **PARCIAL** for the original M2-02: its DB lease/fencing/quarantine subset is demonstrated in M2-A; signed leases/checkpoints remain **PENDIENTE** and provisionally mapped to M2-B, while automated recovery is M2-B/C. Transfer is not satisfaction. |
| M2-06: Crash recovery, repeated event delivery and denied-action tests (backlog) | M2-A explicit reconciliation requires active individual AUDITOR credential, project grant, project-scoped artifact reference, and current uncertain state; retry refuses paused projects or unresolved effects. Selected PostgreSQL races, denied-action tests, and idempotent stage request replay after HTTP client reconnection are recorded. | This is not process restart or post-reconciliation event replay. M2-A has helper-driven quarantine; no restart orchestrator, recovery controller, or automated cold-recovery harness. | **SATISFECHO** for M2-A denied actions and manual recovery; automated restart/repeated-delivery guarantees are **DIFERIDO** to M2-B/C. |
| Evidence provenance and artifact integrity (Constitution §6; backlog M1-04) | Migrations 008/009 and `evidence_registry.py` store project-scoped content by SHA-256, rehash on use, restrict submission and inspection to individual credentials/capabilities, and block row UPDATE/DELETE/TRUNCATE through triggers. The frozen code run had 83 tests; corrected candidate `31e7397` has a fresh 91-test disposable PostgreSQL run. Controlled grant-deletion races cover evidence read and registration. | Hash integrity is not truth or authorship. A database/schema owner can disable triggers or alter schema; test role is owner, so least-privilege runtime permissions are unproven. No HTTP artifact surface; audit access is internal Python only. No signed disposition. | **SATISFECHO** for M2-A application-level evidence integrity only; H-02 owner tampering/role separation and factual validity/human provenance are explicit residual risks requiring disposition, not owner-resistant guarantees. |
| External-effect ledger, reconciliation and idempotency (backlog M2-03) | Effect proposal/rejection ledger is transactionally scoped, records journal events, and has selected locking/idempotency tests. No external adapter is enabled. | M2-A proves inert containment only. Provider-side fencing, exactly-once effects, external idempotency outcomes and real-provider reconciliation are unimplemented and not authorized by the scope decision. | **PARCIAL** for original M2-03: inert proposal/rejection containment is demonstrated in M2-A; provider-side effects, idempotency and reconciliation remain **PENDIENTES**, with implementation prohibited absent separately formalized scope/authority. |
| Project suspension applicable to the inert environment (backlog M2-05; Constitution §10) | CEO-authenticated PostgreSQL API supports audited `ACTIVE→PAUSED`, `PAUSED→ACTIVE`, and active/paused→`CANCELLED` transitions; database-owned generation fencing invalidates stale leases. PostgreSQL integration test covers authorization, allowed/denied transitions, audit rows, and generation changes. | Not an independent stop controller for a live AI runtime; none is enabled. Production CEO identity/stop authority remain absent. | **SATISFECHO** for M2-A inert project suspension; runtime-independent control is **DIFERIDO** to M2-B and production supervision to M2-C. |
| M2-04: Sandbox runners with operation-scoped capabilities (backlog) | The PostgreSQL candidate's worker emits only a deterministic inert marker; no tools, shell, network, model or external calls are enabled. The SQLite prototype's `sandbox-queue` route is not a sandbox and is not evidence for this criterion. | A capability-constrained sandbox is not implemented. CEO scope disposition places it in M2-B. | **DIFERIDO** to M2-B; still **PENDIENTE** there and not satisfied by transfer. |
| Independent security/architecture review and competent acceptance | Candidate review package is prepared by this repository and M2-A scope is now explicitly recorded; internal subagent reviews are recorded as internal only. | No qualified independent reviewer is assigned/available through current repository collaborators; no M2-A acceptance exists. | **PENDIENTE**; acceptance follows formal review and explicit disposition of residual risks. |

## External adversarial audit disposition

The static external report dated 2026-10-19 is individually assessed in
[`ADVERSARIAL_AUDIT_20261019.md`](ADVERSARIAL_AUDIT_20261019.md). H-01 is a
confirmed defect in frozen `dc084417` and corrected only in separate candidate
`31e7397`. H-02 is a known trust-boundary residual requiring competent
disposition; H-03 remains a fail-closed independent-human review gate; H-04's
manual reconciliation subset is implemented/tested while automatic restart
recovery is deferred to M2-B/C; H-05's frozen package/source relationship was
verified and must be re-pinned for any corrected candidate. This report is
not a formal independent review and closes no acceptance gate.

## Stage disposition

M2-A is limited to the inert local candidate. M2-B retains sandboxing,
automated operational recovery, runtime-independent controls, and governed
execution; M2-C retains continuous/production maturity. No stage authorizes
activating models, tools, providers or real external effects. Later-stage
assignment does not count as satisfaction. The technical matrix cannot be
used to infer operational powers. Planner/admission inputs for capacity,
budget, risk, and authorization remain simulated; they are not operational
safeguards or evidence of safe admission.
