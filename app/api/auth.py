"""
Auth API: register, login, login-by-telegram-username, verify-telegram-login, get_current_user.
"""
import secrets
import string
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.orm import Session

from app.config import settings
from app.core.auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
    verify_telegram_login,
)
from app.database import get_db
from app.models import User, OneTimeLoginToken
from app.schemas import UserResponse
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    LoginByTelegramUsernameRequest,
    VerifyTelegramLoginRequest,
    TelegramAuthRequest,
    LoginByTelegramUsernameResponse,
)
from app.services.telegram_service import telegram_service

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


def normalize_telegram_username(username: str) -> str:
    """Strip leading @ and lowercase."""
    if not username:
        return ""
    u = username.strip().lstrip("@").lower()
    return u


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Extract Bearer token, decode JWT, load user; raise 401 if invalid."""
    if not credentials or credentials.credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = credentials.credentials
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        user_id = int(user_id)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


def _make_token_response(user: User) -> dict:
    """Build { access_token, token_type, user }."""
    access_token = create_access_token(data={"sub": str(user.id)})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user),
    }


@router.post("/register", response_model=dict)
async def register(
    body: RegisterRequest,
    db: Session = Depends(get_db),
):
    """Register with email and/or phone + password. At least one of email or phone required."""
    if not body.email and not body.phone:
        raise HTTPException(
            status_code=422,
            detail="At least one of email or phone is required",
        )
    if body.email:
        existing = db.query(User).filter(User.email == body.email.strip()).first()
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered")
    if body.phone:
        existing = db.query(User).filter(User.phone == body.phone.strip()).first()
        if existing:
            raise HTTPException(status_code=409, detail="Phone already registered")
    user = User(
        telegram_id=None,
        telegram_username=None,
        email=body.email.strip() if body.email else None,
        phone=body.phone.strip() if body.phone else None,
        password_hash=hash_password(body.password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _make_token_response(user)


@router.post("/login", response_model=dict)
async def login(
    body: LoginRequest,
    db: Session = Depends(get_db),
):
    """Login with email or phone + password."""
    login_val = body.login.strip()
    user = db.query(User).filter(
        (User.email == login_val) | (User.phone == login_val)
    ).first()
    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid login or password")
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid login or password")
    if not user.is_active:
        raise HTTPException(status_code=401, detail="User is inactive")
    return _make_token_response(user)


@router.post("/login-by-telegram-username", response_model=LoginByTelegramUsernameResponse)
async def login_by_telegram_username(
    body: LoginByTelegramUsernameRequest,
    db: Session = Depends(get_db),
):
    """Send magic link and/or OTP via Telegram bot for the given username. No JWT yet."""
    username = normalize_telegram_username(body.telegram_username)
    if not username:
        raise HTTPException(status_code=422, detail="Telegram username is required")
    user = db.query(User).filter(User.telegram_username == username).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="No account found for this username. Use the Telegram bot first to create an account.",
        )
    if not user.telegram_id:
        raise HTTPException(
            status_code=400,
            detail="This username is not linked to Telegram. Connect Telegram in Profile first, or log in with email/password.",
        )
    expire_minutes = settings.magic_link_expire_minutes
    expires_at = datetime.utcnow() + timedelta(minutes=expire_minutes)
    token = secrets.token_urlsafe(32)
    code = "".join(secrets.choice(string.digits) for _ in range(6))
    row = OneTimeLoginToken(
        token=token,
        code=code,
        user_id=user.id,
        expires_at=expires_at,
    )
    db.add(row)
    db.commit()
    base_url = (settings.magic_link_base_url or "").rstrip("/")
    link = f"{base_url}/auth/verify?token={token}" if base_url else None
    message_lines = []
    if link:
        message_lines.append(f"Your login link: {link}")
    message_lines.append(f"Your login code: {code}")
    message_lines.append(f"Valid for {expire_minutes} minutes.")
    text = "\n".join(message_lines)
    chat_id = int(user.telegram_id)
    ok = await telegram_service.send_message(chat_id, text)
    if not ok:
        raise HTTPException(
            status_code=500,
            detail="Failed to send message to Telegram. Please try again.",
        )
    return LoginByTelegramUsernameResponse(
        message="Check your Telegram for the login link or code",
        expires_in=expire_minutes * 60,
    )


@router.post("/verify-telegram-login", response_model=dict)
async def verify_telegram_login(
    body: VerifyTelegramLoginRequest,
    db: Session = Depends(get_db),
):
    """Exchange magic-link token or OTP code for JWT."""
    token_or_code = (body.token or "").strip()
    if not token_or_code:
        raise HTTPException(status_code=422, detail="Token or code is required")
    row = db.query(OneTimeLoginToken).filter(
        (OneTimeLoginToken.token == token_or_code) | (OneTimeLoginToken.code == token_or_code),
        OneTimeLoginToken.expires_at > datetime.utcnow(),
    ).first()
    if not row:
        raise HTTPException(
            status_code=401,
            detail="Link or code expired or invalid. Request a new one from the login page.",
        )
    user = db.query(User).filter(User.id == row.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    db.delete(row)
    db.commit()
    return _make_token_response(user)


@router.get("/verify-telegram-login", response_model=dict)
async def verify_telegram_login_get(
    token: str = "",
    db: Session = Depends(get_db),
):
    """GET variant for magic link (query param ?token=...)."""
    return await verify_telegram_login(
        VerifyTelegramLoginRequest(token=token or ""),
        db,
    )


@router.post("/telegram", response_model=dict)
async def login_with_telegram_widget(
    body: TelegramAuthRequest,
    db: Session = Depends(get_db),
):
    """Login/signup via Telegram Login Widget. Verify payload and issue JWT."""
    auth_data = body.model_dump(exclude_none=True)
    telegram_id = verify_telegram_login(auth_data)
    if not telegram_id:
        raise HTTPException(status_code=401, detail="Invalid Telegram authorization")
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        username = body.username
        if username:
            username = normalize_telegram_username(username)
        user = User(
            telegram_id=telegram_id,
            telegram_username=username,
            email=None,
            phone=None,
            password_hash=None,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    if not user.is_active:
        raise HTTPException(status_code=401, detail="User is inactive")
    return _make_token_response(user)


@router.get("/me", response_model=UserResponse)
async def auth_me(current_user: User = Depends(get_current_user)):
    """Return current user (requires Bearer token)."""
    return UserResponse.model_validate(current_user)
