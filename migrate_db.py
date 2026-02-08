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

                # --- Users table: hybrid auth columns ---
                for col, col_type in [
                    ("telegram_username", "VARCHAR"),
                    ("password_hash", "VARCHAR"),
                    ("phone", "VARCHAR"),
                ]:
                    result = conn.execute(text("""
                        SELECT column_name FROM information_schema.columns
                        WHERE table_name='users' AND column_name=%s
                    """ % ("'" + col + "'",)))
                    if result.fetchone() is None:
                        logger.info("Adding users.%s column...", col)
                        conn.execute(text("ALTER TABLE users ADD COLUMN " + col + " " + col_type))
                        logger.info("Added users.%s", col)

                # Make telegram_id nullable
                try:
                    conn.execute(text("ALTER TABLE users ALTER COLUMN telegram_id DROP NOT NULL"))
                    logger.info("Made users.telegram_id nullable")
                except Exception:
                    pass  # might already be nullable

                # --- Categories: category_type and parent_id ---
                result = conn.execute(text("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name='categories' AND column_name='category_type'
                """))
                if result.fetchone() is None:
                    logger.info("Adding categories.category_type column...")
                    conn.execute(text("ALTER TABLE categories ADD COLUMN category_type VARCHAR(20) DEFAULT 'EXPENSE'"))
                    conn.execute(text("UPDATE categories SET category_type = 'EXPENSE' WHERE category_type IS NULL"))
                    conn.execute(text("ALTER TABLE categories ALTER COLUMN category_type SET NOT NULL"))
                    logger.info("Added categories.category_type")
                result = conn.execute(text("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name='categories' AND column_name='parent_id'
                """))
                if result.fetchone() is None:
                    logger.info("Adding categories.parent_id column...")
                    conn.execute(text("ALTER TABLE categories ADD COLUMN parent_id INTEGER REFERENCES categories(id)"))
                    logger.info("Added categories.parent_id")

                # --- Users: expense_sub_category_enabled ---
                result = conn.execute(text("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name='users' AND column_name='expense_sub_category_enabled'
                """))
                if result.fetchone() is None:
                    logger.info("Adding users.expense_sub_category_enabled column...")
                    conn.execute(text("ALTER TABLE users ADD COLUMN expense_sub_category_enabled BOOLEAN DEFAULT FALSE"))
                    logger.info("Added users.expense_sub_category_enabled")

                # Create one_time_login_tokens table if not exists (via create_all in init_db handles it; ensure table exists)
                result = conn.execute(text("""
                    SELECT table_name FROM information_schema.tables
                    WHERE table_name='one_time_login_tokens'
                """))
                if result.fetchone() is None:
                    logger.info("Creating one_time_login_tokens table...")
                    conn.execute(text("""
                        CREATE TABLE one_time_login_tokens (
                            id SERIAL PRIMARY KEY,
                            token VARCHAR UNIQUE NOT NULL,
                            code VARCHAR,
                            user_id INTEGER NOT NULL REFERENCES users(id),
                            expires_at TIMESTAMP NOT NULL
                        )
                    """))
                    conn.execute(text("CREATE INDEX ix_one_time_login_tokens_token ON one_time_login_tokens(token)"))
                    conn.execute(text("CREATE INDEX ix_one_time_login_tokens_user_id ON one_time_login_tokens(user_id)"))
                    logger.info("Created one_time_login_tokens table")
                
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
