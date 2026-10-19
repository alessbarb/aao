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
