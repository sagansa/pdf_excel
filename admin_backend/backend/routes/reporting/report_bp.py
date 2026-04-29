import uuid
from datetime import datetime

from flask import Blueprint, jsonify, request, send_file
from sqlalchemy import text

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
from backend.services.reporting.amortization_report_service import fetch_amortization_report_data
from backend.services.reporting.report_sql_fragments import _get_reporting_start_date

report_bp = Blueprint('report_bp', __name__)


def _resolve_report_year(filters, start_date=None, as_of_date=None):
    raw_year = filters.get('year')
    if raw_year:
        try:
            return int(raw_year)
        except (TypeError, ValueError):
            pass

    for candidate in (start_date, as_of_date):
        if candidate:
            try:
                return datetime.strptime(candidate, '%Y-%m-%d').year
            except ValueError:
                continue

    return datetime.now().year


def _load_report_settings(conn, company_id, year):
    settings = conn.execute(text("""
        SELECT * FROM report_settings
        WHERE company_id = :company_id AND year = :year
    """), {'company_id': company_id, 'year': year}).fetchone()

    if settings:
        return serialize_row_values(settings._mapping)

    return {
        'director_name': '(Belum diatur)',
        'director_title': 'Direktur Utama',
        'location': 'Jakarta'
    }


def _load_company_name(conn, company_id):
    company_row = conn.execute(text("SELECT name FROM companies WHERE id = :id"), {'id': company_id}).fetchone()
    if company_row:
        return company_row.name
    return 'Company Name'


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

        result = conn.execute(build_coa_detail_query(conn, npwp_expr, method_expr, split_exclusion, report_type), {
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


@report_bp.route('/api/reports/settings', methods=['GET'])
def get_report_settings():
    engine = require_db_engine()
    company_id = request.args.get('company_id')
    year_str = request.args.get('year')

    if not company_id or not year_str:
        return jsonify({'error': 'company_id and year are required'}), 400

    try:
        year = int(year_str)
    except ValueError:
        return jsonify({'error': 'year must be integer'}), 400

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT * FROM report_settings 
            WHERE company_id = :company_id AND year = :year
        """), {'company_id': company_id, 'year': year}).fetchone()

        if result:
            return jsonify(serialize_row_values(result._mapping))
        
        return jsonify({
            'company_id': company_id,
            'year': year,
            'director_name': '',
            'director_title': 'Direktur Utama',
            'location': 'Jakarta'
        })


@report_bp.route('/api/reports/settings', methods=['POST', 'PUT'])
def save_report_settings():
    engine = require_db_engine()
    data = request.json or {}
    company_id = data.get('company_id')
    year_val = data.get('year')

    if not company_id or not year_val:
        return jsonify({'error': 'company_id and year are required'}), 400

    try:
        year = int(year_val)
    except ValueError:
        return jsonify({'error': 'year must be integer'}), 400

    with engine.begin() as conn:
        # Check if exists
        existing = conn.execute(text("""
            SELECT id FROM report_settings 
            WHERE company_id = :company_id AND year = :year
        """), {'company_id': company_id, 'year': year}).fetchone()

        params = {
            'company_id': company_id,
            'year': year,
            'director_name': data.get('director_name'),
            'director_title': data.get('director_title', 'Direktur Utama'),
            'location': data.get('location', 'Jakarta'),
            'updated_at': datetime.now()
        }

        if existing:
            conn.execute(text("""
                UPDATE report_settings 
                SET director_name = :director_name,
                    director_title = :director_title,
                    location = :location,
                    updated_at = :updated_at
                WHERE id = :id
            """), {**params, 'id': existing.id})
        else:
            params['id'] = str(uuid.uuid4())
            conn.execute(text("""
                INSERT INTO report_settings (id, company_id, year, director_name, director_title, location)
                VALUES (:id, :company_id, :year, :director_name, :director_title, :location)
            """), params)

    return jsonify({'success': True, 'message': 'Report settings saved'})


@report_bp.route('/api/reports/export', methods=['POST'])
def export_report():
    engine = require_db_engine()
    data = request.json or {}
    report_type = data.get('report_type')  # 'income-statement', 'balance-sheet', etc.
    format_type = data.get('format')  # 'excel', 'pdf', 'xml'
    filters = data.get('filters', {})

    company_id = filters.get('company_id')
    start_date = filters.get('start_date')
    end_date = filters.get('end_date')
    as_of_date = filters.get('as_of_date') or filters.get('date') or end_date
    report_mode = filters.get('report_type', 'real')
    
    if report_type != 'balance-sheet' and (not start_date or not end_date):
         start_date, end_date = default_report_period(start_date, end_date)

    if format_type == 'pdf' and report_mode == 'coretax' and report_type in {'income-statement', 'balance-sheet'}:
        from backend.services.reporting.pdf_service import generate_coretax_combined_pdf

        if not as_of_date:
            as_of_date = end_date or datetime.now().strftime('%Y-%m-%d')

        year = _resolve_report_year(filters, start_date, as_of_date)

        with engine.connect() as conn:
            settings = _load_report_settings(conn, company_id, year)
            company_name = _load_company_name(conn, company_id)

            income_statement_data = fetch_income_statement_data(
                conn,
                start_date,
                end_date,
                company_id,
                report_mode,
                comparative=filters.get('comparative', False)
            )
            income_statement_data['settings'] = settings
            income_statement_data['period'] = {'start_date': start_date, 'end_date': end_date}
            income_statement_data['company_name'] = company_name

            balance_sheet_data = fetch_balance_sheet_data(
                conn,
                as_of_date,
                company_id,
                report_mode,
            )
            balance_sheet_data['settings'] = settings
            balance_sheet_data['company_name'] = company_name

            amortization_data = fetch_amortization_report_data(conn, year, company_id)
            amortization_data['settings'] = settings
            amortization_data['company_name'] = company_name
            amortization_data['year'] = year

            try:
                pdf_path = generate_coretax_combined_pdf(
                    income_statement_data,
                    balance_sheet_data,
                    amortization_data,
                    report_filename=f"coretax_financial_statements_{year}.pdf",
                )
                return send_file(
                    pdf_path,
                    as_attachment=True,
                    download_name=f"CoreTax_Financial_Statements_{company_name.replace(' ', '_')}_{year}.pdf",
                    mimetype='application/pdf'
                )
            except Exception as e:
                return jsonify({'error': str(e)}), 500

    if format_type == 'pdf' and report_type == 'income-statement':
        from backend.services.reporting.pdf_service import generate_income_statement_pdf
        
        with engine.connect() as conn:
            # Fetch data
            report_data = fetch_income_statement_data(
                conn, 
                start_date, 
                end_date, 
                company_id, 
                report_mode, 
                comparative=filters.get('comparative', False)
            )
            
            year = _resolve_report_year(filters, start_date, as_of_date)
            report_data['settings'] = _load_report_settings(conn, company_id, year)
            
            report_data['period'] = {'start_date': start_date, 'end_date': end_date}
            report_data['company_name'] = _load_company_name(conn, company_id)
            
            # Generate PDF
            try:
                pdf_path = generate_income_statement_pdf(report_data)
                return send_file(
                    pdf_path,
                    as_attachment=True,
                    download_name=f"Income_Statement_{report_data['company_name'].replace(' ', '_')}_{start_date}.pdf",
                    mimetype='application/pdf'
                )
            except Exception as e:
                return jsonify({'error': str(e)}), 500

    if format_type == 'pdf' and report_type == 'balance-sheet':
        from backend.services.reporting.pdf_service import generate_balance_sheet_pdf

        if not as_of_date:
            as_of_date = datetime.now().strftime('%Y-%m-%d')

        with engine.connect() as conn:
            report_data = fetch_balance_sheet_data(
                conn,
                as_of_date,
                company_id,
                report_mode,
            )

            year = _resolve_report_year(filters, start_date, as_of_date)
            report_data['settings'] = _load_report_settings(conn, company_id, year)
            report_data['company_name'] = _load_company_name(conn, company_id)

            try:
                pdf_path = generate_balance_sheet_pdf(report_data)
                return send_file(
                    pdf_path,
                    as_attachment=True,
                    download_name=f"Balance_Sheet_{report_data['company_name'].replace(' ', '_')}_{as_of_date}.pdf",
                    mimetype='application/pdf'
                )
            except Exception as e:
                return jsonify({'error': str(e)}), 500

    return jsonify({'error': f'Export for {report_type} in {format_type} format not implemented yet'}), 400
