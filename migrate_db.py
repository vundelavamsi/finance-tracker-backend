"""
Database migration script to update transactions table schema.
This script adds category_id and account_id columns and removes the old category column.
"""
from sqlalchemy import text
from app.database import engine
import logging

logger = logging.getLogger(__name__)


def migrate_database():
    """
    Migrate the database schema to match the new models.
    - Adds category_id and account_id columns to transactions table
    - Drops the old category column
    """
    try:
        with engine.connect() as conn:
            # Start a transaction
            trans = conn.begin()
            
            try:
                # First, ensure categories and accounts tables exist
                # (They should be created by Base.metadata.create_all first)
                
                # Check if category_id column exists
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='transactions' AND column_name='category_id'
                """))
                
                if result.fetchone() is None:
                    logger.info("Adding category_id column to transactions table...")
                    # Add category_id column (nullable first, then we can add FK constraint)
                    conn.execute(text("""
                        ALTER TABLE transactions 
                        ADD COLUMN category_id INTEGER
                    """))
                    # Add foreign key constraint if categories table exists
                    try:
                        conn.execute(text("""
                            ALTER TABLE transactions 
                            ADD CONSTRAINT fk_transactions_category 
                            FOREIGN KEY (category_id) REFERENCES categories(id)
                        """))
                    except Exception:
                        # Constraint might already exist or table doesn't exist yet
                        pass
                    logger.info("Added category_id column")
                else:
                    logger.info("category_id column already exists")
                
                # Check if account_id column exists
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='transactions' AND column_name='account_id'
                """))
                
                if result.fetchone() is None:
                    logger.info("Adding account_id column to transactions table...")
                    # Add account_id column
                    conn.execute(text("""
                        ALTER TABLE transactions 
                        ADD COLUMN account_id INTEGER
                    """))
                    # Add foreign key constraint if accounts table exists
                    try:
                        conn.execute(text("""
                            ALTER TABLE transactions 
                            ADD CONSTRAINT fk_transactions_account 
                            FOREIGN KEY (account_id) REFERENCES accounts(id)
                        """))
                    except Exception:
                        # Constraint might already exist or table doesn't exist yet
                        pass
                    logger.info("Added account_id column")
                else:
                    logger.info("account_id column already exists")
                
                # Check if old category column exists and drop it
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='transactions' AND column_name='category'
                """))
                
                if result.fetchone() is not None:
                    logger.info("Dropping old category column from transactions table...")
                    # Drop the old category column
                    conn.execute(text("ALTER TABLE transactions DROP COLUMN IF EXISTS category"))
                    logger.info("Dropped old category column")
                else:
                    logger.info("Old category column does not exist")
                
                # Commit the transaction
                trans.commit()
                logger.info("Database migration completed successfully")
                
            except Exception as e:
                trans.rollback()
                logger.error(f"Error during migration: {e}")
                raise
                
    except Exception as e:
        logger.error(f"Failed to migrate database: {e}")
        raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    migrate_database()
