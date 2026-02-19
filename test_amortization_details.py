import sys
sys.path.append('backend')
from db.session import get_db_engine
from sqlalchemy import text
from datetime import datetime

def test_amortization_details():
    engine, _ = get_db_engine()
    with engine.connect() as conn:
        start_date = '2025-01-01'
        end_date = '2025-12-31'
        company_id = None
        
        print("=" * 80)
        print("ANALISIS DATA AMORTISASI 5314")
        print("=" * 80)
        
        # 1. Get data from transactions
        print("\n1. Data dari TRANSACTIONS:")
        transactions_query = text("""
            SELECT 
                t.txn_date,
                t.description,
                t.amount,
                t.db_cr,
                m.personal_use
            FROM transactions t
            INNER JOIN marks m ON t.mark_id = m.id
            INNER JOIN mark_coa_mapping mcm ON m.id = mcm.mark_id
            INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
            WHERE t.txn_date BETWEEN :start_date AND :end_date
                AND coa.code = '5314'
                AND (:company_id IS NULL OR t.company_id = :company_id)
            ORDER BY t.txn_date
        """)
        
        result = conn.execute(transactions_query, {
            'start_date': start_date,
            'end_date': end_date,
            'company_id': company_id
        })
        
        transactions_total = 0
        for row in result:
            d = dict(row._mapping)
            amount = float(d['amount'])
            sign = 1 if d['db_cr'] == 'DB' else -1
            signed_amount = amount * sign
            transactions_total += signed_amount
            print(f"  {d['txn_date']}: {d['description'][:50]} - {d['db_cr']}: {amount:,.0f} -> {signed_amount:,.0f}")
        
        print(f"\nTOTAL TRANSACTIONS: {transactions_total:,.2f}")
        
        # 2. Get manual data
        print("\n2. Data dari MANUAL (amortization_items):")
        manual_query = text("""
            SELECT ai.*, coa.code as coa_code, coa.name as coa_name,
                ag.group_name, ag.tarif_rate, ag.useful_life_years, ag.asset_type
            FROM amortization_items ai
            INNER JOIN chart_of_accounts coa ON ai.coa_id = coa.id
            LEFT JOIN amortization_asset_groups ag ON ai.asset_group_id = ag.id
            WHERE (ai.company_id = :company OR :company IS NULL)
            AND coa.code = '5314'
            AND (ai.year = :year OR ai.year IS NULL)
        """)
        
        manual_result = conn.execute(manual_query, {
            'company': company_id,
            'year': datetime.strptime(start_date, '%Y-%m-%d').year
        })
        
        manual_total = 0
        for row in manual_result:
            d = dict(row._mapping)
            amount = float(d['amount'] or 0)
            manual_total += amount
            print(f"  {d.get('year', 'N/A')}: {d.get('asset_type', 'N/A')} - {amount:,.0f}")
        
        print(f"\nTOTAL MANUAL: {manual_total:,.2f}")
        
        # 3. Combined result
        combined_total = transactions_total + manual_total
        print(f"\n3. GABUNGAN TRANSACTIONS + MANUAL: {combined_total:,.2f}")
        
        # 4. Test with the function
        from backend.services.report_service import fetch_income_statement_data
        result_data = fetch_income_statement_data(conn, start_date, end_date, company_id)
        
        for expense in result_data['expenses']:
            if expense['code'] == '5314':
                print(f"\n4. HASIL DARI FUNCTION: {expense['amount']:,.2f}")
                break
        
        if 'amortization_breakdown' in result_data:
            print(f"\n5. BREAKDOWN BY ASSET TYPE:")
            for asset_type, amount in result_data['amortization_breakdown']['by_asset_type'].items():
                print(f"   {asset_type}: {amount:,.2f}")

if __name__ == "__main__":
    test_amortization_details()
