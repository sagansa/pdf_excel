import io

import pytest
from sqlalchemy import text

from backend.routes.integrations import n8n_bp as n8n_bp_module

API_KEY = 'test-integration-key'

TRANSACTIONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY,
    txn_date TEXT,
    description TEXT,
    amount REAL,
    db_cr TEXT,
    bank_code TEXT,
    bank_account_number TEXT,
    source_file TEXT,
    file_hash TEXT,
    mark_id TEXT,
    company_id TEXT,
    created_at TEXT,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS app_settings (
    setting_key TEXT PRIMARY KEY,
    setting_value TEXT,
    updated_at TEXT
);
"""

BRI_CSV = (
    'NOREK;TGL_TRAN;TGL_EFEKTIF;DESK_TRAN;REMARK_CUSTOM;'
    'MUTASI_DEBET;MUTASI_KREDIT;GLSIGN;SALDO_AKHIR_MUTASI\r\n'
    '1234567890123;05/11/2026 10:00;05/11/2026 10:00;TRF DB;;'
    '1250000.00;0;DB;9000000.00\r\n'
    '1234567890123;06/11/2026 11:00;06/11/2026 11:00;SETOR;;'
    '0;250000.00;CR;9250000.00\r\n'
)


@pytest.fixture()
def integration_env(monkeypatch, engine):
    """Endpoint aktif dengan API key + DB sqlite (transaksi & app_settings)."""
    with engine.begin() as conn:
        for statement in TRANSACTIONS_SCHEMA.split(';'):
            if statement.strip():
                conn.execute(text(statement))
    monkeypatch.setenv('INTEGRATION_API_KEY', API_KEY)
    monkeypatch.setattr(n8n_bp_module, 'require_db_engine', lambda: engine)
    from backend.db import session as db_session
    from backend.services.ai import mark_pass
    from backend.services.transactions import transaction_service
    monkeypatch.setattr(transaction_service, 'get_db_engine', lambda: (engine, None))
    monkeypatch.setattr(db_session, 'get_db_engine', lambda: (engine, None))
    monkeypatch.setattr(mark_pass, 'queue_ai_mark_pass', lambda ids: False)
    return engine


def _post(client, *, key=API_KEY, **data):
    headers = {'X-API-Key': key} if key is not None else {}
    return client.post(
        '/api/integrations/statement',
        data=data,
        headers=headers,
        content_type='multipart/form-data',
    )


def _bri_file(name='bri-2026.csv'):
    return (io.BytesIO(BRI_CSV.encode('utf-8')), name)


def test_disabled_without_api_key(client, integration_env, monkeypatch):
    monkeypatch.delenv('INTEGRATION_API_KEY', raising=False)
    response = _post(client, pdf_file=_bri_file(), bank_type='bri')
    assert response.status_code == 503
    assert response.get_json()['code'] == 'integration_disabled'


def test_rejects_invalid_api_key(client, integration_env):
    response = _post(client, key='salah', pdf_file=_bri_file(), bank_type='bri')
    assert response.status_code == 401
    assert response.get_json()['code'] == 'invalid_api_key'


def test_rejects_missing_file(client, integration_env):
    response = _post(client, bank_type='bri')
    assert response.status_code == 400


def test_rejects_unknown_bank_type(client, integration_env):
    response = _post(client, pdf_file=_bri_file(), bank_type='bni')
    assert response.status_code == 400
    assert response.get_json()['code'] == 'invalid_bank_type'


def test_imports_bri_csv(client, integration_env):
    response = _post(
        client,
        pdf_file=_bri_file(),
        bank_type='bri',
        email_from='bank@example.com',
        email_subject='e-statement BRI November',
        message_id='<abc123@gmail.com>',
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload['status'] == 'imported'
    assert payload['duplicate'] is False
    assert payload['source_file'] == 'bri-2026.csv'
    assert payload['bank_type'] == 'bri'
    assert payload['rows_inserted'] == 2

    with integration_env.connect() as conn:
        rows = conn.execute(text(
            'SELECT bank_code, source_file, file_hash, db_cr, amount '
            'FROM transactions ORDER BY amount'
        )).fetchall()
    assert len(rows) == 2
    assert {row[0] for row in rows} == {'BRI'}
    assert {row[1] for row in rows} == {'bri-2026.csv'}
    assert all(row[2] for row in rows)  # file_hash terisi untuk deteksi duplikat


def test_duplicate_file_returns_success(client, integration_env):
    first = _post(client, pdf_file=_bri_file(), bank_type='bri')
    assert first.status_code == 200
    assert first.get_json()['status'] == 'imported'

    # Email yang sama ter-poll ulang: 200 + status duplicate, bukan error.
    second = _post(client, pdf_file=_bri_file(), bank_type='bri')
    assert second.status_code == 200
    assert second.get_json()['status'] == 'duplicate'

    with integration_env.connect() as conn:
        count = conn.execute(text('SELECT COUNT(1) FROM transactions')).scalar_one()
    assert count == 2


def test_csv_only_supported_for_bri(client, integration_env):
    response = _post(client, pdf_file=_bri_file('bca-2026.csv'), bank_type='bca')
    assert response.status_code == 400
    assert response.get_json()['code'] == 'parse_failed'
