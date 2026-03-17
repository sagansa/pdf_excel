import json
import os
import re
import uuid
from datetime import date, datetime

from sqlalchemy import text

from backend.db.schema import get_table_columns
from backend.db.session import get_sagansa_engine
from backend.routes.accounting_utils import serialize_db_value
from backend.routes.route_utils import _normalize_iso_date, _parse_bool, _safe_int


def _safe_identifier(value, fallback):
    raw = str(value or fallback).strip()
    if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', raw):
        return fallback
    return raw


def _get_sagansa_users(search=None):
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


def _normalize_month_start(value):
    if value in (None, ''):
        return None
    if isinstance(value, datetime):
        dt = value.date().replace(day=1)
        return serialize_db_value(dt)
    if isinstance(value, date):
        dt = value.replace(day=1)
        return serialize_db_value(dt)
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        for fmt in ('%Y-%m', '%Y-%m-%d'):
            try:
                dt = datetime.strptime(raw[:10], fmt).date().replace(day=1)
                return serialize_db_value(dt)
            except ValueError:
                continue
    return None


def _normalize_datetime_string(value):
    if value in (None, ''):
        return None
    if isinstance(value, datetime):
        return serialize_db_value(value)
    if isinstance(value, date):
        return serialize_db_value(datetime.combine(value, datetime.min.time()))

    raw = str(value).strip()
    if not raw:
        return None

    raw = raw.replace('T', ' ')
    if raw.endswith('Z'):
        raw = raw[:-1]

    try:
        parsed = datetime.fromisoformat(raw)
        return serialize_db_value(parsed)
    except ValueError:
        pass

    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d'):
        try:
            parsed = datetime.strptime(raw[:19], fmt)
            return serialize_db_value(parsed)
        except ValueError:
            continue
    return None


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

    existing_columns = get_table_columns(conn, 'payroll_presences')
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


def _split_parent_exclusion_clause(conn, alias='t'):
    """
    Generate SQL clause to exclude parent transactions when children have marks.

    This prevents double-counting when transactions are split:
    - Parent transaction is just a container (should be excluded from reports)
    - Child transactions have individual marks (should be included in reports)

    Args:
        conn: Database connection
        alias: Table alias for transactions table (default 't')

    Returns:
        SQL WHERE clause string (empty if parent_id column doesn't exist)
    """
    txn_columns = get_table_columns(conn, 'transactions')
    if 'parent_id' not in txn_columns:
        return ''
    # Exclude parent if it has children (children will be included individually)
    return f" AND NOT EXISTS (SELECT 1 FROM transactions t_child WHERE t_child.parent_id = {alias}.id)"


def _new_uuid():
    return str(uuid.uuid4())
