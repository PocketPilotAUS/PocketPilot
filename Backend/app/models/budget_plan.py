from sqlalchemy import Column, ForeignKey, Integer, Text, UniqueConstraint
from app.database import Base

class BudgetPlan(Base):
    __tablename__ = "budget_plans"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    percentages = Column(Text, nullable=False)
    __table_args__ = (UniqueConstraint("user_id", "year", "month"),)
