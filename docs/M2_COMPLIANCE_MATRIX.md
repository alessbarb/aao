# M2 candidate compliance matrix

**Purpose:** engineering traceability for a reviewable M2 candidate, not a
ratified acceptance specification. The Constitution identifies itself as a
draft interpretation, and the engineering backlog identifies itself as an
initial planning seed. No approved M2 acceptance contract is currently present
in the repository. Therefore `SATISFECHO` below means only that the narrowly
stated candidate behavior is implemented and supported by the cited evidence;
it does not mean M2 is formally complete.

**Source revision:** `88ec4264d655e6d25ec2b8f6859019a411a797fa`.
**Verification:** see the exact-SHA entry in
[`VERIFICATION_EVIDENCE_REGISTER.md`](VERIFICATION_EVIDENCE_REGISTER.md).

| Requirement / source | Implementation and evidence | Residual risk / limit | Status |
| --- | --- | --- | --- |
| Confirmed CEO mandate before operating a project (Constitution §§1–4; backlog M0-02/03) | Mandate draft/confirm and project creation routes exist in `work_management_api.py`; project workflow integration tests exercise the path. AAO may be the first AAO project, subject to the same gate. | CEO is a static development/test bearer, not verified human identity or constitutional signature; no approved mandate for an operational AAO instance is recorded here. | **PARCIAL** for local candidate; **BLOQUEADO** for production authority and formal operating mandate. |
| Individual principal identity, roles, project grants, revocation (Constitution §§2–3, 10) | Migrations 005/006 and credential/grant transaction checks; selected actual PostgreSQL race tests cover grant/credential revocation and stale request contexts. See authorization matrix and evidence register. | Coverage is selected, not exhaustive; application checks are not PostgreSQL RLS/role isolation; no formal independent IAM review. | **PARCIAL** |
| Segregation of duties and auditor independence (Constitution §6) | Work author/reviewer principal-ID separation and execution claimant/reviewer ID separation are implemented; positive `APPROVE` remains fail-closed. | Different principal IDs do not establish distinct humans or organizations; no independent auditor identity proof, appointment, appeal path, or formal review evidence. | **PARCIAL** for denial controls; **PENDIENTE** for positive independent review. |
| Project data isolation (Constitution §7) | API reads and grants are scoped to project; evidence artifact primary key and lookups include project ID; tests cover cross-project authorization. | No DB RLS or isolated DB roles; privileged direct SQL/code can bypass application scope. | **PARCIAL** |
| Durable execution, leases, expiry and fencing (Constitution §8; backlog M2-02) | PostgreSQL queue, lease ownership/expiry, project state generation in migration 007, atomic claim/completion, `UNCERTAIN` quarantine; controlled integration schedules and selected cold-restart evidence are registered. | There is no autonomous worker runtime or scheduler/startup quarantine path. Leases are not signed attestations; no complete checkpoint protocol or exhaustive crash/restart matrix. | **PARCIAL** (durable inert candidate behavior is demonstrated; operational recovery is not). |
| Recovery and reconciliation (Constitution §8; backlog M2-06) | Explicit reconciliation requires active individual AUDITOR credential, project grant, project-scoped artifact reference, and current uncertain state; retry refuses paused projects or unresolved effects. Integration tests cover selected authorization and lock orderings. | Expiry quarantine is explicit/helper-driven. No restart orchestrator, recovery controller, or automated evidence-backed cold-recovery acceptance harness. | **PARCIAL** |
| Evidence provenance and artifact integrity (Constitution §6; backlog M1-04) | Migrations 008/009 and `evidence_registry.py` store project-scoped content by SHA-256, rehash on use, restrict submission and inspection to individual credentials/capabilities, and block row UPDATE/DELETE/TRUNCATE through triggers. 78 local PostgreSQL tests passed at exact SHA. | Hash integrity is not truth or authorship. A database owner can disable triggers or alter schema. No HTTP artifact surface; audit access is internal Python only. No signed disposition. | **PARCIAL** |
| External-effect containment and idempotency (backlog M2-03) | Effect proposal/rejection ledger is transactionally scoped, records journal events, and has selected locking/idempotency tests. No external adapter is enabled. | Provider-side fencing, exactly-once effects, external idempotency outcomes and reconciliation against a real provider are unimplemented and intentionally disabled. | **SATISFECHO** only for inert proposal/rejection containment; **DIFERIDO** for real provider effects. |
| Independent stop control (backlog M2-05; Constitution §10) | Project pause/state-generation fence and CEO-controlled development actions exist; stale leases cannot be revived by pause/resume. | No production CEO identity or independent stop controller outside the agent/application/database control plane. | **PARCIAL** locally; **PENDIENTE** for independent production control. |
| Sandbox worker (backlog M2-04) | Current one-shot worker only emits a deterministic inert marker; external tools, shell, network and model calls remain disabled. | A capability-constrained production sandbox is not implemented. | **DIFERIDO**; current inert worker is not a sandbox acceptance. |
| Independent security/architecture review and competent acceptance | Candidate review package is prepared by this repository; internal subagent reviews are recorded as internal only. | No formal independent reviewer report or CEO/competent owner acceptance exists. | **BLOQUEADO** pending qualified reviewer and formal authority. |

## Scope disposition

No autonomous model runtime, real tool execution, provider integration,
production deployment, or real external side effect is required or enabled by
this candidate. Such work is **DIFERIDO** pending authority and a separate
accepted design. The technical matrix cannot be used to infer those powers.
