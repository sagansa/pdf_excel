#!/usr/bin/env python3
"""
Migration script to restore location_id to rental_contracts table
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))

from backend.db.session import get_db_engine
from sqlalchemy import text

def migrate():
    """Restore location_id column and foreign key to rental_contracts table"""
    
    engine, error_msg = get_db_engine()
    if engine is None:
        print(f"Database connection error: {error_msg}")
        return False

    print("Starting migration: Restore location_id to rental_contracts...")
    
    try:
        with engine.begin() as conn:
            print("1. Checking current rental_contracts structure...")
            result = conn.execute(text("SHOW COLUMNS FROM rental_contracts")).fetchall()
            contract_columns = [row[0] for row in result]
            print(f"   Current columns: {contract_columns}")
            
            # Check if location_id exists
            has_location_id = 'location_id' in contract_columns
            has_location_name = 'location_name' in contract_columns
            
            print(f"   Has location_id: {has_location_id}")
            print(f"   Has location_name: {has_location_name}")
            
            if not has_location_id:
                print("2. Adding location_id column to rental_contracts...")
                conn.execute(text("ALTER TABLE rental_contracts ADD COLUMN location_id CHAR(36)"))
                print("   ✓ location_id column added")
            else:
                print("   ✓ location_id column already exists")
            
            if has_location_name:
                print("3. Removing location_name column from rental_contracts...")
                conn.execute(text("ALTER TABLE rental_contracts DROP COLUMN location_name"))
                print("   ✓ location_name column removed")
            
            print("4. Checking current rental_stores structure...")
            result = conn.execute(text("SHOW COLUMNS FROM rental_stores")).fetchall()
            store_columns = [row[0] for row in result]
            print(f"   Current rental_stores columns: {store_columns}")
            
            # Check if current_location_id exists in rental_stores
            has_current_location_id = 'current_location_id' in store_columns
            
            if not has_current_location_id:
                print("5. Adding current_location_id column to rental_stores...")
                conn.execute(text("ALTER TABLE rental_stores ADD COLUMN current_location_id CHAR(36)"))
                print("   ✓ current_location_id column added")
            else:
                print("   ✓ current_location_id column already exists")
            
            print("6. Verifying final structure...")
            result = conn.execute(text("SHOW COLUMNS FROM rental_contracts")).fetchall()
            contract_columns = [row[0] for row in result]
            print(f"   Final rental_contracts columns: {contract_columns}")
            
            result = conn.execute(text("SHOW COLUMNS FROM rental_stores")).fetchall()
            store_columns = [row[0] for row in result]
            print(f"   Final rental_stores columns: {store_columns}")
            
        print("\n✓ Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
