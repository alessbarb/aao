# Adversarial technical audit findings — 2026-10-19

## Provenance and limits

This record evaluates `AAO_M2A_AUDITORIA_TECNICA_EXTERNA_20261019.md`, a
remote static inspection that reported no execution of code, tests, migrations,
or PostgreSQL. It is useful adversarial input, but it is not a formal
independent security/architecture review, reviewer qualification evidence, or
M2-A acceptance.

Frozen review references remain unchanged: implementation review SHA
`dc084417a2ba683fe4737342f89e9cd1036b38ad` and package/PR #2 SHA
`ef1a6e64ad4d6523cacd6c98a3b25ae7cebf4ad5`. The correction for H-01 is a
separate proposed code revision, `31e7397be082394a6da95eadebd0d8ad6bf99c39`.
The correction does not rewrite or move either frozen ref. It requires a new
formal review against the corrected code and its final review-package SHA.

## Finding dispositions

### H-01 — Confirmed and corrected in a separate candidate

At frozen SHA `dc084417`, `_development_credentials_enabled()` used
`os.getenv("AAO_ENV", "development")`, which enabled individual AGENT/AUDITOR
credential checks if the variable was absent. The CEO bearer guard already
required an explicit environment. This was a real fail-open inconsistency.

Revision `31e7397be082394a6da95eadebd0d8ad6bf99c39` changes only the default to
empty, preserving acceptance of the two normalized explicit values
`development` and `test`. New regression cases exercise both
`authenticate()` and `authenticate_in_transaction()` with the variable absent,
empty, production, or misspelled, and assert rejection before database access.
No legacy credential path or compatibility fallback was added. Focused
credential tests passed 26 tests; the full disposable PostgreSQL suite passed
91 tests with warnings as errors (details in the evidence register).

**Disposition:** corrected in a separate candidate; the frozen PR #2 package
still contains the finding. Do not treat H-01 as closed for SHA `ef1a6e64`.

### H-02 — Confirmed known trust-boundary limit; formal residual-risk disposition
required

Migrations 008/009 and `evidence_registry.py` protect application-level
append-only behavior and byte integrity. They do not prevent a PostgreSQL
schema owner/superuser from disabling/dropping triggers or changing the schema.
The disposable-suite role is the database/schema owner, so these test results
do not establish least-privilege runtime permissions or owner-resistant
immutability. This is consistent with the existing threat boundary and is not
a newly reproduced application bypass.

**Disposition:** not an M2-A implementation defect for its bounded
application-level evidence-integrity claim. Keep owner tampering and the lack
of a segregated least-privilege runtime role as explicit M2-A residual risks
requiring competent acceptance/disposition. Production role separation,
backup/restore, and continuous operational controls remain M2-C. Never claim
absolute or owner-resistant immutability.

### H-03 — Confirmed limitation; approval gate remains fail-closed

SHA-256 rehashing establishes stored-byte integrity only. Credential records
establish application principal IDs, not distinct humans, appointment, or
organizational independence. `review.py` blocks `APPROVE`; the work API blocks
positive approval and completion when independence/evidence cannot be
verified. This behavior is consistent with the required M2-A safety boundary.

**Disposition:** no code change. Lack of verifiable human independence is a
formal review/acceptance blocker, not a defect to paper over with additional
software claims. Auditor identity binding, approved review ceremony, and
positive governed review must remain gated; any runtime capability needed for
that belongs to separately scoped M2-B/C work. This audit report does not
satisfy the independent-review gate.

### H-04 — Partially confirmed; bounded manual controls exist, automated
recovery is deferred

The PostgreSQL queue implements explicit expiry quarantine to `UNCERTAIN`;
`execution_reconciliation.reconcile()` requires an active AUDITOR credential,
project grant, distinct principal from the former worker, valid project-scoped
evidence, and eligible uncertain state. Integration tests exercise quarantine
and both manual dispositions. There is no startup/periodic controller or
repeatable cold-process restart harness. The manual function is an internal
Python operation, not an HTTP/operator interface, and tests do not prove
human identity or unattended operations.

**Disposition:** no autonomous restart/recovery defect within M2-A's inert
boundary; automated recovery is reserved to M2-B/C. M2-A may claim only the
tested explicit quarantine and authorized manual reconciliation code paths.
Its operational limitation (trusted internal caller; no supported operator
interface) remains explicit for formal M2-A risk disposition. Do not imply
continuous recovery or production operability.

### H-05 — Verified at the frozen references; corrected-candidate trace is new

Live GitHub verification on 2026-10-19 reports PR #2 OPEN/DRAFT at
`ef1a6e64ad4d6523cacd6c98a3b25ae7cebf4ad5`. The frozen implementation is
`dc084417a2ba683fe4737342f89e9cd1036b38ad`; `git diff` over `src`, `tests`,
and `db` between those revisions is empty, confirming the intervening package
changes are documentation-only. The PR head therefore correctly binds the
reported prior test source, but not the H-01 correction.

The corrected implementation `31e7397be082394a6da95eadebd0d8ad6bf99c39`
has separate local full-suite evidence. PR #2 remains on its frozen package;
it was not moved to the corrected candidate. A future formal review request
must identify the corrected implementation SHA and the final package SHA
separately, and reviewers must not use the old package as evidence for the
correction.

**Disposition:** frozen trace verified; future candidate trace must be
re-pinned. The code fix and this response do not update or merge PR #2.

## Overall disposition

H-01 is fixed in the separate proposed revision. H-02 is a known M2-A residual
risk pending competent disposition; H-03 remains a fail-closed acceptance
gate; H-04's tested manual subset is within M2-A while automated restart
recovery remains deferred; H-05 is verified for the frozen pair. The report is
an adversarial technical input only. M2-A acceptance, formal independent
review, and integration into `main` remain blocked.
