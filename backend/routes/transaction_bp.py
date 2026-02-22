import uuid
import os
import re
from flask import Blueprint, request, jsonify
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import text, bindparam
from backend.db.session import get_db_engine, get_sagansa_engine

transaction_bp = Blueprint('transaction_bp', __name__)
VALID_SERVICE_CALCULATION_METHODS = {'BRUTO', 'NETTO'}
VALID_SERVICE_TAX_PAYMENT_TIMINGS = {'same_period', 'next_period', 'next_year'}


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
                d['is_asset'] = _parse_bool(d.get('is_asset'))
                d['is_service'] = _parse_bool(d.get('is_service'))
                d['is_salary_component'] = _parse_bool(d.get('is_salary_component'))
                d['mappings'] = []
                marks.append(d)
                marks_dict[d['id']] = d

            mapping_query = text("""
                SELECT mcm.mark_id, mcm.mapping_type, coa.code, coa.name
                FROM mark_coa_mapping mcm
                JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
            """)
            mapping_result = conn.execute(mapping_query)
            
            for row in mapping_result:
                m = dict(row._mapping)
                mark_id = m['mark_id']
                if mark_id in marks_dict:
                    marks_dict[mark_id]['mappings'].append({
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
            new_row = {
                'id': mark_id,
                'internal_report': data.get('internal_report', ''),
                'personal_use': data.get('personal_use', ''),
                'tax_report': data.get('tax_report', ''),
                'is_asset': _parse_bool(data.get('is_asset', False)),
                'is_service': _parse_bool(data.get('is_service', False)),
                'is_salary_component': _parse_bool(data.get('is_salary_component', False)),
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

            field_map = {
                'internal_report': 'internal_report',
                'personal_use': 'personal_use',
                'tax_report': 'tax_report',
                'is_asset': 'is_asset',
                'is_service': 'is_service',
                'is_salary_component': 'is_salary_component'
            }

            params = {'id': mark_id, 'updated_at': datetime.now()}
            set_fields = []

            for payload_key, column_name in field_map.items():
                if payload_key in data and column_name in mark_columns:
                    if payload_key in {'is_asset', 'is_service', 'is_salary_component'}:
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
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT mcm.*, coa.code, coa.name, coa.category
                FROM mark_coa_mapping mcm
                INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
                WHERE mcm.mark_id = :mark_id
                ORDER BY coa.code
            """), {'mark_id': mark_id})
            
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
        data = request.json
        coa_id = data.get('coa_id')
        mapping_type = data.get('mapping_type', 'DEBIT')
        
        if not coa_id:
            return jsonify({'error': 'COA ID is required'}), 400
        
        if mapping_type not in ['DEBIT', 'CREDIT']:
            return jsonify({'error': 'Invalid mapping type'}), 400
        
        mapping_id = str(uuid.uuid4())
        now = datetime.now()
        
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO mark_coa_mapping 
                (id, mark_id, coa_id, mapping_type, notes, created_at, updated_at)
                VALUES (:id, :mark_id, :coa_id, :mapping_type, :notes, :created_at, :updated_at)
            """), {
                'id': mapping_id,
                'mark_id': mark_id,
                'coa_id': coa_id,
                'mapping_type': mapping_type,
                'notes': data.get('notes'),
                'created_at': now,
                'updated_at': now
            })
            conn.commit()
            return jsonify({'message': 'Mapping created successfully', 'id': mapping_id}), 201
    except Exception as e:
        if 'Duplicate entry' in str(e):
            return jsonify({'error': 'This mapping already exists'}), 409
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/api/mark-coa-mappings/fix-expense-mappings', methods=['POST'])
def fix_expense_mappings():
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    try:
        with engine.begin() as conn:
            query = text("""
                SELECT mcm.id, mcm.mark_id, mcm.coa_id, mcm.mapping_type, 
                       coa.code, coa.name, coa.category, m.personal_use
                FROM mark_coa_mapping mcm
                INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
                INNER JOIN marks m ON mcm.mark_id = m.id
                WHERE coa.category IN ('EXPENSE', 'COGS', 'OTHER_EXPENSE')
                  AND mcm.mapping_type = 'CREDIT'
            """)
            
            result = conn.execute(query)
            incorrect_mappings = list(result)
            
            if not incorrect_mappings:
                return jsonify({
                    'message': 'No incorrect mappings found',
                    'fixed_count': 0,
                    'mappings': []
                })
            
            update_query = text("""
                UPDATE mark_coa_mapping
                SET mapping_type = 'DEBIT'
                WHERE id = :mapping_id
            """)
            
            fixed_mappings = []
            for mapping in incorrect_mappings:
                conn.execute(update_query, {'mapping_id': mapping.id})
                fixed_mappings.append({
                    'id': mapping.id,
                    'mark': mapping.personal_use,
                    'coa_code': mapping.code,
                    'coa_name': mapping.name,
                    'old_type': 'CREDIT',
                    'new_type': 'DEBIT'
                })
            
            return jsonify({
                'message': f'Successfully fixed {len(fixed_mappings)} expense mappings',
                'fixed_count': len(fixed_mappings),
                'mappings': fixed_mappings
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transaction_bp.route('/api/mark-coa-mappings/fix-revenue-mappings', methods=['POST'])
def fix_revenue_mappings():
    engine, error_msg = get_db_engine()
    if engine is None:
        return jsonify({'error': error_msg}), 500
    
    try:
        with engine.begin() as conn:
            query = text("""
                SELECT mcm.id, mcm.mark_id, mcm.coa_id, mcm.mapping_type, 
                       coa.code, coa.name, coa.category, m.personal_use
                FROM mark_coa_mapping mcm
                INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
                INNER JOIN marks m ON mcm.mark_id = m.id
                WHERE coa.category IN ('REVENUE', 'OTHER_REVENUE')
                  AND mcm.mapping_type = 'DEBIT'
            """)
            
            result = conn.execute(query)
            incorrect_mappings = list(result)
            
            if not incorrect_mappings:
                return jsonify({
                    'message': 'No incorrect mappings found',
                    'fixed_count': 0,
                    'mappings': []
                })
            
            update_query = text("""
                UPDATE mark_coa_mapping
                SET mapping_type = 'CREDIT'
                WHERE id = :mapping_id
            """)
            
            fixed_mappings = []
            for mapping in incorrect_mappings:
                conn.execute(update_query, {'mapping_id': mapping.id})
                fixed_mappings.append({
                    'id': mapping.id,
                    'mark': mapping.personal_use,
                    'coa_code': mapping.code,
                    'coa_name': mapping.name,
                    'old_type': 'DEBIT',
                    'new_type': 'CREDIT'
                })
            
            return jsonify({
                'message': f'Successfully fixed {len(fixed_mappings)} revenue mappings',
                'fixed_count': len(fixed_mappings),
                'mappings': fixed_mappings
            })
    except Exception as e:
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
