from sqlalchemy import create_engine, text
import json
from datetime import datetime

DB_USER = 'root'
DB_PASS = 'root'
DB_HOST = '127.0.0.1'
DB_PORT = '3306'
DB_NAME = 'bank_converter'

DB_URL = f'mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

engine = create_engine(DB_URL)

def main():
    with engine.connect() as conn:
        print("=== AMORTIZATION BREAKDOWN ANALYSIS ===\n")

        company_id = '019aba4b-efca-70ee-a4ab-702dc8c246a8'  # Headquarters
        year = 2025

        # 1. Manual Amortization Items
        print("1. MANUAL AMORTIZATION ITEMS (amortization_items table)")
        manual_query = text("""
            SELECT ai.*, coa.code as coa_code, coa.name as coa_name,
                   ag.group_name, ag.group_number, ag.tarif_rate, ag.tarif_half_rate, ag.useful_life_years, ag.asset_type
            FROM amortization_items ai
            INNER JOIN chart_of_accounts coa ON ai.coa_id = coa.id
            LEFT JOIN amortization_asset_groups ag ON ai.asset_group_id = ag.id
            WHERE (:company_id IS NULL OR ai.company_id = :company_id)
        """)
        manual_result = conn.execute(manual_query, {'company_id': company_id})

        manual_items = []
        for row in manual_result:
            d = dict(row._mapping)
            manual_items.append(d)

        print(f"   Found {len(manual_items)} manual items")
        manual_total = 0
        for item in manual_items:
            amount = float(item['amount'])
            amort_amount = float(item.get('annual_amortization', amount))
            print(f"   - {item['description']}: Rp {amort_amount:,.2f} (COA: {item['coa_code']})")
            manual_total += amort_amount

        print(f"   MANUAL TOTAL: Rp {manual_total:,.2f}\n")

        # 2. Calculated Amortization (from marks)
        print("2. CALCULATED AMORTIZATION (from marks/mark_asset_mapping)")
        calculated_query = text("""
            SELECT
                t.id, t.description, t.amount as acquisition_cost, 0 as residual_value,
                COALESCE(t.use_half_rate, mam.is_deductible_50_percent, FALSE) as use_half_rate,
                t.txn_date as acquisition_date,
                COALESCE(t.amortization_start_date, t.txn_date) as amortization_start_date,
                t.amount as book_value, 0 as accumulated_amortization,
                COALESCE(ag_direct.group_number, ag_mapping.group_number, 2) as group_number,
                COALESCE(ag_direct.group_name, ag_mapping.group_name, 'Kelompok 2') as group_name,
                COALESCE(ag_direct.asset_type, ag_mapping.asset_type, mam.asset_type, 'Tangible') as asset_type,
                COALESCE(ag_direct.useful_life_years, ag_mapping.useful_life_years, mam.useful_life_years, 5) as useful_life_years,
                COALESCE(ag_direct.tarif_rate, ag_mapping.tarif_rate, 20.00) as tarif_rate,
                COALESCE(ag_direct.tarif_half_rate, ag_mapping.tarif_half_rate, 10.00) as tarif_half_rate,
                TRUE as is_from_ledger,
                COALESCE(t.amortization_asset_group_id, mam.asset_group_id) as amortization_asset_group_id,
                m.personal_use as mark_name,
                m.id as mark_id
            FROM transactions t
            INNER JOIN marks m ON t.mark_id = m.id
            LEFT JOIN mark_asset_mapping mam ON m.id = mam.mark_id AND mam.is_active = TRUE
            LEFT JOIN amortization_asset_groups ag_direct ON t.amortization_asset_group_id = ag_direct.id
            LEFT JOIN amortization_asset_groups ag_mapping ON mam.asset_group_id = ag_mapping.id
            WHERE t.company_id = :company
            AND YEAR(t.txn_date) <= :year
            AND m.is_asset = TRUE
            AND (t.is_amortizable IS TRUE OR t.is_amortizable IS NULL)
            ORDER BY t.txn_date
        """)

        calculated_result = conn.execute(calculated_query, {'company': company_id, 'year': year})
        calculated_items = list(calculated_result)

        calculated_total = 0
        print(f"   Found {len(calculated_items)} mark-based assets")
        for row in calculated_items:
            acquisition_cost = float(row[3])
            use_half_rate = row[5]
            base_multiplier = 0.5 if use_half_rate else 1.0
            base_amount = acquisition_cost * base_multiplier
            rate = float(row[14]) if row[14] else 20.0
            annual_amortization = base_amount * (rate / 100)
            calculated_total += annual_amortization
            deductible = "50%" if use_half_rate else "100%"
            print(f"   - {row[1]}: Rp {annual_amortization:,.2f} (Deductible: {deductible}, Rate: {rate}%)")

        print(f"   CALCULATED TOTAL: Rp {calculated_total:,.2f}\n")

        # 3. Total Summary
        total_amortization = manual_total + calculated_total

        print("3. TOTAL AMORTIZATION BREAKDOWN")
        print(f"   Manual Items:       Rp {manual_total:,.2f}")
        print(f"   Calculated Assets:  Rp {calculated_total:,.2f}")
        print(f"   ─────────────────────────────────")
        print(f"   TOTAL AMORTIZATION: Rp {total_amortization:,.2f}\n")

        # 4. Check what will be sent to frontend
        print("4. WHAT WILL BE SENT TO FRONTEND (amortization_breakdown)")
        breakdown = {
            'calculated_amortization': {
                'items': calculated_items,
                'total': round(calculated_total + manual_total, 2),  # Note: Backend adds manual to calculated total
                'asset_count': len(calculated_items)
            },
            'manual_amortization': {
                'items': manual_items,
                'total': round(manual_total, 2)
            },
            'prepaid_amortization': {
                'items': [],
                'total': 0
            },
            'transaction_amortization': 0,
            'transaction_items': [],
            'total_amortization': round(total_amortization, 2),
            'year': year
        }

        print(f"   calculated_amortization.total: Rp {breakdown['calculated_amortization']['total']:,.2f}")
        print(f"   manual_amortization.total: Rp {breakdown['manual_amortization']['total']:,.2f}")
        print(f"   total_amortization: Rp {breakdown['total_amortization']:,.2f}")

if __name__ == "__main__":
    main()
