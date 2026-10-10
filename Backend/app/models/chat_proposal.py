from sqlalchemy import Column, ForeignKey, Integer, String, Text
from app.database import Base

class ChatProposal(Base):
    __tablename__ = "chat_proposals"
    id = Column(String(36), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    payload = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
