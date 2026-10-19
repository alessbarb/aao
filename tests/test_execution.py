from datetime import UTC, datetime, timedelta

import pytest

from aao.execution import (
    QueueConflict,
    claim,
    complete,
    enqueue,
    initialize,
    quarantine_expired,
    reconcile,
    state,
)


def test_durable_claim_and_completion(tmp_path):
    path = str(tmp_path / "jobs.db")
    initialize(path)
    work_id = "w1"
    eid = enqueue(path, project_id="p1", work_id=work_id, data={"task": "inert"})
    assert enqueue(path, project_id="p1", work_id=work_id, data={}) == eid
    lease = claim(path, worker_id="worker1")
    assert lease.execution_id == eid
    assert claim(path, worker_id="worker2") is None
    complete(path, lease, {"ok": True})
    assert state(path, eid)["status"] == "SUCCEEDED"
    with pytest.raises(QueueConflict):
        complete(path, lease, {"ok": True})


def test_expiration_is_quarantined_not_retried_automatically(tmp_path):
    path = str(tmp_path / "jobs.db")
    initialize(path)
    base = datetime(2026, 10, 18, tzinfo=UTC)
    eid = enqueue(path, project_id="p1", work_id="w2", data={})
    lease = claim(path, worker_id="worker1", ttl_seconds=10, now=base)
    assert quarantine_expired(path, now=base+timedelta(seconds=11)) == 1
    assert state(path, eid)["status"] == "UNCERTAIN"
    assert claim(path, worker_id="worker2") is None
    with pytest.raises(QueueConflict):
        complete(path, lease, {}, now=base+timedelta(seconds=12))
    assert reconcile(path, eid, safe_to_retry=True) == "QUEUED"
    lease2 = claim(path, worker_id="worker2", now=base+timedelta(seconds=13))
    assert lease2.token != lease.token
    complete(path, lease2, {"ok": True}, now=base+timedelta(seconds=14))


def test_unsafe_work_is_not_retried(tmp_path):
    path = str(tmp_path / "jobs.db")
    initialize(path)
    base = datetime(2026, 10, 18, tzinfo=UTC)
    eid = enqueue(path, project_id="p1", work_id="w3", data={})
    claim(path, worker_id="worker1", ttl_seconds=1, now=base)
    quarantine_expired(path, now=base+timedelta(seconds=2))
    assert reconcile(path, eid, safe_to_retry=False) == "FAILED"
    assert claim(path, worker_id="worker2") is None
