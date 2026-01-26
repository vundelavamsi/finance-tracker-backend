from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TransactionBase(BaseModel):
    """Base schema for transaction data."""
    amount: str
    currency: str = "INR"
    merchant: Optional[str] = None
    category: Optional[str] = None
    source_image_url: Optional[str] = None
    status: str = "PENDING"


class TransactionCreate(TransactionBase):
    """Schema for creating a new transaction."""
    user_id: int


class TransactionResponse(TransactionBase):
    """Schema for transaction response."""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserBase(BaseModel):
    """Base schema for user data."""
    telegram_id: str
    email: Optional[str] = None
    is_active: bool = True


class UserCreate(UserBase):
    """Schema for creating a new user."""
    pass


class UserResponse(UserBase):
    """Schema for user response."""
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class TelegramWebhookUpdate(BaseModel):
    """Schema for Telegram webhook update."""
    update_id: int
    message: Optional[dict] = None
