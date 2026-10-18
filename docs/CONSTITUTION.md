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
- Review transitions fail closed until independent verification is implemented.
- Autonomous execution is disabled by default.
- SQLite is a disposable development store; PostgreSQL is the planned persistent datastore.
- No real project integrations, external side effects or model credentials are configured.

## Reserved operations

See `src/aao/policy.py`. These are prototype-deny gates, not the complete deployable policy engine.
