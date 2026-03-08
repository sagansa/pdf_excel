from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import text

from backend.db.schema import get_table_columns
from backend.db.session import get_db_engine
from backend.errors import ApiError


def require_db_engine():
    engine, error_msg = get_db_engine()
    if engine is None:
        raise ApiError(error_msg or 'Database connection failed', status_code=500, code='db_unavailable')
    return engine


def current_timestamp_expression(conn):
    return "CURRENT_TIMESTAMP" if conn.dialect.name == 'sqlite' else "NOW()"


def split_parent_exclusion_clause(conn, alias='t'):
    txn_columns = get_table_columns(conn, 'transactions')
    if 'parent_id' not in txn_columns:
        return ''
    return f" AND NOT EXISTS (SELECT 1 FROM transactions t_child WHERE t_child.parent_id = {alias}.id)"


def to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def serialize_db_value(value, datetime_format='%Y-%m-%d %H:%M:%S'):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.strftime(datetime_format)
    if isinstance(value, date):
        return value.isoformat()
    return value


def serialize_row_values(row_dict, datetime_format='%Y-%m-%d %H:%M:%S', field_datetime_formats=None):
    field_datetime_formats = field_datetime_formats or {}
    return {
        key: serialize_db_value(
            value,
            datetime_format=field_datetime_formats.get(key, datetime_format),
        )
        for key, value in dict(row_dict).items()
    }


def serialize_result_rows(rows, datetime_format='%Y-%m-%d %H:%M:%S', field_datetime_formats=None):
    return [
        serialize_row_values(
            row._mapping,
            datetime_format=datetime_format,
            field_datetime_formats=field_datetime_formats,
        )
        for row in rows
    ]


def normalize_iso_date_value(value, allow_raw_fallback=False):
    if value in (None, ''):
        return None
    if isinstance(value, datetime):
        return serialize_db_value(value, datetime_format='%Y-%m-%d')
    if isinstance(value, date):
        return serialize_db_value(value)
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        try:
            return datetime.strptime(raw[:10], '%Y-%m-%d').date().isoformat()
        except ValueError:
            return raw[:10] if allow_raw_fallback else None
    return str(value)[:10] if allow_raw_fallback else None


def fetch_inventory_balance_row(conn, year, company_id):
    result = conn.execute(text("""
        SELECT *
        FROM inventory_balances
        WHERE year = :year AND company_id = :company_id
        ORDER BY updated_at DESC, created_at DESC
        LIMIT 1
    """), {
        'year': int(year),
        'company_id': company_id
    })
    row = result.fetchone()
    return serialize_row_values(row._mapping) if row else None


def serialize_inventory_balance(row_dict):
    if not row_dict:
        return {}
    return serialize_row_values(row_dict)


def build_inventory_balance_with_carry(conn, year, company_id):
    year = int(year)
    current = serialize_inventory_balance(fetch_inventory_balance_row(conn, year, company_id))
    previous = serialize_inventory_balance(fetch_inventory_balance_row(conn, year - 1, company_id))

    prev_ending_amount = to_float(previous.get('ending_inventory_amount')) if previous else 0.0
    prev_ending_qty = to_float(previous.get('ending_inventory_qty')) if previous else 0.0

    if not current:
        if abs(prev_ending_amount) < 0.000001 and abs(prev_ending_qty) < 0.000001:
            return {}
        return {
            'id': None,
            'company_id': company_id,
            'year': year,
            'beginning_inventory_amount': prev_ending_amount,
            'beginning_inventory_qty': prev_ending_qty,
            'ending_inventory_amount': 0.0,
            'ending_inventory_qty': 0.0,
            'base_value': prev_ending_amount,
            'is_manual': True,
            'is_carry_forward': True,
            'carried_from_year': year - 1
        }

    current_beginning_amount = to_float(current.get('beginning_inventory_amount'))
    current_beginning_qty = to_float(current.get('beginning_inventory_qty'))
    carry_allowed = (
        abs(current_beginning_amount) < 0.000001 and
        abs(current_beginning_qty) < 0.000001 and
        (abs(prev_ending_amount) >= 0.000001 or abs(prev_ending_qty) >= 0.000001)
    )

    if carry_allowed:
        current['beginning_inventory_amount'] = prev_ending_amount
        current['beginning_inventory_qty'] = prev_ending_qty
        current['is_carry_forward'] = True
        current['carried_from_year'] = year - 1
    else:
        current['is_carry_forward'] = False
        current['carried_from_year'] = None

    if 'is_manual' not in current:
        current['is_manual'] = True
    return current
