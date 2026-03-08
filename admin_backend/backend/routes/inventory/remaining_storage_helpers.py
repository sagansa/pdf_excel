from backend.routes.accounting_utils import normalize_iso_date_value
from backend.routes.route_utils import _normalize_iso_date, _safe_int, _to_float


def extract_remaining_storage_rows(payload):
    if isinstance(payload, list):
        return payload, {}

    if not isinstance(payload, dict):
        return [], {}

    container = payload.get('data', payload)
    if isinstance(container, list):
        return container, {}

    if not isinstance(container, dict):
        return [], {}

    rows = container.get('data')
    if not isinstance(rows, list):
        rows = container.get('items') if isinstance(container.get('items'), list) else []

    meta = {
        'current_page': _safe_int(container.get('current_page'), 1),
        'per_page': _safe_int(container.get('per_page'), len(rows) or 15),
        'total': _safe_int(container.get('total'), len(rows)),
        'last_page': _safe_int(container.get('last_page'), 1)
    }
    return rows, meta


def normalize_detail_stock_card_item(item):
    if not isinstance(item, dict):
        return None
    quantity_value = _to_float(item.get('quantity'), 0.0)
    return {
        'id': item.get('id'),
        'product_id': item.get('product_id'),
        'product_name': item.get('product_name') or item.get('product') or item.get('name'),
        'unit_id': item.get('unit_id'),
        'unit_name': item.get('unit_name') or item.get('unit'),
        'quantity': quantity_value
    }


def normalize_stock_card_for(value):
    raw = str(value or '').strip().lower().replace('_', ' ').replace('-', ' ')
    while '  ' in raw:
        raw = raw.replace('  ', ' ')
    return raw


def normalize_remaining_storage_row(item):
    if not isinstance(item, dict):
        return {
            'id': None,
            'date': None,
            'store_name': None,
            'user_name': None,
            'description': '',
            'detail_count': 0,
            'total_quantity': 0.0
        }

    detail_rows = item.get('detailStockCards')
    if not isinstance(detail_rows, list):
        detail_rows = item.get('detail_stock_cards') if isinstance(item.get('detail_stock_cards'), list) else []
    if not isinstance(detail_rows, list):
        detail_rows = item.get('details') if isinstance(item.get('details'), list) else []

    total_quantity = 0.0
    normalized_details = []
    for detail in detail_rows:
        if isinstance(detail, dict):
            quantity_value = _to_float(detail.get('quantity'), 0.0)
            total_quantity += quantity_value
            product_data = detail.get('product') if isinstance(detail.get('product'), dict) else {}
            unit_data = detail.get('unit') if isinstance(detail.get('unit'), dict) else {}
            normalized_details.append({
                'id': detail.get('id'),
                'product_id': detail.get('product_id'),
                'product_name': detail.get('product_name') or product_data.get('name') or product_data.get('product_name'),
                'unit_id': detail.get('unit_id'),
                'unit_name': detail.get('unit_name') or unit_data.get('name') or unit_data.get('unit_name'),
                'quantity': quantity_value
            })

    store_data = item.get('store') if isinstance(item.get('store'), dict) else {}
    user_data = item.get('user') if isinstance(item.get('user'), dict) else {}

    return {
        'id': item.get('id'),
        'for': item.get('for') or item.get('stock_card_for'),
        'date': item.get('date') or _normalize_iso_date(item.get('created_at')),
        'store_id': item.get('store_id'),
        'store_name': (
            item.get('store_name')
            or item.get('store_nickname')
            or store_data.get('nickname')
            or store_data.get('store_name')
            or store_data.get('name')
        ),
        'user_id': item.get('user_id'),
        'user_name': item.get('user_name') or user_data.get('name') or user_data.get('username'),
        'description': item.get('description') or '',
        'detail_count': len(detail_rows),
        'total_quantity': total_quantity,
        'details': normalized_details
    }


def remaining_storage_sort_key(row):
    date_value = str(row.get('date') or '')
    return (date_value, _safe_int(row.get('id'), 0))


def extract_remaining_storage_detail_item(payload):
    if isinstance(payload, dict):
        data = payload.get('data', payload)
        if isinstance(data, dict):
            return data
    return {}


def extract_detail_stock_card_rows(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        rows = payload.get('data')
        if isinstance(rows, list):
            return rows
        if isinstance(rows, dict) and isinstance(rows.get('data'), list):
            return rows.get('data')
    return []


def derive_api_root_from_remaining_storage_url(api_url):
    base_url = str(api_url or '').strip()
    if not base_url:
        return ''
    return base_url.split('/remaining-storages')[0].rstrip('/')


def build_remaining_storage_store_options(rows):
    options_map = {}
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        store_name = str(row.get('store_name') or '').strip()
        if not store_name:
            continue
        store_id = str(row.get('store_id') or '').strip() or None
        key = store_id or store_name.lower()
        if key in options_map:
            continue
        options_map[key] = {
            'store_id': store_id,
            'store_name': store_name
        }
    return sorted(options_map.values(), key=lambda item: str(item.get('store_name') or '').lower())


def to_iso_date(value):
    return normalize_iso_date_value(value, allow_raw_fallback=True)
