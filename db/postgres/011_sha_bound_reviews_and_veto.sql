-- Bind new review records to an exact source revision and preserve vetoes.
-- Existing rows remain historical and unattested (candidate_sha IS NULL).
BEGIN;

ALTER TABLE reviews
  ADD COLUMN candidate_sha text,
  ADD CONSTRAINT reviews_candidate_sha_format
    CHECK (candidate_sha IS NULL OR candidate_sha ~ '^[0-9a-f]{40}$');

ALTER TABLE reviews DROP CONSTRAINT reviews_decision_check;
ALTER TABLE reviews ADD CONSTRAINT reviews_decision_check
  CHECK (decision IN ('APPROVE', 'REJECT', 'VETO'));

CREATE INDEX ix_reviews_work_candidate ON reviews(work_id, candidate_sha);

CREATE FUNCTION reject_review_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'review records are append-only';
END;
$$;

CREATE TRIGGER reviews_append_only
BEFORE UPDATE OR DELETE ON reviews
FOR EACH ROW EXECUTE FUNCTION reject_review_mutation();

INSERT INTO schema_migrations(version)
VALUES ('011_sha_bound_reviews_and_veto')
ON CONFLICT DO NOTHING;
COMMIT;
