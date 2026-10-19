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

- **Frozen historical implementation/package:**
  `dc084417a2ba683fe4737342f89e9cd1036b38ad` /
  `ef1a6e64ad4d6523cacd6c98a3b25ae7cebf4ad5` (PR #2). This pair is retained
  for provenance and still contains H-01; do not use it as the corrected
  candidate or move the PR ref.
- **Corrected implementation candidate:**
  `31e7397be082394a6da95eadebd0d8ad6bf99c39`.
- **Initial corrected documentation package:**
  `c9b2c7ad44d2cadc2e214904073073221e1207cd`; the code/test/database diff
  (`src`, `tests`, `db`) from implementation to this package is empty. A later
  package SHA will include this formal review request and must be pinned
  separately.
- **Review status:** PR #2 remains OPEN/DRAFT at `ef1a6e64`; it is not the
  corrected review vehicle. No qualified independent reviewer is assigned.
  The exact formal review request is in
  [`FORMAL_REVIEW_REQUEST.md`](FORMAL_REVIEW_REQUEST.md).

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
- The corrected source has a reproduced 91-test local disposable-PostgreSQL
  run and static checks; a clean read-only clone of package `c9b2c7a` also
  reproduced the suite. CI is not asserted as part of this evidence.

These are bounded implementation and test facts, not formal assurance or
acceptance.

## Conditions before M2-A may be presented for acceptance

1. **Reproducibility:** migrations 001–009 were replayed in order on a newly
   created explicitly disposable PostgreSQL database using the synthetic
   legacy-row upgrade path; the full 91-test suite passed and the container was
   removed. A clean read-only clone of package `c9b2c7a` reproduced 91 passing
   tests and static checks. This is local automated evidence, not CI or formal
   review.
2. **Formal review:** source `31e7397` and the exact final documentation
   package SHA require review by a qualified independent human other than the
   implementer. The request is prepared in `FORMAL_REVIEW_REQUEST.md`; review
   is not yet available. Do not move PR #2 or claim its old head contains the
   correction.
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
