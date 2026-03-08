#!/usr/bin/env python3
"""
Test script untuk debug API error 500 pada tahun 2026
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

def test_api_endpoints():
    print("=== Testing API Endpoints with Flask App ===")
    
    try:
        from flask import Flask
        from backend.services.report_service import fetch_income_statement_data
        from backend.services.report_service import fetch_balance_sheet_data
        from backend.services.report_service import fetch_cash_flow_data
        from backend.services.report_service import fetch_monthly_revenue_data
        from sqlalchemy import create_engine
        
        app = Flask(__name__)
        
        engine = create_engine("mysql+pymysql://root:root@127.0.0.1:3306/bank_converter")
        
        with app.app_context():
            with engine.connect() as conn:
                print("Testing with Flask app context...")
                
                # Test 1: Income Statement 2026
                try:
                    print("\n1. Testing Income Statement 2026...")
                    result = fetch_income_statement_data(
                        conn, '2026-01-01', '2026-12-31', None, report_type='real', comparative=False
                    )
                    print(f"   ✅ Income Statement 2026: Net Income = {result.get('net_income', 'N/A')}")
                except Exception as e:
                    print(f"   ❌ Income Statement 2026 Error: {e}")
                    import traceback
                    traceback.print_exc()
                
                # Test 2: Balance Sheet 2026
                try:
                    print("\n2. Testing Balance Sheet 2026...")
                    result = fetch_balance_sheet_data(
                        conn, '2026-12-31', None, report_type='real'
                    )
                    print(f"   ✅ Balance Sheet 2026: Is Balanced = {result.get('is_balanced', 'N/A')}")
                except Exception as e:
                    print(f"   ❌ Balance Sheet 2026 Error: {e}")
                    import traceback
                    traceback.print_exc()
                
                # Test 3: Cash Flow 2026
                try:
                    print("\n3. Testing Cash Flow 2026...")
                    result = fetch_cash_flow_data(
                        conn, '2026-01-01', '2026-12-31', None, report_type='real'
                    )
                    print(f"   ✅ Cash Flow 2026: Success")
                except Exception as e:
                    print(f"   ❌ Cash Flow 2026 Error: {e}")
                    import traceback
                    traceback.print_exc()
                
                # Test 4: Monthly Revenue 2026
                try:
                    print("\n4. Testing Monthly Revenue 2026...")
                    result = fetch_monthly_revenue_data(
                        conn, 2026, None, report_type='real'
                    )
                    print(f"   ✅ Monthly Revenue 2026: Success")
                except Exception as e:
                    print(f"   ❌ Monthly Revenue 2026 Error: {e}")
                    import traceback
                    traceback.print_exc()
                
                # Test 5: Payroll Salary Summary 2026
                try:
                    print("\n5. Testing Payroll Salary Summary 2026...")
                    # Try to import this
                    from backend.services.payroll_service import fetch_payroll_salary_summary
                    result = fetch_payroll_salary_summary(
                        conn, '2026-01-01', '2026-12-31', None, report_type='real'
                    )
                    print(f"   ✅ Payroll Salary Summary 2026: Success")
                except Exception as e:
                    print(f"   ❌ Payroll Salary Summary 2026 Error: {e}")
                    import traceback
                    traceback.print_exc()
                    
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_api_endpoints()
