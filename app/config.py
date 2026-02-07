from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database configuration
    database_url: str = "postgresql://user:password@localhost:5432/finance_tracker"
    
    # Telegram Bot configuration
    telegram_bot_token: str = ""
    telegram_api_url: str = "https://api.telegram.org/bot"
    
    # Gemini API configuration
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"  # Override if hitting quota (e.g. gemini-1.5-flash)
    
    # Parser configuration
    parser_type: str = "GEMINI"  # GEMINI or LOCAL
    
    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    # Image storage (for future use)
    image_storage_path: str = "./storage/images"
    
    # JWT configuration
    jwt_secret_key: str = "change-me-in-production-use-env"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours
    
    # Magic link (Telegram username login)
    magic_link_base_url: Optional[str] = None  # e.g. https://app.example.com/auth/verify
    magic_link_expire_minutes: int = 10
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
