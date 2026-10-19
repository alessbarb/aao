# M2-A candidate closure plan

The CEO's M2-A/M2-B/M2-C scope decision is recorded in
[`SCOPE_DISPOSITION.md`](SCOPE_DISPOSITION.md). This plan closes only the
bounded M2-A candidate; later-stage requirements remain visible and pending.
M2-A is not accepted until the formal independent review and competent
acceptance gates are complete.

## M2-A closure sequence

| Order | Required action | Exit evidence | Owner / status |
| --- | --- | --- | --- |
| 1 | Pin the implementation candidate and PR package revisions separately; verify local branch, both remote refs, and live PR #2 head. | Local `HEAD`, candidate source SHA, both branch refs and PR head recorded; no uncommitted code changes. | Engineering; local `HEAD`, both remote refs, and PR #2 currently match `293ef79a147ad05f4c56fd4898c11a7e725b9441`; recheck at formal review checkout. |
| 2 | Prove clean migration-chain application of 001–009 on a newly created, explicitly disposable PostgreSQL database; do not alter applied migrations 001–007. | Fresh replay, legacy-row upgrade, terminal version 009, full suite, cleanup result and exact candidate revision recorded in evidence register. | Engineering; completed locally. |
| 3 | Run M2-A acceptance suite at the exact candidate, including all PostgreSQL tests without skips/warnings, compilation, Ruff, dependency consistency and diff checks. | Exact code SHA and outputs in evidence register. CI is reported separately and is not used as a substitute. | Engineering; code candidate `9fa503c` passed 83 tests and static checks; later commits are documentation-only. |
| 4 | Request formal independent security/architecture review of the current exact PR head, implementation changes, migrations 006–009, criteria, evidence, threat boundary and residual risks. | Reviewer identity/qualification/independence statement, reviewed SHA, reproduced commands, findings and recommendation. | Review request comment is posted against PR #2 head `293ef79`; no reviewer assigned. Current GitHub collaborator roster exposes only the repository owner, who cannot serve as the independent reviewer. |
| 5 | Resolve findings within authority; retest affected behavior and update evidence. Do not enable external effects, positive approval, or production operation. | Findings are fixed or explicitly dispositioned for M2-A; exact post-fix SHA and regression evidence. | Engineering after report. |
| 6 | Submit the M2-A acceptance proposal, with accepted residual risks and operating limits, for competent acceptance. | Explicit accept/reject at exact SHA; no self-acceptance by engineering. | CEO/competent authority; not requested until review is complete. |

## Requirements retained for M2-B and M2-C

| Original backlog requirement | Stage | State; not satisfied by transfer |
| --- | --- | --- |
| M2-02 signed leases/checkpoints and governed runtime | M2-B | Pending; the database lease/fencing subset is M2-A only. |
| M2-03 provider-side external effect reconciliation/idempotency | Stage-specific scope must be formalized before implementation; real effects remain unauthorized | Not implemented; no real adapter or effect is enabled by the CEO scope decision. |
| M2-04 sandbox runners with operation-scoped capabilities | M2-B | Pending; the SQLite prototype route is not a sandbox. |
| M2-05 stop controls independent of an active runtime | M2-B | Pending; M2-A covers only project state fencing in the inert candidate. |
| M2-06 automated restart recovery and repeated delivery | M2-B; continuous full recovery in M2-C | Pending; M2-A covers explicit quarantine/manual reconciliation and selected idempotent HTTP replay. |
| Continuous operation, deployment, supervision, production isolation | M2-C | Scope must be formalized before implementation. |

## Explicitly not part of M2-A acceptance

- Real model/provider/tool execution, shell/network access, or external effects.
- A continuously running autonomous worker, scheduler, or restart controller.
- Production CEO identity/signatures, production deployment, or 24/7 service.
- Provider-side exactly-once guarantees or irreversible operations.
- Formal constitutional changes or any new operating authority.

No feature in this list is implied to be completed or accepted. Each later
stage must receive its own measurable scope and required authority before work
that could activate the capability begins.
