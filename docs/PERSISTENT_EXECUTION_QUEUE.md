# M2: PostgreSQL inert execution integration

Apply migration 003 after the first two migrations to a disposable PostgreSQL database.

This increment uses PostgreSQL transactions, an execution journal and atomic
`FOR UPDATE SKIP LOCKED` claims. Expired leases are quarantined, not
automatically retried. Lease token and worker identity are required to record
completion. The queue can only contain a fixed **inert** payload from the
admission endpoint; it cannot invoke tools or models.

An HTTP admission endpoint stages a READY task into the queue in the **same
transaction** as the audit event. A repeated admission returns the existing
execution instead of adding another one. The queue has no public worker API.
No real model/agent executor is enabled.

Still required: validated authenticated workers, operation effects ledger,
independent reconcilers, project-suspension handling during claim, role-specific
database permissions, and longitudinal recovery tests. This is a development
candidate, not a production durable workflow engine.
