"""Test endpoint /api/credentials: masking secret, bulk save, sentinel, test koneksi."""

import pytest
from flask import Flask
from sqlalchemy import create_engine, text

from backend.error_handlers import register_error_handlers
from backend.routes import credentials_bp as credentials_bp_module
from backend.services import credentials as credentials_service

APP_SETTINGS_SCHEMA = """
CREATE TABLE IF NOT EXISTS app_settings (
    setting_key TEXT PRIMARY KEY,
    setting_value TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


@pytest.fixture()
def cred_engine():
    engine = create_engine('sqlite:///:memory:')
    with engine.begin() as conn:
        conn.execute(text(APP_SETTINGS_SCHEMA))
    yield engine
    engine.dispose()


@pytest.fixture()
def cred_client(monkeypatch, cred_engine):
    # Import backend.db.session menjalankan load_dotenv(.env) sehingga SMTP_*/SAGANSA_*
    # bisa bocor ke env proses test; hapus yang memengaruhi asersi status agar hermetic.
    for _var in ('SMTP_HOST', 'SMTP_PASS'):
        monkeypatch.delenv(_var, raising=False)
    monkeypatch.setattr(credentials_bp_module, 'require_db_engine', lambda: cred_engine)
    app = Flask(__name__)
    # app asli memasang handler error global (BadRequestError -> JSON {error, code});
    # pasang juga di app test agar asersi status 400 + code berjalan sama seperti produksi.
    register_error_handlers(app)
    app.register_blueprint(credentials_bp_module.credentials_bp)
    app.config['TESTING'] = True
    return app.test_client()


def test_get_masking_secret(cred_client):
    resp = cred_client.get('/api/credentials')
    assert resp.status_code == 200
    items = {c['key']: c for c in resp.get_json()['credentials']}
    assert 'smtp_pass' in items
    assert 'value' not in items['smtp_pass']
    assert items['smtp_host']['value'] == ''


def test_put_bulk_save_dan_masked_response(cred_client):
    resp = cred_client.put('/api/credentials', json={
        'updates': {'smtp_host': 'smtp.example.com', 'smtp_pass': 'rahasia123'},
    })
    assert resp.status_code == 200
    body = resp.get_json()
    assert 'rahasia123' not in resp.get_data(as_text=True)
    items = {c['key']: c for c in body['credentials']}
    assert items['smtp_host']['value'] == 'smtp.example.com'
    assert items['smtp_pass']['set'] is True


def test_put_sentinel_menghapus(cred_client):
    cred_client.put('/api/credentials', json={'updates': {'smtp_pass': 'rahasia123'}})
    resp = cred_client.put('/api/credentials', json={'updates': {'smtp_pass': '__CLEAR__'}})
    items = {c['key']: c for c in resp.get_json()['credentials']}
    assert items['smtp_pass']['set'] is False


def test_put_key_tak_dikenal_400(cred_client):
    resp = cred_client.put('/api/credentials', json={'updates': {'bukan_kunci': 'x'}})
    assert resp.status_code == 400
    assert resp.get_json()['code'] == 'credentials_unknown_key'


def test_put_tanpa_updates_400(cred_client):
    resp = cred_client.put('/api/credentials', json={})
    assert resp.status_code == 400
    assert resp.get_json()['code'] == 'credentials_updates_missing'


def test_post_test_sukses(cred_client, monkeypatch):
    monkeypatch.setattr(
        credentials_service, 'run_test',
        lambda key, value=None, extra=None: (True, 'Koneksi berhasil (HTTP 200).'),
    )
    resp = cred_client.post('/api/credentials/sagansa_api_token/test', json={'value': 'tok'})
    assert resp.status_code == 200
    assert resp.get_json() == {'ok': True, 'message': 'Koneksi berhasil (HTTP 200).'}


def test_post_test_key_tak_dikenal_400(cred_client):
    resp = cred_client.post('/api/credentials/bukan_kunci/test', json={})
    assert resp.status_code == 400
    assert resp.get_json()['code'] == 'credentials_unknown_key'


def test_post_test_tetap_200_saaat_handler_gagal(cred_client, monkeypatch):
    monkeypatch.setattr(
        credentials_service, 'run_test',
        lambda key, value=None, extra=None: (False, 'HTTP 401 — token ditolak server (salah atau tidak berlaku).'),
    )
    resp = cred_client.post('/api/credentials/sagansa_api_token/test', json={})
    assert resp.status_code == 200
    assert resp.get_json()['ok'] is False
