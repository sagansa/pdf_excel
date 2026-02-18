import os
import sys
from sqlalchemy import text
from datetime import datetime

# Add current directory to path
sys.path.append(os.getcwd())

from server import get_db_engine

def verify_1401():
    engine, _ = get_db_engine()
    with engine.connect() as conn:
        print("--- Checking COA 1401 ---")
        res = conn.execute(text("SELECT name FROM chart_of_accounts WHERE code = '1401'"))
        row = res.fetchone()
        if row:
            print(f"Name for 1401: {row[0]}")
        
        print("\n--- Checking Year 2025 Balances ---")
        inv_res = conn.execute(text("SELECT ending_inventory_amount FROM inventory_balances WHERE year = '2025'"))
        inv_row = inv_res.fetchone()
        if inv_row:
            print(f"Inventory Balance 2025: {inv_row[0]}")

if __name__ == "__main__":
    verify_1401()
