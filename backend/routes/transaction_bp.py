import uuid
import os
import re
import json
from flask import Blueprint, request, jsonify
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import text, bindparam
from urllib import request as urlrequest, parse as urlparse, error as urlerror
from backend.db.session import get_db_engine, get_sagansa_engine

transaction_bp = Blueprint('transaction_bp', __name__)
VALID_SERVICE_CALCULATION_METHODS = {'BRUTO', 'NETTO', 'NONE'}
VALID_SERVICE_TAX_PAYMENT_TIMINGS = {'same_period', 'next_period', 'next_year'}
DEFAULT_PRESENCE_API_URL = os.environ.get('SAGANSA_PRESENCE_API_URL', 'https://superadmin.sagansa.id/api/presences')
DEFAULT_PRESENCE_API_TOKEN = os.environ.get(
    'SAGANSA_PRESENCE_TOKEN',
    '1928|DvkiyXPhc5ixN0kx71TU6dai9jxaK0kIqvh5ggyJ81f4bc25'
)


def _table_columns(conn, table_name):
    if conn.dialect.name == 'sqlite':
        rows = conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
        return {str(row[1]) for row in rows}

    rows = conn.execute(text("""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = :table_name
    """), {'table_name': table_name}).fetchall()
    return {str(row[0]) for row in rows}


def _parse_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {'1', 'true', 'yes', 'y', 'on'}
    return False


def _normalize_mapping_report_type(value, allow_all=False):
    normalized = str(value or '').strip().lower()
    if normalized == 'coretax':
        return 'coretax'
    if allow_all and normalized == 'all':
        return 'all'
    return 'real'


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


def _normalize_iso_date(value):
    if value in (None, ''):
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        try:
            return datetime.strptime(value[:10], '%Y-%m-%d').date().isoformat()
        except ValueError:
            return None
    return None


def _normalize_month_start(value):
    if value in (None, ''):
        return None
    if isinstance(value, datetime):
        dt = value.date().replace(day=1)
        return dt.isoformat()
    if isinstance(value, date):
        dt = value.replace(day=1)
        return dt.isoformat()
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        for fmt in ('%Y-%m', '%Y-%m-%d'):
            try:
                dt = datetime.strptime(raw[:10], fmt).date().replace(day=1)
                return dt.isoformat()
            except ValueError:
                continue
    return None


def _normalize_db_cr(value, default='DB'):
    raw = str(value or '').strip().upper()
    if not raw:
        return default

    if raw in {'CR', 'CREDIT', 'KREDIT', 'K'}:
        return 'CR'
    if raw in {'DB', 'DEBIT', 'D', 'DE'}:
        return 'DB'

    if raw.startswith('CR') or 'CREDIT' in raw or raw.startswith('K'):
        return 'CR'
    if raw.startswith('DB') or raw.startswith('DE') or 'DEBIT' in raw:
        return 'DB'

    return default


def _split_parent_exclusion_clause(conn, alias='t'):
    txn_columns = _table_columns(conn, 'transactions')
    if 'parent_id' not in txn_columns:
        return ''
    return f" AND NOT EXISTS (SELECT 1 FROM transactions t_child WHERE t_child.parent_id = {alias}.id)"


def _safe_identifier(value, fallback):
    raw = str(value or fallback).strip()
    if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', raw):
        return fallback
    return raw


def _get_sagansa_users(search=None):
    """
    Fetch user master data from Sagansa DB.
    Table/column names are configurable via env:
      SAGANSA_USER_TABLE, SAGANSA_USER_ID_COLUMN, SAGANSA_USER_NAME_COLUMN, SAGANSA_USER_ACTIVE_COLUMN
    """
    engine, error_msg = get_sagansa_engine()
    if engine is None:
        raise RuntimeError(error_msg or 'Sagansa DB is not configured')

    user_table = _safe_identifier(os.environ.get('SAGANSA_USER_TABLE'), 'users')
    user_id_col = _safe_identifier(os.environ.get('SAGANSA_USER_ID_COLUMN'), 'id')
    user_name_col = _safe_identifier(os.environ.get('SAGANSA_USER_NAME_COLUMN'), 'name')
    user_active_col = _safe_identifier(os.environ.get('SAGANSA_USER_ACTIVE_COLUMN'), '')

    where_clauses = []
    params = {}
    if search:
        where_clauses.append(f"LOWER(COALESCE(CAST(`{user_name_col}` AS CHAR), '')) LIKE :search")
        params['search'] = f"%{str(search).strip().lower()}%"

    if user_active_col:
        where_clauses.append(f"COALESCE(`{user_active_col}`, 1) = 1")

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ''
    query = text(f"""
        SELECT
            CAST(`{user_id_col}` AS CHAR) AS id,
            CAST(`{user_name_col}` AS CHAR) AS name
        FROM `{user_table}`
        {where_sql}
        ORDER BY `{user_name_col}` ASC
        LIMIT 1000
    """)

    users = []
    with engine.connect() as conn:
        result = conn.execute(query, params)
        for row in result:
            user_id = str(row.id or '').strip()
            user_name = str(row.name or '').strip()
            if not user_id:
                continue
            users.append({
                'id': user_id,
                'name': user_name or user_id
            })
    return users


def _get_sagansa_user_map():
    try:
        users = _get_sagansa_users()
    except Exception:
        return {}
    return {str(user.get('id')): user for user in users}


def _sagansa_user_exists(user_id):
    engine, error_msg = get_sagansa_engine()
    if engine is None:
        raise RuntimeError(error_msg or 'Sagansa DB is not configured')

    user_table = _safe_identifier(os.environ.get('SAGANSA_USER_TABLE'), 'users')
    user_id_col = _safe_identifier(os.environ.get('SAGANSA_USER_ID_COLUMN'), 'id')
    user_active_col = _safe_identifier(os.environ.get('SAGANSA_USER_ACTIVE_COLUMN'), '')

    where_active_sql = f"AND COALESCE(`{user_active_col}`, 1) = 1" if user_active_col else ''
    query = text(f"""
        SELECT 1
        FROM `{user_table}`
        WHERE CAST(`{user_id_col}` AS CHAR) = :user_id
        {where_active_sql}
        LIMIT 1
    """)

    with engine.connect() as conn:
        row = conn.execute(query, {'user_id': str(user_id)}).fetchone()
        return bool(row)


def _ensure_payroll_employee_flags_table(conn):
    if conn.dialect.name == 'sqlite':
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS payroll_employee_flags (
                sagansa_user_id TEXT PRIMARY KEY,
                is_employee INTEGER NOT NULL DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
    else:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS payroll_employee_flags (
                sagansa_user_id VARCHAR(128) PRIMARY KEY,
                is_employee BOOLEAN NOT NULL DEFAULT TRUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """))


def _get_payroll_employee_ids(conn):
    _ensure_payroll_employee_flags_table(conn)
    rows = conn.execute(text("""
        SELECT CAST(sagansa_user_id AS CHAR) AS sagansa_user_id
        FROM payroll_employee_flags
        WHERE COALESCE(is_employee, 0) = 1
    """)).fetchall()
    return {str(row.sagansa_user_id or '').strip() for row in rows if str(row.sagansa_user_id or '').strip()}


def _is_payroll_employee(conn, user_id):
    normalized_user_id = str(user_id or '').strip()
    if not normalized_user_id:
        return False
    _ensure_payroll_employee_flags_table(conn)
    row = conn.execute(text("""
        SELECT COALESCE(is_employee, 0) AS is_employee
        FROM payroll_employee_flags
        WHERE CAST(sagansa_user_id AS CHAR) = :user_id
        LIMIT 1
    """), {'user_id': normalized_user_id}).fetchone()
    if not row:
        return False
    return _parse_bool(row.is_employee)


def _set_payroll_employee_flag(conn, user_id, is_employee):
    normalized_user_id = str(user_id or '').strip()
    if not normalized_user_id:
        raise ValueError('user_id is required')

    _ensure_payroll_employee_flags_table(conn)
    if not is_employee:
        conn.execute(text("""
            DELETE FROM payroll_employee_flags
            WHERE CAST(sagansa_user_id AS CHAR) = :user_id
        """), {'user_id': normalized_user_id})
        return

    now = datetime.now()
    if conn.dialect.name == 'sqlite':
        conn.execute(text("""
            INSERT INTO payroll_employee_flags (sagansa_user_id, is_employee, created_at, updated_at)
            VALUES (:user_id, 1, :now, :now)
            ON CONFLICT(sagansa_user_id) DO UPDATE SET
                is_employee = 1,
                updated_at = :now
        """), {'user_id': normalized_user_id, 'now': now})
    else:
        conn.execute(text("""
            INSERT INTO payroll_employee_flags (sagansa_user_id, is_employee, created_at, updated_at)
            VALUES (:user_id, TRUE, :now, :now)
            ON DUPLICATE KEY UPDATE
                is_employee = VALUES(is_employee),
                updated_at = VALUES(updated_at)
        """), {'user_id': normalized_user_id, 'now': now})


def _normalize_year(value):
    if value in (None, ''):
        return datetime.now().year
    try:
        year = int(value)
    except (TypeError, ValueError):
        return None
    if year < 1900 or year > 3000:
        return None
    return year


def _normalize_month(value):
    if value in (None, ''):
        return None
    try:
        month = int(value)
    except (TypeError, ValueError):
        return None
    if month < 1 or month > 12:
        return None
    return month


def _normalize_datetime_string(value):
    if value in (None, ''):
        return None
    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%d %H:%M:%S')
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time()).strftime('%Y-%m-%d %H:%M:%S')

    raw = str(value).strip()
    if not raw:
        return None

    raw = raw.replace('T', ' ')
    if raw.endswith('Z'):
        raw = raw[:-1]

    try:
        parsed = datetime.fromisoformat(raw)
        return parsed.strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        pass

    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d'):
        try:
            parsed = datetime.strptime(raw[:19], fmt)
            return parsed.strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            continue
    return None


def _safe_int(value, default=0):
    if value in (None, ''):
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _safe_json_dumps(value):
    try:
        return json.dumps(value, ensure_ascii=False, separators=(',', ':'))
    except (TypeError, ValueError):
        return '{}'


def _deep_get(data, path_candidates, default=None):
    for path in path_candidates:
        current = data
        ok = True
        for key in str(path).split('.'):
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                ok = False
                break
        if ok and current not in (None, ''):
            return current
    return default


def _extract_presence_records(payload):
    if isinstance(payload, list):
        return payload

    if not isinstance(payload, dict):
        return []

    for key in ('data', 'presences', 'items', 'records', 'results'):
        value = payload.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            nested_list = value.get('data')
            if isinstance(nested_list, list):
                return nested_list

    return []


def _parse_work_minutes(value):
    if value in (None, ''):
        return 0

    if isinstance(value, (int, float)):
        return max(0, int(float(value)))

    raw = str(value).strip()
    if not raw:
        return 0

    if ':' in raw:
        parts = raw.split(':')
        if len(parts) >= 2:
            try:
                hour_val = int(parts[0])
                min_val = int(parts[1])
                return max(0, (hour_val * 60) + min_val)
            except (TypeError, ValueError):
                return 0

    return max(0, _safe_int(raw, 0))


def _presence_source_key(presence_id, user_id, presence_date, check_in_at, check_out_at, status):
    normalized_presence_id = str(presence_id or '').strip()
    if normalized_presence_id:
        return f"id:{normalized_presence_id}"[:255]

    signature = "|".join([
        str(user_id or '').strip(),
        str(presence_date or '').strip(),
        str(check_in_at or '').strip(),
        str(check_out_at or '').strip(),
        str(status or '').strip()
    ])
    return f"sig:{signature}"[:255]


def _minutes_between(start_dt, end_dt):
    start_raw = _normalize_datetime_string(start_dt)
    end_raw = _normalize_datetime_string(end_dt)
    if not start_raw or not end_raw:
        return 0
    try:
        start_obj = datetime.strptime(start_raw, '%Y-%m-%d %H:%M:%S')
        end_obj = datetime.strptime(end_raw, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        return 0
    diff_minutes = int((end_obj - start_obj).total_seconds() // 60)
    return max(0, diff_minutes)


def _normalize_presence_record(raw_record, fallback_company_id=None):
    if not isinstance(raw_record, dict):
        return None

    presence_id = str(_deep_get(raw_record, ['id', 'presence_id', 'attendance_id'], '') or '').strip()
    user_id = str(_deep_get(raw_record, ['user_id', 'employee_id', 'user.id', 'employee.id'], '') or '').strip()
    creator_name = str(_deep_get(raw_record, ['creator', 'creator_name', 'user_name', 'employee_name', 'name', 'user.name', 'employee.name'], '') or '').strip()
    user_name = creator_name or str(_deep_get(raw_record, ['user_name', 'employee_name', 'name', 'user.name', 'employee.name'], '') or '').strip()
    store_name = str(_deep_get(raw_record, ['store', 'store_name', 'branch', 'location', 'store.name'], '') or '').strip()
    shift_name = str(_deep_get(raw_record, ['shift_name', 'shift.name'], '') or '').strip()
    shift_start_time = str(_deep_get(raw_record, ['shift_start_time', 'shift.start_time'], '') or '').strip()
    shift_end_time = str(_deep_get(raw_record, ['shift_end_time', 'shift.end_time'], '') or '').strip()
    shift_duration_hours = _safe_int(_deep_get(raw_record, ['shift_duration', 'shift.duration', 'shift_hours']), 0)
    presence_date = _normalize_iso_date(_deep_get(raw_record, ['presence_date', 'date', 'attendance_date', 'work_date']))
    check_in_at = _normalize_datetime_string(_deep_get(raw_record, ['check_in_at', 'check_in', 'clock_in', 'in_time']))
    check_out_at = _normalize_datetime_string(_deep_get(raw_record, ['check_out_at', 'check_out', 'clock_out', 'out_time']))
    status = str(_deep_get(raw_record, ['status', 'attendance_status', 'state'], '') or '').strip()
    source_created_at = _normalize_datetime_string(_deep_get(raw_record, ['created_at', 'inserted_at']))
    source_updated_at = _normalize_datetime_string(_deep_get(raw_record, ['updated_at', 'last_updated_at', 'modified_at']))
    company_id = str(_deep_get(raw_record, ['company_id', 'company.id'], fallback_company_id or '') or '').strip() or None

    if not presence_date and check_in_at:
        presence_date = check_in_at[:10]
    if not presence_date and check_out_at:
        presence_date = check_out_at[:10]
    if not presence_date and source_created_at:
        presence_date = source_created_at[:10]

    if not user_id and not user_name and not creator_name and not presence_date and not check_in_at and not check_out_at:
        return None

    work_minutes_raw = _deep_get(raw_record, ['work_minutes', 'working_minutes', 'duration_minutes', 'work_duration'])
    if work_minutes_raw in (None, ''):
        if shift_duration_hours > 0:
            work_minutes = shift_duration_hours * 60
        else:
            work_minutes = _minutes_between(check_in_at, check_out_at)
    else:
        work_minutes = _parse_work_minutes(work_minutes_raw)

    if not status:
        if check_in_at and check_out_at:
            status = 'present'
        elif check_in_at:
            status = 'checked_in'
        elif check_out_at:
            status = 'checked_out'

    source_key = _presence_source_key(presence_id, user_id, presence_date, check_in_at, check_out_at, status)

    return {
        'source_key': source_key,
        'sagansa_presence_id': presence_id or None,
        'sagansa_user_id': user_id or None,
        'user_name': user_name or None,
        'presence_date': presence_date,
        'check_in_at': check_in_at,
        'check_out_at': check_out_at,
        'status': status or None,
        'creator_name': creator_name or user_name or None,
        'store_name': store_name or None,
        'shift_name': shift_name or None,
        'shift_start_time': shift_start_time or None,
        'shift_end_time': shift_end_time or None,
        'shift_duration_hours': shift_duration_hours,
        'work_minutes': work_minutes,
        'source_created_at': source_created_at,
        'source_updated_at': source_updated_at,
        'company_id': company_id,
        'raw_payload': _safe_json_dumps(raw_record)
    }


def _ensure_payroll_presences_table(conn):
    if conn.dialect.name == 'sqlite':
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS payroll_presences (
                id TEXT PRIMARY KEY,
                source_key TEXT NOT NULL UNIQUE,
                sagansa_presence_id TEXT,
                sagansa_user_id TEXT,
                user_name TEXT,
                creator_name TEXT,
                store_name TEXT,
                shift_name TEXT,
                shift_start_time TEXT,
                shift_end_time TEXT,
                shift_duration_hours INTEGER NOT NULL DEFAULT 0,
                presence_date DATE,
                check_in_at DATETIME,
                check_out_at DATETIME,
                status TEXT,
                work_minutes INTEGER NOT NULL DEFAULT 0,
                company_id TEXT,
                source_created_at DATETIME,
                source_updated_at DATETIME,
                raw_payload TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_payroll_presences_date ON payroll_presences (presence_date)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_payroll_presences_user ON payroll_presences (sagansa_user_id)"))
    else:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS payroll_presences (
                id VARCHAR(64) PRIMARY KEY,
                source_key VARCHAR(255) NOT NULL UNIQUE,
                sagansa_presence_id VARCHAR(128) NULL,
                sagansa_user_id VARCHAR(128) NULL,
                user_name VARCHAR(255) NULL,
                creator_name VARCHAR(255) NULL,
                store_name VARCHAR(255) NULL,
                shift_name VARCHAR(255) NULL,
                shift_start_time VARCHAR(16) NULL,
                shift_end_time VARCHAR(16) NULL,
                shift_duration_hours INT NOT NULL DEFAULT 0,
                presence_date DATE NULL,
                check_in_at DATETIME NULL,
                check_out_at DATETIME NULL,
                status VARCHAR(64) NULL,
                work_minutes INT NOT NULL DEFAULT 0,
                company_id VARCHAR(64) NULL,
                source_created_at DATETIME NULL,
                source_updated_at DATETIME NULL,
                raw_payload LONGTEXT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_payroll_presences_date (presence_date),
                INDEX idx_payroll_presences_user (sagansa_user_id)
            )
        """))

    # Backfill columns for older table versions.
    existing_columns = _table_columns(conn, 'payroll_presences')
    if conn.dialect.name == 'sqlite':
        missing_defs = {
            'creator_name': "ALTER TABLE payroll_presences ADD COLUMN creator_name TEXT",
            'store_name': "ALTER TABLE payroll_presences ADD COLUMN store_name TEXT",
            'shift_name': "ALTER TABLE payroll_presences ADD COLUMN shift_name TEXT",
            'shift_start_time': "ALTER TABLE payroll_presences ADD COLUMN shift_start_time TEXT",
            'shift_end_time': "ALTER TABLE payroll_presences ADD COLUMN shift_end_time TEXT",
            'shift_duration_hours': "ALTER TABLE payroll_presences ADD COLUMN shift_duration_hours INTEGER NOT NULL DEFAULT 0",
            'source_created_at': "ALTER TABLE payroll_presences ADD COLUMN source_created_at DATETIME"
        }
    else:
        missing_defs = {
            'creator_name': "ALTER TABLE payroll_presences ADD COLUMN creator_name VARCHAR(255) NULL",
            'store_name': "ALTER TABLE payroll_presences ADD COLUMN store_name VARCHAR(255) NULL",
            'shift_name': "ALTER TABLE payroll_presences ADD COLUMN shift_name VARCHAR(255) NULL",
            'shift_start_time': "ALTER TABLE payroll_presences ADD COLUMN shift_start_time VARCHAR(16) NULL",
            'shift_end_time': "ALTER TABLE payroll_presences ADD COLUMN shift_end_time VARCHAR(16) NULL",
            'shift_duration_hours': "ALTER TABLE payroll_presences ADD COLUMN shift_duration_hours INT NOT NULL DEFAULT 0",
            'source_created_at': "ALTER TABLE payroll_presences ADD COLUMN source_created_at DATETIME NULL"
        }

    for column_name, alter_sql in missing_defs.items():
        if column_name not in existing_columns:
            conn.execute(text(alter_sql))


def _fetch_remote_presences(api_url, token, query_params=None):
    params = {k: v for k, v in (query_params or {}).items() if v not in (None, '')}
    url = str(api_url or '').strip()
    if not url:
        raise RuntimeError('Presence API URL is required')

    # Tolerate common typo such as "ttps://..."
    if url.startswith('ttps://'):
        url = f"https://{url[len('ttps://'):]}"
    elif url.startswith('//'):
        url = f"https:{url}"
    elif not (url.startswith('https://') or url.startswith('http://')):
        url = f"https://{url.lstrip('/')}"

    if params:
        separator = '&' if '?' in url else '?'
        url = f"{url}{separator}{urlparse.urlencode(params)}"

    headers = {'Accept': 'application/json'}
    if token:
        headers['Authorization'] = f"Bearer {token}"

    req = urlrequest.Request(url, headers=headers, method='GET')
    try:
        with urlrequest.urlopen(req, timeout=60) as resp:
            raw_body = resp.read().decode('utf-8')
        return json.loads(raw_body)
    except urlerror.HTTPError as e:
        err_body = e.read().decode('utf-8', errors='ignore')
        raise RuntimeError(f"Presence API request failed ({e.code}): {err_body[:500]}")
    except urlerror.URLError as e:
        raise RuntimeError(f"Presence API connection failed: {e.reason}")
    except json.JSONDecodeError:
        raise RuntimeError('Presence API did not return valid JSON')


@transaction_bp.route('/api/transactions/manual', methods=['POST'])
def create_manual_transaction():
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    try:
        data = request.json or {}
        txn_date = data.get('txn_date')
        header_description = data.get('description', 'Manual Journal')
        company_id = data.get('company_id')
        lines = data.get('lines', [])
        
        # Validation
        if not txn_date or not lines:
            return jsonify({'error': 'Missing required fields (date, lines)'}), 400

        # Calculate totals and validate balance
        total_debit = 0.0
        total_credit = 0.0
        for line in lines:
            try:
                amt = float(line.get('amount', 0))
            except (ValueError, TypeError):
                return jsonify({'error': f"Invalid amount in line for COA {line.get('coa_id')}"}), 400
            
            side = str(line.get('side', 'DEBIT')).upper()
            if side == 'DEBIT':
                total_debit += amt
            else:
                total_credit += amt
        
        # Allow small floating point difference
        if abs(total_debit - total_credit) > 0.01:
            return jsonify({'error': f'Journal is not balanced. Debits ({total_debit:,.2f}) != Credits ({total_credit:,.2f})'}), 400

        now = datetime.now()
        parent_txn_id = str(uuid.uuid4())
        
        with engine.begin() as conn:
            mark_columns = _table_columns(conn, 'marks')
            txn_columns = _table_columns(conn, 'transactions')
            
            # 1. Create Parent "Header" Transaction (0 amount or total debit, doesn't matter much as it will be excluded if children exist)
            conn.execute(text("""
                INSERT INTO transactions (id, txn_date, description, amount, db_cr, bank_code, source_file, company_id, created_at, updated_at)
                VALUES (:id, :txn_date, :description, :amount, 'DB', 'MANUAL', 'MANUAL', :company_id, :now, :now)
            """), {
                'id': parent_txn_id,
                'txn_date': txn_date,
                'description': header_description,
                'amount': total_debit,
                'company_id': company_id if company_id else None,
                'now': now
            })
            
            # 2. Create Child Transactions for each line
            for line in lines:
                line_id = str(uuid.uuid4())
                line_amount = float(line.get('amount', 0))
                line_side = str(line.get('side', 'DEBIT')).upper()
                line_coa_id = line.get('coa_id')
                line_desc = line.get('description') or header_description
                
                # Create a specific Mark for this line mapping
                mark_id = str(uuid.uuid4())
                mark_name = f"JV: {line_desc}"
                
                mark_data = {
                    'id': mark_id,
                    'internal_report': mark_name,
                    'personal_use': mark_name,
                    'created_at': now,
                    'updated_at': now
                }
                if 'is_asset' in mark_columns: mark_data['is_asset'] = False
                if 'is_service' in mark_columns: mark_data['is_service'] = False
                if 'is_salary_component' in mark_columns: mark_data['is_salary_component'] = False
                if 'is_rental' in mark_columns: mark_data['is_rental'] = False
                if 'is_coretax' in mark_columns: mark_data['is_coretax'] = False
                
                insert_cols = [c for c in mark_data.keys() if c in mark_columns]
                cols_sql = ', '.join(insert_cols)
                vals_sql = ', '.join(f":{c}" for c in insert_cols)
                conn.execute(text(f"INSERT INTO marks ({cols_sql}) VALUES ({vals_sql})"), mark_data)
                
                # Create Mapping
                mapping_id = str(uuid.uuid4())
                conn.execute(text("""
                    INSERT INTO mark_coa_mapping (id, mark_id, coa_id, mapping_type, created_at, updated_at)
                    VALUES (:id, :mark_id, :coa_id, :side, :now, :now)
                """), {
                    'id': mapping_id,
                    'mark_id': mark_id,
                    'coa_id': line_coa_id,
                    'side': line_side,
                    'now': now
                })
                
                # Child Transaction record
                line_db_cr = 'DB' if line_side == 'DEBIT' else 'CR'
                
                child_data = {
                    'id': line_id,
                    'parent_id': parent_txn_id,
                    'txn_date': txn_date,
                    'description': line_desc,
                    'amount': line_amount,
                    'db_cr': line_db_cr,
                    'bank_code': 'MANUAL',
                    'source_file': 'MANUAL',
                    'mark_id': mark_id,
                    'company_id': company_id if company_id else None,
                    'now': now
                }
                
                # Filter columns based on actual schema
                child_insert_cols = [c for c in child_data.keys() if c in txn_columns]
                c_cols_sql = ', '.join(child_insert_cols)
                c_vals_sql = ', '.join(f":{c}" for c in child_insert_cols)
                
                conn.execute(text(f"INSERT INTO transactions ({c_cols_sql}) VALUES ({c_vals_sql})"), child_data)
                
        return jsonify({'message': 'Manual multi-line journal entry created successfully', 'id': parent_txn_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/api/transactions', methods=['GET'])
def get_transactions():
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT t.*, m.internal_report, m.personal_use, m.tax_report, 
                       c.name as company_name, c.short_name as company_short_name
                FROM transactions t 
                LEFT JOIN marks m ON t.mark_id = m.id 
                LEFT JOIN companies c ON t.company_id = c.id
                ORDER BY t.txn_date DESC, t.created_at DESC
            """)
            result = conn.execute(query)
            transactions = []
            for row in result:
                d = dict(row._mapping)
                for key, value in d.items():
                    if isinstance(value, datetime):
                        d[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                    elif isinstance(value, Decimal):
                        d[key] = float(value)
                d['db_cr'] = _normalize_db_cr(d.get('db_cr'))
                transactions.append(d)
            return jsonify({'transactions': transactions})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/api/transactions/upload-summary', methods=['GET'])
def get_upload_summary():
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT t.source_file, 
                       COUNT(*) as transaction_count, 
                       MIN(t.txn_date) as start_date, 
                       MAX(t.txn_date) as end_date,
                       t.bank_code,
                       COUNT(DISTINCT t.company_id) as company_count,
                       SUM(CASE WHEN t.db_cr = 'DB' THEN t.amount ELSE 0 END) as total_debit,
                       SUM(CASE WHEN t.db_cr = 'CR' THEN t.amount ELSE 0 END) as total_credit,
                       MAX(t.created_at) as last_upload
                FROM transactions t
                GROUP BY t.source_file, t.bank_code
                ORDER BY last_upload DESC
            """)
            result = conn.execute(query)
            summary = []
            for row in result:
                d = dict(row._mapping)
                for key, value in d.items():
                    if isinstance(value, datetime):
                        d[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                    elif isinstance(value, Decimal):
                        d[key] = float(value)
                summary.append(d)
            return jsonify({'summary': summary})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/api/transactions/delete-by-source', methods=['POST'])
def delete_by_source():
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    data = request.json or {}
    source_file = data.get('source_file')
    bank_code = data.get('bank_code')
    company_id = data.get('company_id')
    
    if not source_file:
        return jsonify({'error': 'source_file is required'}), 400
        
    try:
        with engine.begin() as conn:
            where_clauses = ["source_file = :source_file"]
            params = {"source_file": source_file}
            
            if bank_code:
                where_clauses.append("bank_code = :bank_code")
                params["bank_code"] = bank_code
            if company_id:
                where_clauses.append("company_id = :company_id")
                params["company_id"] = company_id
                
            query = text(f"DELETE FROM transactions WHERE {' AND '.join(where_clauses)}")
            result = conn.execute(query, params)
            return jsonify({'message': f'Deleted {result.rowcount} transactions'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/api/marks', methods=['GET'])
def get_marks():
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    try:
        with engine.connect() as conn:
            mark_columns = _table_columns(conn, 'marks')
            result = conn.execute(text("SELECT * FROM marks ORDER BY personal_use ASC"))
            marks = []
            marks_dict = {}
            for row in result:
                d = dict(row._mapping)
                for key, value in d.items():
                    if isinstance(value, datetime):
                        d[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                # Keep response contract stable across DB schema versions.
                if 'is_asset' not in d:
                    d['is_asset'] = False
                if 'is_service' not in d:
                    d['is_service'] = False
                if 'is_salary_component' not in d:
                    d['is_salary_component'] = False
                if 'is_rental' not in d:
                    d['is_rental'] = False
                if 'is_coretax' not in d:
                    d['is_coretax'] = False
                d['is_asset'] = _parse_bool(d.get('is_asset'))
                d['is_service'] = _parse_bool(d.get('is_service'))
                d['is_salary_component'] = _parse_bool(d.get('is_salary_component'))
                d['is_rental'] = _parse_bool(d.get('is_rental'))
                d['is_coretax'] = _parse_bool(d.get('is_coretax'))
                d['mappings'] = []
                marks.append(d)
                marks_dict[d['id']] = d

            mapping_columns = _table_columns(conn, 'mark_coa_mapping')
            mapping_scope_filter = ""
            if 'report_type' in mapping_columns:
                if conn.dialect.name == 'sqlite':
                    mapping_scope_filter = "WHERE LOWER(COALESCE(CAST(mcm.report_type AS TEXT), 'real')) = 'real'"
                else:
                    mapping_scope_filter = "WHERE LOWER(COALESCE(CAST(mcm.report_type AS CHAR), 'real')) = 'real'"

            mapping_query = text(f"""
                SELECT mcm.mark_id, mcm.coa_id, mcm.mapping_type, coa.code, coa.name
                FROM mark_coa_mapping mcm
                JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
                {mapping_scope_filter}
            """)
            mapping_result = conn.execute(mapping_query)
            
            for row in mapping_result:
                m = dict(row._mapping)
                mark_id = m['mark_id']
                if mark_id in marks_dict:
                    marks_dict[mark_id]['mappings'].append({
                        'id': m['coa_id'],
                        'coa_id': m['coa_id'],
                        'code': m['code'],
                        'name': m['name'],
                        'type': m['mapping_type']
                    })

            return jsonify({'marks': marks})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/api/marks', methods=['POST'])
def create_mark():
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    try:
        data = request.json or {}
        now = datetime.now()
        mark_id = str(uuid.uuid4())
        with engine.begin() as conn:
            mark_columns = _table_columns(conn, 'marks')
            if 'is_service' not in mark_columns:
                return jsonify({'error': 'Kolom is_service belum tersedia. Jalankan migrasi terbaru.'}), 400
            if 'is_coretax' not in mark_columns:
                return jsonify({'error': 'Kolom is_coretax belum tersedia. Jalankan migrasi terbaru.'}), 400
            new_row = {
                'id': mark_id,
                'internal_report': data.get('internal_report', ''),
                'personal_use': data.get('personal_use', ''),
                'tax_report': data.get('tax_report', ''),
                'is_asset': _parse_bool(data.get('is_asset', False)),
                'is_service': _parse_bool(data.get('is_service', False)),
                'is_salary_component': _parse_bool(data.get('is_salary_component', False)),
                'is_rental': _parse_bool(data.get('is_rental', False)),
                'is_coretax': _parse_bool(data.get('is_coretax', False)),
                'created_at': now,
                'updated_at': now
            }
            insert_columns = [column for column in new_row.keys() if column in mark_columns]
            columns_sql = ', '.join(insert_columns)
            values_sql = ', '.join(f":{column}" for column in insert_columns)
            conn.execute(text(f"""
                INSERT INTO marks ({columns_sql})
                VALUES ({values_sql})
            """), new_row)
        return jsonify({'message': 'Mark created successfully', 'id': mark_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/api/marks/<mark_id>', methods=['PUT', 'DELETE'])
def update_or_delete_mark(mark_id):
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    try:
        if request.method == 'DELETE':
            with engine.connect() as conn:
                conn.execute(text("UPDATE transactions SET mark_id = NULL WHERE mark_id = :id"), {'id': mark_id})
                conn.execute(text("DELETE FROM marks WHERE id = :id"), {'id': mark_id})
                conn.commit()
                return jsonify({'message': 'Mark deleted successfully'})
        
        data = request.json or {}
        with engine.begin() as conn:
            mark_columns = _table_columns(conn, 'marks')
            if 'is_service' in data and 'is_service' not in mark_columns:
                return jsonify({'error': 'Kolom is_service belum tersedia. Jalankan migrasi terbaru.'}), 400
            if 'is_salary_component' in data and 'is_salary_component' not in mark_columns:
                return jsonify({'error': 'Kolom is_salary_component belum tersedia. Jalankan migrasi terbaru.'}), 400
            if 'is_rental' in data and 'is_rental' not in mark_columns:
                return jsonify({'error': 'Kolom is_rental belum tersedia. Jalankan migrasi terbaru.'}), 400
            if 'is_coretax' in data and 'is_coretax' not in mark_columns:
                return jsonify({'error': 'Kolom is_coretax belum tersedia. Jalankan migrasi terbaru.'}), 400

            field_map = {
                'internal_report': 'internal_report',
                'personal_use': 'personal_use',
                'tax_report': 'tax_report',
                'is_asset': 'is_asset',
                'is_service': 'is_service',
                'is_salary_component': 'is_salary_component',
                'is_rental': 'is_rental',
                'is_coretax': 'is_coretax'
            }

            params = {'id': mark_id, 'updated_at': datetime.now()}
            set_fields = []

            for payload_key, column_name in field_map.items():
                if payload_key in data and column_name in mark_columns:
                    if payload_key in {'is_asset', 'is_service', 'is_salary_component', 'is_rental', 'is_coretax'}:
                        params[payload_key] = _parse_bool(data.get(payload_key))
                    else:
                        params[payload_key] = data.get(payload_key)
                    set_fields.append(f"{column_name} = :{payload_key}")

            if 'updated_at' in mark_columns:
                set_fields.append("updated_at = :updated_at")

            if not set_fields:
                return jsonify({'error': 'No valid fields to update'}), 400

            query = text(f"""
                UPDATE marks
                SET {', '.join(set_fields)}
                WHERE id = :id
            """)
            conn.execute(query, params)
        return jsonify({'message': 'Mark updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/api/transactions/<txn_id>/assign-mark', methods=['POST'])
def assign_mark_transaction(txn_id):
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    try:
        data = request.json
        mark_id = data.get('mark_id')
        now = datetime.now()
        with engine.begin() as conn:
            txn_columns = _table_columns(conn, 'transactions')
            if mark_id and 'parent_id' in txn_columns:
                has_children = conn.execute(text("""
                    SELECT 1
                    FROM transactions
                    WHERE parent_id = :txn_id
                    LIMIT 1
                """), {'txn_id': txn_id}).fetchone()
                if has_children:
                    return jsonify({
                        'error': 'Transaksi ini sudah memiliki multi mark (split). Ubah mark pada split, bukan parent.'
                    }), 400

            query = text("UPDATE transactions SET mark_id = :mark_id, updated_at = :updated_at WHERE id = :id")
            conn.execute(query, {'id': txn_id, 'mark_id': mark_id, 'updated_at': now})
            return jsonify({'message': 'Transaction marked successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@transaction_bp.route('/api/transactions/<txn_id>/amortization-group', methods=['PUT', 'PATCH', 'POST'])
def update_transaction_amortization_group(txn_id):
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500

    payload = request.json or {}
    asset_group_id_raw = payload.get('asset_group_id')
    asset_group_id = str(asset_group_id_raw).strip() if asset_group_id_raw not in (None, '') else None
    is_amortizable = _parse_bool(payload.get('is_amortizable', True))
    use_half_rate = _parse_bool(payload.get('use_half_rate', False))
    amortization_start_date = _normalize_iso_date(payload.get('amortization_start_date'))
    amortization_notes = payload.get('amortization_notes')
    if amortization_notes is not None:
        amortization_notes = str(amortization_notes).strip()
    if amortization_notes == '':
        amortization_notes = None

    useful_life_raw = payload.get('amortization_useful_life')
    amortization_useful_life = None
    if useful_life_raw not in (None, ''):
        try:
            amortization_useful_life = int(useful_life_raw)
            if amortization_useful_life <= 0:
                return jsonify({'error': 'amortization_useful_life must be greater than 0'}), 400
        except (TypeError, ValueError):
            return jsonify({'error': 'amortization_useful_life must be numeric'}), 400

    try:
        with engine.begin() as conn:
            txn_columns = _table_columns(conn, 'transactions')

            required_columns = {'amortization_asset_group_id', 'is_amortizable', 'use_half_rate', 'amortization_start_date'}
            if not required_columns.issubset(txn_columns):
                return jsonify({
                    'error': 'Kolom amortization di transactions belum lengkap. Jalankan migrasi amortization terbaru.'
                }), 400

            set_fields = [
                "amortization_asset_group_id = :asset_group_id",
                "is_amortizable = :is_amortizable",
                "use_half_rate = :use_half_rate",
                "amortization_start_date = :amortization_start_date"
            ]
            params = {
                'txn_id': txn_id,
                'asset_group_id': asset_group_id,
                'is_amortizable': is_amortizable,
                'use_half_rate': use_half_rate,
                'amortization_start_date': amortization_start_date
            }

            if 'amortization_useful_life' in txn_columns:
                set_fields.append("amortization_useful_life = :amortization_useful_life")
                params['amortization_useful_life'] = amortization_useful_life
            if 'amortization_notes' in txn_columns:
                set_fields.append("amortization_notes = :amortization_notes")
                params['amortization_notes'] = amortization_notes
            if 'updated_at' in txn_columns:
                set_fields.append("updated_at = :updated_at")
                params['updated_at'] = datetime.now()

            query = text(f"""
                UPDATE transactions
                SET {', '.join(set_fields)}
                WHERE id = :txn_id
            """)
            result = conn.execute(query, params)
            if int(result.rowcount or 0) == 0:
                return jsonify({'error': 'Transaction not found'}), 404

        return jsonify({
            'message': 'Transaction amortization group updated successfully',
            'transaction_id': txn_id,
            'asset_group_id': asset_group_id,
            'is_amortizable': is_amortizable,
            'use_half_rate': use_half_rate,
            'amortization_start_date': amortization_start_date,
            'amortization_useful_life': amortization_useful_life,
            'amortization_notes': amortization_notes
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@transaction_bp.route('/api/service-marks', methods=['GET'])
def get_service_marks():
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500

    company_id = request.args.get('company_id')
    year = request.args.get('year')
    year_int = None
    if year not in (None, ''):
        try:
            year_int = int(year)
        except ValueError:
            return jsonify({'error': 'year must be numeric'}), 400

    try:
        with engine.connect() as conn:
            mark_columns = _table_columns(conn, 'marks')
            service_expr = "COALESCE(m.is_service, FALSE)" if 'is_service' in mark_columns else "FALSE"
            asset_expr = "COALESCE(m.is_asset, FALSE)" if 'is_asset' in mark_columns else "FALSE"
            split_exclusion = _split_parent_exclusion_clause(conn, 't')

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

            query = text(f"""
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
            """)
            result = conn.execute(query, params)

            marks = []
            for row in result:
                d = dict(row._mapping)
                d['is_asset'] = _parse_bool(d.get('is_asset'))
                d['is_service'] = _parse_bool(d.get('is_service'))
                d['transaction_count'] = int(d.get('transaction_count') or 0)
                marks.append(d)

        return jsonify({'marks': marks})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@transaction_bp.route('/api/service-marks/<mark_id>', methods=['PUT'])
def update_service_mark(mark_id):
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500

    data = request.json or {}
    is_service = _parse_bool(data.get('is_service', False))

    try:
        with engine.begin() as conn:
            mark_columns = _table_columns(conn, 'marks')
            if 'is_service' not in mark_columns:
                return jsonify({'error': 'is_service column is not available. Run latest migration.'}), 400

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
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@transaction_bp.route('/api/service-transactions', methods=['GET'])
def get_service_transactions():
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500

    company_id = request.args.get('company_id')
    search = (request.args.get('search') or '').strip().lower()
    year = request.args.get('year')
    year_int = None
    if year not in (None, ''):
        try:
            year_int = int(year)
        except ValueError:
            return jsonify({'error': 'year must be numeric'}), 400

    try:
        with engine.connect() as conn:
            mark_columns = _table_columns(conn, 'marks')
            txn_columns = _table_columns(conn, 'transactions')
            split_exclusion = _split_parent_exclusion_clause(conn, 't')

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

            query = text(f"""
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
            """)
            result = conn.execute(query, params)

            transactions = []
            for row in result:
                d = dict(row._mapping)
                for key, value in d.items():
                    if isinstance(value, datetime):
                        d[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                    elif isinstance(value, date):
                        d[key] = value.isoformat()
                    elif isinstance(value, Decimal):
                        d[key] = float(value)
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
                transactions.append(d)

        return jsonify({'transactions': transactions})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@transaction_bp.route('/api/service-transactions/<txn_id>/npwp', methods=['PUT'])
def update_service_transaction_tax_config(txn_id):
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500

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
        return jsonify({'error': 'NPWP wajib 15 digit angka jika status NPWP = ada'}), 400
    if has_tax_payment_date and data.get('tax_payment_date') not in (None, '') and not tax_payment_date:
        return jsonify({'error': 'tax_payment_date harus format YYYY-MM-DD'}), 400

    try:
        with engine.begin() as conn:
            txn_columns = _table_columns(conn, 'transactions')
            if 'service_npwp' not in txn_columns:
                return jsonify({'error': 'service_npwp column is not available. Run latest migration.'}), 400

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
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@transaction_bp.route('/api/payroll/presences/sync', methods=['POST'])
def sync_payroll_presences():
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500

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
        return jsonify({'error': 'year must be numeric (1900-3000)'}), 400
    if payload.get('month') not in (None, '') and month is None:
        return jsonify({'error': 'month must be numeric (1-12)'}), 400
    if (payload.get('start_date') or payload.get('date_start')) and not start_date:
        return jsonify({'error': 'start_date/date_start must be YYYY-MM-DD'}), 400
    if (payload.get('end_date') or payload.get('date_end')) and not end_date:
        return jsonify({'error': 'end_date/date_end must be YYYY-MM-DD'}), 400
    if not token:
        return jsonify({'error': 'Presence API token is required (payload.token or env SAGANSA_PRESENCE_TOKEN)'}), 400

    remote_params = {}
    if year is not None:
        remote_params['year'] = year
    if month is not None:
        remote_params['month'] = month
    if start_date:
        remote_params['start_date'] = start_date
    if end_date:
        remote_params['end_date'] = end_date

    try:
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

                row_id = str(existing.id) if existing and getattr(existing, 'id', None) else str(uuid.uuid4())
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
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@transaction_bp.route('/api/payroll/presences', methods=['GET'])
def get_payroll_presences():
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500

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
        return jsonify({'error': 'year must be numeric (1900-3000)'}), 400
    if request.args.get('month') not in (None, '') and month is None:
        return jsonify({'error': 'month must be numeric (1-12)'}), 400
    if (request.args.get('date_start') or request.args.get('start_date')) and not date_start:
        return jsonify({'error': 'date_start/start_date must be YYYY-MM-DD'}), 400
    if (request.args.get('date_end') or request.args.get('end_date')) and not date_end:
        return jsonify({'error': 'date_end/end_date must be YYYY-MM-DD'}), 400

    try:
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
            query = text(f"""
                SELECT
                    id,
                    source_key,
                    sagansa_presence_id,
                    sagansa_user_id,
                    user_name,
                    creator_name,
                    store_name,
                    shift_name,
                    shift_start_time,
                    shift_end_time,
                    shift_duration_hours,
                    presence_date,
                    check_in_at,
                    check_out_at,
                    status,
                    work_minutes,
                    company_id,
                    source_created_at,
                    source_updated_at,
                    raw_payload,
                    created_at,
                    updated_at
                FROM payroll_presences
                {where_sql}
                ORDER BY presence_date DESC, check_in_at DESC, created_at DESC
                LIMIT :limit
            """)
            result = conn.execute(query, params)

            rows = []
            for row in result:
                d = dict(row._mapping)
                for key, value in d.items():
                    if isinstance(value, datetime):
                        d[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                    elif isinstance(value, date):
                        d[key] = value.strftime('%Y-%m-%d')
                    elif isinstance(value, Decimal):
                        d[key] = float(value)
                d['work_minutes'] = _safe_int(d.get('work_minutes'), 0)
                rows.append(d)

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
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@transaction_bp.route('/api/payroll/users', methods=['GET'])
def get_payroll_users():
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500

    search = (request.args.get('search') or '').strip()
    employees_only = _parse_bool(request.args.get('employees_only', False))
    try:
        users = _get_sagansa_users(search=search or None)
        with engine.connect() as conn:
            employee_user_ids = _get_payroll_employee_ids(conn)
        for user in users:
            user['is_employee'] = user.get('id') in employee_user_ids
        if employees_only:
            users = [user for user in users if user.get('is_employee')]
        return jsonify({'users': users})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@transaction_bp.route('/api/payroll/users/<user_id>/employee', methods=['PUT', 'POST', 'PATCH'])
@transaction_bp.route('/api/payroll/users/<user_id>/employee/', methods=['PUT', 'POST', 'PATCH'])
def update_payroll_user_employee_status(user_id):
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500

    normalized_user_id = str(user_id or '').strip()
    if not normalized_user_id:
        return jsonify({'error': 'user_id is required'}), 400

    payload = request.json or {}
    is_employee = _parse_bool(payload.get('is_employee', False))

    try:
        if not _sagansa_user_exists(normalized_user_id):
            return jsonify({'error': f'User Sagansa tidak ditemukan atau tidak aktif: {normalized_user_id}'}), 400

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
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@transaction_bp.route('/api/payroll/transactions', methods=['GET'])
def get_payroll_transactions():
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500

    company_id = request.args.get('company_id')
    year = _normalize_year(request.args.get('year'))
    month = _normalize_month(request.args.get('month'))
    search = (request.args.get('search') or '').strip().lower()
    user_id = (request.args.get('user_id') or '').strip()

    if year is None:
        return jsonify({'error': 'year must be numeric (1900-3000)'}), 400
    if request.args.get('month') not in (None, '') and month is None:
        return jsonify({'error': 'month must be numeric (1-12)'}), 400

    try:
        with engine.connect() as conn:
            mark_columns = _table_columns(conn, 'marks')
            txn_columns = _table_columns(conn, 'transactions')
            split_exclusion = _split_parent_exclusion_clause(conn, 't')

            if 'is_salary_component' not in mark_columns:
                return jsonify({
                    'transactions': [],
                    'summary': {
                        'total_transactions': 0,
                        'assigned_transactions': 0,
                        'total_amount': 0.0
                    },
                    'message': 'Kolom is_salary_component belum tersedia. Jalankan migrasi terbaru.'
                })

            user_col_expr = "t.sagansa_user_id" if 'sagansa_user_id' in txn_columns else "NULL"
            period_col_expr = "t.payroll_period_month" if 'payroll_period_month' in txn_columns else "NULL"
            if conn.dialect.name == 'sqlite':
                effective_date_expr = "COALESCE(t.payroll_period_month, t.txn_date)" if 'payroll_period_month' in txn_columns else "t.txn_date"
                year_filter = f"strftime('%Y', {effective_date_expr}) = :year_str"
                month_filter = f"AND strftime('%m', {effective_date_expr}) = :month_str" if month else ""
                effective_period_expr = f"strftime('%Y-%m', {effective_date_expr})"
                params = {
                    'company_id': company_id,
                    'year_str': f"{year:04d}",
                    'month_str': f"{month:02d}" if month else None,
                    'search': f"%{search}%" if search else None,
                    'user_id': user_id or None
                }
            else:
                effective_date_expr = "COALESCE(t.payroll_period_month, t.txn_date)" if 'payroll_period_month' in txn_columns else "t.txn_date"
                year_filter = f"YEAR({effective_date_expr}) = :year"
                month_filter = f"AND MONTH({effective_date_expr}) = :month" if month else ""
                effective_period_expr = f"DATE_FORMAT({effective_date_expr}, '%Y-%m')"
                params = {
                    'company_id': company_id,
                    'year': year,
                    'month': month,
                    'search': f"%{search}%" if search else None,
                    'user_id': user_id or None
                }

            user_filter = "AND (:user_id IS NULL OR COALESCE(CAST(t.sagansa_user_id AS CHAR), '') = :user_id)" if 'sagansa_user_id' in txn_columns else ""

            query = text(f"""
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
            """)
            rows = conn.execute(query, params)

            user_map = _get_sagansa_user_map()
            employee_user_ids = _get_payroll_employee_ids(conn)
            transactions = []
            total_amount = 0.0
            assigned_count = 0
            for row in rows:
                d = dict(row._mapping)
                for key, value in d.items():
                    if isinstance(value, datetime):
                        d[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                    elif isinstance(value, date):
                        d[key] = value.isoformat()
                    elif isinstance(value, Decimal):
                        d[key] = float(value)

                amount_abs = abs(float(d.get('amount') or 0.0))
                total_amount += amount_abs
                d['amount'] = amount_abs
                component_name = d.get('personal_use') or d.get('internal_report') or d.get('tax_report') or '(Unnamed Salary Component)'
                d['component_name'] = component_name
                current_user_id = str(d.get('sagansa_user_id') or '').strip() or None
                d['sagansa_user_id'] = current_user_id
                d['sagansa_user_name'] = (user_map.get(current_user_id, {}).get('name') or current_user_id) if current_user_id else None
                d['is_employee'] = bool(current_user_id and current_user_id in employee_user_ids)
                d['payroll_period_month'] = _normalize_month_start(d.get('payroll_period_month'))
                d['effective_payroll_period'] = str(d.get('effective_payroll_period') or '').strip() or None
                if current_user_id:
                    assigned_count += 1
                transactions.append(d)

        return jsonify({
            'transactions': transactions,
            'summary': {
                'total_transactions': len(transactions),
                'assigned_transactions': assigned_count,
                'total_amount': total_amount
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@transaction_bp.route('/api/payroll/transactions/<txn_id>/assign-user', methods=['PUT'])
def assign_payroll_user(txn_id):
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500

    payload = request.json or {}
    user_id_raw = payload.get('sagansa_user_id')
    user_id = str(user_id_raw).strip() if user_id_raw not in (None, '') else None

    try:
        with engine.begin() as conn:
            txn_columns = _table_columns(conn, 'transactions')
            if 'sagansa_user_id' not in txn_columns:
                return jsonify({'error': 'Kolom sagansa_user_id belum tersedia. Jalankan migrasi terbaru.'}), 400

            if user_id and not _sagansa_user_exists(user_id):
                return jsonify({'error': f'User Sagansa tidak ditemukan atau tidak aktif: {user_id}'}), 400
            if user_id and not _is_payroll_employee(conn, user_id):
                return jsonify({'error': f'User Sagansa belum ditandai sebagai employee: {user_id}'}), 400

            conn.execute(text("""
                UPDATE transactions
                SET sagansa_user_id = :sagansa_user_id,
                    updated_at = :updated_at
                WHERE id = :txn_id
            """), {
                'sagansa_user_id': user_id,
                'updated_at': datetime.now(),
                'txn_id': txn_id
            })

        user_map = _get_sagansa_user_map() if user_id else {}
        return jsonify({
            'message': 'Payroll user assigned successfully',
            'txn_id': txn_id,
            'sagansa_user_id': user_id,
            'sagansa_user_name': (user_map.get(user_id, {}).get('name') or user_id) if user_id else None
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@transaction_bp.route('/api/payroll/transactions/<txn_id>/period-month', methods=['PUT'])
def update_payroll_transaction_period_month(txn_id):
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500

    payload = request.json or {}
    month_raw = payload.get('payroll_period_month')
    month_value = _normalize_month_start(month_raw) if month_raw not in (None, '') else None

    if month_raw not in (None, '') and not month_value:
        return jsonify({'error': 'payroll_period_month harus format YYYY-MM atau YYYY-MM-DD'}), 400

    try:
        with engine.begin() as conn:
            txn_columns = _table_columns(conn, 'transactions')
            if 'payroll_period_month' not in txn_columns:
                return jsonify({'error': 'Kolom payroll_period_month belum tersedia. Jalankan migrasi terbaru.'}), 400

            conn.execute(text("""
                UPDATE transactions
                SET payroll_period_month = :payroll_period_month,
                    updated_at = :updated_at
                WHERE id = :txn_id
            """), {
                'payroll_period_month': month_value,
                'updated_at': datetime.now(),
                'txn_id': txn_id
            })

        effective_period = (month_value or '')[:7] if month_value else None
        return jsonify({
            'message': 'Payroll period month updated successfully',
            'txn_id': txn_id,
            'payroll_period_month': month_value,
            'effective_payroll_period': effective_period
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@transaction_bp.route('/api/payroll/transactions/bulk-assign-user', methods=['PUT', 'POST'])
def bulk_assign_payroll_user():
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500

    payload = request.json or {}
    txn_ids_raw = payload.get('transaction_ids') or []
    user_id_raw = payload.get('sagansa_user_id')
    user_id = str(user_id_raw).strip() if user_id_raw not in (None, '') else None

    if not isinstance(txn_ids_raw, list):
        return jsonify({'error': 'transaction_ids must be an array'}), 400

    txn_ids = []
    seen = set()
    for raw_id in txn_ids_raw:
        normalized = str(raw_id or '').strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        txn_ids.append(normalized)

    if not txn_ids:
        return jsonify({'error': 'No transaction IDs provided'}), 400

    try:
        with engine.begin() as conn:
            txn_columns = _table_columns(conn, 'transactions')
            if 'sagansa_user_id' not in txn_columns:
                return jsonify({'error': 'Kolom sagansa_user_id belum tersedia. Jalankan migrasi terbaru.'}), 400

            if user_id and not _sagansa_user_exists(user_id):
                return jsonify({'error': f'User Sagansa tidak ditemukan atau tidak aktif: {user_id}'}), 400
            if user_id and not _is_payroll_employee(conn, user_id):
                return jsonify({'error': f'User Sagansa belum ditandai sebagai employee: {user_id}'}), 400

            update_query = text("""
                UPDATE transactions
                SET sagansa_user_id = :sagansa_user_id,
                    updated_at = :updated_at
                WHERE id IN :ids
            """).bindparams(bindparam('ids', expanding=True))
            result = conn.execute(update_query, {
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
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@transaction_bp.route('/api/payroll/monthly-summary', methods=['GET'])
def get_payroll_monthly_summary():
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500

    company_id = request.args.get('company_id')
    year = _normalize_year(request.args.get('year'))
    month = _normalize_month(request.args.get('month'))

    if year is None:
        return jsonify({'error': 'year must be numeric (1900-3000)'}), 400
    if request.args.get('month') not in (None, '') and month is None:
        return jsonify({'error': 'month must be numeric (1-12)'}), 400

    try:
        with engine.connect() as conn:
            mark_columns = _table_columns(conn, 'marks')
            txn_columns = _table_columns(conn, 'transactions')
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
                params = {
                    'company_id': company_id,
                    'year_str': f"{year:04d}",
                    'month_str': f"{month:02d}"
                }
            else:
                period_clause = f"YEAR({effective_date_expr}) = :year"
                if month:
                    period_clause += f" AND MONTH({effective_date_expr}) = :month"
                params = {
                    'company_id': company_id,
                    'year': year,
                    'month': month
                }

            query = text(f"""
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
                  AND {period_clause}
                  AND (:company_id IS NULL OR t.company_id = :company_id)
                  {split_exclusion}
            """)
            result = conn.execute(query, params)

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
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@transaction_bp.route('/api/transactions/<txn_id>/assign-company', methods=['POST'])
def assign_company_transaction(txn_id):
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    try:
        data = request.json
        company_id = data.get('company_id')
        now = datetime.now()
        with engine.connect() as conn:
            query = text("UPDATE transactions SET company_id = :company_id, updated_at = :updated_at WHERE id = :id")
            conn.execute(query, {'id': txn_id, 'company_id': company_id, 'updated_at': now})
            conn.commit()
            return jsonify({'message': 'Company assigned successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/api/transactions/bulk-mark', methods=['POST'])
def bulk_mark_transactions():
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    try:
        data = request.json
        txn_ids = data.get('transaction_ids', [])
        mark_id = data.get('mark_id') or None
        
        if not txn_ids:
            return jsonify({'error': 'No transaction IDs provided'}), 400
            
        now = datetime.now()
        with engine.begin() as conn:
            txn_columns = _table_columns(conn, 'transactions')
            blocked_ids = []
            updatable_ids = list(txn_ids)

            # If applying a mark (not unmark), protect parent transactions with split children.
            if mark_id and 'parent_id' in txn_columns:
                blocked_query = text("""
                    SELECT t.id
                    FROM transactions t
                    WHERE t.id IN :ids
                      AND EXISTS (
                        SELECT 1
                        FROM transactions c
                        WHERE c.parent_id = t.id
                      )
                """).bindparams(bindparam('ids', expanding=True))
                blocked_rows = conn.execute(blocked_query, {'ids': updatable_ids}).fetchall()
                blocked_ids = [str(row.id) for row in blocked_rows]
                blocked_set = set(blocked_ids)
                updatable_ids = [txn_id for txn_id in updatable_ids if str(txn_id) not in blocked_set]

            if updatable_ids:
                update_query = text("""
                    UPDATE transactions
                    SET mark_id = :mark_id, updated_at = :updated_at
                    WHERE id IN :ids
                """).bindparams(bindparam('ids', expanding=True))
                conn.execute(update_query, {
                    'ids': updatable_ids,
                    'mark_id': mark_id,
                    'updated_at': now
                })

            return jsonify({
                'message': f'{len(updatable_ids)} transactions updated successfully',
                'updated_count': len(updatable_ids),
                'skipped_split_parent_ids': blocked_ids
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/api/transactions/bulk-assign-company', methods=['POST'])
def bulk_assign_company_transactions():
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    try:
        data = request.json
        txn_ids = data.get('transaction_ids', [])
        company_id = data.get('company_id') or None
        
        if not txn_ids:
            return jsonify({'error': 'No transaction IDs provided'}), 400
            
        now = datetime.now()
        with engine.connect() as conn:
            query = text("UPDATE transactions SET company_id = :company_id, updated_at = :updated_at WHERE id IN :ids")
            conn.execute(query, {'ids': txn_ids, 'company_id': company_id, 'updated_at': now})
            conn.commit()
            return jsonify({'message': f'{len(txn_ids)} transactions updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/api/transactions/<txn_id>', methods=['DELETE'])
def delete_transaction(txn_id):
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    try:
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM transactions WHERE id = :id"), {'id': txn_id})
            conn.commit()
            return jsonify({'message': 'Transaction deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/api/transactions/bulk-delete', methods=['POST'])
def bulk_delete_transactions():
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    try:
        data = request.json
        txn_ids = data.get('transaction_ids', [])
        if not txn_ids:
            return jsonify({'error': 'No transaction IDs provided'}), 400
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM transactions WHERE id IN :ids"), {'ids': txn_ids})
            conn.commit()
            return jsonify({'message': f'{len(txn_ids)} transactions deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/api/transactions/<transaction_id>/notes', methods=['PUT'])
def update_transaction_notes(transaction_id):
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    try:
        data = request.json
        notes = data.get('notes')
        with engine.connect() as conn:
            query = text("UPDATE transactions SET notes = :notes, updated_at = :now WHERE id = :id")
            conn.execute(query, {'id': transaction_id, 'notes': notes, 'now': datetime.now()})
            conn.commit()
            return jsonify({'message': 'Notes updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Marking - COA Mappings
@transaction_bp.route('/api/marks/<mark_id>/coa-mappings', methods=['GET'])
def get_mark_coa_mappings(mark_id):
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    try:
        requested_report_type = _normalize_mapping_report_type(
            request.args.get('report_type'),
            allow_all=True
        )
        with engine.connect() as conn:
            mapping_columns = _table_columns(conn, 'mark_coa_mapping')
            report_type_select_sql = "'real' AS report_type"
            report_type_filter_sql = ""
            params = {'mark_id': mark_id}

            if 'report_type' in mapping_columns:
                if conn.dialect.name == 'sqlite':
                    report_type_expr = "LOWER(COALESCE(CAST(mcm.report_type AS TEXT), 'real'))"
                else:
                    report_type_expr = "LOWER(COALESCE(CAST(mcm.report_type AS CHAR), 'real'))"
                report_type_select_sql = f"{report_type_expr} AS report_type"
                if requested_report_type != 'all':
                    report_type_filter_sql = f"AND {report_type_expr} = :report_type"
                    params['report_type'] = requested_report_type

            result = conn.execute(text(f"""
                SELECT mcm.*, {report_type_select_sql}, coa.code, coa.name, coa.category
                FROM mark_coa_mapping mcm
                INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
                WHERE mcm.mark_id = :mark_id
                {report_type_filter_sql}
                ORDER BY coa.code
            """), params)
            
            mappings = []
            for row in result:
                d = dict(row._mapping)
                for key, value in d.items():
                    if isinstance(value, datetime):
                        d[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                mappings.append(d)
            return jsonify({'mappings': mappings})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/api/marks/<mark_id>/coa-mappings', methods=['POST'])
def create_mark_coa_mapping(mark_id):
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    try:
        data = request.json or {}
        coa_id = data.get('coa_id')
        mapping_type = data.get('mapping_type', 'DEBIT')
        report_type = _normalize_mapping_report_type(data.get('report_type'))
        
        if not coa_id:
            return jsonify({'error': 'COA ID is required'}), 400
        
        if mapping_type not in ['DEBIT', 'CREDIT']:
            return jsonify({'error': 'Invalid mapping type'}), 400
        
        mapping_id = str(uuid.uuid4())
        now = datetime.now()
        
        with engine.connect() as conn:
            mapping_columns = _table_columns(conn, 'mark_coa_mapping')
            mapping_payload = {
                'id': mapping_id,
                'mark_id': mark_id,
                'coa_id': coa_id,
                'mapping_type': mapping_type,
                'notes': data.get('notes'),
                'created_at': now,
                'updated_at': now,
                'report_type': report_type
            }
            insert_columns = [column for column in mapping_payload.keys() if column in mapping_columns]
            columns_sql = ', '.join(insert_columns)
            values_sql = ', '.join(f":{column}" for column in insert_columns)
            conn.execute(text(f"""
                INSERT INTO mark_coa_mapping ({columns_sql})
                VALUES ({values_sql})
            """), mapping_payload)
            conn.commit()
            return jsonify({
                'message': 'Mapping created successfully',
                'id': mapping_id,
                'report_type': report_type
            }), 201
    except Exception as e:
        if 'Duplicate entry' in str(e):
            return jsonify({'error': 'This mapping already exists'}), 409
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/api/mark-coa-mappings/<mapping_id>', methods=['DELETE'])
def delete_mark_coa_mapping(mapping_id):
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    try:
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM mark_coa_mapping WHERE id = :id"), {'id': mapping_id})
            conn.commit()
            return jsonify({'message': 'Mapping deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/api/transactions/<txn_id>/splits', methods=['GET'])
def get_transaction_splits(txn_id):
    """Get splits for a specific transaction"""
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    try:
        with engine.connect() as conn:
            # Get main transaction
            main_query = text("""
                SELECT id, description, amount, db_cr, txn_date, mark_id, company_id, notes
                FROM transactions 
                WHERE id = :txn_id
            """)
            main_result = conn.execute(main_query, {'txn_id': txn_id}).fetchone()
            
            if not main_result:
                return jsonify({'error': 'Transaction not found'}), 404
            
            # Get split transactions
            splits_query = text("""
                SELECT id, description, amount, db_cr, txn_date, mark_id, notes
                FROM transactions 
                WHERE parent_id = :txn_id
                ORDER BY txn_date
            """)
            splits_result = conn.execute(splits_query, {'txn_id': txn_id}).fetchall()
            
            main_transaction = dict(main_result._mapping)
            split_transactions = [dict(row._mapping) for row in splits_result]
            
            # Format amounts
            if main_transaction.get('amount'):
                main_transaction['amount'] = float(main_transaction['amount'])
            for split in split_transactions:
                if split.get('amount'):
                    split['amount'] = float(split['amount'])
            
            return jsonify({
                'main_transaction': main_transaction,
                'splits': split_transactions,
                'total_split_amount': sum(split.get('amount', 0) for split in split_transactions)
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/api/transactions/<txn_id>/splits', methods=['POST'])
def save_transaction_splits(txn_id):
    """Save splits for a specific transaction"""
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    try:
        data = request.json or {}
        splits = data.get('splits', [])

        with engine.begin() as conn:
            txn_columns = _table_columns(conn, 'transactions')
            if 'parent_id' not in txn_columns:
                return jsonify({'error': 'Split feature unavailable: transactions.parent_id column is missing'}), 400

            parent_result = conn.execute(text("""
                SELECT company_id, txn_date, mark_id, db_cr
                FROM transactions
                WHERE id = :txn_id
                LIMIT 1
            """), {'txn_id': txn_id}).fetchone()
            if not parent_result:
                return jsonify({'error': 'Transaction not found'}), 404

            parent_data = dict(parent_result._mapping)

            # Remove previous split children.
            conn.execute(text("DELETE FROM transactions WHERE parent_id = :txn_id"), {'txn_id': txn_id})

            # IMPORTANT: when multi-mark (splits) is used, parent single mark must be ignored.
            # We clear parent mark to prevent double counting in reports.
            if len(splits) > 0 and 'mark_id' in txn_columns:
                if 'updated_at' in txn_columns:
                    conn.execute(text("""
                        UPDATE transactions
                        SET mark_id = NULL, updated_at = :updated_at
                        WHERE id = :txn_id
                    """), {'txn_id': txn_id, 'updated_at': datetime.now()})
                else:
                    conn.execute(text("""
                        UPDATE transactions
                        SET mark_id = NULL
                        WHERE id = :txn_id
                    """), {'txn_id': txn_id})

            insert_sql = text("""
                INSERT INTO transactions (
                    id, parent_id, description, amount, db_cr, txn_date,
                    mark_id, notes, company_id, created_at, updated_at
                ) VALUES (
                    :id, :parent_id, :description, :amount, :db_cr, :txn_date,
                    :mark_id, :notes, :company_id, :created_at, :updated_at
                )
            """)

            now = datetime.now()
            for split in splits:
                conn.execute(insert_sql, {
                    'id': str(uuid.uuid4()),
                    'parent_id': txn_id,
                    'description': split.get('description', ''),
                    'amount': split.get('amount', 0),
                    # Keep DB/CR consistent with parent unless explicitly provided.
                    'db_cr': _normalize_db_cr(split.get('db_cr') or parent_data.get('db_cr') or 'DB'),
                    'txn_date': parent_data.get('txn_date'),
                    'mark_id': split.get('mark_id'),
                    'notes': split.get('notes', ''),
                    'company_id': parent_data.get('company_id'),
                    'created_at': now,
                    'updated_at': now
                })

            return jsonify({'message': 'Splits saved successfully', 'splits_count': len(splits)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
