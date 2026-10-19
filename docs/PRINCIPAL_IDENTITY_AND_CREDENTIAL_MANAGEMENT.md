# Principal identity and credential management

This document retains incremental implementation notes. **Current status:**
individual AGENT/AUDITOR bearer credentials are wired into PostgreSQL work,
review and project-read routes, and AGENT credentials are accepted by queue
claim/completion. The verified local baseline is recorded in
`VERIFICATION_EVIDENCE_REGISTER.md`; the exact current HTTP/internal operation
map is in `PRINCIPAL_AUTHORIZATION_MATRIX.md`. This remains development-only:
shared worker/reviewer fallbacks have been removed from the PostgreSQL API,
the CEO bearer is provisional, and independent review is unresolved. Remaining
concurrency and recovery gaps are listed in the authorization matrix and
backlog. M2 is not accepted.

Migration `006_unified_execution_identity` transfers legacy worker rows into
the AGENT credential registry, aborts on identity or digest collisions, then
drops the separate `worker_registrations` table.

## Initial implementation snapshot (historical)

Migration 005 adds an enabled/disabled credential record for independently
identified AGENT and AUDITOR principals. The Python verifier maps a presented
token to the stored principal identifier, without trusting caller-supplied IDs.
Disabled and unrecognized credentials are rejected.

At this initial checkpoint the registry was not wired into HTTP work/review
routes and no administrative provisioning API existed. That state has since
changed as described below. SHA-256 bearer-token digests assume high-entropy
generated tokens and are not for passwords.

Before adoption: add trusted credential provisioning, per-principal grants,
request-level principal binding, project isolation tests, revocation and
independence proofs, and migration integration validation. Do not enable
external-effect execution.

## First API adoption (historical checkpoint)

`POST /v1/work/{id}/reviews` now additionally accepts an individually
provisioned `X-Auditor-Token` and resolves the reviewer identity from the
database, never from a client-provided reviewer ID. The project-specific
`work.review` grant is still required. An invalid individual token is denied;
the shared `X-Review-Token` remains supported **only as a transitional
development compatibility route**, and must be removed before production.

To validate locally, apply migration `005_principal_credentials.sql` to
the isolated `aao_test` database (and `aao_dev` when ready), then run:
`AAO_ENV=test AAO_ENV_FILE=.env.test python -m pytest -q`.

Credentials must be generated locally and never copied into source, logs,
messages or documentation. Provisioning and rotation need a governed
administrative workflow; do not manually insert production credentials.
No execution authority is granted by authentication alone.

## Individual agent work identity (historical checkpoint)

The PostgreSQL work endpoints also accept `X-Agent-Token` with an enabled
`AGENT` principal credential. A valid bearer token resolves to the registered
principal ID; project-specific grants determine authorized operations.
The payload's `author_id` is not trusted. Revocation (`enabled=false`) blocks
subsequent requests. If an invalid individual token is sent alongside a
shared development worker token, the operation is denied without fallback.

This is a development-stage transition: the shared `X-Work-Token` is still
accepted where no individual token is supplied. It must be retired before
production, alongside the shared reviewer token.

A PostgreSQL integration regression test exercises cross-project denial,
non-spoofable work authorship and credential revocation. Execution leases
are still authenticated through a separate worker registration mechanism;
the two identity registries must be consolidated before M2 acceptance.

## Shared identity across work and inert execution (historical checkpoint)

The PostgreSQL queue's `claim()` and `complete()` accept
`agent_credential` and map it to an enabled `AGENT` principal in the
same database transaction as the lease operation. Exact `execution.claim`
project grants are still mandatory. Revocation blocks subsequent completion.
The one-shot inert worker forwards that credential, without invoking tools.

Legacy worker registrations remain available in development when no individual
credential is given. This is a transitional compatibility path, not accepted
production authentication. A database-backed test has been added for invalid
credential, authorized project claim, and revocation after claim. **It has not
yet been executed on the operator's machine.**

## Restriction of transitional shared credentials (historical checkpoint)

The work API, review API and project/board reads recognize individual AGENT /
AUDITOR bearer credentials. Project/board reads with `X-Agent-Token` are
filtered by that principal's `project.read` grants. A supplied but invalid
individual token never falls back to a shared development token.

`AAO_ALLOW_SHARED_DEV_TOKENS=false` disables `X-Work-Token` and
`X-Review-Token` compatibility in development; regardless of that setting,
`AAO_ENV=production` refuses these shared credentials. This gate does not
constitute production readiness: CEO still uses a prototype shared token,
provisioning and rotation require governance, and worker registrations remain
available through the old internal queue API. All external effects remain off.

The original validation-pending note for these changes is superseded by the
local validation recorded for commit
`d080da58d4a8a41749a932d8fdf2c1caec5ac652`. That run is engineering evidence,
not a concurrent revocation test, independent review or M2 acceptance.

## Credential lifecycle (historical validation checkpoint)

The development PostgreSQL API now exposes CEO-authorized operations:
`POST /v1/principals/credentials` (issue),
`POST /v1/principals/{id}/rotate` and
`POST /v1/principals/{id}/revoke`. Issuance accepts the principal identifier
and kind (`AGENT` or `AUDITOR`); the service generates a high-entropy token
and returns it **only in the issuance/rotation response**, storing only SHA-256
of the token. Rotating invalidates the prior token; revocation sets
`enabled=false`. All three actions append event records excluding tokens.
This is development administration, not a hardened production identity
provider or independent authorization to execute any project work.

The integration regression checks CEO-only issuance, duplicate denial,
rotation, revocation and audit events. It was included in the 51-test local
run recorded in `VERIFICATION_EVIDENCE_REGISTER.md`; that does not establish
production governance or M2 acceptance.
