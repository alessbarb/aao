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
