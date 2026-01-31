from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from app.database import get_db
from app.models import User
from app.schemas import UserResponse, UserUpdate
from app.schemas.auth import SetPasswordRequest, ConnectTelegramRequest
from app.api.auth import get_current_user
from app.core.auth import hash_password, verify_telegram_login

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["users"])


def _normalize_telegram_username(username: str) -> str:
    if not username:
        return ""
    return username.strip().lstrip("@").lower()


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user profile (requires Bearer token)."""
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update current user profile."""
    try:
        update_data = user_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(current_user, field, value)
        db.commit()
        db.refresh(current_user)
        return UserResponse.model_validate(current_user)
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update user")


@router.post("/me/set-password", response_model=UserResponse)
async def set_password(
    body: SetPasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Set email/phone and password for Telegram-first users (enable email/phone + password login)."""
    if not body.email and not body.phone:
        raise HTTPException(
            status_code=422,
            detail="At least one of email or phone is required",
        )
    email = body.email.strip() if body.email else None
    phone = body.phone.strip() if body.phone else None
    if email:
        other = db.query(User).filter(User.email == email, User.id != current_user.id).first()
        if other:
            raise HTTPException(status_code=409, detail="Email already used by another account")
    if phone:
        other = db.query(User).filter(User.phone == phone, User.id != current_user.id).first()
        if other:
            raise HTTPException(status_code=409, detail="Phone already used by another account")
    current_user.email = email or current_user.email
    current_user.phone = phone or current_user.phone
    current_user.password_hash = hash_password(body.password)
    db.commit()
    db.refresh(current_user)
    return UserResponse.model_validate(current_user)


@router.post("/me/connect-telegram", response_model=UserResponse)
async def connect_telegram(
    body: ConnectTelegramRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Link Telegram account (Telegram Login Widget payload). For web-first users."""
    auth_data = body.model_dump(exclude_none=True)
    telegram_id = verify_telegram_login(auth_data)
    if not telegram_id:
        raise HTTPException(status_code=401, detail="Invalid Telegram authorization")
    other = db.query(User).filter(User.telegram_id == telegram_id).first()
    if other and other.id != current_user.id:
        raise HTTPException(
            status_code=409,
            detail="This Telegram account is already linked to another account",
        )
    current_user.telegram_id = telegram_id
    username = body.username
    if username:
        current_user.telegram_username = _normalize_telegram_username(username)
    db.commit()
    db.refresh(current_user)
    return UserResponse.model_validate(current_user)
