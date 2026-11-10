"""Test trial balance: opening balance + mutasi periode = closing per akun COA.

Mutasi dihitung dengan query GL yang sama dengan laporan lain (mark → COA
mapping, report_type real/coretax) supaya konsisten dengan GL/income statement.
"""

import uuid

import pytest
from sqlalchemy import text

from backend.services.reporting import trial_balance

COA_CASH = '11111111-1111-1111-1111-111111111111'
COA_SALES = '22222222-2222-2222-2222-222222222222'
COA_EXPENSE = '33333333-3333-3333-3333-333333333333'
MARK_SALES = 'aaaa1111-1111-1111-1111-111111111111'
MARK_EXPENSE = 'aaaa2222-2222-2222-2222-222222222222'


@pytest.fixture()
def tb_engine(engine):
    """Skema minimal yang dibutuhkan mesin GL: marks, COA, mapping, transactions."""
    with engine.begin() as conn:
        conn.execute(text('''CREATE TABLE marks (
            id TEXT PRIMARY KEY,
            internal_report TEXT, personal_use TEXT, tax_report TEXT,
            natural_direction TEXT
        )'''))
        conn.execute(text('''CREATE TABLE chart_of_accounts (
            id TEXT PRIMARY KEY,
            code TEXT NOT NULL,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            subcategory TEXT, description TEXT, is_active INTEGER DEFAULT 1,
            parent_id TEXT, created_at TEXT, updated_at TEXT
        )'''))
        conn.execute(text('''CREATE TABLE mark_coa_mapping (
            id TEXT PRIMARY KEY,
            mark_id TEXT NOT NULL,
            coa_id TEXT NOT NULL,
            mapping_type TEXT NOT NULL,
            report_type TEXT DEFAULT 'real'
        )'''))
        conn.execute(text('''CREATE TABLE transactions (
            id TEXT PRIMARY KEY,
            txn_date TEXT, description TEXT, amount REAL, db_cr TEXT,
            bank_code TEXT, bank_account_number TEXT, source_file TEXT,
            file_hash TEXT, mark_id TEXT, company_id TEXT,
            created_at TEXT, updated_at TEXT
        )'''))
        conn.execute(text('''CREATE TABLE opening_balances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id TEXT,
            coa_id TEXT NOT NULL,
            period_year INTEGER NOT NULL,
            opening_debit REAL NOT NULL DEFAULT 0,
            opening_credit REAL NOT NULL DEFAULT 0,
            updated_at TEXT
        )'''))

        conn.execute(text(
            "INSERT INTO chart_of_accounts (id, code, name, category) VALUES "
            "(:cash, '1-1000', 'Kas & Bank', 'ASSET'),"
            "(:sales, '4-1000', 'Pendapatan', 'REVENUE'),"
            "(:exp, '5-1000', 'Beban Operasional', 'EXPENSE')"
        ), {'cash': COA_CASH, 'sales': COA_SALES, 'exp': COA_EXPENSE})

        conn.execute(text(
            # natural_direction pasca-068 = perspektif owner: DB = uang masuk,
            # CR = uang keluar — jadi mark Penjualan DB, mark Beban CR.
            "INSERT INTO marks (id, internal_report, natural_direction) VALUES "
            "(:ms, 'Penjualan', 'DB'), (:me, 'Beban Kantor', 'CR')"
        ), {'ms': MARK_SALES, 'me': MARK_EXPENSE})

        conn.execute(text(
            "INSERT INTO mark_coa_mapping (id, mark_id, coa_id, mapping_type, report_type) VALUES "
            "(:m1, :ms, :sales, 'CREDIT', 'real'),"
            "(:m2, :me, :exp, 'DEBIT', 'real')"
        ), {
            'm1': str(uuid.uuid4()), 'm2': str(uuid.uuid4()),
            'ms': MARK_SALES, 'sales': COA_SALES, 'me': MARK_EXPENSE, 'exp': COA_EXPENSE,
        })
    return engine


def _txn(conn, id, date, amount, db_cr, mark_id):
    conn.execute(text(
        'INSERT INTO transactions (id, txn_date, description, amount, db_cr, mark_id) '
        'VALUES (:id, :d, :x, :amount, :dbcr, :mark)'
    ), {'id': id, 'd': date, 'x': 'desc', 'amount': amount,
        'dbcr': db_cr, 'mark': mark_id})


def _row(tb, coa_id):
    for row in tb['rows']:
        if row['coa_id'] == coa_id:
            return row
    return None


def test_opening_dan_mutasi_digabung(tb_engine):
    with tb_engine.begin() as conn:
        # Opening: Kas D 10.000.000, akumulasi penjualan C 50.000.000
        conn.execute(text(
            'INSERT INTO opening_balances (company_id, coa_id, period_year, opening_debit, opening_credit) '
            "VALUES (NULL, :cash, 2026, 10000000, 0), (NULL, :sales, 2026, 0, 50000000)"
        ), {'cash': COA_CASH, 'sales': COA_SALES})
        # Mutasi 2026: penjualan 2.000.000 (CR mark → CREDIT), beban 500.000 (DB → DEBIT)
        _txn(conn, 't1', '2026-03-01', 2000000, 'DB', MARK_SALES)
        _txn(conn, 't2', '2026-04-01', 500000, 'CR', MARK_EXPENSE)
        # Di luar tahun — tidak boleh ikut.
        _txn(conn, 't3', '2025-12-31', 999999, 'DB', MARK_SALES)

    tb = trial_balance.build_trial_balance(tb_engine, company_id=None, year=2026)
    sales = _row(tb, COA_SALES)
    assert sales['opening_debit'] == 0
    assert sales['opening_credit'] == 50000000
    assert sales['period_debit'] == 0
    assert sales['period_credit'] == 2000000
    # Closing revenue: net kredit → kolom kredit
    assert sales['closing_credit'] == 52000000
    assert sales['closing_debit'] == 0

    expense = _row(tb, COA_EXPENSE)
    assert expense['opening_debit'] == 0
    assert expense['period_debit'] == 500000
    assert expense['closing_debit'] == 500000

    cash = _row(tb, COA_CASH)
    assert cash['opening_debit'] == 10000000
    assert cash['closing_debit'] == 10000000  # tanpa mutasi (tidak ada mark bank)

    assert tb['year'] == 2026
    assert tb['totals']['opening_debit'] == 10000000
    assert tb['totals']['opening_credit'] == 50000000
    assert tb['totals']['closing_credit'] > 0


def test_akun_tanpa_opening_tetap_muncul(tb_engine):
    with tb_engine.begin() as conn:
        _txn(conn, 't1', '2026-03-01', 2000000, 'DB', MARK_SALES)

    tb = trial_balance.build_trial_balance(tb_engine, company_id=None, year=2026)
    sales = _row(tb, COA_SALES)
    assert sales is not None
    assert sales['opening_debit'] == 0
    assert sales['opening_credit'] == 0
    assert sales['period_credit'] == 2000000


def test_opening_tanpa_mutasi_tetap_muncul(tb_engine):
    with tb_engine.begin() as conn:
        conn.execute(text(
            'INSERT INTO opening_balances (company_id, coa_id, period_year, opening_debit) '
            'VALUES (NULL, :cash, 2026, 10000000)'
        ), {'cash': COA_CASH})

    tb = trial_balance.build_trial_balance(tb_engine, company_id=None, year=2026)
    cash = _row(tb, COA_CASH)
    assert cash is not None
    assert cash['opening_debit'] == 10000000
    assert cash['period_debit'] == 0


def test_is_balanced_dan_selisih(tb_engine):
    with tb_engine.begin() as conn:
        _txn(conn, 't1', '2026-03-01', 2000000, 'DB', MARK_SALES)  # CREDIT 2jt
        _txn(conn, 't2', '2026-04-01', 1500000, 'CR', MARK_EXPENSE)  # DEBIT 1.5jt

    tb = trial_balance.build_trial_balance(tb_engine, company_id=None, year=2026)
    # Mutasi satu sisi (mark→COA tunggal) memang belum D=C — TB harus jujur.
    # Konvensi: unbalanced = total debit - total kredit (negatif = kredit lebih besar).
    assert tb['is_balanced'] is False
    assert tb['unbalanced_amount'] == pytest.approx(-500000.0)


def test_simpan_opening_balance_validasi_seimbang(tb_engine):
    entries = [
        {'coa_id': COA_CASH, 'opening_debit': 10000000, 'opening_credit': 0},
        {'coa_id': COA_SALES, 'opening_debit': 0, 'opening_credit': 10000000},
    ]
    trial_balance.save_opening_balances(tb_engine, company_id=None, year=2026, entries=entries)

    with tb_engine.connect() as conn:
        rows = conn.execute(text(
            'SELECT coa_id, opening_debit, opening_credit FROM opening_balances '
            'WHERE period_year = 2026'
        )).fetchall()
    assert len(rows) == 2

    # Update kedua kalinya harus replace, bukan append.
    trial_balance.save_opening_balances(tb_engine, company_id=None, year=2026, entries=[
        {'coa_id': COA_CASH, 'opening_debit': 9000000, 'opening_credit': 0},
        {'coa_id': COA_SALES, 'opening_debit': 0, 'opening_credit': 9000000},
    ])
    with tb_engine.connect() as conn:
        count = conn.execute(text(
            'SELECT COUNT(1) FROM opening_balances WHERE period_year = 2026'
        )).scalar_one()
        cash = conn.execute(text(
            'SELECT opening_debit FROM opening_balances WHERE coa_id = :c AND period_year = 2026'
        ), {'c': COA_CASH}).scalar_one()
    assert count == 2
    assert cash == 9000000


def test_simpan_opening_balance_tidak_seimbang_ditolak(tb_engine):
    with pytest.raises(ValueError, match='seimbang'):
        trial_balance.save_opening_balances(tb_engine, company_id=None, year=2026, entries=[
            {'coa_id': COA_CASH, 'opening_debit': 10000000, 'opening_credit': 0},
            {'coa_id': COA_SALES, 'opening_debit': 0, 'opening_credit': 9000000},
        ])


def test_simpan_opening_balance_coa_tidak_ada_ditolak(tb_engine):
    with pytest.raises(ValueError, match='tidak ditemukan'):
        trial_balance.save_opening_balances(tb_engine, company_id=None, year=2026, entries=[
            {'coa_id': '99999999-9999-9999-9999-999999999999',
             'opening_debit': 1000, 'opening_credit': 1000},
        ])


def test_opening_per_company_terpisah(tb_engine):
    company_a = 'cccc1111-1111-1111-1111-111111111111'
    with tb_engine.begin() as conn:
        conn.execute(text(
            'INSERT INTO opening_balances (company_id, coa_id, period_year, opening_debit) '
            'VALUES (:c, :cash, 2026, 7500000)'
        ), {'c': company_a, 'cash': COA_CASH})

    tb_a = trial_balance.build_trial_balance(tb_engine, company_id=company_a, year=2026)
    tb_all = trial_balance.build_trial_balance(tb_engine, company_id=None, year=2026)
    assert _row(tb_a, COA_CASH)['opening_debit'] == 7500000
    # Tanpa company_id = gabungan semua (semantik yang sama dengan GL).
    assert _row(tb_all, COA_CASH)['opening_debit'] == 7500000
