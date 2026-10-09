from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("length(trim(email)) > 0", name="ck_users_email_not_empty"),
        CheckConstraint("length(trim(name)) > 0", name="ck_users_name_not_empty"),
    )

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    # passive_deletes="all" stops SQLAlchemy from silently setting
    # transactions.user_id to NULL when a user is deleted. The database
    # foreign key then refuses to delete a user who still owns transactions.
    transactions = relationship(
        "Transaction",
        back_populates="owner",
        passive_deletes="all"
    )
