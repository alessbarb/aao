# M2 — Principal authority and revocation boundaries

## Implemented candidate

Individual bearer credentials are initially authenticated before the PostgreSQL work transaction. Previously, project grants only verified the resolved principal identifier and grant, allowing authorization to outlive a concurrent credential revocation.

The require_grant function now verifies the individual credential's enabled state and kind under SELECT FOR SHARE, inside the same transaction as the protected work operation. This serializes against concurrent UPDATE-based revocation and rotation. Review requires AUDITOR; other currently implemented grant capabilities require AGENT. Shared development fallback remains limited to explicitly allowed development identities and capabilities.

## Boundaries and remaining risks

- The project listing endpoint performs its own grant queries and is not covered by the new transaction-time revalidation. Read paths need an independent audit.
- The queue still has legacy worker registrations. Its individual principal path already locks credential rows, but legacy retirement is outstanding.
- Grant expiry/revocation races and real database concurrent rotation must be tested.
- CEO authentication remains provisional. No production identity provider, privileged token management, or independent security approval exists.
- PostgreSQL role isolation, adverse concurrency, audit guarantees and cold-restart recovery remain acceptance gates.
- External execution and effects remain disabled.

## Evidence classification

Three additional unit tests were committed to check nonexistent, inactive, wrong-kind, active, and shared development principal behavior. The new revision remains UNVERIFIED pending operator execution of Ruff and the full disposable PostgreSQL suite. The most recent validated baseline was 5fe0b4b86d999b020e928e0bd4e8375e5c0dc7c9 (47 passing tests; warnings-as-errors clean). These changes are neither independent security review nor acceptance of M2.

## Increment: transactional project-list read authorization (candidate)

Project-list reads for individual agents now revalidate an active AGENT credential under `FOR SHARE` within the same database transaction as the project-scoped listing query. Shared development readers are rechecked against the development-only feature gate. An inactive, missing, or AUDITOR-kind credential is denied before project data is queried. A new isolated unit test covers these states and the SQL boundary. Direct board reads already route through `require_grant`, which checks individual credential state inside its transaction.

This increment is not yet locally verified. Read grants themselves are not locked, and project grant revocation, credential rotation races and database concurrency still require adversarial integration tests. The CEO development token is provisional. M2 remains open.
