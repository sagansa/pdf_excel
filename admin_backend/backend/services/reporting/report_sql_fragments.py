from sqlalchemy import text
from backend.db.schema import get_table_columns


def _trimmed_text_expr(conn, expr):
    if conn.dialect.name == 'sqlite':
        return f"NULLIF(TRIM(CAST({expr} AS TEXT)), '')"
    return f"NULLIF(TRIM(CAST({expr} AS CHAR)), '')"


def _split_parent_exclusion_clause(conn, alias='t'):
    """
    Generate SQL clause to exclude parent transactions when all children have marks.

    This prevents double-counting when transactions are split:
    - Parent transaction is just a container (should be excluded from reports)
    - Child transactions have individual marks (should be included in reports)

    Logic:
    - Exclude parent if there exists at least one child with a mark_id
    - This ensures child transactions (the actual split entries) are counted, not the parent

    Args:
        conn: Database connection
        alias: Table alias for transactions table (default 't')

    Returns:
        SQL WHERE clause string (empty if parent_id column doesn't exist)
    """
    txn_columns = get_table_columns(conn, 'transactions')
    if 'parent_id' not in txn_columns:
        return ''
    if 'mark_id' not in txn_columns:
        # If mark_id doesn't exist, exclude all children to avoid double-counting
        return f" AND NOT EXISTS (SELECT 1 FROM transactions t_child WHERE t_child.parent_id = {alias}.id)"

    if conn.dialect.name == 'sqlite':
        mark_expr = "NULLIF(TRIM(COALESCE(CAST(t_child.mark_id AS TEXT), '')), '')"
    else:
        mark_expr = "NULLIF(TRIM(COALESCE(CAST(t_child.mark_id AS CHAR), '')), '')"

    # Exclude parent if it has children with marks (i.e., this is a split transaction container)
    # The children will be included in the report individually
    return (
        " AND NOT EXISTS ("
        "SELECT 1 FROM transactions t_child "
        f"WHERE t_child.parent_id = {alias}.id "
        f"AND {mark_expr} IS NOT NULL)"
    )


def _coretax_filter_clause(conn, report_type='real', alias='m'):
    """
    Generate filter clause for CoreTax reporting.
    
    REFACTORED: Both 'real' and 'coretax' now include the SAME transactions.
    The difference is in which COA mappings are used (see _mark_coa_join_clause).
    
    This function returns an empty string (no transaction filtering) for all types.
    Transactions are filtered only by date/company, not by report_type.
    
    Args:
        conn: Database connection
        report_type: 'real' or 'coretax' (no longer affects transaction filtering)
        alias: Table alias for marks table
        
    Returns:
        Empty string (no transaction filtering applied)
    """
    # No transaction filtering - include all transactions regardless of report_type
    # The COA mapping difference is handled in _mark_coa_join_clause
    return ""


def _mapping_report_type_expr(conn, alias, fallback='real'):
    """
    Generate SQL expression to normalize report_type values.
    
    Handles database dialect differences (SQLite vs MySQL/MariaDB).
    """
    if conn.dialect.name == 'sqlite':
        return (
            f"LOWER(COALESCE(NULLIF(TRIM(CAST({alias}.report_type AS TEXT)), ''), '{fallback}'))"
        )
    return (
        f"LOWER(COALESCE(NULLIF(TRIM(CAST({alias}.report_type AS CHAR)), ''), '{fallback}'))"
    )


def _mark_coa_join_clause(conn, report_type='real', mark_ref='m.id', mapping_alias='mcm', join_type='INNER'):
    """
    Generate JOIN clause for mark_coa_mapping table.
    
    REFACTORED: 
    - SAME transactions are included for both 'real' and 'coretax'
    - DIFFERENT COA mappings are used based on report_type
    
    This allows the same transaction to be mapped to different COA accounts
    depending on whether it's a 'real' or 'coretax' report.
    
    For example:
    - A PNBP transaction might map to COA 4001 (real) or 4002 (coretax)
    - The transaction is the same, but the COA classification differs
    
    Args:
        conn: Database connection
        report_type: 'real' or 'coretax' (determines which COA mapping to use)
        mark_ref: Reference to mark ID (e.g., 'm.id' or 't.mark_id')
        mapping_alias: Alias for mark_coa_mapping table
        join_type: 'INNER' or 'LEFT'
        
    Returns:
        SQL JOIN clause string
    """
    mapping_columns = get_table_columns(conn, 'mark_coa_mapping')
    txn_columns = get_table_columns(conn, 'transactions')
    normalized_report_type = str(report_type or 'real').strip().lower()
    direct_coa_guard = ''
    if normalized_report_type == 'coretax':
        coretax_expr = _trimmed_text_expr(conn, 't.coa_id_coretax') if 'coa_id_coretax' in txn_columns else 'NULL'
        real_expr = _trimmed_text_expr(conn, 't.coa_id') if 'coa_id' in txn_columns else 'NULL'
        if coretax_expr != 'NULL' and real_expr != 'NULL':
            direct_coa_guard = f" AND COALESCE({coretax_expr}, {real_expr}) IS NULL"
        elif coretax_expr != 'NULL':
            direct_coa_guard = f" AND {coretax_expr} IS NULL"
        elif real_expr != 'NULL':
            direct_coa_guard = f" AND {real_expr} IS NULL"
    elif 'coa_id' in txn_columns:
        direct_coa_guard = f" AND {_trimmed_text_expr(conn, 't.coa_id')} IS NULL"
    manual_side_guard = ''
    if 'bank_code' in txn_columns and 'parent_id' in txn_columns:
        # Manual journal child rows represent explicit debit/credit lines.
        # If a direct COA for the active report type is missing, only fall back to a
        # mark-level mapping with the SAME side as the child line. This mirrors the
        # "real" behaviour where each line resolves to a single side-specific account.
        manual_child_condition = (
            f"UPPER(TRIM(COALESCE(t.bank_code, ''))) = 'MANUAL' "
            f"AND {_trimmed_text_expr(conn, 't.parent_id')} IS NOT NULL"
        )
        manual_side_expr = (
            f"CASE "
            f"WHEN UPPER(TRIM(COALESCE(t.db_cr, ''))) IN ('CR', 'CREDIT', 'K', 'KREDIT') THEN 'CREDIT' "
            f"WHEN UPPER(TRIM(COALESCE(t.db_cr, ''))) IN ('DB', 'DEBIT', 'D', 'DE') THEN 'DEBIT' "
            f"ELSE NULL END"
        )
        manual_side_guard = (
            f" AND (NOT ({manual_child_condition}) "
            f"OR UPPER(COALESCE({mapping_alias}.mapping_type, '')) = {manual_side_expr})"
        )
    
    # If report_type column doesn't exist, use simple JOIN
    if 'report_type' not in mapping_columns:
        return f"{join_type} JOIN mark_coa_mapping {mapping_alias} ON {mapping_alias}.mark_id = {mark_ref}{direct_coa_guard}{manual_side_guard}"
    
    # Use specific report_type mapping
    # This ensures 'real' reports use 'real' COA mappings
    # and 'coretax' reports use 'coretax' COA mappings
    mapping_scope_expr = _mapping_report_type_expr(conn, mapping_alias, 'real')
    
    if normalized_report_type == 'coretax':
        return f"""
        {join_type} JOIN mark_coa_mapping {mapping_alias}
            ON {mapping_alias}.mark_id = {mark_ref}
           {direct_coa_guard}
           {manual_side_guard}
           AND {mapping_scope_expr} = 'coretax'
        """
    
    return f"""
    {join_type} JOIN mark_coa_mapping {mapping_alias}
        ON {mapping_alias}.mark_id = {mark_ref}
       {direct_coa_guard}
       {manual_side_guard}
       AND {mapping_scope_expr} = 'real'
    """


def _transaction_direct_coa_expr(conn, report_type='real', alias='t'):
    txn_columns = get_table_columns(conn, 'transactions')
    normalized_report_type = str(report_type or 'real').strip().lower()
    column_name = 'coa_id_coretax' if normalized_report_type == 'coretax' else 'coa_id'
    if normalized_report_type == 'coretax':
        coretax_expr = _trimmed_text_expr(conn, f'{alias}.coa_id_coretax') if 'coa_id_coretax' in txn_columns else 'NULL'
        real_expr = _trimmed_text_expr(conn, f'{alias}.coa_id') if 'coa_id' in txn_columns else 'NULL'
        if coretax_expr == 'NULL' and real_expr == 'NULL':
            return 'NULL'
        if coretax_expr == 'NULL':
            return real_expr
        if real_expr == 'NULL':
            return coretax_expr
        # If a direct coretax COA is missing, reuse the real direct COA as the next-best
        # fallback. This keeps manual journal lines aligned with the proven "real" side
        # instead of dropping to mark-level mapping and risking account drift.
        return f'COALESCE({coretax_expr}, {real_expr})'

    if column_name not in txn_columns:
        return 'NULL'
    return _trimmed_text_expr(conn, f'{alias}.{column_name}')


def _effective_coa_id_expr(conn, report_type='real', txn_alias='t', mapping_alias='mcm'):
    direct_expr = _transaction_direct_coa_expr(conn, report_type, txn_alias)
    if direct_expr == 'NULL':
        return f'{mapping_alias}.coa_id'
    return f'COALESCE({direct_expr}, {mapping_alias}.coa_id)'


def _effective_mapping_type_expr(conn, report_type='real', txn_alias='t', mapping_alias='mcm'):
    direct_expr = _transaction_direct_coa_expr(conn, report_type, txn_alias)
    direct_mapping_expr = (
        f"CASE "
        f"WHEN UPPER(TRIM(COALESCE({txn_alias}.db_cr, ''))) IN ('CR', 'CREDIT', 'K', 'KREDIT') THEN 'CREDIT' "
        f"WHEN UPPER(TRIM(COALESCE({txn_alias}.db_cr, ''))) IN ('DB', 'DEBIT', 'D', 'DE') THEN 'DEBIT' "
        f"ELSE NULL END"
    )
    if direct_expr == 'NULL':
        return f'{mapping_alias}.mapping_type'
    return f"CASE WHEN {direct_expr} IS NOT NULL THEN {direct_mapping_expr} ELSE {mapping_alias}.mapping_type END"


def _effective_natural_direction_expr(conn, report_type='real', txn_alias='t', mark_alias='m'):
    direct_expr = _transaction_direct_coa_expr(conn, report_type, txn_alias)
    direct_direction_expr = (
        f"CASE "
        f"WHEN UPPER(TRIM(COALESCE({txn_alias}.db_cr, ''))) IN ('CR', 'CREDIT', 'K', 'KREDIT') THEN 'CR' "
        f"WHEN UPPER(TRIM(COALESCE({txn_alias}.db_cr, ''))) IN ('DB', 'DEBIT', 'D', 'DE') THEN 'DB' "
        f"ELSE NULL END"
    )
    if direct_expr == 'NULL':
        return f'{mark_alias}.natural_direction'
    return f"CASE WHEN {direct_expr} IS NOT NULL THEN {direct_direction_expr} ELSE {mark_alias}.natural_direction END"
def _get_reporting_start_date(conn, company_id, report_type='real'):
    """
    Get the reporting start date based on initial_capital_settings.
    Any transactions before this date should be ignored.
    """
    if not company_id:
        return None
        
    res = conn.execute(text("""
        SELECT start_year
        FROM initial_capital_settings
        WHERE company_id = :company_id AND report_type = :report_type
        LIMIT 1
    """), {'company_id': company_id, 'report_type': report_type}).fetchone()
    
    if res and res.start_year:
        return f"{res.start_year}-01-01"
    return None
