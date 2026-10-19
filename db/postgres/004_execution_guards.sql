-- M2 guarded workers and effects. Development schema, apply after 003.
BEGIN;
CREATE TABLE IF NOT EXISTS worker_registrations (
  worker_id text PRIMARY KEY,
  token_digest text NOT NULL,
  enabled boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS external_effects (
  id uuid PRIMARY KEY,
  execution_id uuid NOT NULL REFERENCES execution_queue(id),
  idempotency_key text NOT NULL UNIQUE,
  capability text NOT NULL,
  status text NOT NULL CHECK(status IN ('PROPOSED','AUTHORIZED','IN_FLIGHT','CONFIRMED','UNCERTAIN','REJECTED')),
  request_digest text NOT NULL,
  response_digest text,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_effect_execution ON external_effects(execution_id,status);
INSERT INTO schema_migrations(version) VALUES ('004_execution_guards') ON CONFLICT DO NOTHING;
COMMIT;
