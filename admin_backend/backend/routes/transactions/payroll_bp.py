import json
import os
from datetime import datetime

from flask import Blueprint, jsonify, request
from sqlalchemy import bindparam, text

from backend.errors import BadRequestError, NotFoundError
from backend.db.schema import get_table_columns
from backend.routes.accounting_utils import require_db_engine, serialize_result_rows
from backend.routes.transactions.payroll_utils import (
    _deep_get,
    _ensure_payroll_presences_table,
    _extract_presence_records,
    _get_payroll_employee_ids,
    _get_sagansa_user_map,
    _get_sagansa_users,
    _is_payroll_employee,
    _new_uuid,
    _normalize_datetime_string,
    _normalize_month,
    _normalize_month_start,
    _normalize_presence_record,
    _normalize_year,
    _set_payroll_employee_flag,
    _sagansa_user_exists,
    _split_parent_exclusion_clause,
)
from backend.routes.route_utils import (
    _fetch_remote_presences,
    _normalize_iso_date,
    _parse_bool,
    _safe_int,
)

payroll_bp = Blueprint('payroll_bp', __name__)

DEFAULT_PRESENCE_API_URL = os.environ.get('SAGANSA_PRESENCE_API_URL', 'https://superadmin.sagansa.id/api/presences')
DEFAULT_PRESENCE_API_TOKEN = os.environ.get('SAGANSA_PRESENCE_TOKEN', '')


@payroll_bp.route('/api/payroll/presences/sync', methods=['POST'])
def sync_payroll_presences():
    engine = require_db_engine()

    payload = request.json or {}
    api_url = str(payload.get('api_url') or payload.get('apiUrl') or DEFAULT_PRESENCE_API_URL).strip()
    token = str(
        payload.get('token')
        or payload.get('access_token')
        or payload.get('api_token')
        or DEFAULT_PRESENCE_API_TOKEN
        or ''
    ).strip()
    company_id = str(payload.get('company_id') or '').strip() or None

    year = _normalize_year(payload.get('year'))
    month = _normalize_month(payload.get('month'))
    start_date = _normalize_iso_date(payload.get('start_date') or payload.get('date_start'))
    end_date = _normalize_iso_date(payload.get('end_date') or payload.get('date_end'))

    if payload.get('year') not in (None, '') and year is None:
        raise BadRequestError('year must be numeric (1900-3000)')
    if payload.get('month') not in (None, '') and month is None:
        raise BadRequestError('month must be numeric (1-12)')
    if (payload.get('start_date') or payload.get('date_start')) and not start_date:
        raise BadRequestError('start_date/date_start must be YYYY-MM-DD')
    if (payload.get('end_date') or payload.get('date_end')) and not end_date:
        raise BadRequestError('end_date/date_end must be YYYY-MM-DD')
    if not token:
        raise BadRequestError('Presence API token is required (payload.token or env SAGANSA_PRESENCE_TOKEN)')

    remote_params = {}
    if year is not None:
        remote_params['year'] = year
    if month is not None:
        remote_params['month'] = month
    if start_date:
        remote_params['start_date'] = start_date
    if end_date:
        remote_params['end_date'] = end_date

    api_payload = _fetch_remote_presences(api_url, token, remote_params)
    records = _extract_presence_records(api_payload)

    now = datetime.now()
    inserted = 0
    updated = 0
    skipped = 0

    with engine.begin() as conn:
        _ensure_payroll_presences_table(conn)

        if conn.dialect.name == 'sqlite':
            upsert_query = text("""
                INSERT INTO payroll_presences (
                    id, source_key, sagansa_presence_id, sagansa_user_id, user_name, creator_name, store_name,
                    shift_name, shift_start_time, shift_end_time, shift_duration_hours, presence_date,
                    check_in_at, check_out_at, status, work_minutes, company_id, source_created_at, source_updated_at, raw_payload, created_at, updated_at
                ) VALUES (
                    :id, :source_key, :sagansa_presence_id, :sagansa_user_id, :user_name, :creator_name, :store_name,
                    :shift_name, :shift_start_time, :shift_end_time, :shift_duration_hours, :presence_date,
                    :check_in_at, :check_out_at, :status, :work_minutes, :company_id, :source_created_at, :source_updated_at, :raw_payload, :created_at, :updated_at
                )
                ON CONFLICT(source_key) DO UPDATE SET
                    sagansa_presence_id = excluded.sagansa_presence_id,
                    sagansa_user_id = excluded.sagansa_user_id,
                    user_name = excluded.user_name,
                    creator_name = excluded.creator_name,
                    store_name = excluded.store_name,
                    shift_name = excluded.shift_name,
                    shift_start_time = excluded.shift_start_time,
                    shift_end_time = excluded.shift_end_time,
                    shift_duration_hours = excluded.shift_duration_hours,
                    presence_date = excluded.presence_date,
                    check_in_at = excluded.check_in_at,
                    check_out_at = excluded.check_out_at,
                    status = excluded.status,
                    work_minutes = excluded.work_minutes,
                    company_id = excluded.company_id,
                    source_created_at = excluded.source_created_at,
                    source_updated_at = excluded.source_updated_at,
                    raw_payload = excluded.raw_payload,
                    updated_at = excluded.updated_at
            """)
        else:
            upsert_query = text("""
                INSERT INTO payroll_presences (
                    id, source_key, sagansa_presence_id, sagansa_user_id, user_name, creator_name, store_name,
                    shift_name, shift_start_time, shift_end_time, shift_duration_hours, presence_date,
                    check_in_at, check_out_at, status, work_minutes, company_id, source_created_at, source_updated_at, raw_payload, created_at, updated_at
                ) VALUES (
                    :id, :source_key, :sagansa_presence_id, :sagansa_user_id, :user_name, :creator_name, :store_name,
                    :shift_name, :shift_start_time, :shift_end_time, :shift_duration_hours, :presence_date,
                    :check_in_at, :check_out_at, :status, :work_minutes, :company_id, :source_created_at, :source_updated_at, :raw_payload, :created_at, :updated_at
                )
                ON DUPLICATE KEY UPDATE
                    sagansa_presence_id = VALUES(sagansa_presence_id),
                    sagansa_user_id = VALUES(sagansa_user_id),
                    user_name = VALUES(user_name),
                    creator_name = VALUES(creator_name),
                    store_name = VALUES(store_name),
                    shift_name = VALUES(shift_name),
                    shift_start_time = VALUES(shift_start_time),
                    shift_end_time = VALUES(shift_end_time),
                    shift_duration_hours = VALUES(shift_duration_hours),
                    presence_date = VALUES(presence_date),
                    check_in_at = VALUES(check_in_at),
                    check_out_at = VALUES(check_out_at),
                    status = VALUES(status),
                    work_minutes = VALUES(work_minutes),
                    company_id = VALUES(company_id),
                    source_created_at = VALUES(source_created_at),
                    source_updated_at = VALUES(source_updated_at),
                    raw_payload = VALUES(raw_payload),
                    updated_at = VALUES(updated_at)
            """)

        for record in records:
            normalized = _normalize_presence_record(record, fallback_company_id=company_id)
            if not normalized:
                skipped += 1
                continue

            existing = conn.execute(text("""
                SELECT id
                FROM payroll_presences
                WHERE source_key = :source_key
                LIMIT 1
            """), {'source_key': normalized['source_key']}).fetchone()

            row_id = str(existing.id) if existing and getattr(existing, 'id', None) else _new_uuid()
            params = {
                'id': row_id,
                'source_key': normalized['source_key'],
                'sagansa_presence_id': normalized['sagansa_presence_id'],
                'sagansa_user_id': normalized['sagansa_user_id'],
                'user_name': normalized['user_name'],
                'creator_name': normalized['creator_name'],
                'store_name': normalized['store_name'],
                'shift_name': normalized['shift_name'],
                'shift_start_time': normalized['shift_start_time'],
                'shift_end_time': normalized['shift_end_time'],
                'shift_duration_hours': normalized['shift_duration_hours'],
                'presence_date': normalized['presence_date'],
                'check_in_at': normalized['check_in_at'],
                'check_out_at': normalized['check_out_at'],
                'status': normalized['status'],
                'work_minutes': normalized['work_minutes'],
                'company_id': normalized['company_id'],
                'source_created_at': normalized['source_created_at'],
                'source_updated_at': normalized['source_updated_at'],
                'raw_payload': normalized['raw_payload'],
                'created_at': now,
                'updated_at': now
            }

            conn.execute(upsert_query, params)
            if existing:
                updated += 1
            else:
                inserted += 1

    return jsonify({
        'message': 'Payroll presences synced successfully',
        'fetched': len(records),
        'inserted': inserted,
        'updated': updated,
        'skipped': skipped
    })


@payroll_bp.route('/api/payroll/presences', methods=['GET'])
def get_payroll_presences():
    engine = require_db_engine()

    company_id = str(request.args.get('company_id') or '').strip() or None
    user_id = str(request.args.get('user_id') or '').strip() or None
    search = str(request.args.get('search') or '').strip().lower()
    year = _normalize_year(request.args.get('year'))
    month = _normalize_month(request.args.get('month'))
    date_start = _normalize_iso_date(request.args.get('date_start') or request.args.get('start_date'))
    date_end = _normalize_iso_date(request.args.get('date_end') or request.args.get('end_date'))
    limit = _safe_int(request.args.get('limit'), 300)
    limit = min(max(limit, 1), 2000)

    if request.args.get('year') not in (None, '') and year is None:
        raise BadRequestError('year must be numeric (1900-3000)')
    if request.args.get('month') not in (None, '') and month is None:
        raise BadRequestError('month must be numeric (1-12)')
    if (request.args.get('date_start') or request.args.get('start_date')) and not date_start:
        raise BadRequestError('date_start/start_date must be YYYY-MM-DD')
    if (request.args.get('date_end') or request.args.get('end_date')) and not date_end:
        raise BadRequestError('date_end/end_date must be YYYY-MM-DD')

    with engine.connect() as conn:
        _ensure_payroll_presences_table(conn)

        where_clauses = []
        params = {'limit': limit}
        if company_id:
            where_clauses.append("company_id = :company_id")
            params['company_id'] = company_id
        if user_id:
            where_clauses.append("CAST(sagansa_user_id AS CHAR) = :user_id")
            params['user_id'] = user_id
        if year is not None:
            if conn.dialect.name == 'sqlite':
                where_clauses.append("strftime('%Y', presence_date) = :year_str")
                params['year_str'] = str(year)
            else:
                where_clauses.append("YEAR(presence_date) = :year")
                params['year'] = year
        if month is not None:
            if conn.dialect.name == 'sqlite':
                where_clauses.append("strftime('%m', presence_date) = :month_str")
                params['month_str'] = f"{month:02d}"
            else:
                where_clauses.append("MONTH(presence_date) = :month")
                params['month'] = month
        if date_start:
            where_clauses.append("presence_date >= :date_start")
            params['date_start'] = date_start
        if date_end:
            where_clauses.append("presence_date <= :date_end")
            params['date_end'] = date_end
        if search:
            where_clauses.append("""
                (
                    LOWER(COALESCE(CAST(user_name AS CHAR), '')) LIKE :search
                    OR LOWER(COALESCE(CAST(creator_name AS CHAR), '')) LIKE :search
                    OR LOWER(COALESCE(CAST(store_name AS CHAR), '')) LIKE :search
                    OR LOWER(COALESCE(CAST(shift_name AS CHAR), '')) LIKE :search
                    OR LOWER(COALESCE(CAST(sagansa_user_id AS CHAR), '')) LIKE :search
                    OR LOWER(COALESCE(CAST(status AS CHAR), '')) LIKE :search
                )
            """)
            params['search'] = f"%{search}%"

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ''
        result = conn.execute(text(f"""
            SELECT
                id, source_key, sagansa_presence_id, sagansa_user_id, user_name, creator_name, store_name,
                shift_name, shift_start_time, shift_end_time, shift_duration_hours, presence_date,
                check_in_at, check_out_at, status, work_minutes, company_id, source_created_at,
                source_updated_at, raw_payload, created_at, updated_at
            FROM payroll_presences
            {where_sql}
            ORDER BY presence_date DESC, check_in_at DESC, created_at DESC
            LIMIT :limit
        """), params)

        rows = serialize_result_rows(result)
        for d in rows:
            d['work_minutes'] = _safe_int(d.get('work_minutes'), 0)

        data_rows = []
        for d in rows:
            raw_payload = {}
            raw_payload_text = d.get('raw_payload')
            if raw_payload_text:
                try:
                    parsed_payload = json.loads(raw_payload_text)
                    if isinstance(parsed_payload, dict):
                        raw_payload = parsed_payload
                except (TypeError, ValueError):
                    raw_payload = {}

            fallback_creator = str(_deep_get(raw_payload, ['creator', 'creator_name', 'user_name', 'employee_name', 'name']) or '').strip() or None
            fallback_store = str(_deep_get(raw_payload, ['store', 'store_name', 'branch', 'location']) or '').strip() or None
            fallback_shift_name = str(_deep_get(raw_payload, ['shift_name', 'shift.name']) or '').strip() or None
            fallback_shift_start = str(_deep_get(raw_payload, ['shift_start_time', 'shift.start_time']) or '').strip() or None
            fallback_shift_end = str(_deep_get(raw_payload, ['shift_end_time', 'shift.end_time']) or '').strip() or None
            fallback_shift_duration = _safe_int(_deep_get(raw_payload, ['shift_duration', 'shift.duration', 'shift_hours']), 0)
            fallback_check_in = _normalize_datetime_string(_deep_get(raw_payload, ['check_in', 'check_in_at', 'clock_in', 'in_time']))
            fallback_check_out = _normalize_datetime_string(_deep_get(raw_payload, ['check_out', 'check_out_at', 'clock_out', 'out_time']))
            fallback_created = _normalize_datetime_string(_deep_get(raw_payload, ['created_at', 'inserted_at']))
            fallback_updated = _normalize_datetime_string(_deep_get(raw_payload, ['updated_at', 'modified_at', 'last_updated_at']))

            source_presence_id = d.get('sagansa_presence_id')
            normalized_id = _safe_int(source_presence_id, 0) if str(source_presence_id or '').isdigit() else (source_presence_id or d.get('source_key') or d.get('id'))
            work_minutes = _safe_int(d.get('work_minutes'), 0)
            shift_duration = _safe_int(d.get('shift_duration_hours'), 0)
            if shift_duration <= 0 and fallback_shift_duration > 0:
                shift_duration = fallback_shift_duration
            if shift_duration <= 0 and work_minutes > 0:
                shift_duration = max(1, round(work_minutes / 60))

            data_rows.append({
                'id': normalized_id,
                'creator': d.get('creator_name') or d.get('user_name') or fallback_creator,
                'store': d.get('store_name') or fallback_store,
                'shift_name': d.get('shift_name') or fallback_shift_name,
                'shift_start_time': d.get('shift_start_time') or fallback_shift_start,
                'shift_end_time': d.get('shift_end_time') or fallback_shift_end,
                'shift_duration': shift_duration,
                'check_in': d.get('check_in_at') or fallback_check_in,
                'check_out': d.get('check_out_at') or fallback_check_out,
                'created_at': d.get('source_created_at') or d.get('created_at') or fallback_created,
                'updated_at': d.get('source_updated_at') or d.get('updated_at') or fallback_updated
            })

        return jsonify({
            'success': True,
            'data': data_rows,
            'presences': data_rows,
            'count': len(data_rows)
        })


@payroll_bp.route('/api/payroll/users', methods=['GET'])
def get_payroll_users():
    engine = require_db_engine()

    search = (request.args.get('search') or '').strip()
    employees_only = _parse_bool(request.args.get('employees_only', False))
    users = _get_sagansa_users(search=search or None)
    with engine.connect() as conn:
        employee_user_ids = _get_payroll_employee_ids(conn)
    for user in users:
        user['is_employee'] = user.get('id') in employee_user_ids
    if employees_only:
        users = [user for user in users if user.get('is_employee')]
    return jsonify({'users': users})


@payroll_bp.route('/api/payroll/users/<user_id>/employee', methods=['PUT', 'POST', 'PATCH'])
@payroll_bp.route('/api/payroll/users/<user_id>/employee/', methods=['PUT', 'POST', 'PATCH'])
def update_payroll_user_employee_status(user_id):
    engine = require_db_engine()

    normalized_user_id = str(user_id or '').strip()
    if not normalized_user_id:
        raise BadRequestError('user_id is required')

    payload = request.json or {}
    is_employee = _parse_bool(payload.get('is_employee', False))

    if not _sagansa_user_exists(normalized_user_id):
        raise BadRequestError(f'User Sagansa tidak ditemukan atau tidak aktif: {normalized_user_id}')

    with engine.begin() as conn:
        _set_payroll_employee_flag(conn, normalized_user_id, is_employee)

    user_map = _get_sagansa_user_map()
    return jsonify({
        'message': 'Employee status updated successfully',
        'user': {
            'id': normalized_user_id,
            'name': (user_map.get(normalized_user_id, {}).get('name') or normalized_user_id),
            'is_employee': is_employee
        }
    })


@payroll_bp.route('/api/payroll/transactions', methods=['GET'])
def get_payroll_transactions():
    engine = require_db_engine()

    company_id = request.args.get('company_id')
    year = _normalize_year(request.args.get('year'))
    month = _normalize_month(request.args.get('month'))
    search = (request.args.get('search') or '').strip().lower()
    user_id = (request.args.get('user_id') or '').strip()
    report_type = request.args.get('report_type', 'real')

    if year is None:
        raise BadRequestError('year must be numeric (1900-3000)')
    if request.args.get('month') not in (None, '') and month is None:
        raise BadRequestError('month must be numeric (1-12)')

    with engine.connect() as conn:
        mark_columns = get_table_columns(conn, 'marks')
        txn_columns = get_table_columns(conn, 'transactions')
        split_exclusion = _split_parent_exclusion_clause(conn, 't')

        if 'is_salary_component' not in mark_columns:
            return jsonify({
                'transactions': [],
                'summary': {'total_transactions': 0, 'assigned_transactions': 0, 'total_amount': 0.0},
                'message': 'Kolom is_salary_component belum tersedia. Jalankan migrasi terbaru.'
            })

        user_col_expr = "t.sagansa_user_id" if 'sagansa_user_id' in txn_columns else "NULL"
        period_col_expr = "t.payroll_period_month" if 'payroll_period_month' in txn_columns else "NULL"
        effective_date_expr = "COALESCE(t.payroll_period_month, t.txn_date)" if 'payroll_period_month' in txn_columns else "t.txn_date"
        if conn.dialect.name == 'sqlite':
            year_filter = f"strftime('%Y', {effective_date_expr}) = :year_str"
            month_filter = f"AND strftime('%m', {effective_date_expr}) = :month_str" if month else ""
            effective_period_expr = f"strftime('%Y-%m', {effective_date_expr})"
            params = {
                'company_id': company_id,
                'year_str': f"{year:04d}",
                'month_str': f"{month:02d}" if month else None,
                'search': f"%{search}%" if search else None,
                'user_id': user_id or None,
                'report_type': report_type
            }
        else:
            year_filter = f"YEAR({effective_date_expr}) = :year"
            month_filter = f"AND MONTH({effective_date_expr}) = :month" if month else ""
            effective_period_expr = f"DATE_FORMAT({effective_date_expr}, '%Y-%m')"
            params = {
                'company_id': company_id,
                'year': year,
                'month': month,
                'search': f"%{search}%" if search else None,
                'user_id': user_id or None,
                'report_type': report_type
            }

        user_filter = "AND (:user_id IS NULL OR COALESCE(CAST(t.sagansa_user_id AS CHAR), '') = :user_id)" if 'sagansa_user_id' in txn_columns else ""
        rows = conn.execute(text(f"""
            SELECT
                t.id,
                t.txn_date,
                t.description,
                t.amount,
                t.db_cr,
                t.company_id,
                m.id AS mark_id,
                m.personal_use,
                m.internal_report,
                m.tax_report,
                {period_col_expr} AS payroll_period_month,
                {effective_period_expr} AS effective_payroll_period,
                {user_col_expr} AS sagansa_user_id,
                c.name AS company_name
            FROM transactions t
            INNER JOIN marks m ON t.mark_id = m.id
            LEFT JOIN companies c ON t.company_id = c.id
            WHERE COALESCE(m.is_salary_component, 0) = 1
              AND EXISTS (
                  SELECT 1 FROM mark_coa_mapping mcm
                  WHERE mcm.mark_id = m.id AND mcm.report_type = :report_type
              )
              AND (:company_id IS NULL OR t.company_id = :company_id)
              AND {year_filter}
              {month_filter}
              {user_filter}
              {split_exclusion}
              AND (
                  :search IS NULL
                  OR LOWER(COALESCE(t.description, '')) LIKE :search
                  OR LOWER(COALESCE(m.personal_use, '')) LIKE :search
                  OR LOWER(COALESCE(m.internal_report, '')) LIKE :search
                  OR LOWER(COALESCE(m.tax_report, '')) LIKE :search
              )
            ORDER BY t.txn_date DESC, t.created_at DESC
        """), params)

        user_map = _get_sagansa_user_map()
        employee_user_ids = _get_payroll_employee_ids(conn)
        transactions = serialize_result_rows(rows)
        total_amount = 0.0
        assigned_count = 0
        for d in transactions:
            amount_abs = abs(float(d.get('amount') or 0.0))
            total_amount += amount_abs
            d['amount'] = amount_abs
            d['component_name'] = d.get('personal_use') or d.get('internal_report') or d.get('tax_report') or '(Unnamed Salary Component)'
            current_user_id = str(d.get('sagansa_user_id') or '').strip() or None
            d['sagansa_user_id'] = current_user_id
            d['sagansa_user_name'] = (user_map.get(current_user_id, {}).get('name') or current_user_id) if current_user_id else None
            d['is_employee'] = bool(current_user_id and current_user_id in employee_user_ids)
            d['payroll_period_month'] = _normalize_month_start(d.get('payroll_period_month'))
            d['effective_payroll_period'] = str(d.get('effective_payroll_period') or '').strip() or None
            if current_user_id:
                assigned_count += 1

    return jsonify({
        'transactions': transactions,
        'summary': {
            'total_transactions': len(transactions),
            'assigned_transactions': assigned_count,
            'total_amount': total_amount
        }
    })


@payroll_bp.route('/api/payroll/transactions/<txn_id>/assign-user', methods=['PUT'])
def assign_payroll_user(txn_id):
    engine = require_db_engine()

    payload = request.json or {}
    user_id_raw = payload.get('sagansa_user_id')
    user_id = str(user_id_raw).strip() if user_id_raw not in (None, '') else None

    with engine.begin() as conn:
        txn_columns = get_table_columns(conn, 'transactions')
        if 'sagansa_user_id' not in txn_columns:
            raise BadRequestError('Kolom sagansa_user_id belum tersedia. Jalankan migrasi terbaru.')

        if user_id and not _sagansa_user_exists(user_id):
            raise BadRequestError(f'User Sagansa tidak ditemukan atau tidak aktif: {user_id}')
        if user_id and not _is_payroll_employee(conn, user_id):
            raise BadRequestError(f'User Sagansa belum ditandai sebagai employee: {user_id}')

        result = conn.execute(text("""
            UPDATE transactions
            SET sagansa_user_id = :sagansa_user_id,
                updated_at = :updated_at
            WHERE id = :txn_id
        """), {'sagansa_user_id': user_id, 'updated_at': datetime.now(), 'txn_id': txn_id})
        if int(result.rowcount or 0) == 0:
            raise NotFoundError('Transaction not found')

    user_map = _get_sagansa_user_map() if user_id else {}
    return jsonify({
        'message': 'Payroll user assigned successfully',
        'txn_id': txn_id,
        'sagansa_user_id': user_id,
        'sagansa_user_name': (user_map.get(user_id, {}).get('name') or user_id) if user_id else None
    })


@payroll_bp.route('/api/payroll/transactions/<txn_id>/period-month', methods=['PUT'])
def update_payroll_transaction_period_month(txn_id):
    engine = require_db_engine()

    payload = request.json or {}
    month_raw = payload.get('payroll_period_month')
    month_value = _normalize_month_start(month_raw) if month_raw not in (None, '') else None

    if month_raw not in (None, '') and not month_value:
        raise BadRequestError('payroll_period_month harus format YYYY-MM atau YYYY-MM-DD')

    with engine.begin() as conn:
        txn_columns = get_table_columns(conn, 'transactions')
        if 'payroll_period_month' not in txn_columns:
            raise BadRequestError('Kolom payroll_period_month belum tersedia. Jalankan migrasi terbaru.')

        result = conn.execute(text("""
            UPDATE transactions
            SET payroll_period_month = :payroll_period_month,
                updated_at = :updated_at
            WHERE id = :txn_id
        """), {'payroll_period_month': month_value, 'updated_at': datetime.now(), 'txn_id': txn_id})
        if int(result.rowcount or 0) == 0:
            raise NotFoundError('Transaction not found')

    effective_period = (month_value or '')[:7] if month_value else None
    return jsonify({
        'message': 'Payroll period month updated successfully',
        'txn_id': txn_id,
        'payroll_period_month': month_value,
        'effective_payroll_period': effective_period
    })


@payroll_bp.route('/api/payroll/transactions/bulk-assign-user', methods=['PUT', 'POST'])
def bulk_assign_payroll_user():
    engine = require_db_engine()

    payload = request.json or {}
    txn_ids_raw = payload.get('transaction_ids') or []
    user_id_raw = payload.get('sagansa_user_id')
    user_id = str(user_id_raw).strip() if user_id_raw not in (None, '') else None

    if not isinstance(txn_ids_raw, list):
        raise BadRequestError('transaction_ids must be an array')

    txn_ids = []
    seen = set()
    for raw_id in txn_ids_raw:
        normalized = str(raw_id or '').strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        txn_ids.append(normalized)

    if not txn_ids:
        raise BadRequestError('No transaction IDs provided')

    with engine.begin() as conn:
        txn_columns = get_table_columns(conn, 'transactions')
        if 'sagansa_user_id' not in txn_columns:
            raise BadRequestError('Kolom sagansa_user_id belum tersedia. Jalankan migrasi terbaru.')

        if user_id and not _sagansa_user_exists(user_id):
            raise BadRequestError(f'User Sagansa tidak ditemukan atau tidak aktif: {user_id}')
        if user_id and not _is_payroll_employee(conn, user_id):
            raise BadRequestError(f'User Sagansa belum ditandai sebagai employee: {user_id}')

        result = conn.execute(text("""
            UPDATE transactions
            SET sagansa_user_id = :sagansa_user_id,
                updated_at = :updated_at
            WHERE id IN :ids
        """).bindparams(bindparam('ids', expanding=True)), {
            'sagansa_user_id': user_id,
            'updated_at': datetime.now(),
            'ids': txn_ids
        })

    user_map = _get_sagansa_user_map() if user_id else {}
    return jsonify({
        'message': 'Payroll users assigned successfully',
        'updated_count': int(result.rowcount or 0),
        'sagansa_user_id': user_id,
        'sagansa_user_name': (user_map.get(user_id, {}).get('name') or user_id) if user_id else None
    })


@payroll_bp.route('/api/payroll/monthly-summary', methods=['GET'])
def get_payroll_monthly_summary():
    engine = require_db_engine()

    company_id = request.args.get('company_id')
    year = _normalize_year(request.args.get('year'))
    month = _normalize_month(request.args.get('month'))
    report_type = request.args.get('report_type', 'real')

    if year is None:
        raise BadRequestError('year must be numeric (1900-3000)')
    if request.args.get('month') not in (None, '') and month is None:
        raise BadRequestError('month must be numeric (1-12)')

    with engine.connect() as conn:
        mark_columns = get_table_columns(conn, 'marks')
        txn_columns = get_table_columns(conn, 'transactions')
        split_exclusion = _split_parent_exclusion_clause(conn, 't')

        if 'is_salary_component' not in mark_columns:
            return jsonify({
                'rows': [],
                'summary': {
                    'year': year,
                    'month': month,
                    'employee_count': 0,
                    'total_transactions': 0,
                    'total_salary_amount': 0.0
                },
                'message': 'Kolom is_salary_component belum tersedia. Jalankan migrasi terbaru.'
            })

        user_col_expr = "t.sagansa_user_id" if 'sagansa_user_id' in txn_columns else "NULL"
        effective_date_expr = "COALESCE(t.payroll_period_month, t.txn_date)" if 'payroll_period_month' in txn_columns else "t.txn_date"
        if conn.dialect.name == 'sqlite':
            period_clause = f"strftime('%Y', {effective_date_expr}) = :year_str"
            if month:
                period_clause += f" AND strftime('%m', {effective_date_expr}) = :month_str"
            params = {'company_id': company_id, 'year_str': f"{year:04d}", 'month_str': f"{month:02d}", 'report_type': report_type}
        else:
            period_clause = f"YEAR({effective_date_expr}) = :year"
            if month:
                period_clause += f" AND MONTH({effective_date_expr}) = :month"
            params = {'company_id': company_id, 'year': year, 'month': month, 'report_type': report_type}

        result = conn.execute(text(f"""
            SELECT
                t.id,
                t.amount,
                {user_col_expr} AS sagansa_user_id,
                m.personal_use,
                m.internal_report,
                m.tax_report
            FROM transactions t
            INNER JOIN marks m ON t.mark_id = m.id
            WHERE COALESCE(m.is_salary_component, 0) = 1
              AND EXISTS (
                  SELECT 1 FROM mark_coa_mapping mcm
                  WHERE mcm.mark_id = m.id AND mcm.report_type = :report_type
              )
              AND {period_clause}
              AND (:company_id IS NULL OR t.company_id = :company_id)
              {split_exclusion}
        """), params)

        user_map = _get_sagansa_user_map()
        grouped = {}
        component_totals = {}
        total_transactions = 0
        total_salary_amount = 0.0
        for row in result:
            total_transactions += 1
            amount = abs(float(row.amount or 0.0))
            total_salary_amount += amount

            user_id = str(row.sagansa_user_id or '').strip() or None
            group_key = user_id or '__unassigned__'
            if group_key not in grouped:
                grouped[group_key] = {
                    'sagansa_user_id': user_id,
                    'sagansa_user_name': (user_map.get(user_id, {}).get('name') or user_id) if user_id else 'Unassigned',
                    'total_amount': 0.0,
                    'transaction_count': 0,
                    'components': {}
                }

            component_name = row.personal_use or row.internal_report or row.tax_report or '(Unnamed Salary Component)'
            grouped[group_key]['total_amount'] += amount
            grouped[group_key]['transaction_count'] += 1
            grouped[group_key]['components'][component_name] = grouped[group_key]['components'].get(component_name, 0.0) + amount
            component_totals[component_name] = component_totals.get(component_name, 0.0) + amount

        rows = []
        for _, user_row in grouped.items():
            components = [
                {'component_name': name, 'amount': value}
                for name, value in sorted(user_row['components'].items(), key=lambda item: item[1], reverse=True)
            ]
            rows.append({
                'sagansa_user_id': user_row['sagansa_user_id'],
                'sagansa_user_name': user_row['sagansa_user_name'],
                'total_amount': user_row['total_amount'],
                'transaction_count': user_row['transaction_count'],
                'components': components
            })

        rows.sort(key=lambda item: item.get('total_amount', 0), reverse=True)
        component_totals_rows = [
            {'component_name': name, 'amount': value}
            for name, value in sorted(component_totals.items(), key=lambda item: item[1], reverse=True)
        ]

    return jsonify({
        'rows': rows,
        'component_totals': component_totals_rows,
        'summary': {
            'year': year,
            'month': month,
            'employee_count': len(rows),
            'total_transactions': total_transactions,
            'total_salary_amount': total_salary_amount
        }
    })
