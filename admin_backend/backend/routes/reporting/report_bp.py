from datetime import datetime

from flask import Blueprint, jsonify, request

from backend.db.schema import get_table_columns
from backend.errors import BadRequestError
from backend.routes.accounting_utils import (
    require_db_engine,
    serialize_result_rows,
    split_parent_exclusion_clause,
)
from backend.routes.reporting.report_helpers import (
    apply_service_tax_adjustment,
    calculate_coa_effective_amount,
    default_report_period,
    get_coa_or_404,
    get_first_active_coa_id,
    parse_year_or_default,
    resolve_coa_detail_period,
    serialize_row_values,
)
from backend.routes.reporting.report_queries import (
    build_available_years_query,
    build_coa_detail_query,
    build_marks_summary_query,
)
from backend.services.reporting.report_service import (
    fetch_balance_sheet_data,
    fetch_cash_flow_data,
    fetch_income_statement_data,
    fetch_monthly_revenue_data,
    fetch_payroll_salary_summary_data,
)
from backend.services.reporting.report_sql_fragments import _get_reporting_start_date

report_bp = Blueprint('report_bp', __name__)


@report_bp.route('/api/reports/income-statement', methods=['GET'])
def get_income_statement():
    engine = require_db_engine()

    start_date, end_date = default_report_period(
        request.args.get('start_date'),
        request.args.get('end_date')
    )
    company_id = request.args.get('company_id')
    report_type = request.args.get('report_type', 'real')
    comparative = request.args.get('comparative', 'false').lower() == 'true'

    with engine.connect() as conn:
        data = fetch_income_statement_data(conn, start_date, end_date, company_id, report_type, comparative=comparative)
        data['period'] = {'start_date': start_date, 'end_date': end_date}
        data['comparative'] = comparative
        return jsonify(data)


@report_bp.route('/api/reports/balance-sheet', methods=['GET'])
def get_balance_sheet():
    engine = require_db_engine()

    as_of_date = request.args.get('date') or request.args.get('as_of_date') or datetime.now().strftime('%Y-%m-%d')
    company_id = request.args.get('company_id')
    report_type = request.args.get('report_type', 'real')

    with engine.connect() as conn:
        data = fetch_balance_sheet_data(conn, as_of_date, company_id, report_type)
        return jsonify(data)


@report_bp.route('/api/reports/monthly-revenue', methods=['GET'])
def get_monthly_revenue():
    engine = require_db_engine()

    year = parse_year_or_default(request.args.get('year'))
    company_id = request.args.get('company_id')
    report_type = request.args.get('report_type', 'real')

    with engine.connect() as conn:
        current_data = fetch_monthly_revenue_data(conn, year, company_id, report_type)
        prev_data = fetch_monthly_revenue_data(conn, year - 1, company_id, report_type)
        return jsonify({
            'year': year,
            'data': current_data,
            'prev_year_data': prev_data
        })


@report_bp.route('/api/reports/cash-flow', methods=['GET'])
def get_cash_flow():
    engine = require_db_engine()

    start_date, end_date = default_report_period(
        request.args.get('start_date'),
        request.args.get('end_date')
    )
    company_id = request.args.get('company_id')
    report_type = request.args.get('report_type', 'real')

    with engine.connect() as conn:
        data = fetch_cash_flow_data(conn, start_date, end_date, company_id, report_type)
        return jsonify(data)


@report_bp.route('/api/reports/payroll-salary-summary', methods=['GET'])
def get_payroll_salary_summary():
    engine = require_db_engine()

    start_date, end_date = default_report_period(
        request.args.get('start_date'),
        request.args.get('end_date')
    )
    company_id = request.args.get('company_id')
    report_type = request.args.get('report_type', 'real')

    with engine.connect() as conn:
        data = fetch_payroll_salary_summary_data(conn, start_date, end_date, company_id, report_type)
        return jsonify(data)


@report_bp.route('/api/reports/available-years', methods=['GET'])
def get_available_report_years():
    engine = require_db_engine()
    company_id = request.args.get('company_id')

    with engine.connect() as conn:
        split_exclusion = split_parent_exclusion_clause(conn, 't')
        year_expr = "CAST(strftime('%Y', t.txn_date) AS INTEGER)" if conn.dialect.name == 'sqlite' else "YEAR(t.txn_date)"
        query = build_available_years_query(year_expr, split_exclusion)

        years = []
        for row in conn.execute(query, {'company_id': company_id}):
            try:
                year_val = int(row.year)
            except (TypeError, ValueError):
                continue
            if year_val > 0:
                years.append(year_val)

        if not years:
            years = [datetime.now().year]
        return jsonify({'years': years})


@report_bp.route('/api/reports/coa-detail', methods=['GET'])
def get_coa_detail_report():
    engine = require_db_engine()

    coa_id = request.args.get('coa_id')
    as_of_date = request.args.get('as_of_date')

    temp_coa_id = coa_id
    if not temp_coa_id:
        with engine.connect() as conn:
            temp_coa_id = get_first_active_coa_id(conn)

    with engine.connect() as conn:
        coa_info = get_coa_or_404(conn, temp_coa_id)
        coa_category = coa_info.get('category', '')

    coa_id = temp_coa_id
    company_id = request.args.get('company_id')
    report_type = request.args.get('report_type', 'real')

    start_date, end_date = resolve_coa_detail_period(
        coa_category,
        as_of_date,
        request.args.get('start_date'),
        request.args.get('end_date')
    )

    with engine.connect() as conn:
        reporting_start_date = _get_reporting_start_date(conn, company_id, report_type)
        if reporting_start_date:
            if not start_date or start_date < reporting_start_date:
                start_date = reporting_start_date
                
        coa_info = get_coa_or_404(conn, coa_id)
        coa_category = coa_info.get('category', '')
        split_exclusion = split_parent_exclusion_clause(conn, 't')
        txn_columns = get_table_columns(conn, 'transactions')
        npwp_expr = "t.service_npwp" if 'service_npwp' in txn_columns else "NULL"
        method_expr = "COALESCE(t.service_calculation_method, 'BRUTO')" if 'service_calculation_method' in txn_columns else "'BRUTO'"

        result = conn.execute(build_coa_detail_query(npwp_expr, method_expr, split_exclusion, report_type), {
            'coa_id': coa_id,
            'start_date': start_date,
            'end_date': end_date,
            'company_id': company_id
        })

        transactions = []
        total = 0.0
        for row in result:
            data = serialize_row_values(row._mapping)
            amount = float(data['amount'])
            data['effective_amount'] = calculate_coa_effective_amount(
                coa_category,
                amount,
                data['db_cr'],
                data['mapping_type']
            )
            data = apply_service_tax_adjustment(data, coa_category)

            total += data['effective_amount']
            transactions.append(data)

        return jsonify({
            'coa': {'code': coa_info['code'], 'name': coa_info['name'], 'category': coa_info['category']},
            'transactions': transactions,
            'total': total
        })


@report_bp.route('/api/reports/marks-summary', methods=['GET'])
def get_marks_summary():
    engine = require_db_engine()

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    company_id = request.args.get('company_id')
    report_type = request.args.get('report_type', 'real')
    if not start_date or not end_date:
        raise BadRequestError('start_date and end_date are required')

    with engine.connect() as conn:
        result = conn.execute(build_marks_summary_query(report_type), {
            'start_date': start_date,
            'end_date': end_date,
            'company_id': company_id
        })

        marks = []
        total_debit_all = 0.0
        total_credit_all = 0.0
        for data in serialize_result_rows(result):
            total_debit = float(data['total_debit'] or 0)
            total_credit = float(data['total_credit'] or 0)
            total_debit_all += total_debit
            total_credit_all += total_credit
            marks.append({
                'mark_id': data['mark_id'],
                'mark_name': data['mark_name'] or 'Unnamed Mark',
                'total_debit': total_debit,
                'total_credit': total_credit,
                'net_amount': total_debit - total_credit,
                'transaction_count': data['transaction_count']
            })

        return jsonify({
            'marks': marks,
            'summary': {
                'total_debit': total_debit_all,
                'total_credit': total_credit_all,
                'net_difference': total_debit_all - total_credit_all,
                'total_marks': len(marks)
            }
        })


@report_bp.route('/api/reports/prepaid-expenses', methods=['GET'])
def get_prepaid_expenses():
    return jsonify({
        'items': [],
        'message': 'Prepaid Rent & Amortization feature has been retired'
    })


@report_bp.route('/api/reports/prepaid-linkable-transactions', methods=['GET'])
@report_bp.route('/api/reports/prepaid-eligible-transactions', methods=['GET'])
def get_prepaid_linkable_transactions():
    return jsonify({
        'transactions': [],
        'message': 'Prepaid Rent & Amortization feature has been retired'
    })
