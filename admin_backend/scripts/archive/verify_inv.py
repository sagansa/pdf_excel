import os
import sys
from sqlalchemy import create_engine, text
from datetime import datetime
from decimal import Decimal

# Add current directory to path
sys.path.append(os.getcwd())

from server import get_db_engine

def verify_inventory_ledger():
    engine, error_msg = get_db_engine()
    if not engine:
        print(f"Error: {error_msg}")
        return

    # COA ID for 1200
    coa_id = 'a587cc88-01c0-11f1-8067-7bf351bab14b'
    company_id = 'c1d2e3f4-5678-90ab-cdef-1234567890ab' # Standard test company? 
    # Let's find a real company id
    
    with engine.connect() as conn:
        comp_res = conn.execute(text("SELECT id FROM companies LIMIT 1"))
        comp_row = comp_res.fetchone()
        if not comp_row:
            print("No company found")
            return
        company_id = comp_row[0]
        
        # Mocking the context of the request
        # We'll just call the logic since we can't easily mock flask request here
        
        # Get COA info
        coa_result = conn.execute(text("SELECT * FROM chart_of_accounts WHERE id = :id"), {'id': coa_id})
        coa_row = coa_result.fetchone()
        if not coa_row:
            print("COA 1200 not found")
            return
        
        coa_info = dict(coa_row._mapping)
        print(f"Testing for COA: {coa_info['code']} - {coa_info['name']}")
        
        # Logic from get_coa_detail_report
        year = '2025'
        inv_query = text("""
            SELECT ending_inventory_amount, updated_at
            FROM inventory_balances
            WHERE year = :year
            AND (:company_id IS NULL OR company_id = :company_id)
        """)
        inv_res = conn.execute(inv_query, {'year': year, 'company_id': company_id})
        inv_row = inv_res.fetchone()
        
        if inv_row:
            print(f"Found inventory balance for 2025: {inv_row[0]}")
        else:
            print("No inventory balance found for 2025")

if __name__ == "__main__":
    verify_inventory_ledger()
