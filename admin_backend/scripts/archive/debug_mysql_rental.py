#!/usr/bin/env python3
"""
Debug rental contract creation directly with MySQL
"""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import uuid
import json

load_dotenv()

DB_USER = os.environ.get('DB_USER', 'root')
DB_PASS = os.environ.get('DB_PASS', 'root')
DB_HOST = os.environ.get('DB_HOST', '127.0.0.1')
DB_PORT = os.environ.get('DB_PORT', '3306')
DB_NAME = os.environ.get('DB_NAME', 'bank_converter')

DB_URL = f'mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

def debug_contract_creation():
    """Debug rental contract creation"""
    try:
        engine = create_engine(DB_URL)
        print(f"Connected to MySQL: {DB_HOST}:{DB_PORT}/{DB_NAME}")
        
        contract_data = {
            'company_id': 'demo-company',
            'store_id': 'store-1',
            'location_id': 'loc-1',
            'start_date': '2024-01-01',
            'end_date': '2024-12-31',
            'total_amount': 60000000,
            'status': 'active',
            'notes': 'Test rental contract with prepaid automation',
            'linked_transaction_ids': []  # Empty for now
        }
        
        with engine.begin() as conn:
            print("Creating rental contract...")
            
            # Check if required tables exist
            print("Checking tables...")
            tables = conn.execute(text("SHOW TABLES")).fetchall()
            table_names = [t[0] for t in tables]
            
            required_tables = ['rental_contracts', 'rental_stores', 'rental_locations', 'prepaid_expenses', 'amortization_settings']
            for table in required_tables:
                if table in table_names:
                    print(f"  ✓ {table} exists")
                else:
                    print(f"  ✗ {table} missing")
            
            # Check if demo company exists
            print("\\nChecking demo company...")
            result = conn.execute(text("SELECT id FROM companies WHERE id = :id"), {'id': 'demo-company'}).fetchone()
            if result:
                print(f"  ✓ Demo company exists: {result[0]}")
            else:
                print(f"  ✗ Demo company not found")
            
            # Check if store exists
            print("\\nChecking store...")
            result = conn.execute(text("SELECT id FROM rental_stores WHERE id = :id"), {'id': 'store-1'}).fetchone()
            if result:
                print(f"  ✓ Store exists: {result[0]}")
            else:
                print(f"  ✗ Store 'store-1' not found")
                # Show available stores
                stores = conn.execute(text("SELECT id, store_name FROM rental_stores")).fetchall()
                print(f"  Available stores: {stores}")
            
            # Check if location exists
            print("\\nChecking location...")
            result = conn.execute(text("SELECT id FROM rental_locations WHERE id = :id"), {'id': 'loc-1'}).fetchone()
            if result:
                print(f"  ✓ Location exists: {result[0]}")
            else:
                print(f"  ✗ Location 'loc-1' not found")
                # Show available locations
                locations = conn.execute(text("SELECT id, location_name FROM rental_locations")).fetchall()
                print(f"  Available locations: {locations}")
            
            # Try to create contract
            print("\\nAttempting to create contract...")
            contract_id = str(uuid.uuid4())
            
            conn.execute(text("""
                INSERT INTO rental_contracts
                (id, company_id, store_id, location_id, contract_number, landlord_name,
                 start_date, end_date, total_amount, status, notes)
                VALUES (:id, :company_id, :store_id, :location_id, :contract_number,
                        :landlord_name, :start_date, :end_date, :total_amount, :status, :notes)
            """), {
                'id': contract_id,
                'company_id': contract_data['company_id'],
                'store_id': contract_data['store_id'],
                'location_id': contract_data['location_id'],
                'contract_number': contract_data.get('contract_number'),
                'landlord_name': contract_data.get('landlord_name'),
                'start_date': contract_data['start_date'],
                'end_date': contract_data['end_date'],
                'total_amount': contract_data.get('total_amount'),
                'status': contract_data.get('status', 'active'),
                'notes': contract_data.get('notes')
            })
            
            print(f"  ✓ Contract created with ID: {contract_id}")
            
    except Exception as e:
        import traceback
        print(f"Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    debug_contract_creation()
