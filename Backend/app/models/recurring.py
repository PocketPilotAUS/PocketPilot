from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer, String, UniqueConstraint
from app.database import Base

class RecurringExpense(Base):
    __tablename__ = "recurring_expenses"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    request_key = Column(String(36), nullable=False)
    __table_args__ = (UniqueConstraint("user_id", "request_key"),)
    amount_cents = Column(Integer, nullable=False)
    category = Column(String(40), nullable=False)
    description = Column(String(500))
    day = Column(Integer, nullable=False)
    next_date = Column(Date, nullable=False)
    active = Column(Boolean, nullable=False, default=True)

class RecurringOccurrence(Base):
    __tablename__ = "recurring_occurrences"
    id = Column(Integer, primary_key=True)
    schedule_id = Column(Integer, ForeignKey("recurring_expenses.id"), nullable=False)
    due_date = Column(Date, nullable=False)
    transaction_id = Column(Integer, nullable=False)
    __table_args__ = (UniqueConstraint("schedule_id", "due_date"),)
