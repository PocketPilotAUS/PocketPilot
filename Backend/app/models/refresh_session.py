from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from app.database import Base


class RefreshSession(Base):
    __tablename__ = "refresh_sessions"
    id = Column(String(64), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_version = Column(Integer, nullable=False)
    expires_at = Column(Integer, nullable=False)
    revoked = Column(Boolean, nullable=False, default=False)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    token_hash = Column(String(64), primary_key=True)
    session_id = Column(String(64), ForeignKey("refresh_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    used = Column(Boolean, nullable=False, default=False)
