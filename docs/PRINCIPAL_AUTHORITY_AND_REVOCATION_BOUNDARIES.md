# M2 — Principal authority and revocation boundaries

## Current status

Individual project-list reads now revalidate AGENT credential state under
`FOR SHARE` inside their database transaction; board reads use the same
transaction-time guard via `require_grant`. The B023 fix and full 51-test local
validation are recorded at exact commit
`d080da58d4a8a41749a932d8fdf2c1caec5ac652` in
`VERIFICATION_EVIDENCE_REGISTER.md`. The implementation still has no proven
concurrent PostgreSQL revocation race: project-grant rows are not locked in
the protected request/execution paths, and sequential tests or stubbed SQL
assertions do not prove lock semantics. Legacy worker registration, provisional
CEO bearer, untrusted reconciliation reviewer identity and absent independent
security review remain open. M2 is not accepted.

## Implemented behavior (not accepted as M2)

Individual bearer credentials are initially authenticated before the PostgreSQL work transaction. Previously, project grants only verified the resolved principal identifier and grant, allowing authorization to outlive a concurrent credential revocation.

The require_grant function now verifies the individual credential's enabled state and kind under SELECT FOR SHARE, inside the same transaction as the protected work operation. This serializes against concurrent UPDATE-based revocation and rotation. Review requires AUDITOR; other currently implemented grant capabilities require AGENT. Shared development fallback remains limited to explicitly allowed development identities and capabilities.

## Boundaries and remaining risks

- Project listing and board reads now recheck individual credentials under `FOR SHARE`; the grant rows themselves are not locked, so grant revocation/expiry races remain.
- The queue still has legacy worker registrations. Its individual principal path already locks credential rows, but legacy retirement is outstanding.
- Grant expiry/revocation races and real database concurrent rotation must be tested.
- CEO authentication remains provisional. No production identity provider, privileged token management, or independent security approval exists.
- PostgreSQL role isolation, adverse concurrency, audit guarantees and cold-restart recovery remain acceptance gates.
- External execution and effects remain disabled.

## Historical evidence classification

Three additional unit tests check nonexistent, inactive, wrong-kind, active,
and shared development principal behavior. The validation-pending note is
historical: the full disposable PostgreSQL suite and Ruff were later executed
on the project-read increment. See the exact revision and results above and
in the evidence register. These changes are neither independent security
review nor acceptance of M2.

## Transactional project-list read authorization (historical checkpoint)

Project-list reads for individual agents now revalidate an active AGENT credential under `FOR SHARE` within the same database transaction as the project-scoped listing query. Shared development readers are rechecked against the development-only feature gate. An inactive, missing, or AUDITOR-kind credential is denied before project data is queried. A new isolated unit test covers these states and the SQL boundary. Direct board reads already route through `require_grant`, which checks individual credential state inside its transaction.

The local verification pending at the time of this increment was completed at
the revision recorded above. Read grants themselves are not locked, and
project-grant revocation, credential rotation races and database concurrency
still require adversarial integration tests. The CEO development token is
provisional. M2 remains open.
