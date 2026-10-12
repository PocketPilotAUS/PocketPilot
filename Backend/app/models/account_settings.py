from sqlalchemy import Column, ForeignKey, Integer, String, inspect
from app.database import Base


class AccountSettings(Base):
    __tablename__ = "account_settings"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    phone = Column(String(20), nullable=True)
    token_version = Column(Integer, nullable=False, default=0)


def get_account_settings(db, user_id):
    # Older installations remain able to sign in before the additive migration.
    if not inspect(db.get_bind()).has_table("account_settings"):
        return None
    return db.get(AccountSettings, user_id)
