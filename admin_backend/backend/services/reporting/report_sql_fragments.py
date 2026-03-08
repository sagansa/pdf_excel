from backend.db.schema import get_table_columns


def _split_parent_exclusion_clause(conn, alias='t'):
    txn_columns = get_table_columns(conn, 'transactions')
    if 'parent_id' not in txn_columns:
        return ''
    return f" AND NOT EXISTS (SELECT 1 FROM transactions t_child WHERE t_child.parent_id = {alias}.id)"


def _coretax_filter_clause(conn, report_type='real', alias='m'):
    if str(report_type).strip().lower() != 'coretax':
        return ""

    mark_columns = get_table_columns(conn, 'marks')
    if 'is_coretax' in mark_columns:
        if conn.dialect.name == 'sqlite':
            return f" AND LOWER(COALESCE(CAST({alias}.is_coretax AS TEXT), '0')) IN ('1', 'true', 'yes', 'y')"
        return f" AND LOWER(COALESCE(CAST({alias}.is_coretax AS CHAR), '0')) IN ('1', 'true', 'yes', 'y')"

    return f" AND ({alias}.tax_report IS NOT NULL AND TRIM({alias}.tax_report) != '')"


def _mapping_report_type_expr(conn, alias, fallback='real'):
    if conn.dialect.name == 'sqlite':
        return f"LOWER(COALESCE(CAST({alias}.report_type AS TEXT), '{fallback}'))"
    return f"LOWER(COALESCE(CAST({alias}.report_type AS CHAR), '{fallback}'))"


def _mark_coa_join_clause(conn, report_type='real', mark_ref='m.id', mapping_alias='mcm', join_type='INNER'):
    mapping_columns = get_table_columns(conn, 'mark_coa_mapping')
    normalized_report_type = str(report_type or 'real').strip().lower()
    if normalized_report_type != 'coretax':
        normalized_report_type = 'real'

    if 'report_type' not in mapping_columns:
        return f"{join_type} JOIN mark_coa_mapping {mapping_alias} ON {mapping_alias}.mark_id = {mark_ref}"

    mapping_scope_expr = _mapping_report_type_expr(conn, mapping_alias, 'real')

    if normalized_report_type == 'coretax':
        fallback_alias = f"{mapping_alias}_coretax"
        fallback_scope_expr = _mapping_report_type_expr(conn, fallback_alias, 'real')
        return f"""
        {join_type} JOIN mark_coa_mapping {mapping_alias}
            ON {mapping_alias}.mark_id = {mark_ref}
           AND (
                {mapping_scope_expr} = 'coretax'
                OR (
                    {mapping_scope_expr} = 'real'
                    AND NOT EXISTS (
                        SELECT 1
                        FROM mark_coa_mapping {fallback_alias}
                        WHERE {fallback_alias}.mark_id = {mark_ref}
                          AND {fallback_scope_expr} = 'coretax'
                          AND UPPER(COALESCE({fallback_alias}.mapping_type, '')) = UPPER(COALESCE({mapping_alias}.mapping_type, ''))
                    )
                )
           )
        """

    return f"""
    {join_type} JOIN mark_coa_mapping {mapping_alias}
        ON {mapping_alias}.mark_id = {mark_ref}
       AND {mapping_scope_expr} = 'real'
    """
