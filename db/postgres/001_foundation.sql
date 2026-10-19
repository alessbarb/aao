-- AAO PostgreSQL baseline. Apply only to a fresh isolated development database.
BEGIN;
CREATE TABLE IF NOT EXISTS schema_migrations (
    version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS mandates (
    id uuid PRIMARY KEY,
    title text NOT NULL CHECK(length(title)>0),
    objective text NOT NULL CHECK(length(objective)>0),
    status text NOT NULL CHECK(status IN ('DRAFT','CONFIRMED')),
    confirmed_by text,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS projects (
    id uuid PRIMARY KEY,
    name text NOT NULL,
    mandate_id uuid NOT NULL UNIQUE REFERENCES mandates(id),
    state text NOT NULL CHECK(state IN ('ACTIVE','PAUSED','CANCELLED'))
);
CREATE TABLE IF NOT EXISTS principals (
    id uuid PRIMARY KEY,
    name text NOT NULL,
    kind text NOT NULL CHECK(kind IN ('CEO','AGENT','AUDITOR','SERVICE')),
    active boolean NOT NULL DEFAULT true
);
CREATE TABLE IF NOT EXISTS project_grants (
    principal_id uuid NOT NULL REFERENCES principals(id),
    project_id uuid NOT NULL REFERENCES projects(id),
    capability text NOT NULL,
    expires_at timestamptz,
    PRIMARY KEY(principal_id, project_id, capability)
);
CREATE TABLE IF NOT EXISTS work_items (
    id uuid PRIMARY KEY,
    project_id uuid NOT NULL REFERENCES projects(id),
    title text NOT NULL,
    status text NOT NULL CHECK(status IN
        ('INBOX','READY','IN_PROGRESS','IN_REVIEW','VERIFIED','DONE')),
    author_id uuid NOT NULL REFERENCES principals(id),
    acceptance_criteria jsonb NOT NULL CHECK(jsonb_typeof(acceptance_criteria)='array'),
    evidence jsonb NOT NULL DEFAULT '[]'::jsonb CHECK(jsonb_typeof(evidence)='array')
);
CREATE TABLE IF NOT EXISTS reviews (
    id uuid PRIMARY KEY,
    work_id uuid NOT NULL REFERENCES work_items(id),
    reviewer_id uuid NOT NULL REFERENCES principals(id),
    decision text NOT NULL CHECK(decision IN ('APPROVE','REJECT')),
    evidence jsonb NOT NULL CHECK(jsonb_typeof(evidence)='array'),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS events (
    id uuid PRIMARY KEY,
    subject_id uuid NOT NULL,
    kind text NOT NULL,
    details jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_work_project_status ON work_items(project_id,status);
CREATE INDEX IF NOT EXISTS ix_events_subject ON events(subject_id,created_at);
INSERT INTO schema_migrations(version) VALUES ('001_foundation')
ON CONFLICT DO NOTHING;
COMMIT;
