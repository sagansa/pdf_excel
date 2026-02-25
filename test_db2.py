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
        print("DB ERROR:", error)
        return
    with engine.connect() as conn:
        res = conn.execute(text("SHOW TABLES"))
        tables = [r[0] for r in res]
        print("TABLES:", tables)
        for t in tables:
            print(f"-- {t} --")
            cols = conn.execute(text(f"SHOW COLUMNS FROM {t}"))
            for c in cols:
                print(c[0], c[1])

if __name__ == "__main__":
    test()
