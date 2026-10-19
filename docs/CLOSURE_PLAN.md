# M2 candidate closure plan

This is a finite, evidence-driven closure plan. It does not broaden M2 into
live AI execution or external actions. Priority order reflects the actual
blockers found in the candidate audit.

| Order | Required action | Exit evidence | Owner / disposition |
| --- | --- | --- | --- |
| 1 | **Confirm M2 acceptance scope and authority.** Decide whether M2 means an inert durable execution/recovery candidate or includes production identity, autonomous recovery, sandboxing and provider effects. Convert the accepted scope into criteria tied to Constitution/backlog. | CEO/competent-owner approved scope and measurable acceptance matrix; explicit deferments and risk authority. | Reserved human decision. Until then, this package is a candidate audit only. |
| 2 | **Independent security/architecture review** of the exact candidate SHA, migrations 006–009, authorization matrix, threat model and evidence register. Reviewer must be independent of implementation and able to inspect the artifacts/tests. Draft PR #2 is the review vehicle. | Signed/attributed report with findings, severity, affected SHA and disposition; no unresolved critical/high findings unless accepted by competent authority. | External/authorized reviewer required; internal subagent reviews do not satisfy it. No formal reviewer is assigned yet. |
| 3 | **Close bounded evidence/authorization findings** from the formal review. At minimum assess credential/grant race coverage for evidence submission/reading, DB role ownership and trigger bypass, evidence data retention/confidentiality, reviewer independence and negative access tests. | Reproducible PostgreSQL tests and role/runtime evidence for the accepted threat boundary; migration corrections only as new migrations. | Engineering; no production secrets or live effects. |
| 4 | **Operational recovery gate**, only if included in accepted M2 scope: define manual vs automatic quarantine ownership, then prove cold restart, expired lease recovery, repeated delivery, pause/cancel, revocation and `UNCERTAIN` reconciliation with an automated isolated-DB harness and runbook. | Exact-SHA suite/harness output plus documented operator procedure and recovery evidence. | Engineering if scoped; otherwise record as a formal deferment. |
| 5 | **Reproducibility and integration readiness.** Run local full suite against the exact candidate migration chain, CI checks when convenient, migration replay from a clean disposable DB, and restore procedure relevant to the accepted scope. | Exact SHA, commands/results, migration list, CI state and environment scope in evidence register. | Engineering. CI was not awaited for the current checkpoint per operator instruction. |
| 6 | **Prepare CEO acceptance proposal** after review findings are resolved or formally dispositioned. Separate demonstrated guarantees, limitations, deferments and reserved risks. | Complete acceptance package and exact requested decision; no self-acceptance by engineering. | CEO/competent authority. |

## Work that is not a closure prerequisite unless explicitly added to scope

- Real model/provider integration, shell/network/tools, autonomous external
  actions, production deployment, 24/7 operations, or provider-level exactly-once
  semantics.
- Biopeia as a dependency. AAO itself may be the first managed project after
  its own mandate is confirmed.
- Broad refactors, new agent abstractions, or repeated concurrency schedules
  already demonstrated by controlled PostgreSQL blockers without a new threat
  or finding.

## Current state

Step 1 remains open because the repository contains no ratified M2 criteria.
The candidate has made engineering progress and has local verification, but is
not ready for formal acceptance until the scope decision, independent review,
and exact evidence disposition are available. Continue authorized technical
work on bounded defects while those gates are pending.
