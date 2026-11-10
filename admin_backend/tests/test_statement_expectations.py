"""Test deteksi statement bulanan yang belum masuk (alert pipeline Gmail).

Sumber ekspektasi: bank_account_definitions yang aktif pada bulan sebelumnya.
Akun yang didefinisikan tapi belum pernah punya transaksi apa pun dilewati
supaya tidak berisik (defined-but-unused).
"""

import datetime

import pytest
from sqlalchemy import text

from backend.services.transactions import statement_expectations


@pytest.fixture()
def expectations_engine(engine):
    """Engine sqlite dengan skema minimal: transactions + bank_account_definitions."""
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
            company_id TEXT
        )'''))
        conn.execute(text('''CREATE TABLE bank_account_definitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bank_code TEXT NOT NULL,
            account_number TEXT NOT NULL,
            display_name TEXT,
            active_from TEXT,
            active_until TEXT
        )'''))
    return engine


def _insert_txn(conn, bank_code, account, txn_date, amount=1000.0):
    conn.execute(text(
        'INSERT INTO transactions (id, txn_date, description, amount, db_cr, '
        'bank_code, bank_account_number, source_file, file_hash) '
        "VALUES (:id, :d, 'x', :amount, 'DB', :bank, :acc, 'f.pdf', :h)"
    ), {
        'id': f'{bank_code}-{account}-{txn_date}',
        'd': txn_date, 'amount': amount, 'bank': bank_code,
        'acc': account, 'h': f'hash-{bank_code}-{account}-{txn_date}',
    })


def _insert_definition(conn, bank_code, account, display_name='akun',
                       active_from=None, active_until=None):
    conn.execute(text(
        'INSERT INTO bank_account_definitions '
        '(bank_code, account_number, display_name, active_from, active_until) '
        'VALUES (:bank, :acc, :name, :from, :until)'
    ), {'bank': bank_code, 'acc': account, 'name': display_name,
        'from': active_from, 'until': active_until})


def test_deteksi_statement_bulan_lalu_hilang(expectations_engine):
    with expectations_engine.begin() as conn:
        _insert_definition(conn, 'DBS', '1234567890', 'digibank ops')
        # Transaksi terakhir akun ini September → statement Oktober hilang.
        _insert_txn(conn, 'DBS', '1234567890', '2026-09-28')

    missing = statement_expectations.find_missing_statements(
        expectations_engine, today=datetime.date(2026, 11, 10),
    )
    assert len(missing) == 1
    item = missing[0]
    assert item['bank_code'] == 'DBS'
    assert item['account_number'] == '1234567890'
    assert item['display_name'] == 'digibank ops'
    assert item['month'] == '2026-10'
    assert item['last_seen'] == '2026-09-28'


def test_tanpa_alert_sebelum_grace_period(expectations_engine):
    with expectations_engine.begin() as conn:
        _insert_definition(conn, 'DBS', '1234567890')
        _insert_txn(conn, 'DBS', '1234567890', '2026-09-28')

    # Tanggal 3 bulan November — e-statement Oktober wajar belum masuk.
    missing = statement_expectations.find_missing_statements(
        expectations_engine, today=datetime.date(2026, 11, 3),
    )
    assert missing == []


def test_statement_sudah_ada_tanpa_alert(expectations_engine):
    with expectations_engine.begin() as conn:
        _insert_definition(conn, 'DBS', '1234567890')
        _insert_txn(conn, 'DBS', '1234567890', '2026-09-28')
        _insert_txn(conn, 'DBS', '1234567890', '2026-10-05')

    missing = statement_expectations.find_missing_statements(
        expectations_engine, today=datetime.date(2026, 11, 10),
    )
    assert missing == []


def test_definisi_tidak_aktif_diabaikan(expectations_engine):
    with expectations_engine.begin() as conn:
        # Akun ditutup akhir September: statement Oktober tidak diharapkan.
        _insert_definition(conn, 'DBS', '1234567890', active_until='2026-09-30')
        _insert_txn(conn, 'DBS', '1234567890', '2026-09-28')

    missing = statement_expectations.find_missing_statements(
        expectations_engine, today=datetime.date(2026, 11, 10),
    )
    assert missing == []


def test_definisi_belum_pernah_dipakai_dilewati(expectations_engine):
    with expectations_engine.begin() as conn:
        _insert_definition(conn, 'BCA', '1112223334')

    missing = statement_expectations.find_missing_statements(
        expectations_engine, today=datetime.date(2026, 11, 10),
    )
    assert missing == []


def test_bulan_januari_merujuk_desember_tahun_lalu(expectations_engine):
    with expectations_engine.begin() as conn:
        _insert_definition(conn, 'DBS', '1234567890')
        _insert_txn(conn, 'DBS', '1234567890', '2025-11-30')

    missing = statement_expectations.find_missing_statements(
        expectations_engine, today=datetime.date(2026, 1, 10),
    )
    assert len(missing) == 1
    assert missing[0]['month'] == '2025-12'


def test_grace_period_bisa_diturunkan(expectations_engine):
    with expectations_engine.begin() as conn:
        _insert_definition(conn, 'DBS', '1234567890')
        _insert_txn(conn, 'DBS', '1234567890', '2026-09-28')

    missing = statement_expectations.find_missing_statements(
        expectations_engine, today=datetime.date(2026, 11, 3), grace_days=2,
    )
    assert len(missing) == 1


def test_tabel_definisi_tidak_ada_mengembalikan_kosong(engine):
    """Graceful: tanpa tabel bank_account_definitions tidak ada yang bisa dicek."""
    with engine.begin() as conn:
        conn.execute(text('''CREATE TABLE transactions (
            id TEXT PRIMARY KEY, txn_date TEXT, bank_code TEXT,
            bank_account_number TEXT
        )'''))

    missing = statement_expectations.find_missing_statements(
        engine, today=datetime.date(2026, 11, 10),
    )
    assert missing == []
