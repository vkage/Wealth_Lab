import os
import sys
from sqlalchemy import text
from utils.db import get_db

def migrate_v2():
    print("Starting Migration V2: Multi-Portfolio...")
    db = get_db()
    session = db.get_db_session()
    
    try:
        # 1. Create Portfolios Table
        print("Creating 'portfolios' table...")
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS portfolios (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(50) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # 2. Insert Default Portfolio (if empty)
        print("Seeding default portfolio...")
        session.execute(text("""
            INSERT INTO portfolios (id, name)
            SELECT 1, 'Default Portfolio'
            WHERE NOT EXISTS (SELECT 1 FROM portfolios WHERE id = 1)
        """))
        
        # 3. Alter Portfolio Table
        # Check if column exists first? 
        # MySQL 8.0 doesn't support IF NOT EXISTS in ALTER COLUMN easily, so we just try/catch or assume it's needed if we are running this.
        # But for safety, we wrap in try/catch block for each step.
        
        print("Adding 'portfolio_id' column to 'portfolio'...")
        try:
             session.execute(text("""
                ALTER TABLE portfolio 
                ADD COLUMN portfolio_id INT NOT NULL DEFAULT 1 AFTER id
            """))
        except Exception as e:
            if "Duplicate column" in str(e):
                print("Column 'portfolio_id' already exists.")
            else:
                print(f"Notice: {e}")

        # 4. Add Foreign Key
        print("Adding FK constraint...")
        try:
            session.execute(text("""
                ALTER TABLE portfolio
                ADD CONSTRAINT fk_portfolio_id
                FOREIGN KEY (portfolio_id) REFERENCES portfolios(id)
            """))
        except Exception as e:
            print(f"Notice FK: {e}")

        # 5. Drop old Unique Index on ticker and Add new Compound Index
        print("Updating Indices...")
        try:
            # Check for existing index name. Usually 'ticker' or 'ticker_UNIQUE'
            # We try to drop index 'ticker'
            session.execute(text("DROP INDEX ticker ON portfolio"))
        except Exception as e:
            print(f"Notice Drop Index: {e}")
            
        try:
            session.execute(text("""
                CREATE UNIQUE INDEX uix_portfolio_ticker ON portfolio (portfolio_id, ticker)
            """))
        except Exception as e:
            print(f"Notice Create Index: {e}")
            
        session.commit()
        print("Migration V2 Complete Successfully.")
        
    except Exception as e:
        print(f"Migration Failed: {e}")
        session.rollback()
    finally:
        db.close_session()

if __name__ == "__main__":
    migrate_v2()
