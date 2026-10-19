# AAO Self Development Mandate

**Mandate ID:** `AAO-MANDATE-20261019-SELFDEV`
**Version:** 1.0
**Authority:** CEO
**Confirmed:** 2026-10-19
**Status:** CONFIRMED
**Project:** AAO — Self Development

## Decision source

This record formalizes the CEO's direct decision, “AAO — Mandato CEO confirmado: primer proyecto AAO Self Development,” provided in the Codex session dated 2026-10-19. That decision confirms the mandate and authorizes establishment of the project under the existing mandate and project procedure. It does not authorize production deployment, unrestricted execution, external effects, critical-PR merging, or acceptance of reserved risks.

## Objective

Build the minimum functional AAO core that can manage, develop, test, audit, and improve AAO software as its first project. The work must be observable from the AAO Control Center using the same authentic state as the backend.

## Success criteria

1. The confirmed mandate and its single associated project are recorded in PostgreSQL with auditable confirmation and creation events.
2. AAO can accept a bounded, authorized software objective and turn it into attributable work with explicit acceptance criteria and dependencies.
3. Work can be assigned to an individually identified agent and executed only in an isolated environment whose permissions and stop controls are demonstrated for that operation.
4. Verification results, audit findings, vetoes, changes, and pull requests are linked to the exact work and source revision; implementer and auditor authority are separated.
5. The Control Center presents the authentic path from mandate and project through objective, task, agent, execution, tests, audit, pull request, and result, with provenance and explicit unavailable/blocked states.
6. The system can continue bounded planning and verification without routine CEO intervention, while failing closed on unproven authority, evidence, isolation, or promotion requirements.

These are target acceptance criteria, not claims that current implementation satisfies them.

## Authorized scope and delegated engineering

- Implement, test, refactor, and document the AAO self-development core and Control Center within the existing constitutional and technical limits.
- Use local development and explicitly disposable test infrastructure; persist this mandate and project only in the identified development instance unless a separately authorized environment is established.
- Develop bounded planning, agent identity and authorization, isolated execution, verification, independent audit, evidence, and PR traceability only as their specific controls are implemented and demonstrated.
- Prepare PRs and technical recommendations. Opening or updating a PR is not permission to merge it or to promote an operational capability.

## Reserved authority and exclusions

CEO authority remains required for constitutional or strategic changes, expansion beyond this mandate, production deployment, extraordinary budgets, acceptance of high residual risk, and any other constitutionally reserved decision. Critical or already blocked PRs remain subject to their existing review and acceptance gates. This mandate does not authorize real external side effects, unrestricted model or tool access, production credentials, autonomous merging, or activation of execution whose isolation and suspension controls are not demonstrated.

The organization may propose changes to this mandate or the Constitution, but cannot confirm or approve them itself.

## Safety, security, and budget constraints

- Keep execution and external effects disabled unless the applicable authorization and control gates are met.
- Do not expose, copy, or log secrets. Do not use production databases or credentials for local verification.
- Use disposable databases for destructive tests; preserve migrations already applied and add descriptive migrations only when required.
- Preserve individual identities, project isolation, least privilege, independent audit, veto, exact-revision evidence, revocation, and fail-closed promotion controls.
- No budget or external-service expenditure is authorized by this mandate.

## Confirmation trace

The CEO confirmed this mandate directly in the Codex session on 2026-10-19. The application record must separately retain its generated mandate UUID, project UUID, `mandate.confirmed` event, and `project.created` event. This document is the governance record; it does not substitute for those persisted records.
