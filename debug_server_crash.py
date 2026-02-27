#!/usr/bin/env python3
"""
Debug script untuk menemukan penyebab server crash
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

def debug_specific_requests():
    print("=== DEBUGGING SPECIFIC REQUESTS ===")
    
    try:
        from flask import Flask, request, jsonify
        from backend.services.report_service import fetch_income_statement_data, fetch_balance_sheet_data
        from backend.db.session import get_db_engine
        from sqlalchemy import create_engine, text
        
        app = Flask(__name__)
        
        engine = create_engine("mysql+pymysql://root:root@127.0.0.1:3306/bank_converter")
        
        @app.route('/test-income-2026')
        def test_income_2026():
            try:
                print("Testing income statement 2026...")
                data = fetch_income_statement_data(
                    engine.connect(), '2026-01-01', '2026-12-31', None, report_type='real', comparative=True
                )
                return jsonify({'status': 'success', 'net_income': data.get('net_income', 0.0)})
            except Exception as e:
                print(f"Income Statement Error: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({'status': 'error', 'message': str(e), 'traceback': str(e.__traceback__)}), 500
        
        @app.route('/test-balance-2026')
        def test_balance_2026():
            try:
                print("Testing balance sheet 2026...")
                data = fetch_balance_sheet_data(
                    engine.connect(), '2026-12-31', None, report_type='real'
                )
                return jsonify({'status': 'success', 'is_balanced': data.get('is_balanced', False)})
            except Exception as e:
                print(f"Balance Sheet Error: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({'status': 'error', 'message': str(e), 'traceback': str(e.__traceback__)}), 500
        
        @app.route('/test-monthly-2026')
        def test_monthly_2026():
            try:
                print("Testing monthly revenue 2026...")
                data = fetch_monthly_revenue_data(
                    engine.connect(), 2026, None, report_type='real'
                )
                return jsonify({'status': 'success'})
            except Exception as e:
                print(f"Monthly Revenue Error: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({'status': 'error', 'message': str(e), 'traceback': str(e.__traceback__)}), 500
        
        @app.route('/test-cash-flow-2026')
        def test_cash_flow_2026():
            try:
                print("Testing cash flow 2026...")
                data = fetch_cash_flow_data(
                    engine.connect(), '2026-01-01', '2026-12-31', None, report_type='real'
                )
                return jsonify({'status': 'success'})
            except Exception as e:
                print(f"Cash Flow Error: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({'status': 'error', 'message': str(e), 'traceback': str(e.__traceback__)}), 500
        
        @app.route('/test-simple-db')
        def test_simple_db():
            try:
                print("Testing simple database connection...")
                with engine.connect() as conn:
                    result = conn.execute(text("SELECT COUNT(*) as count FROM transactions WHERE txn_date LIKE '2026%'")).fetchone()
                    return jsonify({'status': 'success', 'count': result.count})
            except Exception as e:
                print(f"Simple DB Error: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        print("Starting debug server on http://127.0.0.1:5002...")
        app.run(host='0.0.0.0', port=5002, debug=True)
        
    except Exception as e:
        print(f"Debug server error: {e}")
        import traceback
        traceback.print_exc()

def test_import_issues():
    print("=== TESTING IMPORT ISSUES ===")
    
    try:
        print("Testing imports...")
        from backend.server import app
        print("✅ Server import successful")
        
        from backend.services.report_service import fetch_income_statement_data
        print("✅ Report service import successful")
        
        from backend.db.session import get_db_engine
        print("✅ Database session import successful")
        
        from sqlalchemy import create_engine
        engine = create_engine("mysql+pymysql://root:root@127.0.0.1:3306/bank_converter")
        print("✅ Database engine creation successful")
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as test")).fetchone()
            print(f"✅ Database connection successful: {result.test}")
            
    except Exception as e:
        print(f"❌ Import Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # First test imports
    test_import_issues()
    
    print("\n" + "="*60)
    
    # Then test specific requests
    debug_specific_requests()
