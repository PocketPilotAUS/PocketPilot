from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint
from app.database import Base


class MonthlySavings(Base):
    __tablename__ = "monthly_savings"
    __table_args__ = (UniqueConstraint("user_id", "year", "month"),)
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    income_cents = Column(Integer, nullable=False)
    spent_cents = Column(Integer, nullable=False)
    extra_debt_cents = Column(Integer, nullable=False)
    saved_cents = Column(Integer, nullable=False)


class ManualSavings(Base):
    __tablename__ = "manual_savings"
    __table_args__ = (UniqueConstraint("user_id", "request_key"),)
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    label = Column(String(80), nullable=False)
    amount_cents = Column(Integer, nullable=False)
    request_key = Column(String(36), nullable=False)
    # Optional financial plan this contribution counts toward; null is general savings
    goal_id = Column(String(36), nullable=True, index=True)
