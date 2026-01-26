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
    
    # Parser configuration
    parser_type: str = "GEMINI"  # GEMINI or LOCAL
    
    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    # Image storage (for future use)
    image_storage_path: str = "./storage/images"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
