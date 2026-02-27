#!/usr/bin/env python3
"""
Test parameter issue: comparative vs comparatives
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from backend.services.report_service import fetch_income_statement_data
from sqlalchemy import create_engine

def test_parameter_issue():
    print("=== Testing Parameter Issue ===")
    
    engine = create_engine("mysql+pymysql://root:root@127.0.0.1:3306/bank_converter")
    
    with engine.connect() as conn:
        try:
            # Test tanpa parameter comparative (default false)
            print("1. Testing without comparative parameter...")
            data = fetch_income_statement_data(
                conn, '2025-01-01', '2025-12-31', None, report_type='real', comparative=False
            )
            print(f"   Success! Net Income: {data.get('net_income', 'N/A')}")
            
            # Test dengan comparative=True
            print("\n2. Testing with comparative=True...")
            data = fetch_income_statement_data(
                conn, '2025-01-01', '2025-12-31', None, report_type='real', comparative=True
            )
            print(f"   Success! Net Income: {data.get('net_income', 'N/A')}")
            
            # Test dengan tahun 2026 tanpa comparative
            print("\n3. Testing 2026 without comparative...")
            data = fetch_income_statement_data(
                conn, '2026-01-01', '2026-12-31', None, report_type='real', comparative=False
            )
            print(f"   Success! Net Income: {data.get('net_income', 'N/A')}")
            
            # Test dengan tahun 2026 dengan comparative=True
            print("\n4. Testing 2026 with comparative=True...")
            data = fetch_income_statement_data(
                conn, '2026-01-01', '2026-12-31', None, report_type='real', comparative=True
            )
            print(f"   Success! Net Income: {data.get('net_income', 'N/A')}")
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_parameter_issue()
