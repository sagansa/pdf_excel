from backend.db.schema import get_table_columns


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
    
    # If report_type column doesn't exist, use simple JOIN
    if 'report_type' not in mapping_columns:
        return f"{join_type} JOIN mark_coa_mapping {mapping_alias} ON {mapping_alias}.mark_id = {mark_ref}"
    
    # Use specific report_type mapping
    # This ensures 'real' reports use 'real' COA mappings
    # and 'coretax' reports use 'coretax' COA mappings
    mapping_scope_expr = _mapping_report_type_expr(conn, mapping_alias, 'real')
    
    normalized_report_type = str(report_type or 'real').strip().lower()
    
    if normalized_report_type == 'coretax':
        return f"""
        {join_type} JOIN mark_coa_mapping {mapping_alias}
            ON {mapping_alias}.mark_id = {mark_ref}
           AND {mapping_scope_expr} = 'coretax'
        """
    
    return f"""
    {join_type} JOIN mark_coa_mapping {mapping_alias}
        ON {mapping_alias}.mark_id = {mark_ref}
       AND {mapping_scope_expr} = 'real'
    """
