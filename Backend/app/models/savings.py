from sqlalchemy import Column, ForeignKey, Integer, UniqueConstraint
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
