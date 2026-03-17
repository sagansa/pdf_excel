#!/usr/bin/env python3
"""
Test script to verify split transaction fixes and coretax filtering.

Usage:
    python test_split_transactions.py
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / 'backend'
sys.path.insert(0, str(backend_path))

from sqlalchemy import text
from backend.db.session import get_db_engine
from backend.db.schema import get_table_columns
from backend.services.reporting.report_sql_fragments import (
    _split_parent_exclusion_clause,
    _coretax_filter_clause,
    _mark_coa_join_clause,
)


def test_split_exclusion_clause():
    """Test that split exclusion clause is generated correctly."""
    engine, _ = get_db_engine()
    if not engine:
        print("❌ Failed to connect to database")
        return False

    with engine.connect() as conn:
        clause = _split_parent_exclusion_clause(conn, 't')
        print(f"✓ Split exclusion clause:\n{clause}\n")
        
        # Check if parent_id column exists
        txn_columns = get_table_columns(conn, 'transactions')
        has_parent_id = 'parent_id' in txn_columns
        has_mark_id = 'mark_id' in txn_columns
        print(f"✓ Transactions table columns:")
        print(f"  - parent_id: {'✓' if has_parent_id else '✗'}")
        print(f"  - mark_id: {'✓' if has_mark_id else '✗'}\n")
        
    return True


def test_split_transactions_data():
    """Check actual split transactions in database."""
    engine, _ = get_db_engine()
    if not engine:
        print("❌ Failed to connect to database")
        return False

    with engine.connect() as conn:
        txn_columns = get_table_columns(conn, 'transactions')
        if 'parent_id' not in txn_columns:
            print("✗ parent_id column not found in transactions table")
            return
        
        # Check for transactions with parent_id
        result = conn.execute(text("""
            SELECT 
                YEAR(t.txn_date) as year,
                COUNT(*) as total_transactions,
                COUNT(CASE WHEN t.parent_id IS NOT NULL THEN 1 END) as child_transactions,
                COUNT(CASE WHEN t.parent_id IS NULL AND EXISTS (
                    SELECT 1 FROM transactions t2 WHERE t2.parent_id = t.id
                ) THEN 1 END) as parent_transactions
            FROM transactions t
            GROUP BY YEAR(t.txn_date)
            ORDER BY year DESC
        """))
        
        print("✓ Split transactions by year:")
        print(f"{'Year':<10} {'Total':<10} {'Children':<10} {'Parents':<10}")
        print("-" * 40)
        for row in result:
            year = row._mapping['year'] or 'NULL'
            total = row._mapping['total_transactions']
            children = row._mapping['child_transactions']
            parents = row._mapping['parent_transactions']
            print(f"{str(year):<10} {total:<10} {children:<10} {parents:<10}")
        print()
        
        # Check child transactions with mark_id
        result2 = conn.execute(text("""
            SELECT 
                YEAR(t.txn_date) as year,
                COUNT(*) as children_with_mark,
                SUM(t.amount) as total_amount
            FROM transactions t
            WHERE t.parent_id IS NOT NULL
              AND t.mark_id IS NOT NULL
            GROUP BY YEAR(t.txn_date)
            ORDER BY year DESC
            LIMIT 5
        """))
        
        print("✓ Child transactions with mark_id:")
        print(f"{'Year':<10} {'Count':<10} {'Total Amount':<15}")
        print("-" * 35)
        for row in result2:
            year = row._mapping['year'] or 'NULL'
            count = row._mapping['children_with_mark']
            amount = row._mapping['total_amount'] or 0
            print(f"{str(year):<10} {count:<10} {amount:,.0f}")
        print()
        
    return True


def test_coretax_mappings():
    """Check mark_coa_mapping table for coretax mappings."""
    engine, _ = get_db_engine()
    if not engine:
        print("❌ Failed to connect to database")
        return False

    with engine.connect() as conn:
        mapping_columns = get_table_columns(conn, 'mark_coa_mapping')
        has_report_type = 'report_type' in mapping_columns
        
        print(f"✓ mark_coa_mapping table:")
        print(f"  - report_type column: {'✓' if has_report_type else '✗'}\n")
        
        if has_report_type:
            result = conn.execute(text("""
                SELECT 
                    report_type,
                    COUNT(*) as count,
                    COUNT(DISTINCT mark_id) as unique_marks
                FROM mark_coa_mapping
                GROUP BY report_type
            """))
            
            print("✓ COA mappings by report_type:")
            print(f"{'Type':<15} {'Count':<10} {'Unique Marks':<15}")
            print("-" * 40)
            for row in result:
                rtype = row._mapping['report_type'] or 'NULL'
                count = row._mapping['count']
                marks = row._mapping['unique_marks']
                print(f"{str(rtype):<15} {count:<10} {marks:<15}")
            print()
        else:
            print("✗ report_type column not found - all mappings are used for both real and coretax\n")
        
        # Check for marks with both real and coretax mappings
        if has_report_type:
            result2 = conn.execute(text("""
                SELECT 
                    mark_id,
                    GROUP_CONCAT(DISTINCT report_type) as types,
                    COUNT(DISTINCT coa_id) as coa_count
                FROM mark_coa_mapping
                GROUP BY mark_id
                HAVING COUNT(DISTINCT report_type) > 1
                LIMIT 5
            """))
            
            print("✓ Sample marks with both real and coretax mappings:")
            for row in result2:
                mark_id = str(row._mapping['mark_id'])[:8]
                types = row._mapping['types']
                coa_count = row._mapping['coa_count']
                print(f"  Mark {mark_id}... - Types: {types}, COAs: {coa_count}")
            print()
            
    return True


def test_rent_expense_coa():
    """Check if rent expense COA (5315, 5105) exists and has transactions."""
    engine, _ = get_db_engine()
    if not engine:
        print("❌ Failed to connect to database")
        return False

    with engine.connect() as conn:
        # Check if COA exists
        result = conn.execute(text("""
            SELECT code, name, category, is_active
            FROM chart_of_accounts
            WHERE code IN ('5315', '5105')
            ORDER BY code
        """))
        
        print("✓ Rent expense COA:")
        for row in result:
            code = row._mapping['code']
            name = row._mapping['name']
            category = row._mapping['category']
            active = row._mapping['is_active']
            print(f"  {code}: {name} ({category}, Active: {active})")
        
        # Check transactions with these COAs
        result2 = conn.execute(text("""
            SELECT 
                YEAR(t.txn_date) as year,
                coa.code,
                COUNT(*) as transaction_count,
                SUM(t.amount) as total_amount
            FROM transactions t
            INNER JOIN marks m ON t.mark_id = m.id
            INNER JOIN mark_coa_mapping mcm ON m.id = mcm.mark_id
            INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
            WHERE coa.code IN ('5315', '5105')
            GROUP BY YEAR(t.txn_date), coa.code
            ORDER BY year DESC, coa.code
            LIMIT 10
        """))
        
        print("\n✓ Transactions with rent expense COA:")
        print(f"{'Year':<10} {'COA':<10} {'Count':<10} {'Amount':<15}")
        print("-" * 45)
        for row in result2:
            year = row._mapping['year'] or 'NULL'
            code = row._mapping['code']
            count = row._mapping['transaction_count']
            amount = row._mapping['total_amount'] or 0
            print(f"{str(year):<10} {code:<10} {count:<10} {amount:,.0f}")
        print()
        
    return True


def main():
    print("=" * 60)
    print("SPLIT TRANSACTION FIX - VERIFICATION TEST")
    print("=" * 60)
    print()
    
    tests = [
        ("Split Exclusion Clause", test_split_exclusion_clause),
        ("Split Transactions Data", test_split_transactions_data),
        ("CoreTax Mappings", test_coretax_mappings),
        ("Rent Expense COA", test_rent_expense_coa),
    ]
    
    for name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"TEST: {name}")
        print(f"{'='*60}")
        try:
            test_func()
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == '__main__':
    main()
