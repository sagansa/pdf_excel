from flask import Blueprint, jsonify, request

from backend.errors import ApiError, BadRequestError
from backend.routes.accounting_utils import require_db_engine, serialize_result_rows
from backend.routes.general_ledger_helpers import (
    build_ledger_groups,
    coretax_filter_clause,
    export_ledger_to_excel,
    mark_coa_join_clause,
)
from backend.routes.general_ledger_queries import (
    build_general_ledger_entries_query,
    build_general_ledger_summary_query,
)

general_ledger_bp = Blueprint('general_ledger', __name__)

@general_ledger_bp.route('/api/reports/general-ledger', methods=['GET'])
def get_general_ledger():
    """
    Get General Ledger (Buku Besar) for a company and date range.
    Shows all transactions with debit and credit entries (double-entry).
    Each transaction shows both COA entries together.
    """
    engine = require_db_engine()
    company_id = request.args.get('company_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    coa_code = request.args.get('coa_code')
    report_type = request.args.get('report_type', 'real')

    if not start_date or not end_date:
        raise BadRequestError('start_date and end_date are required')

    with engine.connect() as conn:
        params = {'start_date': start_date, 'end_date': end_date}
        company_filter = ""
        coa_filter = ""
        if company_id:
            company_filter = "AND t.company_id = :company_id"
            params['company_id'] = company_id
        if coa_code:
            coa_filter = "AND coa.code = :coa_code"
            params['coa_code'] = coa_code

        result = conn.execute(
            build_general_ledger_entries_query(
                mark_coa_join=mark_coa_join_clause(conn, report_type, mark_ref='m.id', mapping_alias='mcm', join_type='INNER'),
                company_filter=company_filter,
                coretax_filter=coretax_filter_clause(conn, report_type, 'm'),
                coa_filter=coa_filter,
            ),
            params
        )
        grouped = build_ledger_groups(result)

    return jsonify({
        'success': True,
        'data': {
            'company_id': company_id,
            'start_date': start_date,
            'end_date': end_date,
            'report_type': report_type,
            'coa_groups': grouped['coa_groups_list'],
            'total_accounts': len(grouped['coa_groups_list']),
            'total_transactions': len(grouped['transactions']),
            'grand_total_debit': grouped['grand_total_debit'],
            'grand_total_credit': grouped['grand_total_credit'],
            'is_balanced': abs(grouped['grand_total_debit'] - grouped['grand_total_credit']) < 0.01,
        }
    })


@general_ledger_bp.route('/api/reports/general-ledger/export', methods=['GET'])
def export_general_ledger():
    """
    Export General Ledger to Excel or PDF format.
    """
    engine = require_db_engine()
    company_id = request.args.get('company_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    coa_code = request.args.get('coa_code')
    format_type = request.args.get('format', 'excel')
    report_type = request.args.get('report_type', 'real')

    if not start_date or not end_date:
        raise BadRequestError('start_date and end_date are required')

    with engine.connect() as conn:
        params = {'start_date': start_date, 'end_date': end_date}
        company_filter = ""
        coa_filter = ""
        if company_id:
            company_filter = "AND t.company_id = :company_id"
            params['company_id'] = company_id
        if coa_code:
            coa_filter = "AND coa.code = :coa_code"
            params['coa_code'] = coa_code

        result = conn.execute(
            build_general_ledger_entries_query(
                mark_coa_join=mark_coa_join_clause(conn, report_type, mark_ref='m.id', mapping_alias='mcm', join_type='INNER'),
                company_filter=company_filter,
                coretax_filter=coretax_filter_clause(conn, report_type, 'm'),
                coa_filter=coa_filter,
            ),
            params
        )
        grouped = build_ledger_groups(result)

    if format_type != 'excel':
        raise BadRequestError('PDF export not yet implemented')
    try:
        return export_ledger_to_excel(grouped['coa_groups'], company_id or 'all', start_date, end_date)
    except Exception as exc:
        raise ApiError(f'Failed to create Excel file: {exc}', status_code=500, code='excel_export_failed')


@general_ledger_bp.route('/api/reports/general-ledger/summary', methods=['GET'])
def get_general_ledger_summary():
    """
    Get General Ledger Summary - COA balances for a period.
    """
    engine = require_db_engine()
    company_id = request.args.get('company_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    report_type = request.args.get('report_type', 'real')

    if not start_date or not end_date:
        raise BadRequestError('start_date and end_date are required')

    with engine.connect() as conn:
        params = {'start_date': start_date, 'end_date': end_date}
        company_filter = ""
        if company_id:
            company_filter = "AND t.company_id = :company_id"
            params['company_id'] = company_id

        result = conn.execute(
            build_general_ledger_summary_query(
                mark_coa_join=mark_coa_join_clause(conn, report_type, mark_ref='m.id', mapping_alias='mcm', join_type='INNER'),
                company_filter=company_filter,
                coretax_filter=coretax_filter_clause(conn, report_type, 'm'),
            ),
            params
        )
        summary = [
            {
                'coa_code': data['coa_code'],
                'coa_name': data['coa_name'],
                'coa_category': data['coa_category'],
                'balance': float(data['balance'] or 0),
                'total_debit': float(data['total_debit'] or 0),
                'total_credit': float(data['total_credit'] or 0),
                'transaction_count': data['transaction_count'],
            }
            for data in serialize_result_rows(result)
        ]

    return jsonify({
        'success': True,
        'data': {
            'company_id': company_id,
            'start_date': start_date,
            'end_date': end_date,
            'report_type': report_type,
            'accounts': summary,
            'total_accounts': len(summary),
        }
    })
