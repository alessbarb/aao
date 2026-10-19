# M2-A acceptance proposal — awaiting formal independent review

**Status:** candidate package only; **M2-A is not accepted**. The CEO has
defined stage scope in [`SCOPE_DISPOSITION.md`](SCOPE_DISPOSITION.md), but has
not accepted the implementation or residual risks. The decision does not
authorize models, tools, providers, production deployment, or external effects.

The previous frozen review pair was implementation `dc084417a2ba683fe4737342f89e9cd1036b38ad`
and PR/package `ef1a6e64ad4d6523cacd6c98a3b25ae7cebf4ad5`. Static external
finding H-01 was confirmed on that code. A separate corrected engineering
candidate is `31e7397be082394a6da95eadebd0d8ad6bf99c39`; do not treat the frozen
PR package as containing the correction. The corrected candidate has not been
formally reviewed and PR #2 remains unchanged and open/draft.

## Candidate revisions

- **Implementation candidate:** `dc084417a2ba683fe4737342f89e9cd1036b38ad`,
  including production-mode denial for development principal credentials,
  audited CEO-authenticated project suspension, and race-safe inert proposal
  idempotency. The earlier baseline implementation source was
  `99760c7339323600368e5dbb145b088d83ad0715`.
- **Prior evidence package:** `b15dea4f69823bcb894cb58eda54dcffdb48d602`
  passed 80 tests and static checks. Following the identified fixes, the current
  candidate `dc08441` passed 83 tests, zero failures/skips/warnings, plus
  compileall, Ruff, `pip check`, and diff checks. Fresh replay of migrations
  001–009 predates these code-only fixes; they do not change schema.
- **Review vehicle:** [draft GitHub PR #2](https://github.com/alessbarb/aao/pull/2).
  At the pre-fix live check, local `HEAD`, both remote refs and PR head matched
  `b15dea4f69823bcb894cb58eda54dcffdb48d602`. After committing the fixes,
  the current local implementation candidate is
  `dc084417a2ba683fe4737342f89e9cd1036b38ad`; the prior live-ref check was
  package checkpoint `f99563bcc7c4fa9803c4aa4597812b0e23e2d6b8`. Recheck the
  final package/PR head and pin both exact revisions in the formal review
  request; the report must identify package and implementation revisions
  separately.

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
2. **Engineering checks and review:** the frozen `dc084417` checks remain
   historical evidence for PR #2, which contains H-01. The corrected candidate
   `31e7397be082394a6da95eadebd0d8ad6bf99c39` has fresh full PostgreSQL and
   static-check evidence. It requires a new exact package SHA and a qualified
   independent security/architecture review of the corrected code plus that
   package. The reviewer must be different from the implementer and provide an
   attributable report with methods and findings. Do not move PR #2 or claim
   its old head contains the correction.
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
- The planner/admission path still contains simulated authorization,
  dependency, capacity, budget, and risk inputs. These are not operational
  resource/risk controls and must not be treated as evidence that the candidate
  can safely admit real work; autonomous work admission remains outside M2-A.
- No production/deployment, continuous-service, or CI result is claimed here.

The external audit dispositions are itemized in
[`ADVERSARIAL_AUDIT_20261019.md`](ADVERSARIAL_AUDIT_20261019.md). In
particular, M2-A must not claim owner-resistant database immutability; its
disposable test database used an owner role and did not prove least-privilege
runtime permissions. The internal reconciliation function and tested
quarantine/manual paths do not provide an HTTP/operator interface or automated
restart recovery. Human identity and reviewer independence remain unproven;
positive approval stays disabled. These points are not accepted merely by
their appearance here; competent authority must explicitly disposition
applicable residual risks after formal review.

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
