"""Test unit transaction_utils: persist running_balance & currency (Fase 2)."""

import pandas as pd

from backend.services.transactions.transaction_utils import build_transaction_record


def _row(**overrides):
    base = {
        'txn_date': '2026-10-05',
        'description': 'TRF DB',
        'amount': 1250000,
        'db_cr': 'DB',
        'bank_account_number': '1234567890',
    }
    base.update(overrides)
    return base


def test_running_balance_dari_kolom_balance():
    record = build_transaction_record(
        _row(balance='9250000.00', currency='IDR'),
        'BRI', 'bri.csv', 'hash-1',
    )
    assert record['running_balance'] == 9250000.0
    assert record['currency'] == 'IDR'


def test_running_balance_tanpa_kolom_jadi_none():
    record = build_transaction_record(_row(), 'BRI', 'bri.csv', 'hash-1')
    assert record['running_balance'] is None
    assert record['currency'] is None


def test_running_balance_dari_dataframe_row():
    """row asli dari df.iterrows() adalah pandas Series — harus tetap kebaca."""
    df = pd.DataFrame([_row(balance=9000000.0)])
    record = build_transaction_record(df.iloc[0], 'BRI', 'bri.csv', 'hash-1')
    assert record['running_balance'] == 9000000.0


def test_email_meta_tetap_ada_dengan_balance():
    record = build_transaction_record(
        _row(balance='100.00'),
        'BRI', 'bri.csv', 'hash-1',
        email_meta={'email_message_id': '<x@y>', 'email_from': 'bank@x.com'},
    )
    assert record['email_message_id'] == '<x@y>'
    assert record['email_from'] == 'bank@x.com'
    assert record['running_balance'] == 100.0
