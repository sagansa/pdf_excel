"""Deteksi e-statement bulanan yang belum masuk (sumber alert pipeline).

Semantik: untuk setiap akun bank di bank_account_definitions yang aktif pada
bulan lalu, statement bulan lalu dianggap "ada" jika tabel transactions punya
minimal satu baris dengan txn_date di bulan itu. Akun yang didefinisikan tapi
belum pernah punya transaksi apa pun dilewati supaya tidak berisik. Alert hanya
relevan setelah grace period (default tanggal >= 5) — bank butuh beberapa hari
awal bulan untuk mengirim e-statement.
"""

import datetime
import logging

from sqlalchemy import text

logger = logging.getLogger(__name__)

DEFAULT_GRACE_DAYS = 5


def _previous_month(today):
    """Bulan sebelumnya sebagai (year, month)."""
    first_of_current = today.replace(day=1)
    last_of_previous = first_of_current - datetime.timedelta(days=1)
    return last_of_previous.year, last_of_previous.month


def _month_bounds(year, month):
    """(awal, akhir) ISO dari bulan berikutnya untuk pembandingan string tanggal."""
    start = datetime.date(year, month, 1)
    if month == 12:
        nxt = datetime.date(year + 1, 1, 1)
    else:
        nxt = datetime.date(year, month + 1, 1)
    return start.isoformat(), nxt.isoformat()


def find_missing_statements(engine, today=None, grace_days=DEFAULT_GRACE_DAYS):
    """Daftar statement bulan lalu yang belum masuk.

    Return list of dict: bank_code, account_number, display_name, month ('YYYY-MM'),
    last_seen (txn_date terakhir akun tsb, bisa None). Tanpa tabel
    bank_account_definitions → list kosong (tidak ada sumber ekspektasi).
    """
    today = today or datetime.date.today()
    if today.day < grace_days:
        return []

    prev_year, prev_month = _previous_month(today)
    month_start, month_end = _month_bounds(prev_year, prev_month)
    month_label = f'{prev_year:04d}-{prev_month:02d}'

    try:
        with engine.connect() as conn:
            definitions = conn.execute(text(
                'SELECT bank_code, account_number, display_name, active_from, active_until '
                'FROM bank_account_definitions'
            )).fetchall()
    except Exception:
        # Tabel definisi belum ada — tidak ada ekspektasi yang bisa dihitung.
        logger.info('Tabel bank_account_definitions tidak tersedia — statement check dilewati')
        return []

    missing = []
    for definition in definitions:
        bank_code = str(definition.bank_code or '').strip()
        account_number = str(definition.account_number or '').strip()
        if not bank_code or not account_number:
            continue

        # Definisi harus aktif pada bulan yang diperiksa (string ISO bisa
        # dibandingkan langsung; NULL = terbuka).
        active_from = str(definition.active_from or '').strip() or None
        active_until = str(definition.active_until or '').strip() or None
        if active_from and active_from >= month_end:
            continue
        if active_until and active_until < month_start:
            continue

        with engine.connect() as conn:
            month_count = conn.execute(text(
                'SELECT COUNT(1) FROM transactions '
                'WHERE bank_code = :bank AND bank_account_number = :acc '
                'AND txn_date >= :start AND txn_date < :end'
            ), {
                'bank': bank_code, 'acc': account_number,
                'start': month_start, 'end': month_end,
            }).scalar_one()

            if month_count > 0:
                continue

            # Akun belum pernah dipakai sama sekali → tidak berisik.
            last_seen_row = conn.execute(text(
                'SELECT MAX(txn_date) FROM transactions '
                'WHERE bank_code = :bank AND bank_account_number = :acc'
            ), {'bank': bank_code, 'acc': account_number}).scalar_one()
            if last_seen_row is None:
                continue

        missing.append({
            'bank_code': bank_code,
            'account_number': account_number,
            'display_name': str(definition.display_name or '').strip(),
            'month': month_label,
            'last_seen': str(last_seen_row),
        })

    return missing
