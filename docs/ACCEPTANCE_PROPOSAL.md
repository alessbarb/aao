# M2 acceptance proposal — not submitted for approval

**Status:** candidate evidence packet prepared; **M2 is not accepted**.
This document does not grant authority, alter the Constitution, confirm an
AAO project mandate, or authorize production or external execution.

**Implementation candidate proposed for review:**
`99760c7339323600368e5dbb145b088d83ad0715`.
**Verification limits:** local explicitly disposable PostgreSQL test run only;
see [`VERIFICATION_EVIDENCE_REGISTER.md`](VERIFICATION_EVIDENCE_REGISTER.md).

## Demonstrated at the stated candidate boundary

- PostgreSQL work/queue state persists; the candidate enforces project-scoped
  grants and individual AGENT/AUDITOR credentials in the application path.
- Claims/completions use bounded leases, PostgreSQL-clock expiry and project
  state generation fencing. Expired work is quarantined rather than retried
  automatically.
- Reconciliation is explicit, restricted to an AUDITOR credential and
  project-scoped capability, and checks evidence references against stored
  project-scoped bytes. An authorized internal auditor function can inspect
  those bytes.
- Effect proposals and rejections are ledger operations only. No provider,
  model, shell, network or real external action was enabled.
- Review `APPROVE` and completion to `DONE` remain fail-closed because positive
  reviewer independence and evidence sufficiency are not established.
- The exact candidate source passed 80 local tests with PostgreSQL and
  warnings-as-errors; compilation, Ruff, dependency consistency and whitespace
  checks also passed. CI was not awaited.

These are engineering facts within tested paths, not a statement that every
M2 requirement is satisfied.

## Outstanding before any formal M2 acceptance

1. Competent authority must define/confirm M2 acceptance scope; current
   Constitution is a draft and backlog is a planning seed.
2. A qualified independent security/architecture reviewer must review the
   exact SHA and issue a report; same-process subagents do not satisfy this.
3. Residual risks must be disposed against the accepted scope: development-only
   CEO identity, human auditor independence, DB-owner bypass, evidence truth
   and lifecycle, non-RLS project isolation, selected race coverage, and
   explicit/manual recovery without a scheduler.
4. If continuous or production operation is in scope, repeatable crash/restart
   recovery, least-privilege DB role evidence, operational stop control,
   backup/restore and deployment verification are still required.

## Deferred, not silently accepted

Real model execution, external tools/providers, production deployment,
provider-side exactly-once effect guarantees, production 24/7 operation and
Biopeia integration remain disabled or out of scope. AAO may be its own first
managed project only after the same applicable mandate/authorization gate as
any other project.

## Proposed eventual decision

After the scope is ratified and the independent report is reviewed, the CEO or
competent owner may choose one of:

- **Accept bounded M2 candidate** for a precisely stated inert/local operating
  scope with enumerated residual-risk dispositions; or
- **Reject/defer** and direct closure of specific findings.

No decision is requested on this draft package alone. A future approval must
identify the exact SHA, accepted scope, accepted exceptions, operating limits,
and whether any new authority is granted. No authority for external execution
is implied.
