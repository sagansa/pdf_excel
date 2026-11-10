"""Test cek kontinuitas saldo antar-statement per akun bank (Fase 2).

Konvensi db_cr internal esta: DB = uang masuk (+saldo), CR = uang keluar
(-saldo). Baris pertama suatu akun dipakai sebagai baseline (tidak
diverifikasi); baris berikutnya harus memenuhi
running_balance(n) = running_balance(n-1) ± amount.
"""

import pytest
from sqlalchemy import text

from backend.services.reporting import balance_continuity


@pytest.fixture()
def continuity_engine(engine):
    with engine.begin() as conn:
        conn.execute(text('''CREATE TABLE transactions (
            id TEXT PRIMARY KEY,
            txn_date TEXT,
            description TEXT,
            amount REAL,
            db_cr TEXT,
            bank_code TEXT,
            bank_account_number TEXT,
            source_file TEXT,
            file_hash TEXT,
            running_balance REAL,
            currency TEXT
        )'''))
    return engine


def _txn(conn, id, date, amount, db_cr, balance, bank='DBS', acc='111',
         source='stmt-oct.pdf', description='x'):
    conn.execute(text(
        'INSERT INTO transactions (id, txn_date, description, amount, db_cr, '
        'bank_code, bank_account_number, source_file, file_hash, running_balance) '
        'VALUES (:id, :d, :desc, :amount, :dbcr, :bank, :acc, :src, :h, :bal)'
    ), {'id': id, 'd': date, 'desc': description, 'amount': amount,
        'dbcr': db_cr, 'bank': bank, 'acc': acc, 'src': source,
        'h': f'hash-{id}', 'bal': balance})


def _account_summary(result, bank='DBS', acc='111'):
    for item in result['accounts']:
        if item['bank_code'] == bank and item['account_number'] == acc:
            return item
    return None


def test_rantai_kontinu_tanpa_break(continuity_engine):
    with continuity_engine.begin() as conn:
        _txn(conn, 't1', '2026-10-01', 250000, 'DB', 10000000)
        _txn(conn, 't2', '2026-10-02', 100000, 'CR', 9900000)
        _txn(conn, 't3', '2026-10-03', 50000, 'DB', 9950000)

    result = balance_continuity.check_balance_continuity(continuity_engine)
    summary = _account_summary(result)
    assert summary is not None
    assert summary['has_running_balance'] is True
    assert summary['verified_count'] == 2  # t2, t3 (t1 = baseline)
    assert summary['breaks'] == []


def test_mismatch_saldo_terdeteksi(continuity_engine):
    with continuity_engine.begin() as conn:
        _txn(conn, 't1', '2026-10-01', 250000, 'DB', 10000000)
        _txn(conn, 't2', '2026-10-02', 100000, 'CR', 9500000)  # seharusnya 9900000

    result = balance_continuity.check_balance_continuity(continuity_engine)
    breaks = _account_summary(result)['breaks']
    assert len(breaks) == 1
    break_item = breaks[0]
    assert break_item['type'] == 'balance_mismatch'
    assert break_item['txn_id'] == 't2'
    assert break_item['expected'] == 9900000
    assert break_item['actual'] == 9500000
    assert break_item['diff'] == -400000


def test_akun_dipisah_per_nomor(continuity_engine):
    with continuity_engine.begin() as conn:
        _txn(conn, 'a1', '2026-10-01', 100, 'DB', 1000, acc='111')
        _txn(conn, 'a2', '2026-10-02', 100, 'DB', 1100, acc='111')
        # Akun berbeda: mismatch di sini tidak boleh mencemari akun 111.
        _txn(conn, 'b1', '2026-10-01', 100, 'DB', 500, acc='222')
        _txn(conn, 'b2', '2026-10-02', 100, 'DB', 900, acc='222')

    result = balance_continuity.check_balance_continuity(continuity_engine)
    assert len(result['accounts']) == 2
    assert _account_summary(result, acc='111')['breaks'] == []
    assert len(_account_summary(result, acc='222')['breaks']) == 1


def test_toleransi_rounding_kecil_dilewati(continuity_engine):
    with continuity_engine.begin() as conn:
        _txn(conn, 't1', '2026-10-01', 250000.00, 'DB', 10000000.00)
        _txn(conn, 't2', '2026-10-02', 100000.00, 'CR', 9900000.01)  # selisih 1 sen

    result = balance_continuity.check_balance_continuity(continuity_engine)
    assert _account_summary(result)['breaks'] == []


def test_baris_tanpa_saldo_dilewati_dan_rantai_dilanjutkan(continuity_engine):
    """Baris tanpa running_balance tidak diverifikasi tapi tidak memutus rantai."""
    with continuity_engine.begin() as conn:
        _txn(conn, 't1', '2026-10-01', 250000, 'DB', 10000000)
        _txn(conn, 't2', '2026-10-02', 100000, 'CR', None)
        _txn(conn, 't3', '2026-10-03', 50000, 'CR', 9850000)  # 10000000-100000-50000

    result = balance_continuity.check_balance_continuity(continuity_engine)
    summary = _account_summary(result)
    # Hanya t3 yang bisa diverifikasi (terhadap saldo terakhir yang diketahui, t1).
    assert summary['verified_count'] == 1
    assert summary['breaks'] == []


def test_gap_antar_periode_statement_terdeteksi(continuity_engine):
    """File A menutup 31 Okt, file B baru mulai 15 Nov → 1-14 Nov bolong."""
    with continuity_engine.begin() as conn:
        _txn(conn, 't1', '2026-10-30', 250000, 'DB', 10000000, source='okt.pdf')
        _txn(conn, 't2', '2026-10-31', 100000, 'CR', 9900000, source='okt.pdf')
        _txn(conn, 't3', '2026-11-15', 50000, 'DB', 9950000, source='nov.pdf')

    result = balance_continuity.check_balance_continuity(continuity_engine)
    breaks = _account_summary(result)['breaks']
    gap_breaks = [b for b in breaks if b['type'] == 'statement_gap']
    assert len(gap_breaks) == 1
    assert gap_breaks[0]['gap_from'] == '2026-11-01'
    assert gap_breaks[0]['gap_to'] == '2026-11-14'


def test_statement_berturut_tanpa_gap(continuity_engine):
    """Statement bulanan normal overlap/nyambung → tidak ada gap."""
    with continuity_engine.begin() as conn:
        _txn(conn, 't1', '2026-10-30', 250000, 'DB', 10000000, source='okt.pdf')
        _txn(conn, 't2', '2026-10-31', 100000, 'CR', 9900000, source='okt.pdf')
        _txn(conn, 't3', '2026-11-01', 50000, 'DB', 9950000, source='nov.pdf')

    result = balance_continuity.check_balance_continuity(continuity_engine)
    gaps = [b for b in _account_summary(result)['breaks'] if b['type'] == 'statement_gap']
    assert gaps == []


def test_akun_tanpa_saldo_sama_sekali(continuity_engine):
    """Data lama (sebelum migrasi 074) tidak punya saldo → checker no-op jujur."""
    with continuity_engine.begin() as conn:
        _txn(conn, 't1', '2026-10-01', 100, 'DB', None)
        _txn(conn, 't2', '2026-10-02', 100, 'DB', None)

    result = balance_continuity.check_balance_continuity(continuity_engine)
    summary = _account_summary(result)
    assert summary['has_running_balance'] is False
    assert summary['verified_count'] == 0
    assert summary['breaks'] == []
