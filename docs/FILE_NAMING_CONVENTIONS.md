# File naming and responsibility conventions

## Rule

Name files after stable behavior, capability, data contract, or operational
subject. **Do not put milestones, roadmap phases, release numbers, PR numbers,
issue numbers or implementation chronology in file names.** Such identifiers
belong in metadata, issue tracking and evidence records.

- Python: lowercase `snake_case.py`, with descriptive domain responsibility.
- Tests: `test_<behavior_or_component>.py`; divide cross-domain mega-tests.
- Markdown: uppercase `SNAKE_CASE.md` (existing project convention), one
  explicit topic per canonical document.
- SQL migrations: immutable `NNN_<schema_change>.sql` after publication.
  Their prefix is an ordered schema version, **not a project milestone**.
- Configuration: retain ecosystem-standard file names (`pyproject.toml`,
  `.gitignore`, `.env.example`, `README.md`, `conftest.py`, `__init__.py`).
- A storage engine name is justified only to distinguish an adapter or
  implementation, e.g. `postgresql_connection.py`, not as a generic namespace.

## Documentation rename candidates (review contents before moving)

| Current | Candidate responsibility-based path |
| --- | --- |
| M1_NEXT_GATE.md | RUNTIME_READINESS_CRITERIA.md |
| M1_SCOPE.md | WORK_MANAGEMENT_SCOPE.md |
| M2_EXECUTION_BOUNDARY.md | EXECUTION_SECURITY_BOUNDARIES.md |
| M2_INERT_WORKER.md | INERT_WORKER_BEHAVIOR.md |
| M2_PRINCIPAL_IDENTITIES.md | PRINCIPAL_IDENTITY_AND_CREDENTIAL_MANAGEMENT.md |
| M2_RECONCILIATION.md | EXECUTION_RECOVERY_AND_RECONCILIATION.md |
| M2_WORKER_EFFECTS.md | WORKER_EXECUTION_AND_EXTERNAL_EFFECT_CONTROLS.md |
| POSTGRES_AUTH_MIGRATION.md | DATABASE_AUTHENTICATION_TRANSITION.md |
| POSTGRES_EXECUTION.md | PERSISTENT_EXECUTION_QUEUE.md |
| POSTGRES_RUNTIME.md | POSTGRESQL_RUNTIME_OPERATIONS.md |
| IMPLEMENTATION_BACKLOG.md | ENGINEERING_BACKLOG.md |
| VALIDATION_STATUS.md | VERIFICATION_EVIDENCE_REGISTER.md |
| CONFIGURATION.md | ENVIRONMENT_CONFIGURATION.md |

Keep `CONSTITUTION.md` and `README.md`. A purely historical milestone
record should be labeled historical **inside** the document and separated
from normative, continuously updated reference material.

## Python rename candidates (require dependency-aware refactoring)

| Current module in src/aao | Candidate |
| --- | --- |
| main.py | sqlite_api.py |
| pg_work.py | work_management_api.py |
| pg_principals.py | principal_credentials.py |
| pg_execution.py | execution_queue.py |
| pg_effects.py | external_effect_registry.py |
| pg_effect_reconciliation.py | external_effect_reconciliation.py |
| pg_reconciliation.py | execution_reconciliation.py |
| postgres.py | postgresql_connection.py |
| worker_auth.py | legacy_worker_authentication.py |
| storage.py | sqlite_storage.py |
| settings.py | environment_settings.py |
| inert_worker.py | inert_execution_worker.py |

Review `identity.py`, `authorization.py`, `execution.py`, `planner.py`,
`policy.py` and `review.py` for actual cohesion before selecting a name.
Keep `__init__.py` unchanged.

## Test strategy

Rename `test_pg_principals.py` to `test_principal_credentials.py` when
its imports are refactored. Split `test_postgres_integration.py` by
responsibility, for example:
`test_project_workflow_integration.py`,
`test_credential_lifecycle_integration.py`,
`test_execution_leases_integration.py` and
`test_review_authorization_integration.py`.
Each must preserve the disposable database gate and project isolation.

## Immutable migrations

Do not rename applied versions 001–005, even if their original names are
generic. They are historical applied artifacts and their filenames may be
embedded in operator instructions. From 006 onward, use descriptive
schema changes, e.g. `006_add_principal_credential_expiration.sql` only
**if that change is actually implemented**.

## Migration and verification checklist

1. Check contents and distinguish historical evidence from canonical spec.
2. Inventory Python imports, CLI entry points, Uvicorn commands, tests,
   workflows, Docker files and internal Markdown links.
3. Move files and change all references in one controlled change set;
   do not add compatibility aliases just to preserve historical names.
4. Run formatting/static checks, all unit and disposable PostgreSQL tests.
5. Inspect diff for stale references and validate hyperlinks.
6. Obtain review of behavior-preserving refactor separately from functional
   security changes. Do not declare the rename complete without evidence.

This document defines the naming policy and **candidate mappings**; it does
not claim that any existing files have already been moved.
