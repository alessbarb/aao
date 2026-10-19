# Independent audit service — minimal mechanism (GOV-REV-001 v1.1)

**Status:** candidate audit-domain code. It is **not trusted** until a reviewer
independent of its author reviews an exact revision and that revision is listed
in the trusted policy's `trusted_auditor_revisions`. It grants no merge,
deployment or credential authority.

Code: `src/aao/independent_audit.py`. Tests: `tests/test_independent_audit.py`.
The existing verifier `src/aao/pr_conformity.py` (from `main`) is reused
unchanged; the emitter produces exactly the signed report it checks.

## What it does

| GOV-REV-001 requirement | Mechanism |
| --- | --- |
| 1. Candidate by exact SHA | Fresh clone, detached at the full 40-hex SHA, `HEAD` and cleanliness verified before and after checks; the PR head is re-read before the verdict is recorded and a moved head aborts without a verdict. |
| 2. Read-only evidence channel | GitHub is read only (`gh api` GETs). Candidate is mounted read-only in bubblewrap with no network, home or credentials. Evidence files are written `0444`, content-addressed by SHA-256. |
| 3. Technical and adversarial checks | Policy-defined Python argv (ruff, pytest) in the sandbox; deterministic adversarial rules: changes to protected audit/governance/CI paths, deleted tests, added skip/xfail, net-removed assertions. |
| 4. Criteria protected from the implementer | Checks, protected paths and dispositions live only in the trusted policy outside the candidate; the auditor code runs from its own checkout, never from the candidate tree. Candidate CI results are recorded as *implementer-controlled* inputs. |
| 5. Report bound to SHA, policy and evidence | `candidate_sha`, `base_sha`, `policy_sha256`, `auditor_revision`, `evidence_files {digest: path}`, scope, limitations, residual risks, permitted/prohibited operations. |
| 6. Separate auditor identity | Ed25519 detached signature, verified by `pr_conformity` against the public key in the trusted policy. |
| 7. Credentials outside developer control | Signing is refused (`provisional` verdict, no signature) unless: running as `auditor_os_user`, that account is not in `developer_os_users`, the key is owned by it with no group/other bits, and the running auditor code is a clean revision listed in `trusted_auditor_revisions`. |
| 8. Accept / reject / veto record | Append-only, hash-chained JSONL ledger (`approve`, `reject`, `veto`, `provisional`). |
| 9. Block absent/invalid/stale/vetoed verdicts | `promotion_decision` = `pr_conformity.evaluate` + ledger: chain must verify, any veto for the SHA is sticky, and only the latest decision for that SHA counts. |
| 10. Independent merge authority | Not implemented by design: the gate only decides. Merging must be done by a separate identity (see dependencies). |

Every finding blocks unless the trusted policy holds a disposition keyed by
`"<candidate_sha>:<finding_id>"`, so a disposition never carries over to a new
revision.

## Usage

```bash
# Audit (read-only against GitHub); run as the auditor account.
python -m aao.independent_audit audit --github-pr alessbarb/aao 10 \
  --policy /etc/aao-auditor/policy.json --key /etc/aao-auditor/auditor-ed25519.pem \
  --output /var/lib/aao-auditor/runs/pr10-<sha> --ledger /var/lib/aao-auditor/ledger.jsonl \
  [--source <local mirror>] [--veto "<reason>"]

# Promotion decision, run by the merge authority on a clean checkout at the SHA.
python -m aao.independent_audit gate --repository <checkout> --policy ... \
  --report <run>/report.json --signature <run>/report.sig --ledger ... \
  --github-pr alessbarb/aao 10 --implementer <PR author from the merge authority>
```

Policy fields: `version`, `auditor_id`, `auditor_os_user`, `developer_os_users`,
`auditors` (id → public key path), `required_checks` (GitHub check names),
`audit_checks` (name → Python argv), `protected_paths`, `dispositions`,
`trusted_auditor_revisions`.

## First run against PR #10 and PR #11 (provisional)

Run on 2026-10-19 as OS user `alessbarb` with a policy that designates
`aao-auditor` as auditor and `alessbarb` as developer, so the emitter refused to
sign. The auditor code was this branch's uncommitted working tree (its
revision did not match a reviewed one). These are adversarial evidence inputs,
**not** audit verdicts.

| PR | Candidate SHA | Base SHA | Sandbox ruff / pytest | Blocking findings | Verdict |
| --- | --- | --- | --- | --- | --- |
| #10 | `523a5986d4ae22b466aaabe59821dc7acecfaef5` | `b1ce576` (main) | pass / 76 passed, 34 skipped | `.github/workflows/ci.yml` changed; new PostgreSQL `skipif` in `tests/test_project_workflow_integration.py` | provisional |
| #11 | `c3d1df912912974deef5fb1684738f226e62167f` | `523a5986` (PR #10) | pass / 114 passed, 38 skipped | changes to `ci.yml`, `pr_conformity.py`, `review.py`, migration 011 and `docs/CEO_MANDATE_…`; new PostgreSQL `skipif` gates in three integration test files | provisional |

PR #11's head moved from `f929827` to `c3d1df9` during the session; the first
audit attempt bound to the new head. The gate run on PR #10 returned
`conformant: false` (`signed audit report is absent`).

Disposition guidance for an independent auditor: the `skipif` findings are
PostgreSQL environment gates (the sandbox has no database, so those tests are
covered only by implementer-controlled CI); the `pr_conformity.py`/`review.py`
changes alter promotion controls and need review by an auditor independent of
the implementer; `docs/CEO_MANDATE_…` asserts CEO authority, which the auditor
cannot verify from the candidate — it needs confirmation from the CEO through a
channel outside the repository.

## Dependencies outside the current mandate

1. **Auditor account and key custody.** A dedicated OS account (or host/VM)
   `aao-auditor` that the developer cannot become (no shared sudo), owning the
   policy, Ed25519 key, ledger and evidence directory. Provisioning is an
   infrastructure/authority decision.
2. **Read channel.** `gh` currently uses the developer's token. The auditor
   needs its own read-only GitHub credential (fine-grained token or deploy key).
3. **Merge authority and enforcement.** The repository has one collaborator and
   branch protection/rulesets return HTTP 403 on the current private plan.
   Nothing on GitHub enforces the gate. Needs a separate merge identity
   (bot/GitHub App) plus protection, which requires a plan change or a public
   repository — an owner/CEO decision.
4. **Independent review of this code.** Its author cannot certify it
   (CONST-CAP-001 Art. 3). Until a reviewed revision is listed in the trusted
   policy, every verdict is `provisional`.
5. **Runtime recording (proposal to the runtime team, no code here).** To store
   verdicts in AAO reviews, the auditor needs an individual AUDITOR credential
   and review grant (CEO-only issuance) and a review payload carrying
   `candidate_sha`, `report_sha256` and the signature; the runtime should not
   treat that row as promotion authority.

## Limitations

- Heuristic adversarial rules, not a semantic security review.
- PostgreSQL integration tests do not run inside the auditor sandbox.
- Ledger tail truncation is detectable only through file custody (no external anchor yet).
- `gate --implementer` is trusted input from the merge authority.
- A root/sudo-capable developer on the same host defeats the custody checks; the
  checks make the custody explicit, they do not create it.
