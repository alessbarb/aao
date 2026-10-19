-- Protect evidence artifact rows from TRUNCATE as well as UPDATE/DELETE.
BEGIN;

CREATE TRIGGER evidence_artifacts_reject_truncate
BEFORE TRUNCATE ON evidence_artifacts
FOR EACH STATEMENT EXECUTE FUNCTION reject_evidence_artifact_mutation();

INSERT INTO schema_migrations(version)
VALUES ('009_prevent_evidence_truncation')
ON CONFLICT DO NOTHING;
COMMIT;
