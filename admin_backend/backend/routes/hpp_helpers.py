from backend.routes.accounting_utils import (
    require_db_engine,
    serialize_db_value,
    serialize_result_rows,
    serialize_row_values,
)
from backend.routes.route_utils import _to_float


def serialize_value(value, date_format='%Y-%m-%d %H:%M:%S'):
    return serialize_db_value(value, datetime_format=date_format)


def serialize_row(row, date_format='%Y-%m-%d %H:%M:%S'):
    return serialize_row_values(row._mapping, datetime_format=date_format)


def serialize_rows(rows, date_format='%Y-%m-%d %H:%M:%S'):
    return serialize_result_rows(rows, datetime_format=date_format)


def normalize_product_payload(item):
    return {
        'product_id': item.get('product_id'),
        'quantity': _to_float(item.get('quantity')),
        'foreign_currency': item.get('foreign_currency') or 'USD',
        'foreign_price': _to_float(item.get('foreign_price')),
    }
