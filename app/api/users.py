from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from app.database import get_db
from app.models import User
from app.schemas import UserResponse, UserUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["users"])

# Default user ID for MVP
DEFAULT_USER_ID = 1


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    db: Session = Depends(get_db)
):
    """
    Get current user profile (default user for MVP).
    """
    user = db.query(User).filter(User.id == DEFAULT_USER_ID).first()
    
    if not user:
        # Create default user if doesn't exist
        user = User(
            id=DEFAULT_USER_ID,
            telegram_id="default_user",
            email=None,
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    return user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    db: Session = Depends(get_db)
):
    """
    Update current user profile.
    """
    user = db.query(User).filter(User.id == DEFAULT_USER_ID).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        # Update fields
        update_data = user_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        
        db.commit()
        db.refresh(user)
        
        return user
        
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update user")
