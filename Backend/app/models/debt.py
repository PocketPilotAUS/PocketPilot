from sqlalchemy import Column, ForeignKey, Integer, Numeric, String
from app.database import Base


class Debt(Base):
    __tablename__ = "debts"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(80), nullable=False)
    balance = Column(Numeric(14, 2), nullable=False)
    annual_rate = Column(Numeric(7, 4), nullable=False)
    remaining_months = Column(Integer, nullable=False)
    original_principal = Column(Numeric(14, 2), nullable=True)
