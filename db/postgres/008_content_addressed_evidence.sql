-- Store immutable, project-scoped evidence bytes for reconciliation decisions.
BEGIN;

CREATE TABLE evidence_artifacts (
  project_id uuid NOT NULL REFERENCES projects(id),
  digest text NOT NULL CHECK (digest ~ '^[0-9a-f]{64}$'),
  submitted_by text NOT NULL REFERENCES principal_credentials(principal_id),
  media_type text NOT NULL CHECK (length(media_type) BETWEEN 1 AND 127),
  content bytea NOT NULL CHECK (octet_length(content) BETWEEN 1 AND 1048576),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (project_id, digest)
);

CREATE FUNCTION reject_evidence_artifact_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'evidence artifacts are append-only';
END;
$$;

CREATE TRIGGER evidence_artifacts_append_only
BEFORE UPDATE OR DELETE ON evidence_artifacts
FOR EACH ROW EXECUTE FUNCTION reject_evidence_artifact_mutation();

CREATE INDEX ix_evidence_artifacts_project_created
  ON evidence_artifacts(project_id, created_at);

INSERT INTO schema_migrations(version)
VALUES ('008_content_addressed_evidence')
ON CONFLICT DO NOTHING;
COMMIT;
