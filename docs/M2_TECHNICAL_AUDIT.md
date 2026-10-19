# M2 candidate technical audit

**Audit basis:** code and documents at
`88ec4264d655e6d25ec2b8f6859019a411a797fa`, plus local verification recorded
in [`VERIFICATION_EVIDENCE_REGISTER.md`](VERIFICATION_EVIDENCE_REGISTER.md).
This is an engineering audit, not a formal independent review. It uses the
draft Constitution and planning backlog as provisional traceability sources;
neither currently defines a ratified M2 acceptance contract.

## Findings

### P0 — Formal acceptance boundary is undefined

`docs/CONSTITUTION.md` describes itself as a draft engineering interpretation,
not a CEO-confirmed mandate. `docs/ENGINEERING_BACKLOG.md` calls itself an
initial planning seed. Its M2 entries include broad ambitions (sandbox runners,
signed leases/checkpoints, stop controls, repeated crash delivery) without
objective acceptance tests or a declared deployment boundary. Therefore the
repository supports a technical candidate review, but cannot prove that all
approved M2 requirements are satisfied. No code change can resolve this
authority gap.

### P0 — CEO and auditor human identities are not established

The development API uses a static CEO bearer only in explicit development/test
modes. AGENT/AUDITOR credentials are individual application identities, but
there is no verified binding to distinct humans, constitutional signatures,
auditor appointment, or independent approval ceremony. The system correctly
keeps positive work approval fail-closed. Do not treat a principal ID or a
passing test as a human identity proof.

### P0 — Application authorization is not a database security boundary

Operations check individual credentials and grants under PostgreSQL row locks;
selected revocation schedules observe real blocking behavior. However, no
PostgreSQL role isolation or RLS is established. A direct SQL/code actor with
privileges can bypass application checks. Migrations 008/009 also use triggers
that a database owner could disable or drop. Restricting the DB role and
separating administrative ownership needs an accepted runtime threat model.

### P0 — Recovery remains explicit, not autonomous

The durable queue records leases and expiry; `quarantine_expired()` moves stale
leases to `UNCERTAIN`, and reconciliation is explicit. There is no startup or
periodic recovery scheduler and no integrated autonomous worker supervisor.
The manual cold-restart observation is bounded historical evidence, not a
repeatable crash/restart acceptance harness. This is appropriate for a
non-operational candidate but incomplete for any claim of continuously
recovering execution.

### P0 — Integrity does not establish evidentiary validity

Artifacts now have project-scoped SHA-256 addressing, rehash-on-use, bounded
size/reference count, and application capability checks. Internal `read_evidence`
allows a granted individual AUDITOR credential to inspect bytes. Neither the
hash nor the identity credential proves factual truth, human authorship,
independence, or sufficiency for a disposition. Evidence is stored as database
`bytea`; data classification, retention, backup, and confidentiality policy
remain unspecified. Positive approval stays disabled.

### P1 — Selected PostgreSQL race tests are strong evidence, not exhaustive

Integration tests use separate connections and observed lock blockers for
selected project-grant deletion, credential revocation/rotation, queue
claim/completion, review, effect proposal/rejection, and reconciliation
orderings. The exact set is described in the authorization matrix and evidence
register. Not every operation/order, lease-expiry-under-long-transaction
policy, database-owner action, or hostile schedule has been tested. Avoid
absolute atomicity or exhaustive-race claims.

### P1 — Schema rollout and runtime operations need exact environment evidence

Migrations 008/009 are descriptive and the local disposable test database was
advanced under an explicit disposable guard. CI configuration was updated to
apply them but CI was not run or awaited. No production migration, backup
restore, least-privilege database role, or deployed-service verification is
claimed.

## Architectural dispositions

- Keep the worker and effect adapter inert. Provider-side exactly-once behavior
  cannot be validated without an authorized external system and is deferred.
- Keep `APPROVE` and `VERIFIED -> DONE` fail-closed until independent human
  identity, inspectable evidence and an approved review policy exist.
- Treat AAO as eligible to be its own first managed project, not as an implicit
  project record or mandate. It must enter the same CEO-confirmed workflow.
- Do not implement production CEO authentication, constitutional revision,
  live effects, or irreversible operation under this technical delegation.

## Internal review inputs

Read-only architecture, IAM/adversarial, database/concurrency, and evidence
design subagent reviews were used to find issues and improve the candidate.
They ran in the same process context and are **not** the formal independent
review required for acceptance.
