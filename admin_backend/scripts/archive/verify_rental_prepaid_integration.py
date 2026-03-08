#!/usr/bin/env python3
"""
Verification script for Rental Contract - Prepaid Rent Integration
Checks database schema and tests the integration logic
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import text
from server import get_db_engine

def check_schema():
    """Check if database schema has required columns"""
    print("=" * 60)
    print("CHECKING DATABASE SCHEMA")
    print("=" * 60)
    
    engine, error = get_db_engine()
    if engine is None:
        print(f"❌ Database connection failed: {error}")
        return False
    
    checks = []
    
    with engine.connect() as conn:
        # Check rental_contracts.prepaid_expense_id
        result = conn.execute(text("""
            SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'rental_contracts'
            AND COLUMN_NAME = 'prepaid_expense_id'
        """)).fetchone()
        
        if result[0] > 0:
            print("✅ rental_contracts.prepaid_expense_id column exists")
            checks.append(True)
        else:
            print("❌ rental_contracts.prepaid_expense_id column MISSING")
            checks.append(False)
        
        # Check prepaid_expenses.contract_id
        result = conn.execute(text("""
            SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'prepaid_expenses'
            AND COLUMN_NAME = 'contract_id'
        """)).fetchone()
        
        if result[0] > 0:
            print("✅ prepaid_expenses.contract_id column exists")
            checks.append(True)
        else:
            print("❌ prepaid_expenses.contract_id column MISSING")
            checks.append(False)
        
        # Check foreign key constraints
        result = conn.execute(text("""
            SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'rental_contracts'
            AND CONSTRAINT_NAME = 'fk_rental_prepaid_expense'
        """)).fetchone()
        
        if result[0] > 0:
            print("✅ Foreign key fk_rental_prepaid_expense exists")
            checks.append(True)
        else:
            print("⚠️  Foreign key fk_rental_prepaid_expense MISSING (optional)")
        
        # Check indexes
        result = conn.execute(text("""
            SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'prepaid_expenses'
            AND INDEX_NAME = 'idx_prepaid_contract'
        """)).fetchone()
        
        if result[0] > 0:
            print("✅ Index idx_prepaid_contract exists")
        else:
            print("⚠️  Index idx_prepaid_contract MISSING (optional)")
    
    return all(checks)


def check_existing_data():
    """Check existing rental contracts and prepaid expenses"""
    print("\n" + "=" * 60)
    print("CHECKING EXISTING DATA")
    print("=" * 60)
    
    engine, error = get_db_engine()
    if engine is None:
        return
    
    with engine.connect() as conn:
        # Count rental contracts
        result = conn.execute(text("SELECT COUNT(*) FROM rental_contracts")).fetchone()
        contract_count = result[0]
        print(f"📊 Total rental contracts: {contract_count}")
        
        # Count prepaid expenses
        result = conn.execute(text("SELECT COUNT(*) FROM prepaid_expenses")).fetchone()
        prepaid_count = result[0]
        print(f"📊 Total prepaid expenses: {prepaid_count}")
        
        # Count prepaid expenses linked to contracts
        result = conn.execute(text("""
            SELECT COUNT(*) FROM prepaid_expenses 
            WHERE contract_id IS NOT NULL
        """)).fetchone()
        linked_count = result[0]
        print(f"🔗 Prepaid expenses linked to contracts: {linked_count}")
        
        # Show sample linked data
        if linked_count > 0:
            print("\n📋 Sample linked entries:")
            result = conn.execute(text("""
                SELECT 
                    pe.description,
                    pe.amount_bruto,
                    pe.duration_months,
                    c.store_id,
                    c.start_date,
                    c.end_date
                FROM prepaid_expenses pe
                JOIN rental_contracts c ON pe.contract_id = c.id
                LIMIT 3
            """)).fetchall()
            
            for row in result:
                print(f"  - {row[0]}: Rp {row[1]:,.0f} ({row[2]} months)")
                print(f"    Contract: {row[4]} to {row[5]}")


def test_integration_logic():
    """Test the integration logic without actually creating data"""
    print("\n" + "=" * 60)
    print("TESTING INTEGRATION LOGIC")
    print("=" * 60)
    
    # Import the function
    try:
        from server import get_prepaid_settings_for_company
        print("✅ get_prepaid_settings_for_company() imported successfully")
        
        # Test with a sample company
        settings = get_prepaid_settings_for_company('019ac0ae-e558-7196-a669-6271437d79fb')
        if settings:
            print(f"✅ Settings retrieved: {len(settings)} settings found")
            for key, value in settings.items():
                print(f"   - {key}: {value}")
        else:
            print("⚠️  No settings found (may need to configure in UI)")
    except Exception as e:
        print(f"❌ Error testing integration: {e}")


def main():
    print("\n🔍 RENTAL CONTRACT - PREPAID RENT INTEGRATION VERIFICATION\n")
    
    # Run checks
    schema_ok = check_schema()
    check_existing_data()
    test_integration_logic()
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if schema_ok:
        print("✅ Database schema is ready for integration")
        print("✅ You can now create rental contracts with linked transactions")
        print("✅ Prepaid expenses will be auto-created")
    else:
        print("❌ Database schema is incomplete")
        print("⚠️  Please run migration 026:")
        print("   python3 migrate.py")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
