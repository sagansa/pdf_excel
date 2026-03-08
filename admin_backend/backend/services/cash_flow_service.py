from datetime import date, datetime

from sqlalchemy import text

from backend.services.report_sql_fragments import (
    _coretax_filter_clause,
    _mark_coa_join_clause,
    _split_parent_exclusion_clause,
)
from backend.services.report_value_utils import (
    _parse_date,
    _to_float,
)


SECTION_NAMES = {
    'operating': 'Operating Activities',
    'investing': 'Investing Activities',
    'financing': 'Financing Activities',
    'unclassified': 'Unclassified',
}
ORDERED_SECTIONS = ['operating', 'investing', 'financing', 'unclassified']


def _build_cash_flow_transactions_query(conn, report_type, split_exclusion_clause, coretax_clause):
    mark_coa_join = _mark_coa_join_clause(conn, report_type, mark_ref='m.id', mapping_alias='mcm', join_type='LEFT')
    return text(f"""
        SELECT
            t.id,
            t.txn_date,
            t.description,
            t.amount,
            t.db_cr,
            t.company_id,
            c.name AS company_name,
            m.personal_use,
            m.internal_report,
            MAX(CASE WHEN coa.category IN ('REVENUE', 'EXPENSE') THEN 1 ELSE 0 END) AS operating_flag,
            MAX(CASE WHEN coa.category = 'ASSET'
                      AND NOT (
                        coa.code LIKE '11%%'
                        OR coa.code LIKE '12%%'
                        OR coa.code LIKE '13%%'
                        OR coa.code LIKE '14%%'
                      )
                     THEN 1 ELSE 0 END) AS investing_flag,
            MAX(CASE WHEN coa.category IN ('LIABILITY', 'EQUITY') THEN 1 ELSE 0 END) AS financing_flag
        FROM transactions t
        LEFT JOIN companies c ON t.company_id = c.id
        LEFT JOIN marks m ON t.mark_id = m.id
        {mark_coa_join}
        LEFT JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
        WHERE t.txn_date BETWEEN :start_date AND :end_date
          AND (:company_id IS NULL OR t.company_id = :company_id)
          {split_exclusion_clause}
                {coretax_clause}
        GROUP BY
            t.id, t.txn_date, t.description, t.amount, t.db_cr,
            t.company_id, c.name, m.personal_use, m.internal_report
        ORDER BY t.txn_date ASC, t.id ASC
    """)


def _build_cash_balance_query(date_field, split_exclusion_clause, coretax_clause):
    return text(f"""
        SELECT
            COALESCE(SUM(
                CASE
                    WHEN t.db_cr = 'DB' THEN t.amount
                    WHEN t.db_cr = 'CR' THEN -t.amount
                    ELSE 0
                END
            ), 0) AS cash_balance
        FROM transactions t
        LEFT JOIN marks m ON t.mark_id = m.id
        WHERE t.txn_date {date_field}
          AND (:company_id IS NULL OR t.company_id = :company_id)
          {split_exclusion_clause}
          {coretax_clause}
    """)


def _empty_cash_flow_sections():
    return {
        key: {
            'name': SECTION_NAMES[key],
            'inflow_total': 0.0,
            'outflow_total': 0.0,
            'net_cash': 0.0,
            'count': 0,
            'items': [],
        }
        for key in ORDERED_SECTIONS
    }


def _classify_cash_flow_section(row):
    if int(row.investing_flag or 0) == 1:
        return 'investing'
    if int(row.financing_flag or 0) == 1:
        return 'financing'
    if int(row.operating_flag or 0) == 1:
        return 'operating'
    return 'unclassified'


def _cash_flow_row_amounts(row):
    amount = abs(_to_float(row.amount, 0.0))
    db_cr = str(row.db_cr or '').upper().strip()
    signed_amount = amount if db_cr == 'DB' else (-amount if db_cr == 'CR' else 0.0)
    inflow = signed_amount if signed_amount > 0 else 0.0
    outflow = abs(signed_amount) if signed_amount < 0 else 0.0
    return amount, db_cr, signed_amount, inflow, outflow


def _append_cash_flow_row(sections, row):
    amount, db_cr, signed_amount, inflow, outflow = _cash_flow_row_amounts(row)
    section = sections[_classify_cash_flow_section(row)]
    section['inflow_total'] += inflow
    section['outflow_total'] += outflow
    section['count'] += 1
    section['items'].append({
        'id': str(row.id),
        'txn_date': row.txn_date.isoformat() if isinstance(row.txn_date, (datetime, date)) else str(row.txn_date or ''),
        'description': row.description,
        'amount': amount,
        'db_cr': db_cr,
        'signed_amount': signed_amount,
        'company_id': row.company_id,
        'company_name': row.company_name,
        'mark_name': row.personal_use or row.internal_report,
    })


def _finalize_cash_flow_sections(sections):
    for key in ORDERED_SECTIONS:
        section = sections[key]
        section['net_cash'] = section['inflow_total'] - section['outflow_total']
        section['inflow_total'] = round(section['inflow_total'], 2)
        section['outflow_total'] = round(section['outflow_total'], 2)
        section['net_cash'] = round(section['net_cash'], 2)


def _calculate_cash_balance(conn, query, balance_date, company_id):
    row = conn.execute(query, {'balance_date': balance_date, 'company_id': company_id}).fetchone()
    return _to_float(row.cash_balance if row else 0.0, 0.0)


def fetch_cash_flow_data(conn, start_date, end_date, company_id=None, report_type='real'):
    """
    Fetch cash flow report using direct method from transaction cash movements.
    Classification heuristic:
      - operating: revenue/expense mappings
      - investing: non-current asset mappings
      - financing: liability/equity mappings
      - unclassified: no mapping signal
    """
    split_exclusion_clause = _split_parent_exclusion_clause(conn, 't')
    coretax_clause = _coretax_filter_clause(conn, report_type, 'm')
    rows = conn.execute(_build_cash_flow_transactions_query(conn, report_type, split_exclusion_clause, coretax_clause), {
        'start_date': start_date,
        'end_date': end_date,
        'company_id': company_id
    })

    sections = _empty_cash_flow_sections()

    for row in rows:
        _append_cash_flow_row(sections, row)

    _finalize_cash_flow_sections(sections)

    opening_query = _build_cash_balance_query('< :balance_date', split_exclusion_clause, coretax_clause)
    opening_cash = _calculate_cash_balance(conn, opening_query, start_date, company_id)

    closing_query = _build_cash_balance_query('<= :balance_date', split_exclusion_clause, coretax_clause)
    closing_cash = _calculate_cash_balance(conn, closing_query, end_date, company_id)

    operating_net = sections['operating']['net_cash']
    investing_net = sections['investing']['net_cash']
    financing_net = sections['financing']['net_cash']
    unclassified_net = sections['unclassified']['net_cash']
    net_change_by_sections = operating_net + investing_net + financing_net + unclassified_net
    net_change_by_balance = closing_cash - opening_cash

    return {
        'period': {
            'start_date': start_date,
            'end_date': end_date
        },
        'sections': sections,
        'section_order': ORDERED_SECTIONS,
        'summary': {
            'opening_cash': round(opening_cash, 2),
            'operating_net': round(operating_net, 2),
            'investing_net': round(investing_net, 2),
            'financing_net': round(financing_net, 2),
            'unclassified_net': round(unclassified_net, 2),
            'net_change': round(net_change_by_sections, 2),
            'closing_cash': round(closing_cash, 2),
            'reconciliation_difference': round(net_change_by_balance - net_change_by_sections, 2)
        }
    }
