import os
import sys
from sqlalchemy import create_engine, text

# Add current directory to path
sys.path.append(os.getcwd())

from server import get_db_engine

def debug_inventory():
    engine, error_msg = get_db_engine()
    if not engine:
        print(f"Error: {error_msg}")
        return

    with engine.connect() as conn:
        print("--- COA 1200 Details ---")
        coa_res = conn.execute(text("SELECT id, code, name, category, is_active FROM chart_of_accounts WHERE code = '1200'"))
        coa_row = coa_res.fetchone()
        if coa_row:
            coa_id = coa_row[0]
            print(f"ID: {coa_row[0]}, Code: {coa_row[1]}, Name: {coa_row[2]}, Category: {coa_row[3]}, Active: {coa_row[4]}")
        else:
            coa_id = None
            print("COA 1200 not found in chart_of_accounts table")

        print("\n--- Inventory Balances ---")
        inv_res = conn.execute(text("SELECT year, company_id, ending_inventory_amount FROM inventory_balances WHERE ending_inventory_amount > 0"))
        inv_rows = inv_res.fetchall()
        for row in inv_rows:
            print(f"Year: {row[0]}, Company: {row[1]}, Amount: {row[2]}")

        if coa_id:
            print("\n--- Marks mapped to COA 1200 ---")
            map_res = conn.execute(text("""
                SELECT m.id, m.personal_use 
                FROM mark_coa_mapping mcm
                JOIN marks m ON mcm.mark_id = m.id
                WHERE mcm.coa_id = :coa_id
            """), {"coa_id": coa_id})
            map_rows = map_res.fetchall()
            for row in map_rows:
                print(f"ID: {row[0]}, Mark: {row[1]}")

if __name__ == "__main__":
    debug_inventory()
