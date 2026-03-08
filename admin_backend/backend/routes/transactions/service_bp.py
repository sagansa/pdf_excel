from datetime import date, datetime

from flask import Blueprint, jsonify, request
from sqlalchemy import text

from backend.errors import BadRequestError
from backend.db.schema import get_table_columns
from backend.routes.accounting_utils import (
    require_db_engine,
    serialize_result_rows,
    split_parent_exclusion_clause,
)
from backend.routes.route_utils import (
    _normalize_iso_date,
    _parse_bool,
)

service_bp = Blueprint('service_bp', __name__)
VALID_SERVICE_CALCULATION_METHODS = {'BRUTO', 'NETTO', 'NONE'}
VALID_SERVICE_TAX_PAYMENT_TIMINGS = {'same_period', 'next_period', 'next_year'}


def _normalize_npwp(value):
    digits = ''.join(ch for ch in str(value or '') if ch.isdigit())
    if not digits:
        return None
    return digits if len(digits) == 15 else None


def _normalize_service_calculation_method(value):
    method = str(value or 'BRUTO').strip().upper()
    if method not in VALID_SERVICE_CALCULATION_METHODS:
        return 'BRUTO'
    return method


def _normalize_service_tax_payment_timing(value):
    raw = str(value or 'same_period').strip().lower()
    alias_map = {
        'same_month': 'same_period',
        'same_year': 'same_period',
        'next_month': 'next_period',
    }
    normalized = alias_map.get(raw, raw)
    if normalized not in VALID_SERVICE_TAX_PAYMENT_TIMINGS:
        return 'same_period'
    return normalized

@service_bp.route('/api/service-marks', methods=['GET'])
def get_service_marks():
    engine = require_db_engine()

    company_id = request.args.get('company_id')
    year = request.args.get('year')
    year_int = None
    if year not in (None, ''):
        try:
            year_int = int(year)
        except ValueError:
            raise BadRequestError('year must be numeric')

    with engine.connect() as conn:
        mark_columns = get_table_columns(conn, 'marks')
        service_expr = "COALESCE(m.is_service, FALSE)" if 'is_service' in mark_columns else "FALSE"
        asset_expr = "COALESCE(m.is_asset, FALSE)" if 'is_asset' in mark_columns else "FALSE"
        split_exclusion = split_parent_exclusion_clause(conn, 't')

        if conn.dialect.name == 'sqlite':
            year_filter = "(:year_str IS NULL OR strftime('%Y', t.txn_date) = :year_str)"
            params = {
                'company_id': company_id,
                'year_str': str(year_int) if year_int is not None else None
            }
        else:
            year_filter = "(:year IS NULL OR YEAR(t.txn_date) = :year)"
            params = {
                'company_id': company_id,
                'year': year_int
            }

        result = conn.execute(text(f"""
            SELECT
                m.id,
                m.internal_report,
                m.personal_use,
                m.tax_report,
                {asset_expr} AS is_asset,
                {service_expr} AS is_service,
                COUNT(t.id) AS transaction_count
            FROM marks m
            LEFT JOIN transactions t
                ON t.mark_id = m.id
               AND (:company_id IS NULL OR t.company_id = :company_id)
               AND {year_filter}
               {split_exclusion}
            GROUP BY m.id, m.internal_report, m.personal_use, m.tax_report
            ORDER BY m.personal_use ASC
        """), params)

        marks = serialize_result_rows(result)
        for d in marks:
            d['is_asset'] = _parse_bool(d.get('is_asset'))
            d['is_service'] = _parse_bool(d.get('is_service'))
            d['transaction_count'] = int(d.get('transaction_count') or 0)

    return jsonify({'marks': marks})


@service_bp.route('/api/service-marks/<mark_id>', methods=['PUT'])
def update_service_mark(mark_id):
    engine = require_db_engine()

    data = request.json or {}
    is_service = _parse_bool(data.get('is_service', False))

    with engine.begin() as conn:
        mark_columns = get_table_columns(conn, 'marks')
        if 'is_service' not in mark_columns:
            raise BadRequestError('is_service column is not available. Run latest migration.')

        params = {
            'id': mark_id,
            'is_service': is_service,
            'updated_at': datetime.now()
        }
        if 'updated_at' in mark_columns:
            conn.execute(text("""
                UPDATE marks
                SET is_service = :is_service,
                    updated_at = :updated_at
                WHERE id = :id
            """), params)
        else:
            conn.execute(text("""
                UPDATE marks
                SET is_service = :is_service
                WHERE id = :id
            """), params)

    return jsonify({'message': 'Service mark updated successfully', 'is_service': is_service})


@service_bp.route('/api/service-transactions', methods=['GET'])
def get_service_transactions():
    engine = require_db_engine()

    company_id = request.args.get('company_id')
    search = (request.args.get('search') or '').strip().lower()
    year = request.args.get('year')
    year_int = None
    if year not in (None, ''):
        try:
            year_int = int(year)
        except ValueError:
            raise BadRequestError('year must be numeric')

    with engine.connect() as conn:
        mark_columns = get_table_columns(conn, 'marks')
        txn_columns = get_table_columns(conn, 'transactions')
        split_exclusion = split_parent_exclusion_clause(conn, 't')

        if 'is_service' not in mark_columns:
            return jsonify({'transactions': [], 'message': 'No service mark configuration yet'})

        npwp_expr = "t.service_npwp" if 'service_npwp' in txn_columns else "NULL"
        method_expr = "COALESCE(t.service_calculation_method, 'BRUTO')" if 'service_calculation_method' in txn_columns else "'BRUTO'"
        timing_expr = "COALESCE(t.service_tax_payment_timing, 'same_period')" if 'service_tax_payment_timing' in txn_columns else "'same_period'"
        payment_date_expr = "t.service_tax_payment_date" if 'service_tax_payment_date' in txn_columns else "NULL"
        if conn.dialect.name == 'sqlite':
            year_filter = "(:year_str IS NULL OR strftime('%Y', t.txn_date) = :year_str)"
            params = {
                'company_id': company_id,
                'search': f"%{search}%" if search else None,
                'year_str': str(year_int) if year_int is not None else None
            }
        else:
            year_filter = "(:year IS NULL OR YEAR(t.txn_date) = :year)"
            params = {
                'company_id': company_id,
                'search': f"%{search}%" if search else None,
                'year': year_int
            }

        result = conn.execute(text(f"""
            SELECT
                t.id,
                t.txn_date,
                t.description,
                t.amount,
                t.db_cr,
                t.company_id,
                t.mark_id,
                {npwp_expr} AS service_npwp,
                {method_expr} AS service_calculation_method,
                {timing_expr} AS service_tax_payment_timing,
                {payment_date_expr} AS service_tax_payment_date,
                m.personal_use,
                m.internal_report,
                c.name AS company_name
            FROM transactions t
            INNER JOIN marks m ON t.mark_id = m.id
            LEFT JOIN companies c ON t.company_id = c.id
            WHERE COALESCE(m.is_service, 0) = 1
              AND (:company_id IS NULL OR t.company_id = :company_id)
              AND {year_filter}
              {split_exclusion}
              AND (
                  :search IS NULL
                  OR LOWER(COALESCE(t.description, '')) LIKE :search
                  OR LOWER(COALESCE(m.personal_use, '')) LIKE :search
                  OR LOWER(COALESCE(m.internal_report, '')) LIKE :search
              )
            ORDER BY t.txn_date DESC, t.created_at DESC
        """), params)

        transactions = serialize_result_rows(result)
        for d in transactions:
            d['has_npwp'] = bool(_normalize_npwp(d.get('service_npwp')))
            d['service_calculation_method'] = _normalize_service_calculation_method(d.get('service_calculation_method'))
            d['service_tax_payment_timing'] = _normalize_service_tax_payment_timing(d.get('service_tax_payment_timing'))
            d['service_tax_payment_date'] = _normalize_iso_date(d.get('service_tax_payment_date'))
            rate = 2.0 if d['has_npwp'] else 4.0
            amount_base = abs(float(d.get('amount') or 0.0))
            if d['service_calculation_method'] == 'NETTO':
                divisor = max(0.000001, 1.0 - (rate / 100.0))
                bruto = amount_base / divisor
                netto = amount_base
                tax = max(0.0, bruto - netto)
            else:
                bruto = amount_base
                tax = bruto * (rate / 100.0)
                netto = max(0.0, bruto - tax)
            d['service_tax_rate'] = rate
            d['service_amount_bruto'] = bruto
            d['service_amount_netto'] = netto
            d['service_amount_tax'] = tax
    return jsonify({'transactions': transactions})


@service_bp.route('/api/service-transactions/<txn_id>/npwp', methods=['PUT'])
def update_service_transaction_tax_config(txn_id):
    engine = require_db_engine()

    data = request.json or {}
    has_npwp = _parse_bool(data.get('has_npwp', False))
    npwp_raw = data.get('npwp')
    npwp_normalized = _normalize_npwp(npwp_raw) if has_npwp else None
    has_calculation_method = 'calculation_method' in data
    has_tax_payment_timing = 'tax_payment_timing' in data
    has_tax_payment_date = 'tax_payment_date' in data
    calculation_method = _normalize_service_calculation_method(data.get('calculation_method')) if has_calculation_method else None
    tax_payment_timing = _normalize_service_tax_payment_timing(data.get('tax_payment_timing')) if has_tax_payment_timing else None
    tax_payment_date = _normalize_iso_date(data.get('tax_payment_date')) if has_tax_payment_date else None

    if has_npwp and not npwp_normalized:
        raise BadRequestError('NPWP wajib 15 digit angka jika status NPWP = ada')
    if has_tax_payment_date and data.get('tax_payment_date') not in (None, '') and not tax_payment_date:
        raise BadRequestError('tax_payment_date harus format YYYY-MM-DD')

    with engine.begin() as conn:
        txn_columns = get_table_columns(conn, 'transactions')
        if 'service_npwp' not in txn_columns:
            raise BadRequestError('service_npwp column is not available. Run latest migration.')

        params = {
            'id': txn_id,
            'service_npwp': npwp_normalized,
            'updated_at': datetime.now()
        }
        set_fields = ['service_npwp = :service_npwp']
        if has_calculation_method and 'service_calculation_method' in txn_columns:
            params['service_calculation_method'] = calculation_method
            set_fields.append('service_calculation_method = :service_calculation_method')
        if has_tax_payment_timing and 'service_tax_payment_timing' in txn_columns:
            params['service_tax_payment_timing'] = tax_payment_timing
            set_fields.append('service_tax_payment_timing = :service_tax_payment_timing')
        if has_tax_payment_date and 'service_tax_payment_date' in txn_columns:
            params['service_tax_payment_date'] = tax_payment_date
            set_fields.append('service_tax_payment_date = :service_tax_payment_date')
        if 'updated_at' in txn_columns:
            set_fields.append('updated_at = :updated_at')
        update_sql = ",\n                        ".join(set_fields)
        conn.execute(text(f"""
            UPDATE transactions
            SET {update_sql}
            WHERE id = :id
        """), params)

    rate = 2.0 if bool(npwp_normalized) else 4.0

    return jsonify({
        'message': 'Konfigurasi pajak jasa updated successfully',
        'service_npwp': npwp_normalized,
        'has_npwp': bool(npwp_normalized),
        'service_calculation_method': calculation_method,
        'service_tax_payment_timing': tax_payment_timing,
        'service_tax_payment_date': tax_payment_date,
        'service_tax_rate': rate
    })
