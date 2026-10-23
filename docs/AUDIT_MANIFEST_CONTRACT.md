# Audit contract for local Git candidate manifests

**Owner:** audit domain (Claude). **Status:** implemented candidate, untrusted
until independently reviewed. It does not authorize merges, grant permissions,
or modify the runtime or frontend.

Code: `src/aao/manifest_audit.py`. Tests: `tests/test_manifest_audit.py`.

## 1. Manifest (input, produced by the integration controller)

`aao.candidate-manifest.v1`, JSON object with **exactly** these fields:

| Field | Meaning | Auditor check |
| --- | --- | --- |
| `schema` | `"aao.candidate-manifest.v1"` | exact |
| `repository` | absolute local path of the controller's repository | cloned with `--no-hardlinks`; the auditor never writes to it |
| `target_ref` | full ref, `refs/heads/…` | must currently resolve to `target_sha`, at audit time, just before the verdict, and at gate time |
| `target_sha` | full 40-hex target commit | must be a commit |
| `candidate_sha` | full 40-hex candidate commit | must be a commit |
| `candidate_tree` | `git rev-parse <candidate_sha>^{tree}` | recomputed; must match |
| `result_tree` | `git merge-tree --write-tree <target_sha> <candidate_sha>` | recomputed in the auditor's clone; a conflict or mismatch is refused |
| `producer` | controller identity string | recorded as a **declared** identity only (`declared_implementers`); it can only make the decision stricter (if it equals the auditor the candidate is blocked). Recusal uses the anchored attribution (SL-02) |

Unknown fields, abbreviated SHAs, short refs, relative paths, or embedded
policy, key or ledger paths are refused. The manifest is a **selector, not
evidence**: every claim is re-derived.

**Meaning of "resulting tree".** No existing controller defined it, so the
contract binds both readings: `candidate_tree` is the candidate as authored,
and `result_tree` is what would land on `target_ref`. Checks and adversarial
rules run on `result_tree`; the diff for rules is `target_sha → result_tree`.
The report records `git --version`, because merge-tree output can vary between
Git versions.

## 2. Trust anchor (not supplied by any caller)

Fixed path `/etc/aao-audit/trust-anchor.json`, `aao.audit-trust-anchor.v1`:
`policy_path`, `policy_sha256` (canonical JSON digest), `auditor_uid`,
`auditor_public_key` (PEM), `ledger_path`, `ledger_anchor_path`,
`attribution_path`. There is no CLI option or environment variable that
overrides it.

| Object | Required custody (checked with `O_NOFOLLOW` + `fstat`) |
| --- | --- |
| Anchor | regular file, owner uid 0, no group/other write; every parent directory is non-symlink, owned by root or the auditor, and not group/other writable (root-owned sticky directories allowed) |
| Policy | owned by `auditor_uid`, same rules; digest must equal the anchor pin |
| Ledger and its directory | owned by `auditor_uid`, no group/other write; created `0600`. Format: F3a `governance_ledger`, every entry signed by the anchored auditor key (`audit-verdict` / `veto`) |
| Ledger anchor (`ledger_anchor_path`) | owned like the trust anchor; holds a terminal hash that must still be part of the verified chain (`0`×64 = genesis) |
| Attribution (`attribution_path`) | owned like the trust anchor; `aao.implementer-attribution.v1`, `candidates: {sha: [identity…]}` written by the merge authority from authenticated push events (RA-02). Absent, unknown or empty → `provisional` |
| Evidence | owned by `auditor_uid`, `0444`, re-hashed at gate time |
| Signing key | owned by `auditor_uid`, no group/other bits, public key equal to the anchor's |

No anchor means no decision: `verify_promotion` returns not conformant.

## 3. Audit (`python -m aao.manifest_audit audit --manifest M --output O --key K [--veto R]`)

The run is signed only when all of these hold: it runs as `auditor_uid`, the
account is not in `developer_os_users`, the auditor code is a clean revision
listed in `trusted_auditor_revisions`, and the key matches the anchor.
Attribution of the implementers must also be resolved (section 2). Otherwise
the run has custody problems: without `--veto` the verdict is `provisional`;
with `--veto` the report keeps `verdict: "veto"` (a veto always takes
precedence). In both cases the report is unsigned and nothing is recorded.

**Report emitted vs. decision recorded.** A report (`report.json`) is always
written to the output directory. Only a custody-valid run signs the report
and appends a signed ledger entry (`audit-verdict` for `approve`/`reject`,
`veto` for a veto). A `provisional` run, and a `--veto` run without valid
custody, write an unsigned report but **append nothing to the ledger**. They are
not ledger decisions, and the gate never treats their report as an approval.
A veto without custody **does** block, through its pending-veto marker (below).

**Migration note.** Every ledger row containing `resolves_pending` requires
`can_resolve_pending` on its signing key, including rows where the value is an
empty list (`[]`). Before sharing a ledger containing such rows, update the
trust registry to grant that capability to the anchored auditor key; otherwise
ledger verification fails closed.

**Pending vetoes (F4-02).** Every `--veto` run, with or without custody, first
writes a pending-veto marker to `<ledger_path>.pending-vetoes/`, **before any
analysis**, so the analysis window is covered. There is no mutual exclusion
between the gate and the start of an audit run. The directory
has the same custody as the ledger: auditor uid, `0700`, markers `0600`, file
name bound to the marker digest. If the marker cannot be written, the run fails.
The gate denies any candidate with a marker that no verified ledger entry
lists in `resolves_pending`. It also denies when the markers cannot be
verified: tampering, unsafe permissions or an inconsistent name. Only a
custody-valid run resolves markers: a recorded veto (which still blocks), or
an explicit `--resolve-pending-vetoes` run. An ordinary later approval does
not lift a pending veto. Fake markers can only cause a denial of service,
which is the safe direction.
**Open finding A-2 (Codex review of #30, held as class A):** any process
running as the auditor uid, or root, can delete markers. If that uid is shared
by more than one actor, a party other than the vetoing one can remove a veto,
and the gate reads a missing marker as no veto. File permissions alone cannot
close this. F4-01a only narrows A-2 to pending markers observed by the
supervisor and a verified ledger head captured in its signed heartbeat. Before
signing a later heartbeat, the supervisor requires its previous non-genesis
head to remain in the current verified chain; otherwise it records a
continuity incident and refuses to sign. Resolution rows are accepted only
from verified `can_resolve_pending` keys, excluding the integrator key. A
marker removed before the next heartbeat is outside that snapshot; the
exposure window is bounded by the heartbeat validity period. This depends on
exclusive custody of the supervisor uid. P1's
execution does not by itself close the logic gap. The integrator path uses this
signed snapshot; the manifest gate still uses the older external anchor.
F4-01b, independently advancing the gate's anchor, remains pending. This
revision is **not** a candidate for `trusted_auditor_revisions`.

**Supervisor-state migration:** legacy `state.json` files without a valid
signature fail closed. They are not automatically imported, repaired, or
deleted; preserve them for investigation and use an authorized migration
procedure before initializing replacement signed state.

## 4. Gate (`python -m aao.manifest_audit gate --manifest M --report R --signature S [--promoted-sha P]`)

Exit 0 / `{"conformant": true}` only if all of these hold:
- the anchor and policy custody is valid;
- the report is canonical and signed by the anchored key;
- it is bound to this manifest digest and to `target_sha`, `candidate_sha`,
  `result_tree`, `policy_sha256`, `anchor_sha256` and `auditor_uid`;
- the verdict is `approve` with no veto and no blocking findings;
- every evidence file is auditor-owned and matches its digest;
- the ledger is trusted, holds no veto for the candidate, and this report is
  the latest decision for it;
- `target_ref` still equals `target_sha`;
- both trees re-derive identically;
- if `--promoted-sha` is given, the commit's tree is `result_tree` and either
  it is a fast-forward to `candidate_sha` or its parents are exactly
  `[target_sha, candidate_sha]`.

## 5. Integration controller obligations

1. Never pass policy, key, anchor or ledger paths; never run as the implementer identity.
2. Compute the manifest itself from its own repository, not from implementer claims.
3. Build the promotion commit with tree `result_tree`: fast-forward to `candidate_sha`, or `git commit-tree <result_tree> -p <target_sha> -p <candidate_sha>`.
4. Run `gate --promoted-sha <new>` immediately before promotion.
5. Promote only with compare-and-swap: `git update-ref refs/heads/<target> <new> <target_sha>`. If the ref moved, discard and re-audit.
6. Treat any non-zero exit, unparsable output or missing anchor as **not authorized**.
7. The gate decides conformity only; the authority to perform the merge is separate and is not granted here.

## 6. Separation demonstrable on the current local infrastructure

Host facts (read-only checks, 2026-10-20):
- There is one human account, `alessbarb` (uid 1000), and Codex, Claude and
  Antigravity all run under it.
- That account is in `sudo` (password required) and in `docker` (no password).
  `/var/run/docker.sock` is `root:docker 0660`. Docker documents that "the
  `docker` group grants root-level privileges to the user"
  (docs.docker.com/engine/install/linux-postinstall). The escalation was not
  exercised.
- `/etc/aao-audit` and `/var/lib/aao-auditor` do not exist.

| Property | Demonstrable now? | Why |
| --- | --- | --- |
| Candidate code cannot read auditor files or use the network during checks | **Yes, locally** (bwrap probe test passes locally; skipped in CI, which does not install bubblewrap) | `--unshare-all`, read-only tree, secrets refused if under a sandbox mount |
| Exact SHA and result-tree binding; tamper detection of report and evidence | **Yes** | Recomputed trees, canonical signed report, re-hashed evidence (tests) |
| Fail-closed on missing anchor, provisional, veto, moved target, wrong promoted tree | **Yes** | Tests; mutation check showed each disabled control is caught |
| Distinct auditor identity / key custody | **No** | Every agent shares uid 1000, and uid 1000 can become root through `docker` without a password; a separate `aao-auditor` account on this host would not be protected from the agents |
| Ledger veto resistance | **Partial** | Signed entries and an external anchor reject rewrites, forged entries and truncation below the anchor. Entries after the last anchor can still be truncated by the ledger owner or root (custody); root is reachable today |
| Anchor integrity (root-owned) | **No** | Root is reachable by the same agents |
| Application-level AUDITOR principal separation | **No** | Its credentials are readable by the same uid |
| Independent merge authority | **No** | Agents use the owner's admin token; no branch protection on the private Free plan |

Two agents under the same privileged account are **not** an independent
audit, and nothing in this code claims they are.

**Correction to PR #14 comment 6278647774 §2/§3 and to the activation runbook:**
"no sudo" is insufficient. The auditor host must also deny `docker` group (or any
root-equivalent) membership to every implementer account, or run on a separate
host/VM.

## 7. Disposition of the Codex review of PR #14 (comment 6278741396)

- **H-01 (no controller trust anchor):** addressed for the manifest path. The
  policy, key, uid and ledger come from a fixed root-owned anchor, with custody
  verified by the gate. Effective only on a host where implementers cannot
  become root.
- **H-02 (check runs not authenticated by emitter):** not applicable to the
  manifest path, which consumes no GitHub check runs. Still open for the
  GitHub-PR path in `pr_conformity.py`; not changed here because PR #11 also
  modifies that file.
- **H-03 (ledger depends on ACLs; superseded by SL-03 below):** the gate now verifies ledger ownership and
  mode. The hash chain stays unkeyed; resistance to a root or owner writer is
  not claimed.

## 8. Disposition of the Codex second-line review of the auditor (SL-01..SL-06, 2026-10-21)

- **SL-01 (caller-controlled trust in the legacy path):** the legacy
  `independent_audit.audit_candidate` can no longer approve or sign, and
  `promotion_decision` always denies (`LEGACY_RETIRED`). Promotion goes only
  through this manifest path and the F3a integrator.
- **SL-02 (implementer identity not authenticated):** recusal uses only the
  anchored attribution file. `producer` and Git author e-mails are recorded as
  `declared_implementers` and can only make the decision stricter. Without
  resolved attribution the verdict is `provisional`. In the real environment
  this stays provisional until RA-02 (GitHub attribution) closes.
- **SL-03 (unkeyed ledger):** the ledger is now an F3a `governance_ledger`
  with a signature on every entry; the gate verifies all signatures and that
  the external anchor hash is still in the chain. Rewriting or reordering
  entries, forging entries or truncating below the anchor is rejected.
  **Limitation (custody, B):** an account that can write the ledger file (the
  auditor uid or root) can still truncate entries appended after the last
  external anchor. Closing it needs the anchor to be advanced by a different
  role (supervisor/custodian) after each entry.
- **SL-04, SL-05 (sandbox and custody evidence):** limitations; the host
  evidence comes from P1 and the F2 verifier.
- **SL-06 (tamper tests):** added rewrite-with-recomputed-chain, forged-key and
  truncation-below-anchor tests; each validated by mutation.
