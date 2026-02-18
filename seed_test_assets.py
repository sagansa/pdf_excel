
import os
import sqlalchemy
from sqlalchemy import create_engine, text
from datetime import datetime

DB_USER = os.environ.get('DB_USER', 'root')
DB_PASS = os.environ.get('DB_PASS', 'root')
DB_HOST = os.environ.get('DB_HOST', '127.0.0.1')
DB_PORT = os.environ.get('DB_PORT', '3306')
DB_NAME = os.environ.get('DB_NAME', 'bank_converter')

DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DB_URL)

try:
    with engine.connect() as conn:
        # 1. Get a valid asset group
        group_res = conn.execute(text("SELECT id, group_name FROM amortization_asset_groups LIMIT 1"))
        group = group_res.fetchone()
        if not group:
            print("No asset groups found. Cannot insert test assets.")
            exit(1)
            
        group_id = group[0]
        company_id = '8ab69d4a-e591-4f05-909e-25ff12352efb' # PT Asa Pangan Bangsa
        
        print(f"Using Group: {group[1]} ({group_id})")
        
        # 2. Insert a full year asset (acquired Jan 2024)
        conn.execute(text("""
            INSERT INTO amortization_assets 
            (id, company_id, asset_name, asset_group_id, acquisition_cost, residual_value, acquisition_date, amortization_start_date, is_active)
            VALUES 
            ('test-asset-full', :company, 'Test Asset Full Year', :group, 120000000, 0, '2024-01-15', '2024-01-15', 1)
        """), {'company': company_id, 'group': group_id})
        
        # 3. Insert a partial year asset (acquired July 2025) - Should be 6/12
        conn.execute(text("""
            INSERT INTO amortization_assets 
            (id, company_id, asset_name, asset_group_id, acquisition_cost, residual_value, acquisition_date, amortization_start_date, is_active)
            VALUES 
            ('test-asset-partial', :company, 'Test Asset Partial Year', :group, 240000000, 0, '2025-07-20', '2025-07-20', 1)
        """), {'company': company_id, 'group': group_id})
        
        conn.commit()
        print("Test assets inserted successfully.")
except Exception as e:
    print(f"Error: {e}")
