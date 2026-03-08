import os
import sys
from sqlalchemy import create_engine, text

# Add current directory to path
sys.path.append(os.getcwd())

from server import get_db_engine

def find_coa_id():
    engine, error_msg = get_db_engine()
    if not engine:
        print(f"Error: {error_msg}")
        return

    with engine.connect() as conn:
        result = conn.execute(text("SELECT id FROM chart_of_accounts WHERE code = '1200'"))
        row = result.fetchone()
        if row:
            print(f"COA_ID_1200: {row[0]}")
        else:
            print("COA_ID_1200: NOT FOUND")

if __name__ == "__main__":
    find_coa_id()
