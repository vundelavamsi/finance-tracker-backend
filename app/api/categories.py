from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import logging

from app.database import get_db
from app.models import Category, User
from app.models.category import CategoryType
from app.schemas import CategoryResponse, CategoryCreate, CategoryUpdate
from app.api.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=List[CategoryResponse])
async def get_categories(
    type: Optional[str] = Query(None, description="Filter by category_type: INCOME or EXPENSE"),
    include_children: bool = Query(False, description="When type=EXPENSE, nest sub_categories under each parent"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get list of categories for the current user. Optional filter by type and nested sub-categories.
    """
    try:
        q = db.query(Category).filter(
            Category.user_id == current_user.id,
            Category.is_active == True,
        )
        if type and type.upper() in ("INCOME", "EXPENSE"):
            cat_type = CategoryType(type.upper())
            q = q.filter(Category.category_type == cat_type)
        if type and type.upper() == "EXPENSE" and include_children:
            # Return only top-level expense categories (parent_id is null), with sub_categories loaded
            q = q.filter(Category.parent_id == None).order_by(Category.name)
            categories = q.options(joinedload(Category.sub_categories)).all()
            result = []
            for c in categories:
                resp = CategoryResponse.model_validate(c)
                # Attach sub_categories for this parent
                sub_list = [CategoryResponse.model_validate(sc) for sc in c.sub_categories if sc.is_active]
                result.append(CategoryResponse(
                    **resp.model_dump(exclude={"sub_categories"}),
                    sub_categories=sub_list or None,
                ))
            return result
        q = q.order_by(Category.name)
        if type and type.upper() == "EXPENSE":
            q = q.filter(Category.parent_id == None)
        categories = q.all()
        return [CategoryResponse.model_validate(c) for c in categories]
    except Exception as e:
        logger.error(f"Error fetching categories: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch categories")


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a single category by ID.
    """
    category = db.query(Category).filter(
        Category.id == category_id,
        Category.user_id == current_user.id
    ).first()
    
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    return category


def _name_exists(db: Session, user_id: int, name: str, exclude_category_id: Optional[int] = None, parent_id: Optional[int] = None) -> bool:
    q = db.query(Category).filter(Category.user_id == user_id, Category.name == name, Category.is_active == True)
    if exclude_category_id is not None:
        q = q.filter(Category.id != exclude_category_id)
    if parent_id is not None:
        q = q.filter(Category.parent_id == parent_id)
    else:
        q = q.filter(Category.parent_id == None)
    return q.first() is not None


@router.post("", response_model=CategoryResponse, status_code=201)
async def create_category(
    category: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new category. Use parent_id to create a sub-category under an expense category.
    """
    try:
        cat_type = CategoryType(category.category_type)
        parent_id = category.parent_id

        if parent_id is not None:
            parent = db.query(Category).filter(
                Category.id == parent_id,
                Category.user_id == current_user.id,
                Category.is_active == True,
            ).first()
            if not parent:
                raise HTTPException(status_code=404, detail="Parent category not found")
            if parent.category_type != CategoryType.EXPENSE:
                raise HTTPException(status_code=400, detail="Sub-categories only allowed under expense categories")
            if parent.parent_id is not None:
                raise HTTPException(status_code=400, detail="Only one level of sub-categories allowed")
            cat_type = CategoryType.EXPENSE
        else:
            parent_id = None

        if _name_exists(db, current_user.id, category.name, parent_id=parent_id):
            raise HTTPException(status_code=400, detail="Category with this name already exists")

        db_category = Category(
            user_id=current_user.id,
            category_type=cat_type,
            parent_id=parent_id,
            name=category.name,
            description=category.description,
            color=category.color,
            icon=category.icon,
            is_active=category.is_active,
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update an existing category. Sub-categories cannot be changed to top-level or to a different parent via this endpoint.
    """
    db_category = db.query(Category).filter(
        Category.id == category_id,
        Category.user_id == current_user.id,
    ).first()
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")

    try:
        if category_update.name and category_update.name != db_category.name:
            if _name_exists(db, current_user.id, category_update.name, exclude_category_id=category_id, parent_id=db_category.parent_id):
                raise HTTPException(status_code=400, detail="Category with this name already exists")
        update_data = category_update.model_dump(exclude_unset=True)
        if "category_type" in update_data and update_data["category_type"] is not None:
            update_data["category_type"] = CategoryType(update_data["category_type"])
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Soft delete a category (set is_active to False). Cannot delete a category that has sub-categories; remove them first.
    """
    db_category = db.query(Category).filter(
        Category.id == category_id,
        Category.user_id == current_user.id,
    ).first()
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    has_children = db.query(Category).filter(
        Category.parent_id == category_id,
        Category.is_active == True,
    ).first() is not None
    if has_children:
        raise HTTPException(status_code=400, detail="Remove sub-categories before deleting this category")
    try:
        db_category.is_active = False
        db.commit()
        return None
    except Exception as e:
        logger.error(f"Error deleting category: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete category")
