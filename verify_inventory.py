import os
import uuid
import sys
from sqlalchemy import create_engine, text
from decimal import Decimal

# Connection info
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASS = os.environ.get('DB_PASS', 'root')
DB_HOST = os.environ.get('DB_HOST', '127.0.0.1')
DB_PORT = os.environ.get('DB_PORT', '3306')
DB_NAME = os.environ.get('DB_NAME', 'bank_converter')

DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def verify():
    print("--- Verifying Inventory Balances DB Logic ---")
    try:
        engine = create_engine(DB_URL)
        with engine.begin() as conn:
            # 1. Get a company ID
            company_res = conn.execute(text("SELECT id FROM companies LIMIT 1")).fetchone()
            if not company_res:
                print("Error: No companies found in DB. Run seed first.")
                return
            company_id = company_res[0]
            year = 2025
            
            print(f"Using Company ID: {company_id} for Year: {year}")
            
            # 2. Test UPSERT
            balance_id = str(uuid.uuid4())
            conn.execute(
                text("""
                    INSERT INTO inventory_balances 
                        (id, company_id, year, beginning_inventory_amount, beginning_inventory_qty, 
                         ending_inventory_amount, ending_inventory_qty, is_manual) 
                    VALUES 
                        (:id, :company, :year, :beg_amt, :beg_qty, :end_amt, :end_qty, :is_manual)
                    ON DUPLICATE KEY UPDATE 
                        beginning_inventory_amount = VALUES(beginning_inventory_amount),
                        beginning_inventory_qty = VALUES(beginning_inventory_qty),
                        ending_inventory_amount = VALUES(ending_inventory_amount),
                        ending_inventory_qty = VALUES(ending_inventory_qty),
                        is_manual = VALUES(is_manual),
                        updated_at = NOW()
                """),
                {
                    'id': balance_id,
                    'company': company_id,
                    'year': year,
                    'beg_amt': 50000000.0,
                    'beg_qty': 100,
                    'end_amt': 30000000.0,
                    'end_qty': 60,
                    'is_manual': True
                }
            )
            print("Successfully inserted/updated inventory balance.")
            
            # 3. Verify retrieval
            row = conn.execute(
                text("SELECT * FROM inventory_balances WHERE year = :year AND company_id = :company"),
                {'year': year, 'company': company_id}
            ).fetchone()
            
            if row:
                print("Retrieved data matches:")
                print(f"  Beginning Amount: {row._mapping['beginning_inventory_amount']}")
                print(f"  Ending Amount: {row._mapping['ending_inventory_amount']}")
                if float(row._mapping['beginning_inventory_amount']) == 50000000.0:
                    print("✅ Backend Verification Passed!")
                else:
                    print("❌ Data mismatch!")
            else:
                print("❌ Failed to retrieve balance!")
                
    except Exception as e:
        print(f"Error during verification: {e}")

if __name__ == "__main__":
    verify()
