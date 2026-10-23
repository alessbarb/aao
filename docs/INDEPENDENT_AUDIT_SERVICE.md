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

The emitter refuses to run if the key, policy, output or ledger is under a
path the sandbox mounts (`/usr`, `/bin`, `/lib`, `/lib64`, `/etc`, the Python
runtime), so candidate code cannot read auditor secrets. Protected paths should
include test/lint configuration (`pyproject.toml`, `conftest.py`, `pytest.ini`,
`setup.cfg`, `tox.ini`, `ruff.toml`), because the candidate's own configuration
governs how its checks run.

Every finding blocks unless the trusted policy holds a disposition keyed by
`"<candidate_sha>:<finding_id>"`, so a disposition never carries over to a new
revision.

## Usage

```bash
# Audit (read-only against GitHub); run as the auditor account.
python -m aao.independent_audit audit --github-pr autoaiorg/aao 10 \
  --policy /var/lib/aao-auditor/policy.json --key /var/lib/aao-auditor/keys/auditor-ed25519.pem \
  --output /var/lib/aao-auditor/runs/pr10-<sha> --ledger /var/lib/aao-auditor/ledger.jsonl \
  [--source <local mirror>] [--veto "<reason>"]

# Promotion decision, run by the merge authority on a clean checkout at the SHA.
python -m aao.independent_audit gate --repository <checkout> --policy ... \
  --report <run>/report.json --signature <run>/report.sig --ledger ... \
  --github-pr autoaiorg/aao 10 --implementer <PR author from the merge authority>
```

Policy fields: `version`, `auditor_id`, `auditor_os_user`, `developer_os_users`,
`auditors` (id → public key path), `required_checks` (GitHub check names),
`audit_checks` (name → Python argv), `protected_paths`, `dispositions`,
`trusted_auditor_revisions`.

## First run against PR #10 and PR #11 (provisional)

Run on 2026-10-19 as OS user `alessbarb` with a policy that designates
`aao-auditor` as auditor and `alessbarb` as developer, and lists no reviewed
auditor revision, so the emitter refused to sign. These are adversarial
evidence inputs, **not** audit verdicts.

- Auditor code revision: `18f1d6b1d4313b3a9b331f24514ccceb46d25b55` (not independently reviewed).
- Canonical policy digest (`policy_sha256`): `64d3f18a61efa6a639b084a775dc2ab39b3c7bb586fffd45107719b846241c6b`.
- Copies of policy, reports, evidence and ledger: `docs/audit-runs/20261019-provisional/`.
  The absolute paths inside `evidence_files` point to the original session
  scratch directory and are stale; verify each copy by its digest key.
  Report file SHA-256: PR #10 `f2115419fa246fbfd2926dcd87d117f90584d77b4a9e3cb9dc8b31af239c4d82`,
  PR #11 `9665bdd7258ddb9aa4c5094b265094eb6b61c06e0d3072fa43de6de047e4f5a1`.
  Ledger entries 0–5 are earlier provisional runs made while the auditor was
  being developed; entries 6–7 are the runs above.

| PR | Candidate SHA | Base SHA | Sandbox ruff / pytest | Blocking findings | Verdict |
| --- | --- | --- | --- | --- | --- |
| #10 | `523a5986d4ae22b466aaabe59821dc7acecfaef5` | `b1ce576` (main) | pass / 76 passed, 34 skipped | `.github/workflows/ci.yml` changed; new PostgreSQL `skipif` at `tests/test_project_workflow_integration.py:76` | provisional |
| #11 | `677f83d2a96e976d9665abdd49f9ec8d6b327bf0` | `523a5986` (PR #10) | pass / 114 passed, 39 skipped | changes to `ci.yml`, `pr_conformity.py`, `review.py`, migration 011 and `docs/CEO_MANDATE_…`; five new PostgreSQL `skipif` gates; CI `test` not yet successful at audit time | provisional |

PR #11's head moved twice during the session (`f929827` → `c3d1df9` →
`677f83d`); every report binds the head read at audit time, and any later push
needs a new audit. A gate run on PR #10 returned `conformant: false`
(`signed audit report is absent`). Neither PR changes `pyproject.toml` or
`conftest.py`.

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
- The ledger hash chain is unkeyed: it detects corruption, not a writer who recomputes it; protection against dropping a veto comes only from file custody.
- `gate --implementer` is trusted input from the merge authority.
- A root/sudo-capable developer on the same host defeats the custody checks; the
  checks make the custody explicit, they do not create it.

## Activation runbook (for the infrastructure owner, not the developer)

Run by an operator who is not the implementer. No implementer account may have
`sudo`, `docker` group membership or any other root-equivalent access on the
auditor host (or use a separate host/VM). Correction (2026-10-20): the earlier
"no sudo" wording was insufficient, because the `docker` group is root-equivalent.
Manifest-based audits additionally need the root-owned trust anchor described in
`docs/AUDIT_MANIFEST_CONTRACT.md`.

```bash
# 1. Dedicated account and private state outside every checkout and sandbox mount.
sudo useradd --system --create-home --home-dir /var/lib/aao-auditor --shell /usr/sbin/nologin aao-auditor
sudo install -d -o aao-auditor -g aao-auditor -m 0700 /var/lib/aao-auditor/{keys,runs,src}
# 2. Key generated by the auditor account itself; publish only the public key.
sudo -u aao-auditor openssl genpkey -algorithm ED25519 -out /var/lib/aao-auditor/keys/auditor-ed25519.pem
sudo -u aao-auditor chmod 0400 /var/lib/aao-auditor/keys/auditor-ed25519.pem
sudo -u aao-auditor openssl pkey -in /var/lib/aao-auditor/keys/auditor-ed25519.pem -pubout \
  -out /var/lib/aao-auditor/keys/auditor-ed25519.pub
# 3. Auditor code: clone at the independently reviewed revision only.
sudo -u aao-auditor git clone https://github.com/autoaiorg/aao /var/lib/aao-auditor/src/aao
sudo -u aao-auditor git -C /var/lib/aao-auditor/src/aao checkout --detach <REVIEWED_SHA>
# 4. Policy: copy docs/audit-runs/20261019-provisional/policy.json, then set
#    trusted_auditor_revisions=[<REVIEWED_SHA>] and keep developer_os_users=["alessbarb"].
sudo -u aao-auditor install -m 0600 policy.json /var/lib/aao-auditor/policy.json
# 5. Read-only GitHub credential owned by the auditor (fine-grained token:
#    contents:read, pull_requests:read, checks:read), stored only in the auditor's gh config.
sudo -u aao-auditor gh auth login --with-token < auditor-readonly-token.txt
```

The merge authority then runs `gate` with its own identity; GitHub enforcement
additionally requires branch protection with the merge identity as the only
writer to `main`.
