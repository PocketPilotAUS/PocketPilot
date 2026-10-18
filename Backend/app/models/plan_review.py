"""Issued Financial Plan acceptance capabilities, separate from transaction drafts."""
from sqlalchemy import Column, ForeignKey, String, Text
from app.database import Base


class PlanReview(Base):
    __tablename__ = "financial_plan_reviews"
    id = Column(String(36), primary_key=True)
    user_id = Column(ForeignKey("users.id"), nullable=False, index=True)
    payload = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
