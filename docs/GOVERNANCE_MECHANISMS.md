# F3a governance mechanisms (disposable prototype)

This work implements local mechanisms only. It does not activate GOV-REV-002, certify identity, or authorize a merge. GitHub, network, sudo and external publication are out of scope. No claim of independent custody is made.

| Policy requirement | Prototype / evidence | Status |
|---|---|---|
| §6.1–6.2 signed authorization | `integration_authorization.py`; fail-closed snapshot reasons | Prototype; callers must supply authenticated state |
| §6.3 conditional promotion | `integrator.py`; merge-tree, expected two parents, atomic force-with-lease, readback | Local Git only; RA-09 **PENDING**, GitHub server/config untested |
| §7 supervisor / heartbeat | `supervisor.py` signed events and heartbeat | Local history only; operational monitor/clock custody pending |
| §8 ledger | `governance_ledger.py` signed entries and chain checks | File custody independent only by deployment; not established here |
| RA-02 attribution | `identity.py` bare pre-receive uid log | GitHub identity PENDING; uid distinction PENDING (no root / separate uid test) |
| §16.1–16.5 | Tests below cover cryptographic checks and local failure cases | GitHub-only NT-09 cases excluded; do not imply RA-09 PASS |

## Test mapping and limits

The test suite exercises signed canonical data, revocation/recusal, missing required checks, veto/expiry, ledger integrity, replay/expiry, and stale-heartbeat rejection. Local bare Git can exercise compare-and-swap behavior, but does not prove GitHub atomicity. NT-02 cases that require distinct effective uids and all GitHub event/check-run cases are intentionally not claimed as passed. RA-02 and RA-09 remain PENDING for GitHub; real uid isolation also remains PENDING.

Reproduce with the project Python 3.12 environment:

```sh
PYTHONPATH=src /home/alessbarb/workspace/repos/active/aao/.venv/bin/python -m ruff check src tests
PYTHONPATH=src /home/alessbarb/workspace/repos/active/aao/.venv/bin/python -m pytest -q tests/test_governance*.py
```

Merge commits use parents `[base_sha, candidate_sha]`; the `merge-tree --write-tree` tree is used unchanged. Conflicts abort. This prototype is not wired into existing release or audit workflows.
