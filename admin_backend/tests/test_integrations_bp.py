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
    updated_at TEXT,
    email_from TEXT,
    email_subject TEXT,
    email_date TEXT,
    email_message_id TEXT
);
CREATE TABLE IF NOT EXISTS app_settings (
    setting_key TEXT PRIMARY KEY,
    setting_value TEXT,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS bank_account_definitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bank_code TEXT NOT NULL,
    account_number TEXT NOT NULL,
    display_name TEXT,
    active_from TEXT,
    active_until TEXT
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


# --- Metadata email + idempotency message_id -------------------------------


def test_email_metadata_persisted(client, integration_env):
    response = _post(
        client,
        pdf_file=_bri_file(),
        bank_type='bri',
        email_from='digibank@example.com',
        email_subject='e-statement November',
        email_date='Mon, 09 Nov 2026 06:00:00 +0000',
        message_id='<stmt-nov-2026@dbs>',
    )
    assert response.status_code == 200

    with integration_env.connect() as conn:
        rows = conn.execute(text(
            'SELECT email_from, email_subject, email_date, email_message_id '
            'FROM transactions'
        )).fetchall()
    assert len(rows) == 2
    for row in rows:
        assert row[0] == 'digibank@example.com'
        assert row[1] == 'e-statement November'
        assert row[2] == 'Mon, 09 Nov 2026 06:00:00 +0000'
        assert row[3] == '<stmt-nov-2026@dbs>'


def test_duplicate_message_id_beberapa_byte_berbeda(client, integration_env):
    """Bank regenerate PDF (byte beda, hash beda) untuk email yang sama → duplicate."""
    first = _post(
        client, pdf_file=_bri_file(), bank_type='bri', message_id='<regen-001@bank>',
    )
    assert first.status_code == 200
    assert first.get_json()['status'] == 'imported'

    # File sama tapi satu baris berubah → file_hash berbeda.
    regenerated = BRI_CSV.replace('9000000.00', '9000001.00')
    file = (io.BytesIO(regenerated.encode('utf-8')), 'bri-2026-regenerated.csv')
    second = _post(
        client, pdf_file=file, bank_type='bri', message_id='<regen-001@bank>',
    )
    assert second.status_code == 200
    assert second.get_json()['status'] == 'duplicate'
    assert second.get_json()['duplicate'] is True

    with integration_env.connect() as conn:
        count = conn.execute(text('SELECT COUNT(1) FROM transactions')).scalar_one()
    assert count == 2  # tidak ada double-import


# --- Notifikasi Telegram saat import bermasalah ----------------------------


@pytest.fixture()
def telegram_spy(monkeypatch):
    calls = []

    def _spy(bank_type, filename, error_code, detail='', email_meta=None):
        calls.append({
            'bank_type': bank_type, 'filename': filename,
            'error_code': error_code, 'detail': detail, 'email_meta': email_meta,
        })
        return True

    monkeypatch.setattr(n8n_bp_module, 'notify_import_problem', _spy)
    return calls


def test_parse_failure_memanggil_notifikasi(client, integration_env, telegram_spy):
    response = _post(
        client,
        pdf_file=_bri_file('bca-2026.csv'),
        bank_type='bca',
        email_from='bank@example.com',
        message_id='<broken@bank>',
    )
    assert response.status_code == 400
    assert response.get_json()['code'] == 'parse_failed'
    assert len(telegram_spy) == 1
    call = telegram_spy[0]
    assert call['bank_type'] == 'bca'
    assert call['error_code'] == 'parse_failed'
    assert call['email_meta']['email_message_id'] == '<broken@bank>'


def test_notifikasi_gagal_tidak_menelan_error(client, integration_env, monkeypatch):
    """Notifier melempar exception → error response asli tetap dikembalikan."""
    def _explode(*args, **kwargs):
        raise RuntimeError('telegram down')

    monkeypatch.setattr(n8n_bp_module, 'notify_import_problem', _explode)
    response = _post(client, pdf_file=_bri_file('bca-2026.csv'), bank_type='bca')
    assert response.status_code == 400
    assert response.get_json()['code'] == 'parse_failed'


# --- Endpoint statement-check ------------------------------------------------


def _post_statement_check(client, key=API_KEY, date='2026-11-10'):
    from urllib.parse import urlencode
    url = '/api/integrations/statement-check'
    if date:
        url += f'?{urlencode({"date": date})}'
    return client.post(url, headers={'X-API-Key': key} if key else {})


def test_statement_check_mengembalikan_yang_hilang(client, integration_env, monkeypatch):
    with integration_env.begin() as conn:
        conn.execute(text(
            "INSERT INTO bank_account_definitions "
            "(bank_code, account_number, display_name) VALUES ('BRI', '1234567890123', 'bri utama')"
        ))
        conn.execute(text(
            "INSERT INTO transactions (id, txn_date, description, amount, db_cr, "
            "bank_code, bank_account_number, source_file, file_hash) VALUES ("
            "'t1', '2026-09-05', 'x', 1000, 'DB', 'BRI', '1234567890123', 'f.pdf', 'h1')"
        ))

    sent = []
    monkeypatch.setattr(n8n_bp_module, 'notify_missing_statements', lambda missing: sent.append(missing) or True)

    response = _post_statement_check(client)
    assert response.status_code == 200
    payload = response.get_json()
    assert payload['status'] == 'ok'
    assert payload['notified'] is True
    assert len(payload['missing']) == 1
    assert payload['missing'][0]['bank_code'] == 'BRI'
    assert len(sent) == 1  # notifier dipanggil dengan daftar yang sama


def test_statement_check_tanpa_yang_hilang_tidak_mengirim(client, integration_env, monkeypatch):
    monkeypatch.setattr(
        n8n_bp_module, 'notify_missing_statements',
        lambda missing: (_ for _ in ()).throw(AssertionError('tidak boleh kirim')),
    )
    response = _post_statement_check(client)
    assert response.status_code == 200
    payload = response.get_json()
    assert payload['missing'] == []
    assert payload['notified'] is False


def test_statement_check_butuh_api_key(client, integration_env):
    response = _post_statement_check(client, key='salah')
    assert response.status_code == 401
