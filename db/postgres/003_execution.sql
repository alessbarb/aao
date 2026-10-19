-- Durable inert execution queue; apply after 001 and 002 in an isolated DB.
BEGIN;
CREATE TABLE IF NOT EXISTS execution_queue (
  id uuid PRIMARY KEY,
  work_id uuid NOT NULL UNIQUE REFERENCES work_items(id),
  project_id uuid NOT NULL REFERENCES projects(id),
  status text NOT NULL CHECK(status IN ('QUEUED','RUNNING','UNCERTAIN','SUCCEEDED','FAILED')),
  input_json jsonb NOT NULL,
  lease_token uuid,
  worker_id text,
  lease_expires_at timestamptz,
  attempts integer NOT NULL DEFAULT 0,
  result_json jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_execution_claim ON execution_queue(status,created_at);
CREATE TABLE IF NOT EXISTS execution_journal (
  id uuid PRIMARY KEY,
  execution_id uuid NOT NULL REFERENCES execution_queue(id),
  kind text NOT NULL,
  details jsonb NOT NULL,
  occurred_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO schema_migrations(version) VALUES ('003_execution') ON CONFLICT DO NOTHING;
COMMIT;
