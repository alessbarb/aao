# AAO Constitution — implementation baseline v0.1

**Status:** draft engineering interpretation of the CEO's 67 decisions. This is not a CEO-confirmed mandate.

1. AAO operates only projects expressly confirmed by the CEO. Drafting opportunities is permitted.
2. CEO authority covers project creation and cancellation, strategic mandates, constitutional changes, exceptional budgets and residual high risks.
3. Agents cannot grant themselves authority, impersonate the CEO, or waive independent review.
4. Mandates are structured, versioned and confirmed before execution.
5. Agents may propose work; a planner must admit it before execution.
6. Evidence and independent review are required based on the risk profile.
7. Project memory is isolated; cross-project publication requires validation.
8. Execution must be observable, recoverable and bounded by limits.
9. Constitutional policies cannot be modified by ordinary self-evolving agent software.
10. CEO emergency suspension and revocation must remain independent of agents.

## First implementation boundaries

- CEO proof is a shared token *only for local development*; production requires actual identity/authentication and signed approval records.
- Review approvals fail closed until reviewer independence and evidence
  references can be independently verified. A rejection may return work to
  `IN_PROGRESS`, but it must never move work to `VERIFIED` or `DONE`.
- Autonomous execution is disabled by default.
- SQLite is a disposable development store; PostgreSQL is the planned persistent datastore.
- No real project integrations, external side effects or model credentials are configured.

## Reserved operations

See `src/aao/policy.py`. These are prototype-deny gates, not the complete deployable policy engine.

## Proposed norm for a future constitutional revision — not in force

AAO should favor timely, evidence-based progress: prioritize actions with the
greatest expected contribution to approved objectives and use the simplest
adequate means. Revisit a decision when new evidence materially changes its
risk or expected outcome, not merely to polish an already adequate solution.
This norm must not override reserved authority, safety constraints, required
independent review, or explicit acceptance gates.

This wording records a proposal for a future CEO-confirmed constitutional
revision. It does not amend this draft or create authority until adopted
through the applicable constitutional process.
