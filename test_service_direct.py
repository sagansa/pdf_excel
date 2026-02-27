#!/usr/bin/env python3
"""
Test service functions directly
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

def test_service_direct():
    print("=== TESTING SERVICE FUNCTIONS DIRECTLY ===")
    
    try:
        from sqlalchemy import create_engine
        from backend.services.report_service import fetch_income_statement_data
        from backend.services.report_service import fetch_balance_sheet_data
        from backend.services.report_service import fetch_monthly_revenue_data
        from backend.services.report_service import fetch_cash_flow_data
        
        engine = create_engine("mysql+pymysql://root:root@127.0.0.1:3306/bank_converter")
        
        with engine.connect() as conn:
            print("\\n1. Testing Income Statement 2026...")
            try:
                income_data = fetch_income_statement_data(
                    conn, '2026-01-01', '2026-12-31', None, report_type='real', comparative=True
                )
                print(f"   ✅ Income Statement 2026: Net Income = {income_data.get('net_income', 0.0):,.2f}")
            except Exception as e:
                print(f"   ❌ Income Statement 2026 Error: {e}")
                import traceback
                traceback.print_exc()
                
            print("\\n2. Testing Balance Sheet 2026...")
            try:
                balance_data = fetch_balance_sheet_data(
                    conn, '2026-12-31', None, report_type='real'
                )
                print(f"   ✅ Balance Sheet 2026: Is Balanced = {balance_data.get('is_balanced', False)}")
            except Exception as e:
                print(f"   ❌ Balance Sheet 2026 Error: {e}")
                import traceback
                traceback.print_exc()
                
            print("\\n3. Testing Monthly Revenue 2026...")
            try:
                monthly_data = fetch_monthly_revenue_data(
                    conn, 2026, None, report_type='real'
                )
                print(f"   ✅ Monthly Revenue 2026: Success")
            except Exception as e:
                print(f"   ❌ Monthly Revenue 2026 Error: {e}")
                import traceback
                traceback.print_exc()
                
            print("\\n4. Testing Cash Flow 2026...")
            try:
                cash_flow_data = fetch_cash_flow_data(
                    conn, '2026-01-01', '2026-12-31', None, report_type='real'
                )
                print(f"   ✅ Cash Flow 2026: Success")
            except Exception as e:
                print(f"   ❌ Cash Flow 2026 Error: {e}")
                import traceback
                traceback.print_exc()
                
            print("\\n5. Testing Company-Specific 2026...")
            try:
                company_id = '8ab69d4a-e591-4f05-909e-25ff12352efb'
                income_data = fetch_income_statement_data(
                    conn, '2026-01-01', '2026-12-31', company_id, report_type='real', comparative=True
                )
                print(f"   ✅ Company Income 2026: Net Income = {income_data.get('net_income', 0.0):,.2f}")
            except Exception as e:
                print(f"   ❌ Company Income 2026 Error: {e}")
                import traceback
                traceback.print_exc()
                
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_service_direct()
