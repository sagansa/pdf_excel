from datetime import datetime

from sqlalchemy import text

from backend.db.schema import get_table_columns
from backend.services.report_common import (
    _coretax_filter_clause,
    _fetch_sagansa_user_map,
    _parse_date,
    _split_parent_exclusion_clause,
    _to_float,
)


def fetch_payroll_salary_summary_data(conn, start_date, end_date, company_id=None, report_type='real'):
    """
    Fetch payroll summary grouped by month -> employee -> salary component(mark).
    Respects report period and company filter.
    """
    mark_columns = get_table_columns(conn, 'marks')
    if 'is_salary_component' not in mark_columns:
        return {
            'period': {'start_date': start_date, 'end_date': end_date},
            'months': [],
            'summary': {
                'total_amount': 0.0,
                'total_transactions': 0,
                'employee_count': 0,
                'month_count': 0
            },
            'message': 'Kolom is_salary_component belum tersedia. Jalankan migrasi terbaru.'
        }

    txn_columns = get_table_columns(conn, 'transactions')
    split_exclusion_clause = _split_parent_exclusion_clause(conn, 't')
    coretax_clause = _coretax_filter_clause(conn, report_type, 'm')
    user_col_expr = "t.sagansa_user_id" if 'sagansa_user_id' in txn_columns else "NULL"
    effective_date_expr = "COALESCE(t.payroll_period_month, t.txn_date)" if 'payroll_period_month' in txn_columns else "t.txn_date"
    if conn.dialect.name == 'sqlite':
        month_key_expr = f"strftime('%Y-%m', {effective_date_expr})"
    else:
        month_key_expr = f"DATE_FORMAT({effective_date_expr}, '%Y-%m')"

    query = text(f"""
        SELECT
            {month_key_expr} AS month_key,
            {user_col_expr} AS sagansa_user_id,
            COALESCE(m.personal_use, m.internal_report, m.tax_report, '(Unnamed Salary Component)') AS mark_name,
            COUNT(t.id) AS transaction_count,
            COALESCE(SUM(ABS(t.amount)), 0) AS total_amount
        FROM transactions t
        INNER JOIN marks m ON t.mark_id = m.id
        WHERE COALESCE(m.is_salary_component, 0) = 1
          AND {effective_date_expr} BETWEEN :start_date AND :end_date
          AND (:company_id IS NULL OR t.company_id = :company_id)
          {split_exclusion_clause}
                {coretax_clause}
        GROUP BY
            {month_key_expr},
            {user_col_expr},
            COALESCE(m.personal_use, m.internal_report, m.tax_report, '(Unnamed Salary Component)')
        ORDER BY
            {month_key_expr} ASC,
            {user_col_expr} ASC
    """)

    user_map = _fetch_sagansa_user_map()
    month_groups = {}
    employee_set = set()
    total_amount = 0.0
    total_transactions = 0

    rows = conn.execute(query, {
        'start_date': start_date,
        'end_date': end_date,
        'company_id': company_id
    })

    for row in rows:
        month_key = str(row.month_key or '').strip()
        if not month_key:
            continue

        user_id = str(row.sagansa_user_id or '').strip() or None
        user_name = user_map.get(user_id, {}).get('name') if user_id else None
        if user_id:
            employee_set.add(user_id)

        mark_name = str(row.mark_name or '').strip() or '(Unnamed Salary Component)'
        tx_count = int(row.transaction_count or 0)
        amount = _to_float(row.total_amount, 0.0)

        if month_key not in month_groups:
            try:
                month_label = datetime.strptime(f"{month_key}-01", '%Y-%m-%d').strftime('%B %Y')
            except Exception:
                month_label = month_key
            month_groups[month_key] = {
                'month_key': month_key,
                'month_label': month_label,
                'transaction_count': 0,
                'total_amount': 0.0,
                'rows': []
            }

        month_groups[month_key]['rows'].append({
            'sagansa_user_id': user_id,
            'sagansa_user_name': user_name or user_id or 'Unassigned',
            'mark_name': mark_name,
            'transaction_count': tx_count,
            'total_amount': amount
        })
        month_groups[month_key]['transaction_count'] += tx_count
        month_groups[month_key]['total_amount'] += amount
        total_transactions += tx_count
        total_amount += amount

    # Ensure each month in requested period exists in output, even without transactions.
    start_obj = _parse_date(start_date)
    end_obj = _parse_date(end_date)
    if start_obj and end_obj and end_obj >= start_obj:
        cursor = start_obj.replace(day=1)
        limit = end_obj.replace(day=1)
        while cursor <= limit:
            month_key = cursor.strftime('%Y-%m')
            if month_key not in month_groups:
                month_groups[month_key] = {
                    'month_key': month_key,
                    'month_label': cursor.strftime('%B %Y'),
                    'transaction_count': 0,
                    'total_amount': 0.0,
                    'rows': []
                }
            if cursor.month == 12:
                cursor = cursor.replace(year=cursor.year + 1, month=1, day=1)
            else:
                cursor = cursor.replace(month=cursor.month + 1, day=1)

    months = []
    for month_key in sorted(month_groups.keys()):
        group = month_groups[month_key]
        group['rows'] = sorted(
            group['rows'],
            key=lambda item: (item.get('sagansa_user_name') or '', item.get('mark_name') or '')
        )
        group['total_amount'] = round(_to_float(group['total_amount'], 0.0), 2)
        months.append(group)

    return {
        'period': {'start_date': start_date, 'end_date': end_date},
        'months': months,
        'summary': {
            'total_amount': round(_to_float(total_amount, 0.0), 2),
            'total_transactions': int(total_transactions),
            'employee_count': len(employee_set),
            'month_count': len(months)
        }
    }
