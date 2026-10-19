"""PostgreSQL backend connectivity and explicit schema bootstrap.

Not enabled in the active SQLite API. Schema creation is a manual development step.
"""
import os

from aao.settings import load_local_env
from contextlib import contextmanager


def database_url() -> str:
    load_local_env()
    url = os.environ.get("AAO_POSTGRES_URL", "")
    if not url.startswith(("postgresql://", "postgres://")):
        raise RuntimeError("AAO_POSTGRES_URL must be an explicit PostgreSQL DSN")
    return url


@contextmanager
def connect_postgres():
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError("Install the postgres optional dependencies") from exc
    with psycopg.connect(database_url(), autocommit=False) as db:
        yield db


def version():
    with connect_postgres() as db:
        return db.execute("SELECT current_setting('server_version')").fetchone()[0]


def migration_status():
    with connect_postgres() as db:
        row = db.execute(
            "SELECT version FROM schema_migrations ORDER BY applied_at DESC LIMIT 1"
        ).fetchone()
        return row[0] if row else None
