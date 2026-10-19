# M2 candidate — independent review package

**Requested review target:** `88ec4264d655e6d25ec2b8f6859019a411a797fa` on
`feat/aao-m0-foundation`.

This is a prepared package for a qualified independent reviewer. It is not
itself the requested independent review and does not claim formal acceptance.

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
7. Are there any critical/high defects or false claims that prevent a
   candidate acceptance recommendation?

## Artifacts to inspect

- `docs/CONSTITUTION.md` (draft; not a confirmed mandate),
  `docs/ENGINEERING_BACKLOG.md` (planning seed),
  `docs/M2_COMPLIANCE_MATRIX.md`, `docs/M2_TECHNICAL_AUDIT.md`,
  `docs/M2_CLOSURE_PLAN.md`, `docs/M2_ACCEPTANCE_PROPOSAL.md`.
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
- The exact-SHA local run passed 78 tests under PostgreSQL with warnings as
  errors. Compilation, Ruff, `pip check`, and diff checks passed. CI was not
  awaited and no production/deployment test was run.

## Required review output

Reviewer: name/organization and independence statement; reviewed commit SHA;
scope and methods; tests/commands independently reproduced; findings with
severity and exact references; unsupported claims; residual-risk assessment;
and a recommendation limited to the explicitly accepted M2 scope. A review
must not imply CEO acceptance or permission for external execution.
