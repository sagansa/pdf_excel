import sys
sys.path.insert(0, '.')

from sqlalchemy import create_engine, text
from backend.services.report_service import fetch_income_statement_data

# Database connection
DB_URL = "mysql+pymysql://root:root@127.0.0.1:3306/bank_converter"
engine = create_engine(DB_URL)

try:
    with engine.connect() as conn:
        # Test with specific company
        company_id = "8ab69d4a-e591-4f05-909e-25ff12352efb"
        start_date = "2025-01-01"
        end_date = "2025-12-31"

        print(f"Testing income statement for company: PT Asa Pangan Bangsa")
        print(f"Period: {start_date} to {end_date}")
        print("=" * 80)

        data = fetch_income_statement_data(conn, start_date, end_date, company_id)

        # Check if 5314 is in expenses
        amort_5314 = [e for e in data['expenses'] if e['code'] == '5314']
        if amort_5314:
            amort_value = amort_5314[0]['amount']
            print(f"\n5314 Amortisasi Aktiva Berwujud found:")
            print(f"Amount: Rp {amort_value:,.2f}")
            print(f"Expected (from amortization list): Rp ~55,914,986.17")

            if abs(amort_value - 55914986.17) < 10000:
                print("\n✅ PASS: Amortization amount is correct!")
            else:
                print(f"\n❌ FAIL: Amortization amount is incorrect. Difference: {abs(amort_value - 55914986.17):,.2f}")
        else:
            print("\n❌ FAIL: No 5314 amortization found in expenses")

        print(f"\nTotal Expenses: Rp {data['total_expenses']:,.2f}")
        print(f"Net Income: Rp {data['net_income']:,.2f}")

        # Test with company_id=None
        print("\n" + "=" * 80)
        print("Testing with company_id=None (all companies)")
        print("=" * 80)

        data_all = fetch_income_statement_data(conn, start_date, end_date, None)

        amort_5314_all = [e for e in data_all['expenses'] if e['code'] == '5314']
        if amort_5314_all:
            amort_value_all = amort_5314_all[0]['amount']
            print(f"\n5314 Amortisasi Aktiva Berwujud (all companies):")
            print(f"Amount: Rp {amort_value_all:,.2f}")

        print(f"\nTotal Expenses (all companies): Rp {data_all['total_expenses']:,.2f}")
        print(f"Net Income (all companies): Rp {data_all['net_income']:,.2f}")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
