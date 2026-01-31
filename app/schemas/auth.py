"""Auth request/response schemas."""
from pydantic import BaseModel
from typing import Optional


class RegisterRequest(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    password: str
    # at least one of email or phone required; validated in endpoint


class LoginRequest(BaseModel):
    login: str  # email or phone
    password: str


class LoginByTelegramUsernameRequest(BaseModel):
    telegram_username: str


class VerifyTelegramLoginRequest(BaseModel):
    token: str  # magic-link token or OTP code


class TelegramAuthRequest(BaseModel):
    """Payload from Telegram Login Widget (hash, id, first_name, username, etc.)."""
    hash: str
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    auth_date: Optional[int] = None


class SetPasswordRequest(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    password: str
    # at least one of email or phone required


class ConnectTelegramRequest(BaseModel):
    """Same as TelegramAuthRequest - widget payload."""
    hash: str
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    auth_date: Optional[int] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginByTelegramUsernameResponse(BaseModel):
    message: str
    expires_in: int  # seconds
