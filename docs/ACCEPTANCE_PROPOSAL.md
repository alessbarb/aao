# M2-A acceptance proposal — awaiting formal independent review

**Status:** candidate package only; **M2-A is not accepted**. The CEO has
defined stage scope in [`SCOPE_DISPOSITION.md`](SCOPE_DISPOSITION.md), but has
not accepted the implementation or residual risks. The decision does not
authorize models, tools, providers, production deployment, or external effects.

## Candidate revisions

- **Implementation source with 80-test evidence:**
  `99760c7339323600368e5dbb145b088d83ad0715`.
- **Latest verification package with a full-suite run:**
  `acb85a268b3ec32630e858512058d970ae970191`, 80 passed, zero failures/skips/warnings,
  plus compileall, Ruff, `pip check`, and diff checks. A later documentation-only
  evidence-registration revision `0c1c990520d105cf7e16349903f112f485426118`
  records that run and is the currently pinned PR package. The live PR head must
  be rechecked at review time; no runtime code changed after the implementation source.
- **Review vehicle:** [draft GitHub PR #2](https://github.com/alessbarb/aao/pull/2).
  At the latest live check, local `HEAD`, `origin/feat/aao-m0-foundation`,
  `origin/review/m2-inert-candidate`, and the PR head matched
  `0c1c990520d105cf7e16349903f112f485426118`. The formal reviewer must recheck
  the live PR head and identify it separately from the implementation source SHA.
  No runtime code was changed to reconcile revision references.

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

1. **Complete:** migrations 001–009 were replayed in order on a newly created
   explicitly disposable PostgreSQL database using the CI legacy-row upgrade
   path; the full suite passed against it and the scratch database was dropped.
   Exact local evidence is recorded in the verification register.
2. Obtain a qualified independent security/architecture review of the exact
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
