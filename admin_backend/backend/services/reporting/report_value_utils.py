import re
from datetime import date, datetime

RENT_EXPENSE_CODES = {'5315', '5105'}


def _parse_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {'1', 'true', 'yes', 'y'}
    return False


def _parse_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value[:10], '%Y-%m-%d').date()
        except ValueError:
            return None
    return None


def _to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_text(value):
    return re.sub(r'[^a-z0-9]+', '', str(value or '').strip().lower())


def _is_cogs_expense_item(item):
    code = str((item or {}).get('code') or '').strip()
    subcategory = _normalize_text((item or {}).get('subcategory'))

    cogs_subcategories = {
        'cogs',
        'costofgoodssold',
        'costofgoodsold',
        'hargapokokpenjualan',
        'bebanpokokpenjualan',
    }

    if subcategory in cogs_subcategories:
        return True
    if 'costofgoods' in subcategory or 'hargapokok' in subcategory:
        return True
    if code.startswith('50'):
        return True
    return False


def _is_current_asset(subcategory, code):
    normalized_subcategory = _normalize_text(subcategory)
    code = str(code or '').strip()

    if 'noncurrent' in normalized_subcategory:
        return False
    if normalized_subcategory in {
        'currentasset',
        'currentassets',
        'assetlancar',
        'asetlancar',
        'cashandcashequivalents',
        'accountsreceivable',
        'inventory',
        'inventories',
        'prepaidexpenses',
        'othercurrentassets',
    }:
        return True
    if 'currentasset' in normalized_subcategory or normalized_subcategory.endswith('currentassets'):
        return True

    if code.startswith(('11', '12', '13', '14')):
        return True
    if code.startswith(('15', '16', '17', '18', '19')):
        return False
    return False
