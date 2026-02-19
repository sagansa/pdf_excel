import sys
sys.path.insert(0, '.')

from sqlalchemy import create_engine, text
from datetime import datetime
from backend.services.report_service import fetch_income_statement_data

# Database connection
DB_URL = "mysql+pymysql://root:root@127.0.0.1:3306/bank_converter"
engine = create_engine(DB_URL)

try:
    with engine.connect() as conn:
        # Test with 2025 data
        start_date = "2025-01-01"
        end_date = "2025-12-31"
        company_id = None

        print("Testing income statement data with amortization fix...")
        data = fetch_income_statement_data(conn, start_date, end_date, company_id)

        # Check if 5314 is in expenses
        amort_5314 = [e for e in data['expenses'] if e['code'] == '5314']
        if amort_5314:
            amort_value = amort_5314[0]['amount']
            print(f"\n5314 Amortisasi Aktiva Berwujud found:")
            print(f"Amount: Rp {amort_value:,.2f}")
            print(f"Expected: Rp 56,094,288.00")

            if abs(amort_value - 56094288) < 1000:
                print("\n✅ PASS: Amortization amount is correct!")
            else:
                print(f"\n❌ FAIL: Amortization amount is incorrect. Difference: {abs(amort_value - 56094288):,.2f}")
        else:
            print("\n❌ FAIL: No 5314 amortization found in expenses")

        print(f"\nTotal Expenses: Rp {data['total_expenses']:,.2f}")
        print(f"Net Income: Rp {data['net_income']:,.2f}")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
