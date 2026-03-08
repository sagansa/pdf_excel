#!/usr/bin/env python3
"""
Migration script to remove location dependency from rental_stores table
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))

from backend.db.session import get_db_engine
from sqlalchemy import text

def migrate():
    """Remove current_location_id from rental_stores and update rental_contracts"""
    
    engine, error_msg = get_db_engine()
    if engine is None:
        print(f"Database connection error: {error_msg}")
        return False

    print("Starting migration: Remove location from stores...")
    
    try:
        with engine.begin() as conn:
            print("1. Checking current rental_stores structure...")
            result = conn.execute(text("SHOW COLUMNS FROM rental_stores")).fetchall()
            columns = [row[0] for row in result]
            print(f"   Current columns: {columns}")
            
            # Check if current_location_id exists
            has_current_location_id = 'current_location_id' in columns
            print(f"   Has current_location_id: {has_current_location_id}")
            
            if has_current_location_id:
                print("2. Removing current_location_id column from rental_stores...")
                # Drop foreign key constraint first
                try:
                    conn.execute(text("ALTER TABLE rental_stores DROP FOREIGN KEY rental_stores_ibfk_2"))
                    print("   ✓ Foreign key constraint removed")
                except Exception as e:
                    print(f"   ⚠ Foreign key constraint may not exist: {e}")
                
                conn.execute(text("ALTER TABLE rental_stores DROP COLUMN current_location_id"))
                print("   ✓ current_location_id column removed")
            else:
                print("   ✓ current_location_id column already removed")
            
            print("3. Checking rental_contracts structure...")
            result = conn.execute(text("SHOW COLUMNS FROM rental_contracts")).fetchall()
            contract_columns = [row[0] for row in result]
            print(f"   Current columns: {contract_columns}")
            
            # Check if location_id exists in rental_contracts
            has_location_id = 'location_id' in contract_columns
            has_location_name = 'location_name' in contract_columns
            
            print(f"   Has location_id: {has_location_id}")
            print(f"   Has location_name: {has_location_name}")
            
            if has_location_id:
                print("4. Adding location_name column to rental_contracts...")
                if not has_location_name:
                    conn.execute(text("ALTER TABLE rental_contracts ADD COLUMN location_name VARCHAR(255)"))
                    print("   ✓ location_name column added")
                
                print("5. Migrating data from location_id to location_name...")
                conn.execute(text("""
                    UPDATE rental_contracts rc 
                    LEFT JOIN rental_locations rl ON rc.location_id = rl.id 
                    SET rc.location_name = rl.location_name 
                    WHERE rc.location_id IS NOT NULL
                """))
                print("   ✓ Data migrated from location_id to location_name")
                
                print("6. Removing location_id column from rental_contracts...")
                # Drop foreign key constraint first if it exists
                try:
                    conn.execute(text("ALTER TABLE rental_contracts DROP FOREIGN KEY rental_contracts_ibfk_3"))
                    print("   ✓ Foreign key constraint removed")
                except Exception as e:
                    print(f"   ⚠ Foreign key constraint may not exist: {e}")
                
                conn.execute(text("ALTER TABLE rental_contracts DROP COLUMN location_id"))
                print("   ✓ location_id column removed")
            elif has_location_name:
                print("   ✓ location_name column already exists")
            else:
                print("   Adding location_name column to rental_contracts...")
                conn.execute(text("ALTER TABLE rental_contracts ADD COLUMN location_name VARCHAR(255)"))
                print("   ✓ location_name column added")
            
            print("7. Verifying final structure...")
            result = conn.execute(text("SHOW COLUMNS FROM rental_stores")).fetchall()
            store_columns = [row[0] for row in result]
            print(f"   Final rental_stores columns: {store_columns}")
            
            result = conn.execute(text("SHOW COLUMNS FROM rental_contracts")).fetchall()
            contract_columns = [row[0] for row in result]
            print(f"   Final rental_contracts columns: {contract_columns}")
            
        print("\n✓ Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
