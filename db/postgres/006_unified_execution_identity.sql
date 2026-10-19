-- Move legacy development worker identities into the principal registry.
-- Abort on ambiguous identity/digest collisions; never silently rebind a token.
BEGIN;
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM worker_registrations w
    JOIN principal_credentials p ON p.principal_id = w.worker_id
    WHERE p.kind <> 'AGENT' OR p.token_digest <> w.token_digest
  ) OR EXISTS (
    SELECT 1 FROM worker_registrations w
    JOIN principal_credentials p ON p.token_digest = w.token_digest
    WHERE p.principal_id <> w.worker_id
  ) THEN
    RAISE EXCEPTION 'legacy worker identity conflicts with principal credential registry';
  END IF;
END $$;
INSERT INTO principal_credentials(principal_id,kind,token_digest,enabled,created_at)
SELECT worker_id,'AGENT',token_digest,enabled,created_at FROM worker_registrations
ON CONFLICT (principal_id) DO UPDATE SET enabled = principal_credentials.enabled AND EXCLUDED.enabled;
DROP TABLE worker_registrations;
INSERT INTO schema_migrations(version) VALUES ('006_unified_execution_identity') ON CONFLICT DO NOTHING;
COMMIT;
