-- Development transition schema. Text identifiers enable the existing dev token
-- mapped principals while production authentication is being implemented.
BEGIN;
ALTER TABLE project_grants DROP CONSTRAINT IF EXISTS project_grants_principal_id_fkey;
ALTER TABLE work_items DROP CONSTRAINT IF EXISTS work_items_author_id_fkey;
ALTER TABLE reviews DROP CONSTRAINT IF EXISTS reviews_reviewer_id_fkey;
ALTER TABLE project_grants ALTER COLUMN principal_id TYPE text USING principal_id::text;
ALTER TABLE work_items ALTER COLUMN author_id TYPE text USING author_id::text;
ALTER TABLE reviews ALTER COLUMN reviewer_id TYPE text USING reviewer_id::text;
INSERT INTO schema_migrations(version) VALUES ('002_dev_identity')
ON CONFLICT DO NOTHING;
COMMIT;
