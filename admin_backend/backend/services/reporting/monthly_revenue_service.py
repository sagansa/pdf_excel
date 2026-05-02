from sqlalchemy import text

from backend.services.reporting.report_sql_fragments import (
    _coretax_filter_clause,
    _effective_coa_id_expr,
    _effective_mapping_type_expr,
    _effective_natural_direction_expr,
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
    mark_coa_join = _mark_coa_join_clause(conn, report_type, mark_ref='m.id', mapping_alias='mcm', join_type='LEFT')
    effective_coa_id = _effective_coa_id_expr(conn, report_type, txn_alias='t', mapping_alias='mcm')
    effective_mapping_type = _effective_mapping_type_expr(conn, report_type, txn_alias='t', mapping_alias='mcm')
    effective_natural_direction = _effective_natural_direction_expr(conn, report_type, txn_alias='t', mark_alias='m')
    month_expr = "CAST(strftime('%m', t.txn_date) AS INTEGER)" if conn.dialect.name == 'sqlite' else "MONTH(t.txn_date)"
    year_expr = "CAST(strftime('%Y', t.txn_date) AS INTEGER)" if conn.dialect.name == 'sqlite' else "YEAR(t.txn_date)"
    query = text(f"""
        SELECT 
            {month_expr} as month_num,
            -SUM(
                CASE 
                    WHEN UPPER(COALESCE({effective_mapping_type}, '')) = 'DEBIT' THEN
                        t.amount * (CASE
                            WHEN {effective_natural_direction} IS NOT NULL
                                 AND UPPER(TRIM(COALESCE(t.db_cr, ''))) != ''
                                 AND (
                                    (UPPER({effective_natural_direction}) = 'DB' AND UPPER(TRIM(t.db_cr)) IN ('CR', 'CREDIT', 'K', 'KREDIT'))
                                    OR
                                    (UPPER({effective_natural_direction}) = 'CR' AND UPPER(TRIM(t.db_cr)) IN ('DB', 'DEBIT', 'D', 'DE'))
                                 )
                            THEN -1 ELSE 1 END)
                    WHEN UPPER(COALESCE({effective_mapping_type}, '')) = 'CREDIT' THEN
                        -t.amount * (CASE
                            WHEN {effective_natural_direction} IS NOT NULL
                                 AND UPPER(TRIM(COALESCE(t.db_cr, ''))) != ''
                                 AND (
                                    (UPPER({effective_natural_direction}) = 'DB' AND UPPER(TRIM(t.db_cr)) IN ('CR', 'CREDIT', 'K', 'KREDIT'))
                                    OR
                                    (UPPER({effective_natural_direction}) = 'CR' AND UPPER(TRIM(t.db_cr)) IN ('DB', 'DEBIT', 'D', 'DE'))
                                 )
                            THEN -1 ELSE 1 END)
                    WHEN t.db_cr = 'DB' THEN t.amount
                    WHEN t.db_cr = 'CR' THEN -t.amount
                    ELSE 0
                END
            ) as total_amount
        FROM transactions t
        INNER JOIN marks m ON t.mark_id = m.id
        {mark_coa_join}
        INNER JOIN chart_of_accounts coa ON {effective_coa_id} = coa.id
        WHERE {year_expr} = :year
            AND coa.category = 'REVENUE'
            AND (:company_id IS NULL OR t.company_id = :company_id)
            {split_exclusion_clause}
                {coretax_clause}
        GROUP BY {month_expr}
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
