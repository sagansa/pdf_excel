import sys
import os
sys.path.append('.')

from backend.db.session import get_db_engine
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

def migrate():
    engine, error = get_db_engine()
    if error:
        print("Database connection error:", error)
        return False
        
    try:
        with engine.begin() as conn:
            print("Adding batch_date to hpp_batches...")
            conn.execute(text("""
                ALTER TABLE hpp_batches ADD COLUMN IF NOT EXISTS batch_date DATE;
            """))

            print("Migration successful.")
            return True
            
    except Exception as e:
        print("Migration failed:", e)
        return False

if __name__ == '__main__':
    migrate()
