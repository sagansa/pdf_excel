import json

from backend.routes.accounting_utils import require_db_engine, serialize_db_value, serialize_row_values

RENT_CFG_PREFIX = '[RENT_CFG]'


def serialize_value(value):
    return serialize_db_value(value, datetime_format='%Y-%m-%dT%H:%M:%S')


def serialize_row(row):
    return serialize_row_values(row._mapping, datetime_format='%Y-%m-%dT%H:%M:%S')


def normalize_ids(values):
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def split_notes_and_cfg(notes_value):
    text_value = str(notes_value or '')
    if RENT_CFG_PREFIX not in text_value:
        return text_value.strip(), {}

    base, _, tail = text_value.partition(RENT_CFG_PREFIX)
    cfg = {}
    try:
        cfg = json.loads(tail.strip())
        if not isinstance(cfg, dict):
            cfg = {}
    except Exception:
        cfg = {}
    return base.strip(), cfg


def merge_notes_with_cfg(base_notes, cfg):
    cleaned_notes, _ = split_notes_and_cfg(base_notes)
    normalized_cfg = {
        'calculation_method': str(cfg.get('calculation_method') or 'BRUTO').upper(),
        'pph42_rate': float(cfg.get('pph42_rate') or 10),
        'pph42_payment_timing': str(cfg.get('pph42_payment_timing') or 'same_period'),
        'pph42_payment_date': cfg.get('pph42_payment_date'),
        'pph42_payment_ref': cfg.get('pph42_payment_ref'),
    }
    cfg_blob = f"{RENT_CFG_PREFIX}{json.dumps(normalized_cfg, separators=(',', ':'))}"
    return f"{cleaned_notes}\n{cfg_blob}".strip() if cleaned_notes else cfg_blob
