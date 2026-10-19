# M2 individual development principals

Migration 005 adds an enabled/disabled credential record for independently
identified AGENT and AUDITOR principals. The Python verifier maps a presented
token to the stored principal identifier, without trusting caller-supplied IDs.
Disabled and unrecognized credentials are rejected.

This is a **preparatory component** and is not yet wired into the HTTP work
and review routes, which still use shared development tokens. SHA-256 bearer
token digests assume high-entropy generated tokens and are not for passwords.
No administrative provisioning API has been exposed.

Before adoption: add trusted credential provisioning, per-principal grants,
request-level principal binding, project isolation tests, revocation and
independence proofs, and migration integration validation. Do not enable
external-effect execution.

## First API adoption

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

## Individual agent work identity

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

## Shared identity across work and inert execution (candidate)

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
