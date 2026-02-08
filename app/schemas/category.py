from pydantic import BaseModel, field_serializer, model_validator
from typing import Optional, List, Literal, Any
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
    category_type: Literal["INCOME", "EXPENSE"] = "EXPENSE"
    parent_id: Optional[int] = None


class CategoryUpdate(BaseModel):
    """Schema for updating a category."""
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    is_active: Optional[bool] = None
    category_type: Optional[Literal["INCOME", "EXPENSE"]] = None
    parent_id: Optional[int] = None


class CategoryResponse(CategoryBase):
    """Schema for category response."""
    id: int
    user_id: int
    category_type: str = "EXPENSE"
    parent_id: Optional[int] = None
    parent_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    sub_categories: Optional[List["CategoryResponse"]] = None

    class Config:
        from_attributes = True

    @model_validator(mode="wrap")
    @classmethod
    def orm_category_type_to_str(cls, v: Any, handler):
        if hasattr(v, "category_type") and hasattr(v.category_type, "value"):
            d = {f: getattr(v, f, None) for f in cls.model_fields}
            d["category_type"] = v.category_type.value
            if hasattr(v, "parent") and v.parent is not None:
                d["parent_name"] = v.parent.name
            d["sub_categories"] = None  # API attaches when include_children=True
            return cls(**d)
        return handler(v)

    @field_serializer("category_type", when_used="always")
    def serialize_category_type(self, value: Any) -> str:
        if hasattr(value, "value"):
            return value.value
        return value if isinstance(value, str) else "EXPENSE"
