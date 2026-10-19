# Durable execution technology evaluation

## Decision

For the current AAO candidate, retain the PostgreSQL-backed execution queue.
Do not introduce Temporal or another orchestration service in this increment.
This is an engineering recommendation for the current inert, local/testable
boundary, not a CEO scope decision and not a claim that all backlog M2
execution criteria are complete.

## Comparison at the current boundary

| Concern | Existing PostgreSQL queue | Temporal |
| --- | --- | --- |
| Durable state | AAO-owned queue, lease, journal and uncertainty records in PostgreSQL | Temporal persists workflow state and execution history in its service persistence layer |
| Dispatch/recovery model | AAO claims work transactionally; stale or uncertain work requires explicit reconciliation | Temporal task queues dispatch work and workflow code can be replayed from recorded history |
| Operational footprint | Existing PostgreSQL dependency and AAO recovery code | Adds an operated Temporal service and its persistence/configuration; does not remove AAO authorization or effect controls |
| Current fit | Already supports the inert candidate's bounded workflows and integration tests | No measured current need for richer workflow orchestration; adoption would add operational surface without closing human authority or independent-review gaps |

Temporal's official documentation describes its persistence model, task
queues and replay behavior: [Persistence](https://docs.temporal.io/temporal-service/persistence),
[Tasks](https://docs.temporal.io/tasks), and the
[Self-hosted Service Guide](https://docs.temporal.io/self-hosted-guide).
Those capabilities are useful when workflow history, timers/signals, replay,
scale, or operational recovery needs justify the additional service. They do
not by themselves provide AAO project grants, constitutional approval,
auditor independence, or safe external-effect semantics.

## Revisit triggers

Re-evaluate only when an approved operating scope requires workflow features
that the PostgreSQL queue cannot meet, or measured operational evidence shows
that its recovery/dispatch burden is unacceptable. Any adoption proposal must
include migration/ownership boundaries, authorization propagation, failure
and recovery tests, deployment responsibility, and explicit external-effect
gates. Until then, the simpler existing persistence model is the lower-risk
choice for a non-operational candidate.
