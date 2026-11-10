"""Test description enrichment (Fase 3): rule-based cleanup + persist + LLM fallback.

Deskripsi asli TIDAK pernah diubah — hasil bersih disimpan di kolom
clean_description (audit trail utuh).
"""

import pytest
from sqlalchemy import text

from backend.services.ai import description_enricher


# --- Rule-based cleanup ------------------------------------------------------


def test_buang_nomor_referensi_panjang():
    assert description_enricher.clean_description(
        'TRSF E-BANKING 0829347123 GOJEK'
    ) == 'TRSF E-BANKING GOJEK'


def test_buang_id_pelanggan():
    assert description_enricher.clean_description(
        'PEMBAYARAN LISTRIK PLN 9876543210123'
    ) == 'PEMBAYARAN LISTRIK PLN'


def test_buang_nominal_dan_mata_uang():
    assert description_enricher.clean_description(
        'PURCHASE APPLE.COM/BILL 0.99 USD'
    ) == 'PURCHASE APPLE.COM/BILL'


def test_buang_nominal_rupiah():
    assert description_enricher.clean_description(
        'TRF BCA 1234567890 RP 500.000 BERHASIL'
    ) == 'TRF BCA BERHASIL'


def test_buang_tanggal():
    assert description_enricher.clean_description('BUNGA 15/11') == 'BUNGA'
    assert description_enricher.clean_description('BUNGA 15/11/2026') == 'BUNGA'


def test_angka_pendek_dipertahankan():
    """Referensi pendek (<5 digit) bisa bermakna (no. invoice dsb) — dibiarkan."""
    assert description_enricher.clean_description('INV 1234 TOKO MAKMUR') == 'INV 1234 TOKO MAKMUR'


def test_casing_dan_akronim_tetap():
    assert description_enricher.clean_description('PLN 0812345678903') == 'PLN'
    assert 'GOJEK' in description_enricher.clean_description('GOJEK 0829347123')


def test_hanya_noise_mengembalikan_none():
    assert description_enricher.clean_description('1234567890 15/11') is None
    assert description_enricher.clean_description('   ') is None


def test_whitespace_dirapatkan():
    assert description_enricher.clean_description(
        'TOKO   MAKJU  0812345678'
    ) == 'TOKO MAKJU'


# --- Persist ke DB -----------------------------------------------------------


@pytest.fixture()
def enrich_engine(engine):
    with engine.begin() as conn:
        conn.execute(text('''CREATE TABLE transactions (
            id TEXT PRIMARY KEY,
            txn_date TEXT,
            description TEXT,
            amount REAL,
            db_cr TEXT,
            bank_code TEXT,
            mark_id TEXT,
            clean_description TEXT,
            updated_at TEXT
        )'''))
        conn.execute(text(
            'INSERT INTO transactions (id, txn_date, description, amount, db_cr, bank_code) VALUES '
            "('t1', '2026-01-15', 'TRSF E-BANKING 0829347123 GOJEK', 50000, 'CR', 'BCA'),"
            "('t2', '2026-01-16', 'SETORAN TUNAI', 100000, 'DB', 'BCA')"
        ))
    return engine


def test_enrich_transactions_persist(enrich_engine):
    result = description_enricher.enrich_transactions(enrich_engine, ['t1', 't2'])
    # t1 berubah (noise dihapus), t2 tidak — hanya t1 yang di-update.
    assert result['enriched'] == 1
    with enrich_engine.connect() as conn:
        rows = {
            row.id: row.clean_description
            for row in conn.execute(text(
                'SELECT id, clean_description FROM transactions'
            )).fetchall()
        }
    assert rows['t1'] == 'TRSF E-BANKING GOJEK'
    assert rows['t2'] is None  # tidak diubah tanpa LLM

    # Deskripsi asli tetap utuh.
    with enrich_engine.connect() as conn:
        original = conn.execute(text(
            'SELECT description FROM transactions WHERE id = :i'
        ), {'i': 't1'}).scalar_one()
    assert original == 'TRSF E-BANKING 0829347123 GOJEK'


def test_enrich_transactions_idempotent(enrich_engine):
    description_enricher.enrich_transactions(enrich_engine, ['t1'])
    second = description_enricher.enrich_transactions(enrich_engine, ['t1'])
    assert second['enriched'] == 0


def test_llm_fallback_untuk_yang_tidak_berubah(enrich_engine):
    """t2 tanpa noise → rule layer tak menyentuh → LLM dipanggil untuk t2."""

    def _fake_llm(conn, requests):
        return {req['id']: f"Bersih: {req['description'].title()}" for req in requests}

    result = description_enricher.enrich_transactions(
        enrich_engine, ['t1', 't2'], llm_complete=_fake_llm,
    )
    assert result['enriched'] == 2
    assert result['llm_used'] is True
    with enrich_engine.connect() as conn:
        clean = conn.execute(text(
            'SELECT clean_description FROM transactions WHERE id = :i'
        ), {'i': 't2'}).scalar_one()
    assert clean == 'Bersih: Setoran Tunai'


def test_llm_fallback_gagal_tetap_lanjut(enrich_engine):
    """LLM error → enrichment rule-only tetap tersimpan, tanpa exception."""

    def _explode(conn, requests):
        raise RuntimeError('llm down')

    result = description_enricher.enrich_transactions(
        enrich_engine, ['t1', 't2'], llm_complete=_explode,
    )
    assert result['enriched'] == 1
    assert result['llm_used'] is False
