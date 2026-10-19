# M2-A formal review transmittal

**Status:** package pinned; reviewer not yet assigned. This transmittal does not
constitute an independent review, CEO acceptance, merge approval, or operating
authorization.

## Exact revisions

- **Implementation/source under review:**
  `31e7397be082394a6da95eadebd0d8ad6bf99c39`
- **Corrected M2-A documentation package under review:**
  `17e3e3bcda6fde776f41da59fe1b9648cdfc80ef`
- **Initial corrected documentation package:**
  `c9b2c7ad44d2cadc2e214904073073221e1207cd`
- **Historical frozen PR #2 candidate, lineage only:** implementation
  `dc084417a2ba683fe4737342f89e9cd1036b38ad`, package/head
  `ef1a6e64ad4d6523cacd6c98a3b25ae7cebf4ad5`.

The transmittal itself is a separate metadata commit. The exact review-package
tree is the package SHA above; do not silently replace it with the transmittal
commit or the live PR #2 head. Confirm the full SHA and source-tree equality
before review:

```bash
git checkout 17e3e3bcda6fde776f41da59fe1b9648cdfc80ef
git rev-parse HEAD
git diff --exit-code 31e7397be082394a6da95eadebd0d8ad6bf99c39 HEAD -- src tests db
```

The exact source/test/migration equality check passed locally when this
transmittal was prepared. The review request and read-only reproduction
procedure are in `FORMAL_REVIEW_REQUEST.md` and
`INDEPENDENT_REVIEW_RUNBOOK.md`. The reviewer must return an attributable
report that names both exact SHAs and meets the independence/qualification
requirements in the request. PR #2 remains OPEN/DRAFT at the historical
candidate; it is not this review target and must not be merged.

## Availability and reviewer assignment

The corrected review branch is `fix/m2a-explicit-principal-environment`.
At preparation time, the repository collaborator listing contained only the
implementing owner, and PR #2 had no review requests or submitted reviews.
Therefore no qualified independent reviewer is represented as assigned by
this transmittal. A human reviewer must be identified and asked to review the
exact pair above; an internal agent, automated audit, or implementer-authored
report is insufficient.

## Review limits

Review is limited to bounded inert M2-A. H-02 (privileged database-owner
bypass), H-03 (human identity and reviewer independence not proven), and H-04
(no supported operator interface or automated cold-restart recovery) remain
explicit residual risks/limitations, not satisfied requirements. Models,
tools, shell/network execution, real external effects, production deployment,
merge, and M2-A acceptance are not authorized by this transmittal.
