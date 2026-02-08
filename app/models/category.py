import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class CategoryType(str, enum.Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, default=1)
    category_type = Column(Enum(CategoryType, native_enum=False), nullable=False, default=CategoryType.EXPENSE)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    color = Column(String, nullable=False, default="#6366f1")  # Default indigo color
    icon = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to user
    user = relationship("User", back_populates="categories")
    # Self-referential: parent category and sub-categories (only one level; sub-categories are expense by implication)
    parent = relationship("Category", remote_side=[id], back_populates="sub_categories")
    sub_categories = relationship("Category", back_populates="parent", foreign_keys=[parent_id])
    # Relationship to transactions
    transactions = relationship("Transaction", back_populates="category")
