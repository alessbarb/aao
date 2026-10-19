-- Fence execution claims across pause/cancel/resume transitions. Existing
-- in-flight claims receive NULL and fail closed at completion/proposal checks.
BEGIN;

ALTER TABLE projects
  ADD COLUMN state_generation bigint NOT NULL DEFAULT 0
  CHECK (state_generation >= 0);

ALTER TABLE execution_queue
  ADD COLUMN project_state_generation bigint;

CREATE FUNCTION advance_project_state_generation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.state IS DISTINCT FROM OLD.state THEN
    NEW.state_generation := OLD.state_generation + 1;
  ELSE
    -- State generation is database-owned even if a caller updates this column.
    NEW.state_generation := OLD.state_generation;
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER projects_advance_state_generation
BEFORE UPDATE OF state,state_generation ON projects
FOR EACH ROW EXECUTE FUNCTION advance_project_state_generation();

INSERT INTO schema_migrations(version)
VALUES ('007_fence_leases_across_project_state_changes')
ON CONFLICT DO NOTHING;
COMMIT;
