from backend.routes.accounting_utils import (
    require_db_engine,
)
from backend.routes.route_utils import _to_float

def normalize_product_payload(item):
    return {
        'product_id': item.get('product_id'),
        'quantity': _to_float(item.get('quantity')),
        'foreign_currency': item.get('foreign_currency') or 'USD',
        'foreign_price': _to_float(item.get('foreign_price')),
    }
