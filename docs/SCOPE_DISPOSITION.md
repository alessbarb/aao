# CEO M2 stage scope disposition

**Recorded:** 2026-10-19 from the CEO's explicit scope decision in the AAO
engineering session. This record captures a program-scope decision only. It is
not a constitutional amendment, project mandate, production authorization,
M2-A acceptance, or authorization to enable models, tools, or external effects.

## Decision

- **M2-A — Durable inert execution:** the current candidate boundary. It
  includes PostgreSQL persistence, individual development identities,
  project-scoped authorization, inert execution, leases, fencing, quarantine
  of uncertain states, authorized manual reconciliation, evidence integrity,
  and suspension controls applicable to this environment.
- **M2-B — Controlled runtime:** retains the unsatisfied requirements for
  capability-scoped sandboxing, automated operational recovery, controls
  independent of the runtime, and governed execution. This decision does not
  authorize activating models, tools, or real external effects.
- **M2-C — Operational maturity:** continuous operation, complete recovery,
  deployment, supervision, isolation, and production controls beyond M2-A.
  Its scope must be formalized before implementation.

These stage names do not alter the Constitution or grant operational authority.
Requirements retain their original backlog IDs and remain traceable in
[`COMPLIANCE_MATRIX.md`](COMPLIANCE_MATRIX.md); reassignment to a later stage
does not mean satisfaction.

## Candidate and PR trace at disposition

Before recording this scope decision, local `HEAD`,
`origin/feat/aao-m0-foundation`, `origin/review/m2-inert-candidate`, and PR #2's
head all matched `dc7e594a690994b3327b78ce0046e8ec4cf1f616`. That checkout
contained the tested implementation from `99760c7339323600368e5dbb145b088d83ad0715`
plus documentation/test-history commits; it introduced no runtime-code change
after the implementation candidate. Subsequent scope/documentation commits may
advance PR #2's head, so a formal reviewer must use the live PR head SHA and
identify it in the review report. Do not rewrite the validated implementation
history to make the SHAs appear equal. After the scope package was committed,
local `HEAD`, `origin/feat/aao-m0-foundation`, `origin/review/m2-inert-candidate`,
and live PR #2 matched `acb85a268b3ec32630e858512058d970ae970191`; later
documentation-only commits advanced the package through
`0c1c990520d105cf7e16349903f112f485426118` and
`b15dea4f69823bcb894cb58eda54dcffdb48d602`. At the `b15dea4` checkpoint,
local `HEAD`, both remote refs, and PR #2 matched. The implementation source
remains `99760c7339323600368e5dbb145b088d83ad0715`. Subsequent code fixes and
their evidence are recorded separately; recheck exact live refs before review
and acceptance.

Suspension, credential-boundary, and inert proposal idempotency follow-ups are
implemented at `9fa503c334f17e3a7b6ef962a5df3a6428b280e8`; their exact local
evidence is in the verification register. This revision is not yet represented
by the live PR until the push and ref check are complete.

## M2-A measurable acceptance criteria

Each criterion is bounded to the local, development-identity, inert PostgreSQL
candidate. Passing a criterion supports candidacy only; it does not replace
formal independent review or competent acceptance.

| ID | Criterion | Evidence at the implementation candidate | Status |
| --- | --- | --- | --- |
| A-01 | PostgreSQL is the persistence and authorization boundary for the M2-A path; migrations 001–009 are applied and the schema version is 009. Applied migrations 001–005 remain immutable. | Fresh disposable database replay applied 001–009 in order, including the CI legacy-row migration path; terminal version was `009_prevent_evidence_truncation`. Full suite passed against that database and it was dropped afterward. | **SATISFECHO** for fresh schema and tested upgrade path; deployment/backup/restore remain outside A. |
| A-02 | Principals use individual AGENT/AUDITOR development credentials; each protected operation enforces role, project, and capability; legacy shared worker registration is absent from the PostgreSQL path. | Credential lifecycle, grant isolation, and selected in-transaction revocation/rotation races; 80-test local suite. | **SATISFECHO** for tested development API paths; no human identity proof is claimed. |
| A-03 | Queue staging, claim, and completion are project-scoped and fail closed for unauthorized principals, invalid lease ownership/token, inactive project, stale generation, or expired lease. Concurrent claim cannot create two active claims. | PostgreSQL integration and controlled race tests listed in the evidence register; execution uses DB-clock expiry and generation fencing. | **SATISFECHO** for tested operations and schedules; no exhaustive race claim. |
| A-04 | Execution remains inert: the worker produces only a deterministic marker and cannot invoke models, shell, network, tools, providers, or real external effects. | `inert_execution_worker.py`, default-off staging gate, and route/test coverage; no provider adapter is enabled. | **SATISFECHO** within the reviewed code boundary. |
| A-05 | Expired work is quarantined as `UNCERTAIN`; no automatic retry or external action occurs. A manual retry/failure disposition requires an active individual AUDITOR credential, project grant, current uncertain state, and applicable evidence/effect checks. | Queue/reconciliation code and selected PostgreSQL integration schedules. Restart/scheduler automation is explicitly M2-B/C, not claimed here. | **SATISFECHO** for explicit/manual paths; repeatable operational recovery is not part of A. |
| A-06 | Evidence references are project-scoped and content-addressed; bytes are rehashed on use; unauthorized or concurrently revoked evidence access fails closed; app-level writes are append-only. | Migrations 008/009, evidence registry, denial and grant-revocation race tests. | **SATISFECHO** for application paths; database-owner tampering and truth/authorship are residual risks. |
| A-07 | CEO-authenticated API can pause, resume, or cancel an inert project; transitions are audited, pause/cancel fence stale claims/completions, and resume does not revive an old generation. | CEO-only PostgreSQL project-state endpoint, audited transitions, generation trigger, and integration coverage for authorization, transitions, event records and generation increments. | **SATISFECHO** for the M2-A inert project control; not an independent runtime stop controller. |
| A-08 | Positive review approval and transition to DONE remain fail-closed unless reviewer independence and evidence sufficiency are verifiable. | Review route and transition tests. | **SATISFECHO** as a denial control; no positive independent approval is supported. |
| A-09 | Full local PostgreSQL suite has zero failures, skips, and warnings with warnings as errors; compilation, Ruff, dependency consistency, and diff checks pass at an exact candidate revision. | Exact local run recorded in `VERIFICATION_EVIDENCE_REGISTER.md`; clean-replay full suite also passed. | **SATISFECHO** for local verification only; CI is not asserted. |
| A-10 | A qualified independent reviewer examines the exact PR head, code candidate, migrations, evidence, residual risks, and this scope disposition; findings are resolved or explicitly dispositioned. | No qualified reviewer is currently assigned or available through repository collaborators. | **PENDIENTE** |
| A-11 | The competent authority reviews the independent report and explicitly accepts or rejects M2-A at an exact SHA with listed residual risks and operating limits. | No M2-A acceptance has been issued. | **PENDIENTE** |

## Residual risks requiring explicit disposition at M2-A acceptance

- CEO bearer and individual AGENT/AUDITOR credentials are development
  credentials; they do not prove human identity, signatures, or distinct
  organizations. Positive approvals remain disabled.
- Application grants are not PostgreSQL RLS or least-privilege database-role
  isolation. A database owner/superuser can bypass application controls and
  disable triggers.
- SHA-256 proves byte integrity, not factual truth, source authorship,
  relevance, or human independence. Evidence retention and sensitive-data
  policy are not established.
- Verification is local to an explicitly disposable PostgreSQL test database;
  there is no production deployment or continuous-service evidence.
- Selected concurrency schedules are covered, not all possible lock orders or
  hostile database-owner actions.

These are not accepted merely by this scope decision. The eventual M2-A
acceptance proposal must identify which residuals are accepted for the bounded
local candidate and which remain gates.

## Traceability of original backlog M2 requirements

- **M2-01:** PostgreSQL-vs-Temporal evaluation is complete for the current
  inert candidate; no second runtime is introduced without measured need.
- **M2-02:** PostgreSQL persistence, leases, expiry fencing, and quarantine are
  M2-A. Signed leases/checkpoints and runtime-governed execution remain
  unsatisfied and map provisionally to M2-B; full continuous recovery belongs
  to M2-C.
- **M2-03:** Inert proposals/rejections and their database records are within
  M2-A only as containment. Provider-side effects and provider idempotency are
  not implemented or authorized by this decision; their stage must be
  dispositioned before any such work, and no real effects may be activated.
- **M2-04:** Operation-scoped sandboxing is M2-B. The SQLite prototype's
  `sandbox-queue` route is not a sandbox and does not satisfy this requirement.
- **M2-05:** Project pause/cancel generation fencing applicable to the inert
  queue is M2-A. Stop controls independent of an active runtime belong to M2-B;
  production operational supervision belongs to M2-C.
- **M2-06:** Denied-action tests, explicit quarantine, and authorized manual
  reconciliation are M2-A. Automated process-restart recovery and repeated
  event-delivery guarantees are M2-B/C and remain pending.

No requirement is deleted or marked satisfied solely because it is assigned to
a later stage. Scope expansion or activation of real external effects requires
separate authority.
