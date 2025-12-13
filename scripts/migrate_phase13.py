from utils.db import get_db
from sqlalchemy import text
from models import Base
import datetime

def migrate():
    print("Migrating Database Schema for Phase 13...")
    db = get_db()
    
    # 1. Create new table (PortfolioTransaction)
    # SQLAlchemy create_all does this check safely
    print("Creating new tables...")
    Base.metadata.create_all(db.engine)
    
    # 2. Add column to existing table (Portfolio)
    # create_all does NOT do this. We run ALTER TABLE safely.
    session = db.get_db_session()
    try:
        print("Checking/Updating Portfolio table...")
        # Check if purchase_date exists
        try:
            session.execute(text("SELECT purchase_date FROM portfolio LIMIT 1"))
        except Exception:
            print("Adding purchase_date column to portfolio table...")
            # SQLite syntax (since it's likely sqlite or similar generic requirement, but user said Windows/WSL so likely SQLite from previous context 'utils.db')
            # Assuming SQLite for simplicity or standard SQL (works in PG/MySQL too usually)
            session.execute(text("ALTER TABLE portfolio ADD COLUMN purchase_date DATE"))
            
            # Default existing to Today
            today = datetime.date.today().strftime('%Y-%m-%d')
            session.execute(text(f"UPDATE portfolio SET purchase_date = '{today}' WHERE purchase_date IS NULL"))
            session.commit()
            print("Column added and defaults set.")
            
    except Exception as e:
        print(f"Migration Error: {e}")
        session.rollback()
    finally:
        db.close_session()

if __name__ == "__main__":
    migrate()
