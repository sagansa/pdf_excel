import sys
sys.path.insert(0, '.')

from sqlalchemy import create_engine, text
from datetime import datetime, date

# Database connection
DB_URL = "mysql+pymysql://root:root@127.0.0.1:3306/bank_converter"
engine = create_engine(DB_URL)

try:
    with engine.connect() as conn:
        company_id = "8ab69d4a-e591-4f05-909e-25ff12352efb"
        year = 2025
        allow_partial_year = True

        print(f"Calculating amortization for company_id: {company_id}, year: {year}")
        print("=" * 80)

        # Get amortization items
        items_query = text("""
            SELECT
                ai.id, ai.company_id, ai.year, ai.coa_id,
                coa.code as coa_code, coa.name as coa_name,
                ai.description, ai.amount, ai.amortization_date,
                ai.asset_group_id, ai.use_half_rate, ai.notes, ai.is_manual,
                ai.created_at, ai.updated_at,
                ag.group_name, ag.tarif_rate, ag.useful_life_years, ag.asset_type
            FROM amortization_items ai
            LEFT JOIN chart_of_accounts coa ON ai.coa_id = coa.id
            LEFT JOIN amortization_asset_groups ag ON ai.asset_group_id = ag.id
            WHERE ai.company_id = :company_id
            ORDER BY ai.amortization_date DESC, ai.created_at DESC
        """)

        items_result = conn.execute(items_query, {'company_id': company_id})

        items = []
        manual_total_amort = 0
        total_amount = 0

        for row in items_result:
            d = dict(row._mapping)

            amount = float(d.get('amount', 0))
            report_year = year

            # Determine if we should include this item
            purchase_date_str = d.get('amortization_date')
            purchase_year = report_year
            if purchase_date_str:
                try:
                    if isinstance(purchase_date_str, str):
                        purchase_year = int(purchase_date_str[:4])
                    else:
                        purchase_year = purchase_date_str.year
                except:
                    pass

            # Skip if it's a one-time adjustment for another year
            if not d.get('asset_group_id') and d.get('year') != report_year:
                continue
            # Skip if it's an asset not yet purchased
            if purchase_year > report_year:
                continue

            tarif_rate = float(d.get('tarif_rate') or 20)

            # Check if it has an asset group for multi-year calc
            if d.get('asset_group_id'):
                # Multi-year accumulation loop
                annual_amort_base = amount * (tarif_rate / 100)
                accum_prev = 0
                current_year_amort = 0

                start_date_val = d.get('amortization_date')
                if isinstance(start_date_val, str):
                    try:
                        start_date_val = datetime.strptime(start_date_val[:10], '%Y-%m-%d').date()
                    except:
                        start_date_val = date(report_year, 1, 1)

                acquisition_year = start_date_val.year

                for y in range(acquisition_year, report_year + 1):
                    y_amort = annual_amort_base
                    if y == acquisition_year:
                        if allow_partial_year:
                            months = 12 - start_date_val.month + 1
                            y_amort = annual_amort_base * (months / 12)
                        elif d.get('use_half_rate'):
                            y_amort = annual_amort_base * 0.5

                    remaining = amount - accum_prev
                    y_amort = min(y_amort, remaining)

                    if y < report_year:
                        accum_prev += y_amort
                    else:
                        current_year_amort = y_amort

                annual_amortization = current_year_amort
            else:
                # One-time adjustment / Direct expense (must be ai.year == report_year)
                annual_amortization = amount

            print(f"\nItem: {d['description']}")
            print(f"  Amount: Rp {amount:,.2f}")
            print(f"  Asset Group: {d.get('group_name') or 'N/A'}")
            print(f"  Tarif Rate: {tarif_rate}%")
            print(f"  Current Year Amortization: Rp {annual_amortization:,.2f}")

            items.append(d)
            total_amount += amount
            manual_total_amort += annual_amortization

        print("\n" + "=" * 80)
        print(f"Total Manual Amortization: Rp {manual_total_amort:,.2f}")
        print(f"Expected (from screenshot): Rp 56,094,288.00")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
