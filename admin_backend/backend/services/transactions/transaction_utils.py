import re
from datetime import datetime

import pandas as pd


def null_if_nan(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def normalize_company_id(value):
    raw = null_if_nan(value)
    if raw is None:
        return None

    candidate = str(raw).strip()
    if not candidate or candidate.lower() in {'none', 'null'}:
        return None

    match = re.search(
        r'([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})',
        candidate,
    )
    if match:
        return match.group(1)

    if len(candidate) != 36:
        return None
    return candidate


def normalize_db_cr(value, default='DB'):
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


def normalize_bank_db_cr(value, amount=None, default='DB'):
    """
    Convert raw bank statement DB/CR markers to the app's internal perspective:
      DB = Debit to cash/bank = money IN
      CR = Credit to cash/bank = money OUT

    Most bank statements use the opposite convention:
      CR = incoming funds, DB = outgoing funds
    """
    raw = str(value or '').strip().upper()
    if raw:
        if raw in {'CR', 'CREDIT', 'KREDIT', 'K'}:
            return 'DB'
        if raw in {'DB', 'DEBIT', 'D', 'DE'}:
            return 'CR'
        if raw.startswith('CR') or 'CREDIT' in raw or raw.startswith('K'):
            return 'DB'
        if raw.startswith('DB') or raw.startswith('DE') or 'DEBIT' in raw:
            return 'CR'

    parsed_amount = parse_amount(amount)
    if parsed_amount < 0:
        return 'CR'
    if parsed_amount > 0:
        return 'DB'
    return default


def parse_amount(value):
    raw = null_if_nan(value)
    if isinstance(raw, float):
        return raw
    if isinstance(raw, str):
        normalized = raw.replace(',', '').strip()
        if not normalized:
            return 0.0
        try:
            return float(normalized)
        except (TypeError, ValueError):
            return 0.0
    try:
        return float(raw or 0.0)
    except (TypeError, ValueError):
        return 0.0


def normalize_bank_account_number(value):
    raw = null_if_nan(value)
    if raw is None:
        return None

    candidate = str(raw).strip()
    if not candidate:
        return None

    return candidate[:100]


def build_transaction_record(row, bank_code, source_file, file_hash, now=None):
    now = now or datetime.now()
    txn_date = (
        null_if_nan(row.get('txn_date'))
        or null_if_nan(row.get('Transaction Date'))
        or null_if_nan(row.get('Tanggal'))
    )
    description = (
        null_if_nan(row.get('description'))
        or null_if_nan(row.get('Transaction Details'))
        or null_if_nan(row.get('Keterangan'))
    )
    amount = null_if_nan(row.get('amount')) or null_if_nan(row.get('Amount'))
    db_cr = null_if_nan(row.get('db_cr')) or null_if_nan(row.get('DB/CR')) or 'DB'
    created_at = null_if_nan(row.get('created_at')) or now

    return {
        'id': row.get('id') or None,
        'txn_date': txn_date,
        'description': str(description or '')[:1000],
        'amount': parse_amount(amount),
        'db_cr': normalize_bank_db_cr(db_cr, amount=amount),
        'bank_code': bank_code,
        'bank_account_number': (
            normalize_bank_account_number(row.get('bank_account_number'))
            or normalize_bank_account_number(row.get('account_number'))
            or normalize_bank_account_number(row.get('account_no'))
        ),
        'source_file': source_file,
        'file_hash': file_hash,
        'mark_id': None,
        'company_id': normalize_company_id(row.get('company_id')),
        'created_at': created_at,
        'updated_at': now,
    }
