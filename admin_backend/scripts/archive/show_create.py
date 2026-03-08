import sys
import os
sys.path.append('.')

from backend.db.session import get_db_engine
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

def test():
    engine, error = get_db_engine()
    if error:
        print("Database connection error:", error)
        return
        
    try:
        with engine.connect() as conn:
            res = conn.execute(text("SHOW CREATE TABLE transactions"))
            for r in res:
                print(r[1])
    except Exception as e:
        print("Error:", e)

if __name__ == '__main__':
    test()
