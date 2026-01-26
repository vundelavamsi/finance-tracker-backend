from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from app.config import settings

# Create SQLAlchemy engine
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # Verify connections before using
    pool_size=10,
    max_overflow=20,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency injection for FastAPI to get database session.
    Yields a database session and ensures it's closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database by creating all tables.
    Call this function on application startup.
    """
    # Import all models to ensure they're registered with Base.metadata
    from app.models import User, Transaction, Account, Category
    
    # Create all tables (this creates new tables but doesn't alter existing ones)
    Base.metadata.create_all(bind=engine)
    
    # Run migration to update existing tables
    try:
        import sys
        import os
        # Add parent directory to path to import migrate_db
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from migrate_db import migrate_database
        migrate_database()
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Migration failed (this is OK if tables are already up to date): {e}")
