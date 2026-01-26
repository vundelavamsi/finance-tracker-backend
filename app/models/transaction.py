from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(String, nullable=False)  # Using String to preserve precision
    currency = Column(String, default="INR")
    merchant = Column(String, nullable=True)
    category = Column(String, nullable=True)
    source_image_url = Column(String, nullable=True)
    status = Column(String, default="PENDING")  # PENDING, VERIFIED
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to user
    user = relationship("User", back_populates="transactions")
