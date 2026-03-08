#!/usr/bin/env python3
"""
Test exact API call yang menyebabkan error 500
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

def test_exact_api_call():
    print("=== Testing Exact API Call ===")
    
    try:
        from flask import Flask, request
        from backend.services.report_service import fetch_income_statement_data
        from sqlalchemy import create_engine
        
        app = Flask(__name__)
        
        engine = create_engine("mysql+pymysql://root:root@127.0.0.1:3306/bank_converter")
        
        # Simulate exact API call parameters
        with app.test_request_context('/api/reports/income-statement?start_date=2026-01-01&end_date=2026-12-31&report_type=real&comparative=true'):
            # Extract parameters exactly like API does
            start_date = request.args.get('start_date') or '2026-01-01'
            end_date = request.args.get('end_date') or '2026-12-31'
            company_id = request.args.get('company_id')
            report_type = request.args.get('report_type', 'real')
            comparative = request.args.get('comparative', 'false').lower() == 'true'  # Note: typo 'comparative'
            
            print(f"Parameters:")
            print(f"  start_date: {start_date}")
            print(f"  end_date: {end_date}")
            print(f"  company_id: {company_id}")
            print(f"  report_type: {report_type}")
            print(f"  comparative: {comparative}")
            
            with engine.connect() as conn:
                try:
                    print("\nCalling fetch_income_statement_data...")
                    data = fetch_income_statement_data(conn, start_date, end_date, company_id, report_type, comparative=comparative)
                    print(f"Success! Net Income: {data.get('net_income', 'N/A')}")
                    
                    # Try to jsonify the result
                    import json
                    json_str = json.dumps(data, default=str)
                    print(f"JSON serialization successful! Length: {len(json_str)}")
                    
                except Exception as e:
                    print(f"Error in fetch_income_statement_data: {e}")
                    import traceback
                    traceback.print_exc()
                    
                    # Try to jsonify error result
                    try:
                        error_data = {'error': str(e)}
                        import json
                        json_str = json.dumps(error_data)
                        print(f"Error JSON serialization successful! Length: {len(json_str)}")
                    except Exception as json_e:
                        print(f"Error JSON serialization failed: {json_e}")
                
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_exact_api_call()
