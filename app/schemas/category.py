from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CategoryBase(BaseModel):
    """Base schema for category data."""
    name: str
    description: Optional[str] = None
    color: str = "#6366f1"  # Default indigo color
    icon: Optional[str] = None
    is_active: bool = True


class CategoryCreate(CategoryBase):
    """Schema for creating a new category."""
    user_id: int = 1  # Default user for MVP


class CategoryUpdate(BaseModel):
    """Schema for updating a category."""
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    is_active: Optional[bool] = None


class CategoryResponse(CategoryBase):
    """Schema for category response."""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
