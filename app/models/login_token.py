from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from app.database import Base


class OneTimeLoginToken(Base):
    """One-time token for Telegram magic-link / OTP login."""
    __tablename__ = "one_time_login_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    code = Column(String, index=True, nullable=True)  # optional 6-digit code for OTP entry
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
