# M2-A candidate — independent review package

The CEO's stage-scope disposition is recorded in
[`SCOPE_DISPOSITION.md`](SCOPE_DISPOSITION.md). This package requests review
only of M2-A's bounded PostgreSQL-backed, development-identity, inert execution
candidate. M2-B and M2-C requirements remain in the compliance matrix and are
not acceptance claims or implementation authorization.

**Implementation candidate:** `dc084417a2ba683fe4737342f89e9cd1036b38ad` on
`feat/aao-m0-foundation`, with 83-test local evidence recorded in the evidence
register. The earlier base implementation is `99760c7339323600368e5dbb145b088d83ad0715`.
The package revision last verified against both branch refs and the live PR
head was `f99563bcc7c4fa9803c4aa4597812b0e23e2d6b8`. This package has had
documentation-only changes since that checkpoint; the latest PR comment pins
the exact revision to review. Recheck live refs at checkout and report both
package and implementation SHAs.

This is a prepared package for a qualified independent reviewer. It is not
itself the requested independent review and does not claim formal acceptance.
The current review vehicle is the [draft GitHub PR #2](https://github.com/alessbarb/aao/pull/2);
the PR head binds the exact code and package checkout for each review revision.
No formal reviewer has been assigned yet. Review must be performed by a
qualified person other than the implementer; internal agent feedback is not
formal independence evidence.

## Review questions

1. Do the M2 candidate guarantees match the code, migrations and tests at the
   requested SHA? Identify gaps between claim and proof.
2. Can an AGENT or AUDITOR bypass project/role boundaries, reuse stale
   authorization, manipulate evidence or reconcile work they influenced?
3. Are the PostgreSQL lock orders safe for the represented operations and
   selected revocation/reconciliation schedules? Which untested orderings are
   material to the accepted scope?
4. Do migrations 006–009 preserve identity, journal and evidence invariants on
   a fresh disposable database and on upgrade? Assess owner/superuser bypass,
   trigger behavior, backup/restore, and migration rollback policy.
5. Does the evidence storage/access model permit meaningful independent review
   while controlling privacy, provenance and retention risks?
6. Is explicit `UNCERTAIN` quarantine/reconciliation sufficient for the
   agreed M2 operating mode, or is scheduler/startup recovery required?
7. Are there any critical/high defects or false claims that prevent an
   M2-A-only candidate acceptance recommendation? Do not assess later-stage
   requirements as accepted or authorize their activation.

## Artifacts to inspect

- `docs/CONSTITUTION.md` (draft; not a confirmed mandate),
  `docs/SCOPE_DISPOSITION.md` (CEO stage-scope disposition),
  `docs/ENGINEERING_BACKLOG.md` (planning seed),
  `docs/COMPLIANCE_MATRIX.md`, `docs/TECHNICAL_AUDIT.md`,
  `docs/CLOSURE_PLAN.md`, `docs/ACCEPTANCE_PROPOSAL.md`.
- `docs/DURABLE_EXECUTION_EVALUATION.md` (disposition of backlog M2-01).
- `docs/PRINCIPAL_AUTHORIZATION_MATRIX.md`,
  `docs/PRINCIPAL_AUTHORITY_AND_REVOCATION_BOUNDARIES.md`,
  `docs/EXECUTION_RECOVERY_AND_RECONCILIATION.md`,
  `docs/WORKER_EXECUTION_AND_EXTERNAL_EFFECT_CONTROLS.md`.
- `src/aao/work_management_api.py`, `principal_credentials.py`,
  `authorization.py`, `execution_queue.py`, `execution_reconciliation.py`,
  `external_effect_registry.py`, `external_effect_reconciliation.py`,
  `evidence_registry.py`.
- PostgreSQL migrations `001`–`009` (do not alter applied 001–007),
  especially identity unification, project-state lease fencing, and evidence
  migrations 008/009.
- `tests/test_project_workflow_integration.py`,
  `tests/test_execution_leases_integration.py`,
  `tests/test_execution_reconciliation_integration.py`,
  `tests/test_principal_credential_lifecycle_integration.py`,
  `tests/test_principal_credentials.py`, and `tests/test_evidence_registry.py`.
- Exact-SHA commands/results and limitations in
  `docs/VERIFICATION_EVIDENCE_REGISTER.md`.

## Threat boundary and known limitations

- Current system is a local/development candidate; CEO bearer is not a
  production human identity. No external model/tool/provider execution is
  enabled.
- Application policy does not establish DB RLS or least-privilege role
  separation. A database owner can bypass or disable application and trigger
  controls.
- SHA-256 establishes stored-byte integrity only, not truth, authorship or
  independent reviewer identity. Evidence is stored in DB `bytea` with no
  approved sensitive-data lifecycle.
- Evidence read and reconciliation are internal Python operations, not HTTP
  interfaces; no human UI or approval ceremony is claimed.
- Positive approval remains fail-closed. Internal subagent feedback is not
  independent review under the Constitution.
- Recovery quarantine is explicit/helper-driven; no runtime scheduler or
  crash-restart acceptance harness is claimed.
- At the exact implementation candidate SHA, the local explicitly disposable
  PostgreSQL run passed 83 tests with warnings as errors; compileall, Ruff,
  `pip check`, and diff checks passed. The evidence register records a focused
  grant-revocation/read and grant-revocation/write races, each repeated three
  times. CI was not awaited and no
  production/deployment test was run. The documentation package is a later
  revision; the review request must pin its exact checkout separately.
- Internal follow-up identified and corrected the missing CEO-authenticated
  PostgreSQL suspension initiation path, added a fail-closed production
  environment guard for development credentials, and fixed concurrent absent
  idempotency-key races across distinct execution rows. The new concurrency
  test expects one proposal and one domain conflict. Review the correction and
  assess whether its bounded coverage is sufficient; no external effect is
  possible through this ledger.

## Required review output

Reviewer: name/organization and independence statement; reviewed commit SHA;
scope and methods; tests/commands independently reproduced; findings with
severity and exact references; unsupported claims; residual-risk assessment;
and a recommendation limited to the explicitly accepted M2 scope. A review
must not imply CEO acceptance or permission for external execution.
