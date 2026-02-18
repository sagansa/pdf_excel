from server import get_db_engine
from sqlalchemy import text
from datetime import datetime

def debug_report_query():
    engine, _ = get_db_engine()
    with engine.connect() as conn:
        start_date = '2025-01-01'
        end_date = '2025-12-31'
        company_id = None
        
        query = text("""
            SELECT
                coa.id,
                coa.code,
                coa.name,
                coa.category,
                coa.subcategory,
                SUM(
                    CASE
                        WHEN coa.category IN ('REVENUE', 'OTHER_REVENUE') THEN
                            CASE WHEN t.db_cr = 'CR' THEN t.amount ELSE -t.amount END
                        ELSE -- EXPENSE, COGS, OTHER_EXPENSE
                            CASE WHEN t.db_cr = 'DB' THEN t.amount ELSE -t.amount END
                    END
                ) as total_amount
            FROM transactions t
            INNER JOIN marks m ON t.mark_id = m.id
            INNER JOIN mark_coa_mapping mcm ON m.id = mcm.mark_id
            INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
            WHERE t.txn_date BETWEEN :start_date AND :end_date
                AND coa.category IN ('REVENUE', 'EXPENSE', 'OTHER_REVENUE', 'COGS', 'OTHER_EXPENSE')
                AND (:company_id IS NULL OR t.company_id = :company_id)
            GROUP BY coa.id, coa.code, coa.name, coa.category, coa.subcategory
            ORDER BY coa.code
        """)
        
        result = conn.execute(query, {
            'start_date': start_date,
            'end_date': end_date,
            'company_id': company_id
        })
        
        print(f"Results for {start_date} to {end_date}:")
        for row in result:
            d = dict(row._mapping)
            if d['code'] in ['4002', '4011']:
                print(f"Code: {d['code']}, Name: {d['name']}, Category: {d['category']}, Amount: {d['total_amount']}")

if __name__ == "__main__":
    debug_report_query()
