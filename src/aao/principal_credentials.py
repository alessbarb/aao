"""Per-principal development credential verification, fail closed.

These are bearer-token development credentials, not production identities.
"""
import hashlib
import hmac

from aao.postgresql_connection import connect_postgres


class PrincipalDenied(ValueError):
    pass


def digest_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def authenticate(token: str | None, *, kind: str) -> str:
    if kind not in {"AGENT", "AUDITOR"} or not token:
        raise PrincipalDenied("Principal credential required")
    digest = digest_token(token)
    with connect_postgres() as db:
        rows = db.execute(
            "SELECT principal_id,token_digest FROM principal_credentials "
            "WHERE kind=%s AND enabled=true", (kind,)
        ).fetchall()
    for principal, stored_digest in rows:
        if hmac.compare_digest(digest, stored_digest):
            return principal
    raise PrincipalDenied("Principal credential invalid or revoked")


def authenticate_in_transaction(db, token: str | None, *, kind: str) -> str:
    """Resolve and lock an enabled principal credential in the caller's tx."""
    if kind not in {"AGENT", "AUDITOR"} or not token:
        raise PrincipalDenied("Principal credential required")
    row = db.execute(
        "SELECT principal_id FROM principal_credentials "
        "WHERE kind=%s AND token_digest=%s AND enabled=true FOR SHARE",
        (kind, digest_token(token)),
    ).fetchone()
    if not row:
        raise PrincipalDenied("Principal credential invalid or revoked")
    return row[0]
