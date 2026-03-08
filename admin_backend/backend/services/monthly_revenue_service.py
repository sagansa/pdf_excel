from sqlalchemy import text

from backend.services.report_sql_fragments import (
    _coretax_filter_clause,
    _mark_coa_join_clause,
    _split_parent_exclusion_clause,
)
def fetch_monthly_revenue_data(conn, year, company_id=None, report_type='real'):
    """
    Fetch total revenue grouped by month for a specific year.
    Used for Coretax summary.
    """
    split_exclusion_clause = _split_parent_exclusion_clause(conn, 't')
    coretax_clause = _coretax_filter_clause(conn, report_type, 'm')
    mark_coa_join = _mark_coa_join_clause(conn, report_type, mark_ref='m.id', mapping_alias='mcm', join_type='INNER')
    query = text(f"""
        SELECT 
            MONTH(t.txn_date) as month_num,
            SUM(
                CASE 
                    -- Revenue accounts (normal balance CREDIT, except contra-revenue like 4011)
                    WHEN coa.category = 'REVENUE' AND coa.normal_balance = 'CREDIT' THEN
                        CASE 
                            WHEN t.db_cr = 'CR' THEN t.amount
                            WHEN t.db_cr = 'DB' THEN -t.amount
                            ELSE 0
                        END
                    -- Contra-revenue accounts (normal balance DEBIT, like 4011)
                    WHEN coa.category = 'REVENUE' AND coa.normal_balance = 'DEBIT' THEN
                        CASE 
                            WHEN t.db_cr = 'DB' THEN t.amount
                            WHEN t.db_cr = 'CR' THEN -t.amount
                            ELSE 0
                        END
                    ELSE 0
                END
            ) as total_amount
        FROM transactions t
        INNER JOIN marks m ON t.mark_id = m.id
        {mark_coa_join}
        INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
        WHERE YEAR(t.txn_date) = :year
            AND coa.category = 'REVENUE'
            AND (:company_id IS NULL OR t.company_id = :company_id)
            {split_exclusion_clause}
                {coretax_clause}
        GROUP BY MONTH(t.txn_date)
        ORDER BY month_num
    """)
    
    result = conn.execute(query, {
        'year': year,
        'company_id': company_id
    })
    
    # Initialize all months with 0
    monthly_data = {i: 0.0 for i in range(1, 13)}
    
    for row in result:
        d = row._mapping
        if d['month_num']:
            monthly_data[int(d['month_num'])] = float(d['total_amount']) if d['total_amount'] else 0.0
            
    # Convert to list of objects for easier frontend consumption
    return [
        {'month': m, 'revenue': monthly_data[m]} 
        for m in range(1, 13)
    ]
