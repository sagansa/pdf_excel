#!/usr/bin/env python3
"""
Test script untuk debug error 500 pada tahun 2026
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from backend.services.report_service import fetch_income_statement_data
from sqlalchemy import create_engine, text

def test_income_statement_2026():
    print("=== Testing Income Statement 2026 ===")
    
    engine = create_engine("mysql+pymysql://root:root@127.0.0.1:3306/bank_converter")
    
    with engine.connect() as conn:
        try:
            # Test tahun 2026
            print("Testing 2026-01-01 to 2026-12-31...")
            income_data = fetch_income_statement_data(
                conn, '2026-01-01', '2026-12-31', None, report_type='real', comparative=False
            )
            
            print(f"Success! Revenue: {income_data.get('revenue', 'N/A')}")
            print(f"Expenses: {income_data.get('expenses', 'N/A')}")
            print(f"Net Income: {income_data.get('net_income', 'N/A')}")
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            
        try:
            # Test tahun 2025 untuk comparison
            print("\nTesting 2025-01-01 to 2025-12-31 (should work)...")
            income_data = fetch_income_statement_data(
                conn, '2025-01-01', '2025-12-31', None, report_type='real', comparative=False
            )
            
            print(f"Success! Revenue: {income_data.get('revenue', 'N/A')}")
            print(f"Expenses: {income_data.get('expenses', 'N/A')}")
            print(f"Net Income: {income_data.get('net_income', 'N/A')}")
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

def test_database_query_2026():
    print("\n=== Testing Raw Database Query 2026 ===")
    
    engine = create_engine("mysql+pymysql://root:root@127.0.0.1:3306/bank_converter")
    
    with engine.connect() as conn:
        try:
            # Check if transactions exist for 2026
            query = text("""
                SELECT COUNT(*) as count, MIN(txn_date) as min_date, MAX(txn_date) as max_date
                FROM transactions t
                WHERE t.txn_date BETWEEN '2026-01-01' AND '2026-12-31'
            """)
            
            result = conn.execute(query).fetchone()
            print(f"Transactions 2026: {result.count} rows")
            print(f"Date range: {result.min_date} to {result.max_date}")
            
        except Exception as e:
            print(f"Database Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_database_query_2026()
    test_income_statement_2026()
