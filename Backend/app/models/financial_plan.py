from sqlalchemy import Column, Integer, String, Text, ForeignKey
from app.database import Base


class PlanningProfile(Base):
    __tablename__ = "planning_profiles"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    payload = Column(Text, nullable=False)


class FinancialPlan(Base):
    __tablename__ = "financial_plans"
    id = Column(String(36), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    payload = Column(Text, nullable=False)
