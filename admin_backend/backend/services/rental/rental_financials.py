import datetime
import json
from decimal import Decimal

DEFAULT_TAX_RATE = 10.0
VALID_CALCULATION_METHODS = {'BRUTO', 'NETTO'}
VALID_PPH42_TIMINGS = {'same_period', 'next_period', 'next_year'}
RENT_CFG_PREFIX = '[RENT_CFG]'


def to_float(value, default=0.0):
    if value is None:
        return default
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_calculation_method(value):
    method = str(value or 'BRUTO').strip().upper()
    if method not in VALID_CALCULATION_METHODS:
        return 'BRUTO'
    return method


def normalize_pph42_timing(value):
    raw = str(value or 'same_period').strip().lower()
    alias_map = {
        'same_month': 'same_period',
        'same_year': 'same_period',
        'next_month': 'next_period',
    }
    normalized = alias_map.get(raw, raw)
    if normalized not in VALID_PPH42_TIMINGS:
        return 'same_period'
    return normalized


def parse_date(value):
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        try:
            return datetime.date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def extract_cfg_from_notes(notes_value):
    text_value = str(notes_value or '')
    if RENT_CFG_PREFIX not in text_value:
        return {}
    _, _, tail = text_value.partition(RENT_CFG_PREFIX)
    try:
        cfg = json.loads(tail.strip())
        if isinstance(cfg, dict):
            return cfg
    except Exception:
        pass
    return {}


def month_span(start_date, end_date):
    if not start_date or not end_date or end_date < start_date:
        return 1
    months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month) + 1
    return max(1, months)


def calculate_rent_components(base_amount, calculation_method, tax_rate):
    safe_tax_rate = max(0.0, min(to_float(tax_rate, DEFAULT_TAX_RATE), 100.0))
    base = max(0.0, to_float(base_amount, 0.0))

    if calculation_method == 'NETTO':
        divisor = max(0.000001, 1.0 - (safe_tax_rate / 100.0))
        amount_net = base
        amount_bruto = amount_net / divisor
    else:
        amount_bruto = base
        amount_net = amount_bruto * (1.0 - (safe_tax_rate / 100.0))

    amount_tax = max(0.0, amount_bruto - amount_net)

    return {
        'amount_bruto': amount_bruto,
        'amount_net': amount_net,
        'amount_tax': amount_tax,
        'tax_rate': safe_tax_rate,
    }


def build_amortization_schedule(start_date, duration_months, monthly_amount):
    schedule = []
    if not start_date:
        return schedule

    current_year = start_date.year
    current_month = start_date.month

    for month_index in range(duration_months):
        year = current_year + ((current_month - 1 + month_index) // 12)
        month = ((current_month - 1 + month_index) % 12) + 1
        schedule.append({
            'year': year,
            'month': month,
            'amount': round(monthly_amount, 2),
        })

    return schedule
