# AAO configuration (development and test)

`settings.py` loads a local dotenv file before application configuration is
evaluated. By default it selects `.env.local`; `AAO_ENV_FILE=.env.test` selects
the test file. The environment wins over dotenv values. The selected path must
be one of these two filenames in the repository root. In production dotenv
files are never loaded.

These are transitional development settings, **not a secret vault**.
The CEO/worker/reviewer tokens remain shared prototype credentials.

## Setup

1. `cp .env.example .env.local` and replace every placeholder.
2. `chmod 600 .env.local`.
3. Run Python via `python -m uvicorn aao.pg_work:app --host 127.0.0.1 --port 8001`.
4. Docker Compose uses the separate `--env-file` option:
   `docker compose --env-file .env.local -f compose.dev.yaml up -d`.
5. For tests create `.env.test` with `AAO_ENV=test`, a **disposable**
   `AAO_TEST_POSTGRES_URL`, and `AAO_TEST_DB_DISPOSABLE=yes`. Then run:
   `AAO_ENV=test AAO_ENV_FILE=.env.test python -m pytest -q`.

**Important:** an existing PostgreSQL volume retains its initialized database
password. Replacing the password in `.env.local` does not rotate PostgreSQL.
Keep the existing password, or deliberately rotate the database role password
first. Do not upload the private file or paste credentials in issues.

Use URL-encoded values for any password embedded in a PostgreSQL DSN.
`AAO_TEST_DB_DISPOSABLE=yes` authorizes tests to modify that database.
Never point it at a valuable database.

**Production gate:** external secret management, individual identities,
credential rotation, authentication and database isolation must replace local
dotenv and shared tokens before operational deployment.
