# M2-A acceptance proposal — awaiting formal independent review

**Status:** candidate package only; **M2-A is not accepted**. The CEO has
defined stage scope in [`SCOPE_DISPOSITION.md`](SCOPE_DISPOSITION.md), but has
not accepted the implementation or residual risks. The decision does not
authorize models, tools, providers, production deployment, or external effects.

## Candidate revisions

- **Implementation candidate:** `cbcab10f7010004b8ee12801356a2643f9dc6a79`,
  including the production-mode denial for development principal credentials
  and audited CEO-authenticated project suspension API. The earlier baseline
  implementation source was `99760c7339323600368e5dbb145b088d83ad0715`.
- **Prior evidence package:** `b15dea4f69823bcb894cb58eda54dcffdb48d602`
  passed 80 tests and static checks. Following the identified fixes, the current
  candidate `cbcab10` passed 83 tests, zero failures/skips/warnings, plus
  compileall, Ruff, `pip check`, and diff checks. Fresh replay of migrations
  001–009 predates these code-only fixes; they do not change schema.
- **Review vehicle:** [draft GitHub PR #2](https://github.com/alessbarb/aao/pull/2).
  At the pre-fix live check, local `HEAD`, both remote refs and PR head matched
  `b15dea4f69823bcb894cb58eda54dcffdb48d602`. After committing the fixes,
  local `HEAD` is `cbcab10f7010004b8ee12801356a2643f9dc6a79`; the remote and
  live PR must be updated/rechecked before formal review. The review report must
  identify package and source revisions separately.

## What M2-A evidence demonstrates

- PostgreSQL-backed work and execution state, per-principal AGENT/AUDITOR
  development credentials, and project-scoped application authorization.
- Selected real PostgreSQL grant/credential revocation schedules; not an
  exhaustive claim over every possible interleaving.
- Durable inert queue staging, atomic claim/completion, database-clock lease
  expiry, project-state generation fencing, and stale/expired-work quarantine.
- Explicit manual reconciliation restricted to an active individual AUDITOR
  credential, project grant, uncertain state and project-scoped evidence.
- Project-scoped content-addressed evidence bytes, rehash-on-use, and
  application-level append-only protections.
- Pause/cancel controls applicable to the inert project/queue boundary; no
  stale generation may continue as a valid execution lease.
- Approval and transition to DONE remain fail-closed because verified human
  reviewer independence and evidence sufficiency are not established.
- Execution remains inert: no model, shell, network, tool, provider, or real
  external action is enabled.
- Local full suite and static checks at the exact SHA listed above; CI is not
  asserted as part of this evidence.

These are bounded implementation and test facts, not formal assurance or
acceptance.

## Conditions before M2-A may be presented for acceptance

1. **Complete before current code fixes:** migrations 001–009 were replayed in order on a newly created
   explicitly disposable PostgreSQL database using the CI legacy-row upgrade
   path; the full suite passed against it and the scratch database was dropped.
   Exact local evidence is recorded in the verification register.
2. **Repeat required:** run the complete suite and static checks against the
   committed fixes; then obtain a qualified independent security/architecture review of the exact
   PR head and code candidate. The reviewer must be different from the
   implementer and provide an attributable report with methods and findings.
3. Resolve or explicitly disposition review findings within the M2-A boundary.
4. Present exact-SHA evidence and the residual-risk list below for competent
   acceptance. The engineering agent must not self-accept M2-A.

No reviewer is currently assigned. The available GitHub collaborator listing
contains only the repository owner; an internal subagent review cannot satisfy
the formal independence condition.

## Residual risks requiring explicit acceptance or continued gating

- Development credentials do not prove human identity, signatures, or distinct
  human organizations; positive approval stays unavailable.
- Application authorization is not DB RLS/least-privilege role isolation; a
  database owner/superuser can bypass application checks or trigger guards.
- Evidence hashes establish byte integrity, not factual truth, authorship,
  relevance, or human independence; retention/confidentiality policy is not
  established.
- Selected lock/race coverage is not exhaustive. Recovery is explicit/manual;
  no process restart or autonomous recovery controller is claimed in M2-A.
- No production/deployment, continuous-service, or CI result is claimed here.

## Later stages and retained requirements

M2-B retains sandboxing with operation-scoped capabilities, automated
operational recovery, runtime-independent controls, and governed execution.
M2-C retains continuous operation, complete recovery, deployment, supervision,
isolation, and production controls. Provider-side effects/idempotency remain
unimplemented and unauthorized; their stage-specific scope must be defined
before implementation. Requirements are not marked satisfied because they
were moved to a later stage.

Any future M2-A approval must name the exact SHA, bounded operating mode,
accepted residual risks, exclusions, and acceptance authority. No authority
for external execution is implied.
