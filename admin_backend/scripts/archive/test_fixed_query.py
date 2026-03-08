import sys
sys.path.append('backend')
from db.session import get_db_engine
from sqlalchemy import text
from datetime import datetime

def test_fixed_query():
    engine, _ = get_db_engine()
    with engine.connect() as conn:
        start_date = '2025-01-01'
        end_date = '2025-12-31'
        company_id = None
        
        # New improved query
        query = text("""
            SELECT 
                coa.code,
                coa.name,
                coa.category,
                coa.subcategory,
                SUM(
                    CASE 
                        -- For REVENUE accounts: Credit increases, Debit decreases
                        WHEN coa.category = 'REVENUE' THEN
                            CASE WHEN t.db_cr = 'CR' THEN t.amount ELSE -t.amount END
                        -- For EXPENSE accounts: Debit increases, Credit decreases  
                        WHEN coa.category = 'EXPENSE' THEN
                            CASE WHEN t.db_cr = 'DB' THEN t.amount ELSE -t.amount END
                        ELSE 0
                    END
                ) as total_amount
            FROM transactions t
            INNER JOIN marks m ON t.mark_id = m.id
            INNER JOIN mark_coa_mapping mcm ON m.id = mcm.mark_id
            INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
            WHERE t.txn_date BETWEEN :start_date AND :end_date
                AND coa.category IN ('REVENUE', 'EXPENSE')
                AND (:company_id IS NULL OR t.company_id = :company_id)
            GROUP BY coa.id, coa.code, coa.name, coa.category, coa.subcategory
            ORDER BY coa.code
        """)
        
        result = conn.execute(query, {
            'start_date': start_date,
            'end_date': end_date,
            'company_id': company_id
        })
        
        print(f"Results with FIXED query for {start_date} to {end_date}:")
        print("=" * 80)
        for row in result:
            d = dict(row._mapping)
            if d['code'] in ['4002', '4011', '5003']:
                print(f"Code: {d['code']}, Name: {d['name']}, Category: {d['category']}, Amount: {d['total_amount']:.2f}")
        
        print("\n" + "=" * 80)
        print("Testing 5314 amortization calculation:")
        
        # Test the new 5314 calculation
        from backend.services.report_service import fetch_income_statement_data
        result_data = fetch_income_statement_data(conn, start_date, end_date, company_id)
        
        for expense in result_data['expenses']:
            if expense['code'] == '5314':
                print(f"5314 - {expense['name']}: {expense['amount']:.2f}")
        
        if 'amortization_breakdown' in result_data:
            print(f"Amortization by asset type: {result_data['amortization_breakdown']['by_asset_type']}")

if __name__ == "__main__":
    test_fixed_query()
