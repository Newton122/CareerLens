"""One-time tokens for links sent by email.

A token is 32 random bytes (``secrets.token_urlsafe``), far too many to
guess. The link carries the token itself; the database keeps only its
SHA-256 hash, so a copy of the table cannot be turned back into working
links. A plain fast hash is enough here -- unlike passwords, these tokens are
random and long, so there is nothing to brute-force.

Each token has a purpose (reset or verify), an expiry, and is marked used the
moment it is redeemed.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from ai_job_intelligence.clock import utcnow
from ai_job_intelligence.models.auth_token import AuthToken

RESET_TOKEN_TTL = timedelta(hours=1)
VERIFY_TOKEN_TTL = timedelta(hours=48)


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def issue(db, user_id: int, purpose: str, ttl: timedelta) -> str:
    """Create a token and return the raw value for the link (caller commits).

    Any earlier unused token for the same purpose is cancelled, so only the
    most recent email's link works.
    """
    revoke(db, user_id, purpose)
    raw = secrets.token_urlsafe(32)
    db.add(
        AuthToken(
            user_id=user_id,
            purpose=purpose,
            token_hash=_hash(raw),
            expires_at=utcnow() + ttl,
        )
    )
    return raw


def find_valid(db, raw: str, purpose: str) -> AuthToken | None:
    """The unused, unexpired token for ``raw``, or None."""
    if not raw:
        return None
    token = (
        db.query(AuthToken)
        .filter(AuthToken.token_hash == _hash(raw), AuthToken.purpose == purpose)
        .first()
    )
    if token is None or token.used_at is not None or token.expires_at < utcnow():
        return None
    return token


def mark_used(token: AuthToken) -> None:
    token.used_at = utcnow()


def revoke(db, user_id: int, purpose: str) -> None:
    """Cancel every unused token of this purpose for a user (caller commits)."""
    db.query(AuthToken).filter(
        AuthToken.user_id == user_id,
        AuthToken.purpose == purpose,
        AuthToken.used_at.is_(None),
    ).update({AuthToken.used_at: utcnow()}, synchronize_session=False)
