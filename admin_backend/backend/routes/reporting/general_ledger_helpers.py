import io

import pandas as pd
from flask import make_response, send_file

from backend.db.schema import get_table_columns
from backend.routes.accounting_utils import serialize_row_values


def coretax_filter_clause(conn, report_type, alias='m'):
    if str(report_type).strip().lower() != 'coretax':
        return ''

    mark_columns = get_table_columns(conn, 'marks')
    if 'is_coretax' in mark_columns:
        if conn.dialect.name == 'sqlite':
            return f" AND LOWER(COALESCE(CAST({alias}.is_coretax AS TEXT), '0')) IN ('1', 'true', 'yes', 'y')"
        return f" AND LOWER(COALESCE(CAST({alias}.is_coretax AS CHAR), '0')) IN ('1', 'true', 'yes', 'y')"

    return f" AND ({alias}.tax_report IS NOT NULL AND TRIM({alias}.tax_report) != '')"


def mapping_report_type_expr(conn, alias, fallback='real'):
    if conn.dialect.name == 'sqlite':
        return f"LOWER(COALESCE(CAST({alias}.report_type AS TEXT), '{fallback}'))"
    return f"LOWER(COALESCE(CAST({alias}.report_type AS CHAR), '{fallback}'))"


def mark_coa_join_clause(conn, report_type='real', mark_ref='m.id', mapping_alias='mcm', join_type='INNER'):
    mapping_columns = get_table_columns(conn, 'mark_coa_mapping')
    normalized_report_type = str(report_type or 'real').strip().lower()
    if normalized_report_type != 'coretax':
        normalized_report_type = 'real'

    if 'report_type' not in mapping_columns:
        return f"{join_type} JOIN mark_coa_mapping {mapping_alias} ON {mapping_alias}.mark_id = {mark_ref}"

    mapping_scope_expr = mapping_report_type_expr(conn, mapping_alias, 'real')

    if normalized_report_type == 'coretax':
        fallback_alias = f"{mapping_alias}_coretax"
        fallback_scope_expr = mapping_report_type_expr(conn, fallback_alias, 'real')
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


def build_ledger_groups(rows):
    transactions = {}
    coa_groups = {}

    for row in rows:
        data = serialize_row_values(row._mapping, datetime_format='%Y-%m-%d')
        txn_id = data['transaction_id']

        if txn_id not in transactions:
            transactions[txn_id] = {
                'transaction_id': txn_id,
                'txn_date': str(data['txn_date']),
                'description': data['description'] or '',
                'mark_name': data['mark_name'] or '',
                'amount': float(data['amount'] or 0),
                'db_cr': data['db_cr'],
                'entries': [],
            }

        coa_code = data['coa_code']
        signed_amount = float(data['signed_amount'] or 0)
        transactions[txn_id]['entries'].append({
            'coa_code': coa_code,
            'coa_name': data['coa_name'],
            'coa_category': data['coa_category'],
            'mapping_type': data['mapping_type'],
            'debit': signed_amount if signed_amount > 0 else 0,
            'credit': abs(signed_amount) if signed_amount < 0 else 0,
            'signed_amount': signed_amount,
        })

    for txn in transactions.values():
        for entry in txn['entries']:
            coa_code = entry['coa_code']
            if coa_code not in coa_groups:
                coa_groups[coa_code] = {
                    'coa_code': coa_code,
                    'coa_name': entry['coa_name'],
                    'coa_category': entry['coa_category'],
                    'transactions': [],
                    'total_debit': 0,
                    'total_credit': 0,
                    'ending_balance': 0,
                    'running_balance': 0,
                }

            coa_groups[coa_code]['running_balance'] += entry['signed_amount']
            coa_groups[coa_code]['transactions'].append({
                'transaction_id': txn['transaction_id'],
                'txn_date': txn['txn_date'],
                'description': txn['description'],
                'mark_name': txn['mark_name'],
                'amount': txn['amount'],
                'db_cr': txn['db_cr'],
                'entries': txn['entries'],
                'current_entry': {
                    'coa_code': entry['coa_code'],
                    'debit': entry['debit'],
                    'credit': entry['credit'],
                    'running_balance': coa_groups[coa_code]['running_balance'],
                },
            })
            coa_groups[coa_code]['total_debit'] += entry['debit']
            coa_groups[coa_code]['total_credit'] += entry['credit']
            coa_groups[coa_code]['ending_balance'] = coa_groups[coa_code]['running_balance']

    coa_groups_list = []
    for coa_code, group in coa_groups.items():
        formatted_transactions = []
        seen_txns = set()
        for txn in group['transactions']:
            if txn['transaction_id'] in seen_txns:
                continue
            seen_txns.add(txn['transaction_id'])
            formatted_transactions.append({
                'transaction_id': txn['transaction_id'],
                'txn_date': txn['txn_date'],
                'description': txn['description'],
                'mark_name': txn['mark_name'],
                'amount': txn['amount'],
                'db_cr': txn['db_cr'],
                'entries': txn['entries'],
                'current_entry': txn['current_entry'],
            })

        coa_groups_list.append({
            'coa_code': group['coa_code'],
            'coa_name': group['coa_name'],
            'coa_category': group['coa_category'],
            'transactions': formatted_transactions,
            'total_debit': group['total_debit'],
            'total_credit': group['total_credit'],
            'ending_balance': group['ending_balance'],
        })

    grand_total_debit = sum(group['total_debit'] for group in coa_groups_list)
    grand_total_credit = sum(group['total_credit'] for group in coa_groups_list)

    return {
        'transactions': transactions,
        'coa_groups': coa_groups,
        'coa_groups_list': coa_groups_list,
        'grand_total_debit': grand_total_debit,
        'grand_total_credit': grand_total_credit,
    }


def export_ledger_to_excel(coa_groups, company_id, start_date, end_date):
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        summary_data = []
        for coa_code, group in coa_groups.items():
            summary_data.append({
                'COA Code': group['coa_code'],
                'COA Name': group['coa_name'],
                'Category': group['coa_category'],
                'Total Debit': group['total_debit'],
                'Total Credit': group['total_credit'],
                'Ending Balance': group['ending_balance'],
            })

        pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)

        for coa_code, group in coa_groups.items():
            detailed_data = []
            for txn in group['transactions']:
                for entry in txn['entries']:
                    if entry['coa_code'] != coa_code:
                        continue
                    detailed_data.append({
                        'Tanggal': txn['txn_date'],
                        'Deskripsi': txn['description'],
                        'Mark': txn['mark_name'],
                        'COA': entry['coa_code'],
                        'Debit': entry['debit'] if entry['debit'] > 0 else 0,
                        'Kredit': entry['credit'] if entry['credit'] > 0 else 0,
                        'Saldo': entry['current_entry']['running_balance'] if entry['current_entry'] else 0,
                    })

            if detailed_data:
                sheet_name = f"{coa_code}_{group['coa_name']}"[:31].replace('/', '_').replace('\\', '_')
                pd.DataFrame(detailed_data).to_excel(writer, sheet_name=sheet_name, index=False)

    output.seek(0)
    return make_response(send_file(
        output,
        as_attachment=True,
        download_name=f'general_ledger_{company_id}_{start_date}_to_{end_date}.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    ))
