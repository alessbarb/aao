-- Project-local, versioned capability metadata. Registration never authorizes execution.
BEGIN;

CREATE TABLE capability_versions (
  project_id uuid NOT NULL REFERENCES projects(id),
  capability_id text NOT NULL CHECK (length(capability_id) BETWEEN 1 AND 128),
  version text NOT NULL CHECK (length(version) BETWEEN 1 AND 64),
  capability_type text NOT NULL CHECK (capability_type IN (
    'cli_script', 'library', 'application_service', 'agent', 'agent_skill',
    'knowledge_procedure', 'workflow'
  )),
  status text NOT NULL CHECK (status IN (
    'discovered', 'evaluated', 'registered_local', 'candidate_for_promotion',
    'suspended', 'obsolete', 'retired'
  )),
  provenance jsonb NOT NULL,
  contract jsonb NOT NULL,
  required_permissions jsonb NOT NULL DEFAULT '[]'::jsonb,
  risks jsonb NOT NULL DEFAULT '[]'::jsonb,
  dependencies jsonb NOT NULL DEFAULT '[]'::jsonb,
  tests jsonb NOT NULL DEFAULT '[]'::jsonb,
  compatibility jsonb NOT NULL DEFAULT '{}'::jsonb,
  evidence jsonb NOT NULL DEFAULT '[]'::jsonb,
  created_by text NOT NULL REFERENCES principal_credentials(principal_id),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (project_id, capability_id, version),
  CHECK (jsonb_typeof(required_permissions) = 'array'),
  CHECK (jsonb_typeof(risks) = 'array'),
  CHECK (jsonb_typeof(dependencies) = 'array'),
  CHECK (jsonb_typeof(tests) = 'array'),
  CHECK (jsonb_typeof(evidence) = 'array')
);

CREATE INDEX ix_capability_versions_project_status
  ON capability_versions(project_id, status, capability_type, capability_id);

INSERT INTO schema_migrations(version)
VALUES ('010_capability_registry')
ON CONFLICT DO NOTHING;
COMMIT;
