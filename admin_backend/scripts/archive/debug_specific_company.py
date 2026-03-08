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
        company_id = "8ab69d4a-e591-4f05-909e-25ff12352efb"
        year = 2025

        print(f"Debugging report_service.py calculation for company_id: {company_id}")
        print("=" * 80)

        # 1. Get settings
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

        print(f"Settings: use_mark_based={use_mark_based}, marks={asset_marks}")

        # 2. Transaction amortization
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

        txn_query = text(f"""
            SELECT
                t.id, t.txn_date, t.description,
                t.amount as acquisition_cost, t.amortization_asset_group_id as asset_group_id,
                t.amortization_start_date, t.use_half_rate, t.amortization_notes as notes,
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
            base_amount = float(d.get('acquisition_cost', 0))
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
                print(f"\nTxn {count}: {d['description'][:50]}")
                print(f"  Amount: Rp {base_amount:,.2f}, Rate: {tarif_rate}%, Current Year: Rp {current_year_amort:,.2f}")

            transaction_amort_total += current_year_amort

        print(f"\nTransaction amortization: Rp {transaction_amort_total:,.2f} ({count} transactions)")

        # 3. Manual amortization items
        manual_query = text("""
            SELECT ai.*, coa.code as coa_code, coa.name as coa_name
            FROM amortization_items ai
            INNER JOIN chart_of_accounts coa ON ai.coa_id = coa.id
            WHERE ai.company_id = :company
            AND coa.code = '5314'
        """)
        manual_result = conn.execute(manual_query, {'company': company_id})

        manual_amort_total = 0
        count_manual = 0

        for row in manual_result:
            d = dict(row._mapping)
            count_manual += 1
            item_year = d.get('year')
            if item_year:
                if isinstance(item_year, str):
                    try:
                        item_year = int(item_year)
                    except:
                        pass
                if item_year != year:
                    continue

            # Only add items without asset_group_id (direct expenses)
            if not d.get('asset_group_id'):
                annual_amount = d.get('amount', 0)
                if annual_amount:
                    manual_amort_total += float(annual_amount)
                    if count_manual <= 5:
                        print(f"\nManual (direct): {d['description'][:50]} - Rp {annual_amount:,.2f}")
            else:
                # Calculate multi-year amortization for items with asset_group_id
                amount = float(d.get('amount', 0))
                tarif_rate = float(d.get('tarif_rate') or default_rate)

                a_start_date = d.get('amortization_date')
                if isinstance(a_start_date, str):
                    try:
                        a_start_date = datetime.strptime(a_start_date[:10], '%Y-%m-%d').date()
                    except:
                        a_start_date = date(year, 1, 1)

                acquisition_year = a_start_date.year if a_start_date else year
                annual_amort_base = amount * (tarif_rate / 100)

                accum_prev = 0
                current_year_amort = 0

                for y in range(acquisition_year, year + 1):
                    y_amort = annual_amort_base
                    if y == acquisition_year:
                        if allow_partial_year:
                            months = 12 - a_start_date.month + 1
                            y_amort = annual_amort_base * (months / 12)
                        elif d.get('use_half_rate'):
                            y_amort = annual_amort_base * 0.5

                    remaining = amount - accum_prev
                    y_amort = min(y_amort, remaining)

                    if y < year:
                        accum_prev += y_amort
                    else:
                        current_year_amort = y_amort

                manual_amort_total += current_year_amort
                if count_manual <= 5:
                    print(f"\nManual (asset group): {d['description'][:50]} - Amount: Rp {amount:,.2f}, Current Year: Rp {current_year_amort:,.2f}")

        print(f"\nManual amortization: Rp {manual_amort_total:,.2f} ({count_manual} items)")

        print(f"\nTotal: Rp {transaction_amort_total + manual_amort_total:,.2f}")
        print(f"Expected from income statement: Rp 32,290,640.00")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
