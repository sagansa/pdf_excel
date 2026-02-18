
from sqlalchemy import create_engine, text
import json

DB_USER = 'root'
DB_PASS = 'root'
DB_HOST = '127.0.0.1'
DB_PORT = '3306'
DB_NAME = 'bank_converter'

DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def main():
    engine = create_engine(DB_URL)
    try:
        with engine.connect() as conn:
            # 0. List all tables
            print("--- Available Tables ---")
            tables = conn.execute(text("SHOW TABLES")).fetchall()
            for t in tables:
                print(t[0])
            
            # 1. Check companies
            print("--- Companies ---")
            companies = conn.execute(text("SELECT id, name FROM companies")).fetchall()
            for c in companies:
                print(f"ID: {c[0]}, Name: {c[1]}")
            
            # 2. Check amortization adjustments for 2025
            print("\n--- Amortization Items (Manual) ---")
            items = conn.execute(text("SELECT * FROM amortization_items WHERE year = 2025")).fetchall()
            for item in items:
                print(item)
            
            # 3. Check settings
            print("\n--- Amortization Settings ---")
            settings = conn.execute(text("SELECT * FROM amortization_settings")).fetchall()
            for s in settings:
                print(s)
                
            # 4. Check transactions for COA 5314
            print("\n--- Transactions for COA 5314 (via marks) ---")
            query = text("""
                SELECT 
                    t.id, t.txn_date, t.description, t.amount, t.db_cr,
                    coa.code as coa_code, coa.name as coa_name
                FROM transactions t
                INNER JOIN marks m ON t.mark_id = m.id
                INNER JOIN mark_coa_mapping mcm ON m.id = mcm.mark_id
                INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
                WHERE YEAR(t.txn_date) = 2025 
                AND coa.code = '5314'
            """)
            txns = conn.execute(query).fetchall()
            for t in txns:
                print(t)
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
