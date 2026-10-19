-- Store agent-proposed source diffs as immutable review artifacts; proposals
-- never modify the canonical repository or authorize application.
BEGIN;

CREATE TABLE patch_proposals (
  id uuid PRIMARY KEY,
  work_id uuid NOT NULL REFERENCES work_items(id),
  project_id uuid NOT NULL REFERENCES projects(id),
  proposer_id text NOT NULL REFERENCES principal_credentials(principal_id),
  base_sha text NOT NULL CHECK (base_sha ~ '^[0-9a-f]{40}$'),
  patch_sha256 text NOT NULL CHECK (patch_sha256 ~ '^[0-9a-f]{64}$'),
  patch_bytes bytea NOT NULL CHECK (octet_length(patch_bytes) BETWEEN 1 AND 65536),
  changed_paths jsonb NOT NULL CHECK (jsonb_typeof(changed_paths)='array'),
  status text NOT NULL DEFAULT 'PROPOSED' CHECK (status='PROPOSED'),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  UNIQUE (work_id, base_sha, patch_sha256)
);

CREATE FUNCTION reject_patch_proposal_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'patch proposals are append-only';
END;
$$;

CREATE TRIGGER patch_proposals_append_only
BEFORE UPDATE OR DELETE ON patch_proposals
FOR EACH ROW EXECUTE FUNCTION reject_patch_proposal_mutation();

CREATE TABLE patch_proposal_validations (
  id uuid PRIMARY KEY,
  proposal_id uuid NOT NULL REFERENCES patch_proposals(id),
  validator_id text NOT NULL REFERENCES principal_credentials(principal_id),
  base_sha text NOT NULL CHECK (base_sha ~ '^[0-9a-f]{40}$'),
  patch_sha256 text NOT NULL CHECK (patch_sha256 ~ '^[0-9a-f]{64}$'),
  candidate_tree text NOT NULL CHECK (candidate_tree ~ '^[0-9a-f]{40,64}$'),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  UNIQUE (proposal_id, candidate_tree)
);

CREATE TRIGGER patch_proposal_validations_append_only
BEFORE UPDATE OR DELETE ON patch_proposal_validations
FOR EACH ROW EXECUTE FUNCTION reject_patch_proposal_mutation();

CREATE INDEX ix_patch_proposals_work_created
  ON patch_proposals(work_id, created_at);
CREATE INDEX ix_patch_proposal_validations_proposal
  ON patch_proposal_validations(proposal_id, created_at);

INSERT INTO schema_migrations(version)
VALUES ('012_patch_proposals')
ON CONFLICT DO NOTHING;
COMMIT;
