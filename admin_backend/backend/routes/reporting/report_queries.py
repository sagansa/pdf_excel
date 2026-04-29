from sqlalchemy import text
from backend.db.schema import get_table_columns
from backend.services.reporting.report_sql_fragments import (
    _effective_coa_id_expr,
    _effective_mapping_type_expr,
    _split_parent_exclusion_clause,
    _coretax_filter_clause,
    _mark_coa_join_clause,
)


def build_available_years_query(year_expr, split_exclusion):
    return text(f"""
        SELECT DISTINCT {year_expr} AS year
        FROM transactions t
        WHERE t.txn_date IS NOT NULL
          AND (:company_id IS NULL OR t.company_id = :company_id)
          {split_exclusion}
        ORDER BY year DESC
    """)


def build_coa_detail_query(conn, npwp_expr, method_expr, split_exclusion, report_type='real'):
    effective_coa_id = _effective_coa_id_expr(conn, report_type, txn_alias='t', mapping_alias='mcm')
    effective_mapping_type = _effective_mapping_type_expr(conn, report_type, txn_alias='t', mapping_alias='mcm')
    mark_coa_join = _mark_coa_join_clause(conn, report_type, mark_ref='m.id', mapping_alias='mcm', join_type='LEFT')
    return text(f"""
        SELECT
            t.id, t.txn_date, t.description, t.amount, t.db_cr,
            m.personal_use as mark_name, m.is_service, c.name as company_name,
            {effective_mapping_type} AS mapping_type,
            {npwp_expr} AS service_npwp,
            {method_expr} AS service_calculation_method
        FROM transactions t
        INNER JOIN marks m ON t.mark_id = m.id
        {mark_coa_join}
        LEFT JOIN companies c ON t.company_id = c.id
        WHERE {effective_coa_id} = :coa_id
          AND (:start_date IS NULL OR t.txn_date >= :start_date)
          AND (:end_date IS NULL OR t.txn_date <= :end_date)
          AND (:company_id IS NULL OR t.company_id = :company_id)
          {split_exclusion}
        ORDER BY t.txn_date DESC
    """)


def build_marks_summary_query(report_type='real'):
    """
    Build marks summary query with split exclusion and coretax filtering.

    IMPORTANT: We do NOT join with mark_coa_mapping to avoid duplication.
    A mark can have multiple COA mappings, which would cause transactions
    to be counted multiple times.

    For CoreTax filtering, we use the marks.is_coretax flag instead of
    joining with mark_coa_mapping.

    Args:
        report_type: 'real' or 'coretax' - determines which marks to include

    Returns:
        SQLAlchemy text query object
    """
    # Split exclusion: exclude parent transactions that have children with marks
    split_exclusion = """
    AND NOT EXISTS (
        SELECT 1 FROM transactions t_child
        WHERE t_child.parent_id = t.id
        AND t_child.mark_id IS NOT NULL
    )
    """

    # For coretax, filter by marks.is_coretax flag
    # This avoids duplication while still filtering marks correctly
    coretax_filter = ""
    if report_type == 'coretax':
        coretax_filter = "AND COALESCE(m.is_coretax, 0) = 1"

    return text(f"""
        SELECT
            m.id as mark_id,
            m.personal_use as mark_name,
            SUM(CASE
                WHEN t.db_cr = 'CR' THEN t.amount
                WHEN t.db_cr = 'DB' THEN 0
                ELSE 0
            END) as total_debit,
            SUM(CASE
                WHEN t.db_cr = 'DB' THEN t.amount
                WHEN t.db_cr = 'CR' THEN 0
                ELSE 0
            END) as total_credit,
            COUNT(DISTINCT t.id) as transaction_count
        FROM transactions t
        INNER JOIN marks m ON t.mark_id = m.id
        WHERE t.txn_date >= :start_date AND t.txn_date <= :end_date
          AND (:company_id IS NULL OR t.company_id = :company_id)
          {split_exclusion}
          {coretax_filter}
        GROUP BY m.id, m.personal_use
        ORDER BY mark_name ASC
    """)
