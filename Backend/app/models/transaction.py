
from datetime import date

from sqlalchemy import Column, Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    category = Column(String, nullable=False)
    description = Column(String, nullable=True)
    date = Column(Date, nullable=False, default=date.today)

    # Nullable only because transactions created before authentication
    # existed have no owner. New transactions must always be given an
    # owner, and unowned rows must never be returned by authenticated
    # endpoints.
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    owner = relationship("User", back_populates="transactions")
