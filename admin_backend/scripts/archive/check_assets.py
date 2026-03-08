
import os
import sqlalchemy
from sqlalchemy import create_engine, text

DB_USER = os.environ.get('DB_USER', 'root')
DB_PASS = os.environ.get('DB_PASS', 'root')
DB_HOST = os.environ.get('DB_HOST', '127.0.0.1')
DB_PORT = os.environ.get('DB_PORT', '3306')
DB_NAME = os.environ.get('DB_NAME', 'bank_converter')

DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DB_URL)

try:
    with engine.connect() as conn:
        print("--- Companies with Assets ---")
        query = text("""
            SELECT c.name, a.company_id, COUNT(*) 
            FROM amortization_assets a
            JOIN companies c ON a.company_id = c.id
            GROUP BY a.company_id
        """)
        result = conn.execute(query)
        for row in result:
            print(f"Company: {row[0]}, ID: {row[1]}, Asset Count: {row[2]}")
            
        print("\n--- Recent Assets ---")
        query = text("""
            SELECT asset_name, acquisition_date, amortization_start_date, company_id
            FROM amortization_assets
            LIMIT 5
        """)
        result = conn.execute(query)
        for row in result:
            print(row)
except Exception as e:
    print(f"Error: {e}")
