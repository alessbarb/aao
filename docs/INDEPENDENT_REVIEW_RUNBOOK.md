# M2-A external review runbook

**Purpose:** let a qualified reviewer inspect the inert M2-A candidate
and reproduce local checks without write access to the upstream repository or
any non-disposable service. This procedure does not grant review, deployment,
merge, or operating authority.

## Review targets and preserved references

- **Frozen historical PR #2 pair:** implementation
  `dc084417a2ba683fe4737342f89e9cd1036b38ad`; package/PR head
  `ef1a6e64ad4d6523cacd6c98a3b25ae7cebf4ad5`. This pair is preserved as-is;
  the package contains H-01. PR #2 remains OPEN/DRAFT and must not be updated
  or merged under this procedure.
- **Corrected candidate source:**
  `31e7397be082394a6da95eadebd0d8ad6bf99c39`. It is a separate proposed
  revision containing the H-01 fix and regression tests. The current runbook
  package is the exact checkout SHA from which this file is read; record that
  full `PACKAGE_SHA` in the review request after the package commit is
  published. The final report must bind this package SHA and corrected source
  SHA separately. Do not use PR #2's frozen head as if it included the fix.
- Until a distinct review vehicle is explicitly prepared, the corrected
  candidate is reviewed by its exact package SHA from a read-only checkout;
  this runbook does not move refs or merge/update PR #2. The implementation
  source is an ancestor of the package and its exact code/test delta is shown
  below.

If any pinned revision is unavailable or differs, stop. Do not silently
substitute another commit. Confirm separately that PR #2 still has its frozen
head and remains OPEN/DRAFT; that is a preservation check, not the review head
for the corrected candidate.

## Access and safety boundary

Run the shell blocks in order in a single dedicated shell so the pinned SHA,
temporary paths, container name, and disposable DSN remain consistent. The
reviewer-owned pinned clone is read-only by procedure; package installation
and tests use only the separate scratch copy.

1. Obtain read-only access to the repository and review evidence. Do not request
   write, merge, deploy, production, secret-store, or database access.
2. Use a local clone or archive in a reviewer-owned temporary directory. Do
   not edit, commit, or push candidate files. Keep test/build copies and logs
   outside the clone; do not commit audit outputs to the frozen candidate.
3. Do not open, copy, print, or source `.env.local`, `.env.test`, or any other
   private operator configuration. This procedure uses explicit environment
   variables and does not require dotenv files.
4. Do not connect to an operator's development, staging, or production
   database. All PostgreSQL checks below run only against a new disposable
   local container bound to loopback. Do not mount a host database volume or
   publish the database port beyond `127.0.0.1`.
5. No models, tools, shell workers, provider adapters, network actions from
   AAO, or real external effects are part of this review. Do not start the API
   or worker unless a specific read-only inspection requires it; no such start
   is needed for the checks below.

## 1. Verify and pin both revisions

Run from a reviewer-owned temporary directory using read-only GitHub access:

```sh
set -eu
umask 077
ROOT="$(mktemp -d "${TMPDIR:-/tmp}/aao-m2a-review.XXXXXX")"
REPO="$ROOT/repository"
RUN="$ROOT/run-copy"
PACKAGE_SHA=SET_TO_EXACT_PUBLISHED_REVIEW_PACKAGE_SHA
SOURCE_SHA=31e7397be082394a6da95eadebd0d8ad6bf99c39

git clone https://github.com/autoaiorg/aao.git "$REPO"
git -C "$REPO" checkout --detach "$PACKAGE_SHA"
test "$(git -C "$REPO" rev-parse HEAD)" = "$PACKAGE_SHA"
git -C "$REPO" merge-base --is-ancestor "$SOURCE_SHA" "$PACKAGE_SHA"
git -C "$REPO" diff --name-status "$SOURCE_SHA" "$PACKAGE_SHA"
git -C "$REPO" status --short
```

Review the full package diff; verify source changes after `SOURCE_SHA` are
limited to the recorded documentation/test package. Do not claim PR #2's head
equals `PACKAGE_SHA`. Independently confirm PR #2 remains OPEN/DRAFT at frozen
SHA `ef1a6e64ad4d6523cacd6c98a3b25ae7cebf4ad5` using GitHub's read-only UI or
API. Record UTC time, repository URL, both review SHAs, frozen PR state/head,
and exact command output in the reviewer's workpaper. If the repository is not
anonymously readable, use authorized read-only Git credentials; never place a
token in a command argument, shell history, or report.

For mutable build/test output, make an isolated copy. All subsequent commands
operate on that copy, not on the pinned source clone:

```sh
cp -a "$REPO" "$RUN"
```

## 2. Create an explicitly disposable PostgreSQL test instance

Prerequisites: Docker, Python 3.12+, and a free loopback port `55432`. This
container has no mounted data volume and is removed on stop. If the port is
already in use, choose another free local port and use it consistently below.

```sh
PG_CONTAINER="aao-m2a-review-$$"
docker run --rm --detach --name "$PG_CONTAINER" \
  -e POSTGRES_USER=aao_auditor \
  -e POSTGRES_DB=aao_test \
  -e POSTGRES_HOST_AUTH_METHOD=trust \
  -p 127.0.0.1:55432:5432 postgres:16
cleanup() {
  docker stop "$PG_CONTAINER" >/dev/null 2>&1 || true
  case "$ROOT" in
    "${TMPDIR:-/tmp}"/aao-m2a-review.*)
      python3 -c 'import shutil,sys; shutil.rmtree(sys.argv[1])' "$ROOT" ;;
    *) echo "Refusing cleanup outside generated review temp path" >&2; return 1 ;;
  esac
}
trap cleanup EXIT

until docker exec "$PG_CONTAINER" pg_isready -U aao_auditor -d aao_test; do
  sleep 1
done
export AAO_ENV=test
export AAO_TEST_DB_DISPOSABLE=yes
export AAO_TEST_POSTGRES_URL=postgresql://aao_auditor@127.0.0.1:55432/aao_test
export AAO_POSTGRES_URL="$AAO_TEST_POSTGRES_URL"
```

The `trust` authentication setting is confined to the container's loopback
port and temporary lifetime; do not reuse this configuration outside the
disposable review instance.

## 3. Replay migrations and the legacy-upgrade path

From the isolated `RUN` copy, apply migrations in order and seed only the
synthetic legacy row used by CI between migrations 005 and 006:

```sh
cd "$RUN"
apply_migration() {
  docker exec -i "$PG_CONTAINER" psql -U aao_auditor -d aao_test \
    -v ON_ERROR_STOP=1 -f - < "$1"
}
for migration in \
  db/postgres/001_foundation.sql \
  db/postgres/002_dev_identity.sql \
  db/postgres/003_execution.sql \
  db/postgres/004_execution_guards.sql \
  db/postgres/005_principal_credentials.sql; do
  apply_migration "$migration"
done
docker exec "$PG_CONTAINER" psql -U aao_auditor -d aao_test -v ON_ERROR_STOP=1 \
  -c "INSERT INTO worker_registrations(worker_id,token_digest,enabled) VALUES ('legacy-review-agent','f96fec142530f614fd37bdadb76c54cd017b1ccabb0d29164ef894447f36a81f',true)"
for migration in \
  db/postgres/006_unified_execution_identity.sql \
  db/postgres/007_fence_leases_across_project_state_changes.sql \
  db/postgres/008_content_addressed_evidence.sql \
  db/postgres/009_prevent_evidence_truncation.sql \
  db/postgres/010_capability_registry.sql; do
  apply_migration "$migration"
done
docker exec "$PG_CONTAINER" psql -U aao_auditor -d aao_test -v ON_ERROR_STOP=1 \
  -c "SELECT version FROM schema_migrations ORDER BY applied_at DESC LIMIT 1"
```

Expected terminal schema version: `010_capability_registry`. The
synthetic digest is test data, not an operational credential. Do not alter
migrations 001–010. If any migration fails or the terminal version differs,
stop and record the failure; do not improvise a repair in the candidate.

## 4. Reproduce automated engineering checks

Create an isolated Python environment and run checks from the `RUN` copy:

```sh
python3.12 -m venv "$ROOT/venv"
. "$ROOT/venv/bin/activate"
python -m pip install -e "$RUN[dev,postgres]"
python -m pip check
python -m compileall -q src tests
python -m ruff check src tests
AAO_ENV=test AAO_TEST_DB_DISPOSABLE=yes \
  AAO_POSTGRES_URL="$AAO_POSTGRES_URL" \
  AAO_TEST_POSTGRES_URL="$AAO_TEST_POSTGRES_URL" \
  python -m pytest -q -rs -W error -p no:cacheprovider
git status --short
```

Expected at corrected implementation candidate `31e7397`: 91 passed, zero failed,
zero skipped, and zero warnings. Tool versions, exact outputs, elapsed time,
and any deviation must be recorded. The historical 83-test evidence is tied to
implementation SHA `dc084417`; the external run is new evidence and must state
the package checkout used. This command group is automated technical
verification, not the required human security/architecture review or M2-A
acceptance. A `pip check` or linter result cannot establish authorization,
concurrency, or constitutional guarantees.

After checks, confirm no tracked source changes in the pinned clone. Remove
the container and temporary directory using the trap, or stop/remove them
manually if the shell exits unexpectedly. Verify the named container no
longer exists. Do not leave a database volume or export database contents.

## 5. Keep automated findings separate from formal review

Produce two distinct records; do not combine their labels or imply one
substitutes for the other:

1. **Automated reproducibility report:** tool/runtime versions, both SHAs,
   database/container setup and cleanup, exact commands and results, test
   skips/warnings, and machine-detected findings. Attribute it to the person
   who ran the commands. Label it *automated/local technical evidence*.
2. **Formal independent security and architecture review:** authored by a
   qualified person other than the implementer. Include the reviewer's name
   and organization/qualification, independence statement, both exact SHAs,
   scope, methods, files/contracts/threats examined, independently reproduced
   checks, severity-ranked findings with references, unsupported claims,
   residual-risk assessment, and a recommendation limited to M2-A. The report
   must explicitly state that it does not grant M2-A acceptance, merge
   authority, production permission, or permission for external execution.

Use a report filename such as
`m2a-review-<PACKAGE_SHA>-<SOURCE_SHA>.md`. Put both full SHAs in the report
header and verify them against the live PR before submission. Submit through a
GitHub review tied to the exact PR commit when the reviewer has appropriate
review permissions; otherwise provide an attributable report to the CEO for
recording without presenting an implementer-authored transcription as the
reviewer's own work. Record the report's cryptographic digest if it is stored
outside GitHub. A review of different commits must be marked superseded, not
silently carried forward.

## Stop conditions and disposition

Stop the reproduction for any non-disposable database risk, secret exposure,
SHA mismatch, non-loopback database binding, unexpected migration state, or
attempt to enable an operational capability. Report findings; do not fix code
in the frozen package. Demonstrable defects should be corrected on a separate
engineering revision with focused regression evidence, then re-pin and request
a new review explicitly. Do not silently change the frozen candidate.

M2-A acceptance and PR #2 merge remain blocked until an independent formal
review is available, findings are resolved or explicitly dispositioned, and
the competent authority accepts the exact package/source pair and residual
risks. Neither this runbook nor green automated checks change those gates.
