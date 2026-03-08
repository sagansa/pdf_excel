#!/usr/bin/env python3
"""
Simple test untuk basic server functionality
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

def test_basic_functionality():
    print("=== TESTING BASIC FUNCTIONALITY ===")
    
    try:
        # Test basic imports
        print("1. Testing imports...")
        import flask
        print(f"   Flask: {flask.__version__}")
        
        from sqlalchemy import create_engine, text
        print("   SQLAlchemy: ✅")
        
        # Test database connection
        print("\\n2. Testing database connection...")
        engine = create_engine("mysql+pymysql://root:root@127.0.0.1:3306/bank_converter")
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 'DB Connection OK' as test")).fetchone()
            print(f"   Database: {result.test}")
            
            # Test basic query
            print("\\n3. Testing basic query...")
            result = conn.execute(text("SELECT COUNT(*) as count FROM transactions")).fetchone()
            print(f"   Total Transactions: {result.count}")
            
            # Test 2026 query
            print("\\n4. Testing 2026 query...")
            result = conn.execute(text("SELECT COUNT(*) as count FROM transactions WHERE txn_date LIKE '2026%'")).fetchone()
            print(f"   2026 Transactions: {result.count}")
            
            # Test simple Flask app
            print("\\n5. Testing Flask app...")
            from flask import Flask, jsonify
            
            app = Flask(__name__)
            
            @app.route('/test')
            def test():
                return jsonify({'status': 'ok', 'message': 'Test endpoint working'})
            
            @app.route('/test-db')
            def test_db():
                try:
                    with engine.connect() as conn:
                        result = conn.execute(text("SELECT COUNT(*) as count FROM transactions")).fetchone()
                        return jsonify({'status': 'ok', 'count': result.count})
                except Exception as e:
                    return jsonify({'status': 'error', 'message': str(e)}), 500
            
            print("   Flask app created successfully")
            print("   Starting Flask app on http://127.0.0.1:5003...")
            
            app.run(host='0.0.0.0', port=5003, debug=False)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_basic_functionality()
