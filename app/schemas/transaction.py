from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TransactionBase(BaseModel):
    """Base schema for transaction data."""
    amount: str
    currency: str = "INR"
    merchant: Optional[str] = None
    category_id: Optional[int] = None
    account_id: Optional[int] = None
    source_image_url: Optional[str] = None
    status: str = "PENDING"


class TransactionCreate(TransactionBase):
    """Schema for creating a new transaction."""
    user_id: int = 1  # Default user for MVP


class TransactionUpdate(BaseModel):
    """Schema for updating a transaction."""
    amount: Optional[str] = None
    currency: Optional[str] = None
    merchant: Optional[str] = None
    category_id: Optional[int] = None
    account_id: Optional[int] = None
    status: Optional[str] = None


class CategoryInfo(BaseModel):
    """Category information for transaction response."""
    id: int
    name: str
    color: str
    
    class Config:
        from_attributes = True


class AccountInfo(BaseModel):
    """Account information for transaction response."""
    id: int
    name: str
    account_type: str
    
    class Config:
        from_attributes = True


class TransactionResponse(TransactionBase):
    """Schema for transaction response."""
    id: int
    user_id: int
    category: Optional[CategoryInfo] = None
    account: Optional[AccountInfo] = None
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


class UserUpdate(BaseModel):
    """Schema for updating user data."""
    email: Optional[str] = None
    is_active: Optional[bool] = None


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
