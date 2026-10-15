"""Opaque, single-use refresh tokens with a fixed seven-day session lifetime."""
import hashlib
import secrets
import time
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import inspect, text

from app.core.config import get_access_token_expire_minutes
from app.core.security import create_access_token
from app.models.account_settings import get_account_settings
from app.models.refresh_session import RefreshSession, RefreshToken
from app.models.user import User
from app.schemas.user import Token

SESSION_SECONDS = 7 * 24 * 60 * 60


def require_tables(db):
    inspector = inspect(db.get_bind())
    if not all(inspector.has_table(name) for name in ("refresh_sessions", "refresh_tokens")):
        raise HTTPException(503, "Run migrate_refresh_sessions.py on the backend before signing in.")


def digest(token):
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def issue_pair(db, session):
    raw = secrets.token_urlsafe(48)
    db.add(RefreshToken(token_hash=digest(raw), session_id=session.id, used=False))
    seconds = min(get_access_token_expire_minutes() * 60, session.expires_at - int(time.time()))
    return Token(
        access_token=create_access_token(session.user_id, timedelta(seconds=seconds), session.token_version, session_id=session.id),
        refresh_token=raw,
        expires_in=seconds,
    )


def start_session(db, user):
    require_tables(db)
    settings = get_account_settings(db, user.id)
    session = RefreshSession(id=secrets.token_hex(24), user_id=user.id,
        token_version=settings.token_version if settings else 0,
        expires_at=int(time.time()) + SESSION_SECONDS, revoked=False)
    db.add(session)
    db.flush()
    pair = issue_pair(db, session)
    db.commit()
    return pair


def rotate(db, raw):
    require_tables(db)
    # Take the SQLite write lock BEFORE reading; concurrent refreshes cannot
    # both consume a token or race logout/password changes.
    db.execute(text("BEGIN IMMEDIATE"))
    token = db.get(RefreshToken, digest(raw))
    session = db.get(RefreshSession, token.session_id) if token else None
    if session is None:
        db.rollback()
        raise HTTPException(401, "Invalid refresh token.")
    user = db.get(User, session.user_id)
    settings = get_account_settings(db, session.user_id)
    version = settings.token_version if settings else 0
    if token.used or session.revoked or session.expires_at <= int(time.time()) or user is None or session.token_version != version:
        # Keep consumed hashes until the family expires so replay revokes
        # the current descendant, not just the already-used token.
        session.revoked = True
        db.commit()
        raise HTTPException(401, "Refresh session expired or revoked.")
    token.used = True
    pair = issue_pair(db, session)
    db.commit()
    return pair


def revoke(db, raw):
    require_tables(db)
    db.execute(text("BEGIN IMMEDIATE"))
    token = db.get(RefreshToken, digest(raw))
    if token:
        db.query(RefreshSession).filter_by(id=token.session_id).update({RefreshSession.revoked: True})
    db.commit()
