#!/usr/bin/env python3
"""
Debug script untuk menemukan penyebab crash tahun 2026
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

def debug_2026_crash():
    print("=== DEBUG 2026 SERVER CRASH ===")
    
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
                print(f"   ✅ Income Statement 2026 Success: Net Income = {income_data.get('net_income', 'N/A')}")
            except Exception as e:
                print(f"   ❌ Income Statement 2026 Error: {e}")
                import traceback
                traceback.print_exc()
                
            print("\\n2. Testing Balance Sheet 2026...")
            try:
                balance_data = fetch_balance_sheet_data(
                    conn, '2026-12-31', None, report_type='real'
                )
                print(f"   ✅ Balance Sheet 2026 Success: Is Balanced = {balance_data.get('is_balanced', 'N/A')}")
            except Exception as e:
                print(f"   ❌ Balance Sheet 2026 Error: {e}")
                import traceback
                traceback.print_exc()
                
            print("\\n3. Testing Monthly Revenue 2026...")
            try:
                monthly_data = fetch_monthly_revenue_data(
                    conn, 2026, None, report_type='real'
                )
                print(f"   ✅ Monthly Revenue 2026 Success")
            except Exception as e:
                print(f"   ❌ Monthly Revenue 2026 Error: {e}")
                import traceback
                traceback.print_exc()
                
            print("\\n4. Testing Cash Flow 2026...")
            try:
                cash_flow_data = fetch_cash_flow_data(
                    conn, '2026-01-01', '2026-12-31', None, report_type='real'
                )
                print(f"   ✅ Cash Flow 2026 Success")
            except Exception as e:
                print(f"   ❌ Cash Flow 2026 Error: {e}")
                import traceback
                traceback.print_exc()
                
            print("\\n5. Testing Simple Database Query 2026...")
            try:
                from sqlalchemy import text
                query = text("""
                    SELECT COUNT(*) as count, MIN(txn_date) as min_date, MAX(txn_date) as max_date
                    FROM transactions t
                    WHERE t.txn_date BETWEEN '2026-01-01' AND '2026-12-31'
                """)
                result = conn.execute(query).fetchone()
                print(f"   ✅ Simple Query 2026 Success: {result.count} transactions")
            except Exception as e:
                print(f"   ❌ Simple Query 2026 Error: {e}")
                import traceback
                traceback.print_exc()
                
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()

def test_minimal_server():
    print("\\n=== TESTING MINIMAL SERVER ===")
    
    try:
        from flask import Flask, jsonify
        from backend.services.report_service import fetch_income_statement_data
        from sqlalchemy import create_engine
        
        app = Flask(__name__)
        
        @app.route('/test-2026')
        def test_2026():
            try:
                engine = create_engine("mysql+pymysql://root:root@127.0.0.1:3306/bank_converter")
                with engine.connect() as conn:
                    data = fetch_income_statement_data(
                        conn, '2026-01-01', '2026-12-31', None, report_type='real', comparative=True
                    )
                    return jsonify({
                        'status': 'success',
                        'net_income': data.get('net_income', 0.0),
                        'revenue': data.get('total_revenue', 0.0),
                        'expenses': data.get('total_expenses', 0.0)
                    })
            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'message': str(e),
                    'traceback': str(e.__traceback__) if hasattr(e, '__traceback__') else None
                }), 500
        
        @app.route('/health')
        def health():
            return jsonify({'status': 'ok'})
        
        print("Starting minimal test server on http://127.0.0.1:5002...")
        app.run(host='0.0.0.0', port=5002, debug=True)
        
    except Exception as e:
        print(f"Minimal server error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_2026_crash()
    # test_minimal_server()
