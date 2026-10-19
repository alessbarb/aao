---
name: aao-postgres-authorization-concurrency
description: Design and verify AAO authorization, revocation, lease, and recovery behavior under PostgreSQL concurrency. Use for changes involving project grants, principal credential lifecycle, queue claims/completion, or reconciliation.
---

# AAO PostgreSQL Authorization and Concurrency

Use this skill for behavior that relies on PostgreSQL locks or transaction
boundaries. A green sequential test is not evidence that revocation, expiry, or
lease fencing behaves correctly under concurrent transactions.

## Boundaries

- Use only the explicitly disposable `aao_test`/CI test database for
  destructive integration tests. Do not connect this process to production.
- Never read, print, copy, or modify `.env.local` or `.env.test` contents in
  logs, tests, documentation, or artifacts. Load configuration only as the
  documented test runner requires.
- Never alter migrations `001` through `005`. Any schema change starts with a
  new descriptive migration and a documented rollback/forward plan.
- Keep external adapters, model execution, and side effects disabled.
- Do not treat this skill or a test run as independent review or acceptance.

## Procedure

1. Trace the real operation from its entrypoint through credential resolution,
   project/grant check, row locks, mutation, and journal write. Record the
   exact lock order and the competing revocation/recovery operation.
2. Write the denied and allowed cases first. Include wrong principal, wrong
   role, wrong project, absent/revoked grant, revoked/rotated credential,
   stale token, expired lease, and invalid resource state as applicable.
3. For the critical ordering, use separate PostgreSQL connections and prove
   that one transaction is blocked by the other (for example with
   `pg_stat_activity`/`pg_blocking_pids`), rather than inferring a race from
   thread timing alone. Release the blocker and assert the committed state and
   the next operation's authorization result.
4. Test both orderings where both operations can be valid in the initial
   state. If preconditions are mutually exclusive, do not invent a race; state
   the invariant and test the sequential state transition instead.
5. Use barriers only to expose competing schedules, not as proof of lock
   acquisition order. Repeat high-risk schedules and preserve the exact rerun
   count and outcomes.
6. Keep the test behind the repository's explicit disposable-database guard.
   Run the focused integration test, then the full warnings-as-errors suite,
   compilation, Ruff, dependency check, and `git diff --check`.
7. Record the exact code SHA, database/test scope, pass/skip/warning counts,
   CI result, and unresolved orderings in `docs/VERIFICATION_EVIDENCE_REGISTER.md`
   and the relevant authorization/recovery matrix.

## Example acceptance shape

For a protected write racing credential revocation:

- Hold the actual operation transaction after its in-transaction credential
  check, using a database lock or controlled hook.
- Start the real revocation API on another connection and verify it is blocked
  by the credential row lock.
- Release the protected transaction; verify it commits before revocation.
- Verify the revoked credential cannot perform the operation afterward.

For lease-owned operations, also assert the operation is bound to the exact
worker, current lease token, RUNNING state, active project, and database-clock
lease expiry. A barrier-started race can check allowed terminal outcomes, but
does not replace a demonstrated lock wait when the claim concerns blocking
serialization.
