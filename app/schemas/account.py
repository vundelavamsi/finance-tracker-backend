from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.account import AccountType


class AccountBase(BaseModel):
    """Base schema for account data."""
    name: str
    account_type: AccountType
    balance: float = 0.0
    currency: str = "INR"
    is_active: bool = True


class AccountCreate(AccountBase):
    """Schema for creating a new account."""
    user_id: int = 1  # Default user for MVP


class AccountUpdate(BaseModel):
    """Schema for updating an account."""
    name: Optional[str] = None
    account_type: Optional[AccountType] = None
    balance: Optional[float] = None
    currency: Optional[str] = None
    is_active: Optional[bool] = None


class AccountResponse(AccountBase):
    """Schema for account response."""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
