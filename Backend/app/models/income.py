from sqlalchemy import Column, ForeignKey, Integer, UniqueConstraint
from app.database import Base


class MonthlyIncome(Base):
    __tablename__ = "monthly_income"
    __table_args__ = (UniqueConstraint("user_id", "year", "month"),)
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    amount_cents = Column(Integer, nullable=False)
