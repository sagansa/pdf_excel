import sys
sys.path.insert(0, '.')

from sqlalchemy import create_engine, text
from datetime import datetime, date
import json

# Database connection
DB_URL = "mysql+pymysql://root:root@127.0.0.1:3306/bank_converter"
engine = create_engine(DB_URL)

try:
    with engine.connect() as conn:
        company_id = None  # Testing with None like in the test
        year = 2025
        start_date = "2025-01-01"
        end_date = "2025-12-31"

        print(f"Testing with company_id={company_id}, year={year}")
        print("=" * 80)

        # Get settings
        settings_result = conn.execute(text("""
            SELECT setting_name, setting_value, setting_type
            FROM amortization_settings
            WHERE company_id = :company_id OR company_id IS NULL
            ORDER BY company_id ASC
        """), {'company_id': company_id})

        use_mark_based = False
        asset_marks = []
        default_rate = 20.0
        default_life = 5
        allow_partial_year = True

        for row in settings_result:
            if row.setting_name == 'use_mark_based_amortization':
                use_mark_based = row.setting_value.lower() == 'true'
            elif row.setting_name == 'amortization_asset_marks':
                try:
                    asset_marks = json.loads(row.setting_value)
                except:
                    asset_marks = []
            elif row.setting_name == 'default_amortization_rate':
                try:
                    default_rate = float(row.setting_value)
                except:
                    default_rate = 20.0
            elif row.setting_name == 'default_asset_useful_life':
                try:
                    default_life = int(row.setting_value)
                except:
                    default_life = 5
            elif row.setting_name == 'allow_partial_year':
                allow_partial_year = row.setting_value.lower() == 'true'

        print(f"Use mark-based: {use_mark_based}")
        print(f"Asset marks: {asset_marks}")

        # Prepare mark condition
        mark_condition = "1=0"
        query_params = {'company_id': company_id, 'year': year}

        if use_mark_based:
            if asset_marks:
                mark_condition = "(m.personal_use IN :asset_marks OR t.amortization_asset_group_id IS NOT NULL)"
                query_params['asset_marks'] = asset_marks
            else:
                mark_condition = "t.amortization_asset_group_id IS NOT NULL"
        else:
            mark_condition = "t.is_amortizable = TRUE"

        print(f"Mark condition: {mark_condition}")

        # Get transactions
        txn_query = text(f"""
            SELECT
                t.id, t.txn_date, t.description, t.amount,
                t.amortization_asset_group_id, t.amortization_start_date, t.use_half_rate,
                t.company_id,
                ag.group_name, ag.tarif_rate, ag.useful_life_years, ag.asset_type,
                m.personal_use as mark_name
            FROM transactions t
            LEFT JOIN amortization_asset_groups ag ON t.amortization_asset_group_id = ag.id
            LEFT JOIN marks m ON t.mark_id = m.id
            WHERE ({mark_condition})
            AND (t.company_id = :company_id OR :company_id IS NULL)
            AND YEAR(t.txn_date) <= :year
            ORDER BY t.txn_date DESC
        """)

        txn_result = conn.execute(txn_query, query_params)

        transaction_amort_total = 0
        count = 0

        for row in txn_result:
            d = dict(row._mapping)
            count += 1

            tarif_rate = float(d.get('tarif_rate') or default_rate)
            base_amount = float(d.get('amount', 0))
            useful_life = int(d.get('useful_life_years') or default_life)

            start_date_val = d.get('amortization_start_date') or d.get('txn_date')
            if isinstance(start_date_val, str):
                try:
                    start_date_val = datetime.strptime(start_date_val[:10], '%Y-%m-%d').date()
                except:
                    start_date_val = date(year, 1, 1)

            acquisition_year = start_date_val.year
            annual_amort_base = base_amount * (tarif_rate / 100)

            accum_prev = 0
            current_year_amort = 0

            for y in range(acquisition_year, year + 1):
                y_amort = annual_amort_base
                if y == acquisition_year:
                    if allow_partial_year:
                        months = 12 - start_date_val.month + 1
                        y_amort = annual_amort_base * (months / 12)
                    elif d.get('use_half_rate'):
                        y_amort = annual_amort_base * 0.5

                remaining = base_amount - accum_prev
                y_amort = min(y_amort, remaining)

                if y < year:
                    accum_prev += y_amort
                else:
                    current_year_amort = y_amort

            if count <= 10:
                print(f"\nTxn: {d['description'][:50]}")
                print(f"  Amount: Rp {base_amount:,.2f}")
                print(f"  Rate: {tarif_rate}%")
                print(f"  Current Year: Rp {current_year_amort:,.2f}")

            transaction_amort_total += current_year_amort

        print(f"\nTotal transaction amortization: Rp {transaction_amort_total:,.2f} ({count} transactions)")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
