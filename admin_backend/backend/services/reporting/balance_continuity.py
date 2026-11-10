"""Cek kontinuitas saldo bank antar-transaksi & antar-statement (Fase 2).

Per akun bank (bank_code + account_number):
- Baris transaksi diurutkan kronologis; saldo berjalan yang tersimpan harus
  cocok dengan rekomputasi dari saldo terakhir yang diketahui:
  expected = prev ± amount (DB = uang masuk, CR = uang keluar — konvensi
  internal esta, lihat normalize_bank_db_cr).
- Rentang tanggal per source_file dibandingkan dengan statement berikutnya:
  celah > 1 hari antar periode statement = indikasi statement bolong.

Semua dihitung on-the-fly (tanpa kolom flag di DB); import tidak pernah
diblok — hasilnya alat diagnosis.
"""

import logging
from collections import defaultdict

from sqlalchemy import text

logger = logging.getLogger(__name__)

TOLERANCE = 0.01


def _parse_float(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_date_str(value):
    return str(value or '')[:10]


def check_balance_continuity(engine, tolerance=TOLERANCE):
    """Analisis seluruh akun bank yang punya transaksi.

    Return {'accounts': [...]} — satu entri per akun dengan ringkasan dan
    daftar break (balance_mismatch / statement_gap).
    """
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id, txn_date, description, amount, db_cr, bank_code,
                   bank_account_number, source_file, running_balance
            FROM transactions
            WHERE bank_code IS NOT NULL AND UPPER(TRIM(bank_code)) != 'MANUAL'
            ORDER BY bank_code, bank_account_number, txn_date, id
        """)).fetchall()

    grouped = defaultdict(list)
    for row in rows:
        account_number = str(row.bank_account_number or '').strip() or '(tanpa nomor)'
        grouped[(str(row.bank_code).strip(), account_number)].append(row)

    accounts = []
    for (bank_code, account_number), txns in sorted(grouped.items()):
        accounts.append(_check_account(bank_code, account_number, txns, tolerance))

    return {'accounts': accounts}


def _check_account(bank_code, account_number, txns, tolerance):
    breaks = []
    expected = None  # saldo yang diharapkan dari rantai; None = belum ada baseline
    verified_count = 0
    has_running_balance = any(t.running_balance is not None for t in txns)

    for txn in txns:
        actual = _parse_float(txn.running_balance)
        amount = _parse_float(txn.amount) or 0.0
        db_cr = str(txn.db_cr or '').strip().upper()
        signed_amount = amount if db_cr in {'DB', 'DEBIT', 'D', 'DE'} else -amount

        # Setiap transaksi menggeser rantai — termasuk yang saldo cell-nya
        # kosong; yang kosong cuma tidak bisa DIVERIFIKASI.
        if expected is not None:
            expected += signed_amount

        if actual is not None:
            if expected is not None and abs(expected - actual) > tolerance:
                breaks.append({
                    'type': 'balance_mismatch',
                    'txn_id': str(txn.id),
                    'txn_date': _parse_date_str(txn.txn_date),
                    'description': str(txn.description or '')[:120],
                    'source_file': str(txn.source_file or ''),
                    'expected': round(expected, 2),
                    'actual': actual,
                    'diff': round(actual - expected, 2),
                })
                verified_count += 1
            elif expected is not None:
                verified_count += 1
            # Resinkron ke kenyataan supaya satu statement bolong tidak
            # memicu kaskade break di semua baris berikutnya.
            expected = actual

    breaks.extend(_statement_gaps(txns))

    return {
        'bank_code': bank_code,
        'account_number': account_number,
        'transaction_count': len(txns),
        'first_date': _parse_date_str(txns[0].txn_date) if txns else None,
        'last_date': _parse_date_str(txns[-1].txn_date) if txns else None,
        'has_running_balance': has_running_balance,
        'verified_count': verified_count,
        'breaks': breaks,
    }


def _statement_gaps(txns):
    """Celah tanggal > 1 hari antara akhir satu statement dan awal berikutnya."""
    import datetime

    ranges = {}
    for txn in txns:
        source = str(txn.source_file or '').strip()
        date_str = _parse_date_str(txn.txn_date)
        if not source or not date_str:
            continue
        current = ranges.get(source)
        if current is None:
            ranges[source] = [date_str, date_str]
        else:
            current[0] = min(current[0], date_str)
            current[1] = max(current[1], date_str)

    ordered = sorted(ranges.items(), key=lambda item: item[1][0])

    gaps = []
    for (prev_source, prev_range), (next_source, next_range) in zip(ordered, ordered[1:]):
        try:
            prev_end = datetime.date.fromisoformat(prev_range[1])
            next_start = datetime.date.fromisoformat(next_range[0])
        except ValueError:
            continue
        gap_days = (next_start - prev_end).days
        if gap_days > 1:
            gap_from = prev_end + datetime.timedelta(days=1)
            gap_to = next_start - datetime.timedelta(days=1)
            gaps.append({
                'type': 'statement_gap',
                'gap_from': gap_from.isoformat(),
                'gap_to': gap_to.isoformat(),
                'gap_days': gap_days - 1,
                'previous_file': prev_source,
                'next_file': next_source,
            })
    return gaps
