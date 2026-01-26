from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import logging

from app.database import get_db
from app.models import Category
from app.schemas import CategoryResponse, CategoryCreate, CategoryUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/categories", tags=["categories"])

# Default user ID for MVP
DEFAULT_USER_ID = 1


@router.get("/", response_model=List[CategoryResponse])
async def get_categories(
    db: Session = Depends(get_db)
):
    """
    Get list of all categories for the default user.
    """
    try:
        categories = db.query(Category).filter(
            Category.user_id == DEFAULT_USER_ID,
            Category.is_active == True
        ).order_by(Category.name).all()
        
        return categories
        
    except Exception as e:
        logger.error(f"Error fetching categories: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch categories")


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a single category by ID.
    """
    category = db.query(Category).filter(
        Category.id == category_id,
        Category.user_id == DEFAULT_USER_ID
    ).first()
    
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    return category


@router.post("/", response_model=CategoryResponse, status_code=201)
async def create_category(
    category: CategoryCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new category.
    """
    try:
        # Check if category name already exists for this user
        existing = db.query(Category).filter(
            Category.name == category.name,
            Category.user_id == DEFAULT_USER_ID
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail="Category with this name already exists")
        
        db_category = Category(
            user_id=DEFAULT_USER_ID,
            name=category.name,
            description=category.description,
            color=category.color,
            icon=category.icon,
            is_active=category.is_active
        )
        
        db.add(db_category)
        db.commit()
        db.refresh(db_category)
        
        return db_category
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating category: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create category")


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    category_update: CategoryUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing category.
    """
    db_category = db.query(Category).filter(
        Category.id == category_id,
        Category.user_id == DEFAULT_USER_ID
    ).first()
    
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    try:
        # Check if new name conflicts with existing category
        if category_update.name and category_update.name != db_category.name:
            existing = db.query(Category).filter(
                Category.name == category_update.name,
                Category.user_id == DEFAULT_USER_ID,
                Category.id != category_id
            ).first()
            
            if existing:
                raise HTTPException(status_code=400, detail="Category with this name already exists")
        
        # Update fields
        update_data = category_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_category, field, value)
        
        db.commit()
        db.refresh(db_category)
        
        return db_category
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating category: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update category")


@router.delete("/{category_id}", status_code=204)
async def delete_category(
    category_id: int,
    db: Session = Depends(get_db)
):
    """
    Soft delete a category (set is_active to False).
    """
    db_category = db.query(Category).filter(
        Category.id == category_id,
        Category.user_id == DEFAULT_USER_ID
    ).first()
    
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    try:
        # Soft delete
        db_category.is_active = False
        db.commit()
        return None
        
    except Exception as e:
        logger.error(f"Error deleting category: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete category")
