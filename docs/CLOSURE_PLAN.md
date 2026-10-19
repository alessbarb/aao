# M2-A candidate closure plan

The CEO's M2-A/M2-B/M2-C scope decision is recorded in
[`SCOPE_DISPOSITION.md`](SCOPE_DISPOSITION.md). This plan closes only the
bounded M2-A candidate; later-stage requirements remain visible and pending.
M2-A is not accepted until the formal independent review and competent
acceptance gates are complete.

## M2-A closure sequence

| Order | Required action | Exit evidence | Owner / status |
| --- | --- | --- | --- |
| 1 | Pin implementation candidate and review package separately; verify local branch, remote refs, and live PR #2 head. | Exact local and live refs recorded; corrected candidate gets its own source/package pin. | Corrected implementation `31e7397be082394a6da95eadebd0d8ad6bf99c39`; initial corrected package `c9b2c7ad44d2cadc2e214904073073221e1207cd`. Frozen PR #2 remains implementation `dc084417a2ba683fe4737342f89e9cd1036b38ad`, package/head `ef1a6e64ad4d6523cacd6c98a3b25ae7cebf4ad5`, OPEN/DRAFT. Final package with formal review request is to be pinned after commit. |
| 2 | Prove clean migration-chain application of 001–009 on a newly created, explicitly disposable PostgreSQL database; do not alter applied migrations 001–007. | Fresh replay, legacy-row upgrade, terminal version 009, full suite, cleanup result and exact candidate revision recorded in evidence register. | Engineering; completed locally. |
| 3 | Run M2-A acceptance suite at the exact candidate, including all PostgreSQL tests without skips/warnings, compilation, Ruff, dependency consistency and diff checks. | Exact code SHA and outputs in evidence register. CI is reported separately and is not used as a substitute. | Engineering; corrected code candidate `31e7397` and clean package clone `c9b2c7a` each passed 91 tests and static checks against disposable PostgreSQL. |
| 4 | Obtain formal independent security/architecture review of the corrected candidate, migrations 006–009, criteria, evidence, threat boundary and residual risks. | Reviewer identity/qualification/independence statement, exact source/package SHAs, reproduced commands, findings and recommendation. | Reviewer-facing request prepared in `FORMAL_REVIEW_REQUEST.md`; no qualified independent reviewer assigned. PR #2 is the frozen historical pair, not the corrected review target. |
| 5 | Resolve findings within authority; retest affected behavior and update evidence. Do not enable external effects, positive approval, or production operation. | Findings are fixed or explicitly dispositioned for M2-A; exact post-fix SHA and regression evidence. | H-01 fixed on separate candidate `31e7397`; H-02 residual disposition, H-03 formal independent human review, H-04 bounded manual recovery and H-05 repinning remain documented in `ADVERSARIAL_AUDIT_20261019.md`. Formal review and CEO disposition remain pending. |
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
