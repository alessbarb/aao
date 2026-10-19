-- Development principal credential registry. Does not enable external execution.
BEGIN;
CREATE TABLE IF NOT EXISTS principal_credentials (
  principal_id text PRIMARY KEY,
  kind text NOT NULL CHECK (kind IN ('AGENT','AUDITOR')),
  token_digest text NOT NULL UNIQUE,
  enabled boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_principal_credentials_enabled ON principal_credentials(kind,enabled);
INSERT INTO schema_migrations(version) VALUES ('005_principal_credentials') ON CONFLICT DO NOTHING;
COMMIT;
