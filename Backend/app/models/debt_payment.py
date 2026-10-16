from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer, String, UniqueConstraint
from app.database import Base


class DebtPayment(Base):
    __tablename__ = "debt_payments"
    __table_args__ = (UniqueConstraint("user_id", "request_key"),)
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # Keep the payment history even if the loan is later removed.
    debt_id = Column(Integer, nullable=False)
    debt_name = Column(String(80), nullable=False)
    amount_cents = Column(Integer, nullable=False)
    paid_on = Column(Date, nullable=False, index=True)
    request_key = Column(String(36), nullable=False)

    applied_cents = Column(Integer, nullable=False, default=0, server_default="0")
    automatic = Column(Boolean, nullable=False, default=False, server_default="0")
