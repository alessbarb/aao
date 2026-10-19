# Request for formal independent M2-A security and architecture review

**Request status:** prepared; a qualified independent reviewer has not yet
been identified or assigned. This request is not itself a review, certification,
acceptance, merge approval, or operating authorization.

## Exact review targets

- Repository: `https://github.com/alessbarb/aao`
- Corrected implementation/source: `31e7397be082394a6da95eadebd0d8ad6bf99c39`
- Initial corrected documentation package: `c9b2c7ad44d2cadc2e214904073073221e1207cd`
- Final review package: the exact full SHA is pinned in
  [`M2A_REVIEW_TRANSMITTAL.md`](M2A_REVIEW_TRANSMITTAL.md). This request cannot
  embed the SHA of its own containing commit; reviewers must verify the
  transmittal target and checkout SHA directly. Do not substitute the initial
  package SHA for the final package.
- Historical PR #2 implementation/package, preserved for lineage only:
  `dc084417a2ba683fe4737342f89e9cd1036b38ad` /
  `ef1a6e64ad4d6523cacd6c98a3b25ae7cebf4ad5`.

The implementation tree `src`, `tests`, and `db` is unchanged between the
corrected source and initial documentation package. The reviewer must verify
the same for the final package and must keep historical findings on the frozen
pair distinct from findings reproduced on the corrected pair. PR #2 remains
OPEN/DRAFT at the historical package and is not the corrected review target.

## Requested reviewer and independence

The reviewer must be a named, qualified human other than the implementation
author, with relevant security and architecture experience and no material
conflict that would compromise independence. The report must state name,
organization/qualification, independence basis, methods, and any limits. No
internal agent or implementer-authored report may substitute for this review.

## Scope

Review only the bounded, inert M2-A candidate and the claims in
`ACCEPTANCE_PROPOSAL.md` and `COMPLIANCE_MATRIX.md`. Inspect identity and
authorization boundaries; project isolation; revocation/locking schedules;
durable leases, fencing and uncertainty quarantine; manual reconciliation;
evidence storage/integrity; migration behavior; suspension controls; and
fail-closed approval boundaries. Assess whether each claimed guarantee follows
from code/contracts/tests at the exact pinned source and package revisions.

Keep these limits explicit and do not treat documentation as resolution:

- **H-02:** a DB owner/superuser can bypass application/trigger controls;
  least-privilege runtime-role separation is not demonstrated.
- **H-03:** principal IDs and content hashes do not prove distinct human
  identity, authorship, or independent auditor qualification; positive approval
  remains fail-closed.
- **H-04:** explicit helper-driven quarantine/manual reconciliation is tested;
  there is no supported operator interface or automated cold-restart recovery.
- Models, tools, shell/network workers, real external effects, production
  deployment, and autonomous operation are excluded and must remain disabled.

M2-B/M2-C items remain tracked as deferred or pending requirements, not
satisfied by transfer. Review does not grant authority to activate them.

## Reproduction and evidence

Use [`INDEPENDENT_REVIEW_RUNBOOK.md`](INDEPENDENT_REVIEW_RUNBOOK.md) from a
read-only clone. It requires a disposable loopback-only PostgreSQL instance,
isolated test copy, migration replay, warnings-as-errors suite, static checks,
and cleanup. Do not read operator dotenv files or connect to non-disposable
databases. Record exact commands, versions, outputs, skipped tests, and any
deviations. The existing 91-test result is implementer-run local technical
evidence, not independent reproduction.

The separate adversarial input report has SHA-256
`bd7592cb44704f94b357d3a237935187d458dee8dc495be6bc16ce58c1feff48` and is
described in `ADVERSARIAL_AUDIT_20261019.md`. It is not formal review evidence.

## Required report

The reviewer should produce an attributable report bound to both the full
implementation SHA and final package SHA, with:

1. Reviewer identity, qualifications and independence statement.
2. Scope, threat model, methods, files/contracts examined and exact revisions.
3. Independently reproduced checks and any test limitations.
4. Severity-ranked findings with precise file/line or contract references;
   separate historical-only findings from current candidate findings.
5. Unsupported or overstated guarantees, disposition of H-02/H-03/H-04, and
   residual risks.
6. A recommendation limited to M2-A (including reject/conditional/no opinion).

The report must state that it does not constitute CEO acceptance, authorize
PR #2 merge, production deployment, or external execution. M2-A acceptance and
integration remain blocked until findings are dispositioned and the competent
authority accepts the exact candidate and residual risks.

## Review model change (approved 2026-10-19)

GOV-REV-001 v1.1 supersedes the earlier human-reviewer requirement for ordinary technical assurance. A reviewer must be functionally independent with protected evidence and veto power. Same-process subagents without separate authority are insufficient. M2-A is not accepted.
