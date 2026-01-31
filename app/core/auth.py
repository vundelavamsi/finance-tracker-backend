"""
Auth utilities: password hashing, JWT, Telegram Login Widget verification.
"""
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Hash a plain password using bcrypt."""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain password against a bcrypt hash."""
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT with payload e.g. {'sub': str(user_id), 'type': 'access'}."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode["exp"] = expire
    to_encode["type"] = to_encode.get("type", "access")
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    """Decode and verify JWT; returns payload or raises JWTError."""
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


def verify_telegram_login(auth_data: dict) -> Optional[str]:
    """
    Verify Telegram Login Widget payload.
    Given hash and user data from the widget, verify using bot token.
    Returns telegram_id as string if valid, else None.
    See: https://core.telegram.org/widgets/login#checking-authorization
    """
    hash_value = auth_data.get("hash")
    if not hash_value:
        return None
    # Build data-check-string: all fields except hash, sorted by key, key=value\n
    check_dict = {k: v for k, v in auth_data.items() if k != "hash" and v is not None}
    check_dict = {k: str(v) for k, v in check_dict.items()}
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(check_dict.items()))
    # Secret key = SHA256(bot_token)
    secret_key = hashlib.sha256(settings.telegram_bot_token.encode()).digest()
    # HMAC-SHA256(data_check_string, secret_key)
    computed = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(computed, hash_value):
        return None
    # Optional: check auth_date is not too old (e.g. 24h)
    auth_date = auth_data.get("auth_date")
    if auth_date:
        try:
            ts = int(auth_date)
            if datetime.utcnow().timestamp() - ts > 86400:  # 24 hours
                return None
        except (TypeError, ValueError):
            return None
    return str(auth_data.get("id"))
