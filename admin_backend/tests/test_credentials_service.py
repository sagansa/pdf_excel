"""Unit test credentials service: registry, resolusi DB→env, bulk save, masking."""

import pytest
from sqlalchemy import create_engine, text

from backend.db import session as db_session
from backend.services import credentials as credentials_service

APP_SETTINGS_SCHEMA = """
CREATE TABLE IF NOT EXISTS app_settings (
    setting_key TEXT PRIMARY KEY,
    setting_value TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

EXPECTED_KEYS = {
    'sagansa_presence_token',
    'sagansa_remaining_storage_token',
    'sagansa_stock_monitoring_token',
    'sagansa_sales_by_date_token',
    'sagansa_stock_comparison_token',
    'telegram_bot_token',
    'telegram_chat_id',
    'smtp_host', 'smtp_port', 'smtp_user', 'smtp_pass', 'smtp_from', 'smtp_use_tls',
    'integration_api_key',
    'ai_api_key',
}

SECRET_KEYS = {
    'sagansa_presence_token', 'sagansa_remaining_storage_token',
    'sagansa_stock_monitoring_token', 'sagansa_sales_by_date_token',
    'sagansa_stock_comparison_token', 'telegram_bot_token',
    'smtp_pass', 'integration_api_key', 'ai_api_key',
}


@pytest.fixture()
def cred_engine():
    engine = create_engine('sqlite:///:memory:')
    with engine.begin() as conn:
        conn.execute(text(APP_SETTINGS_SCHEMA))
    yield engine
    engine.dispose()


def test_registry_keys_lengkap_dan_unik():
    assert credentials_service.CREDENTIAL_KEYS == EXPECTED_KEYS
    assert credentials_service.CREDENTIAL_CLEAR_SENTINEL == '__CLEAR__'


def test_db_value_menang_atas_env(cred_engine, monkeypatch):
    monkeypatch.setenv('SAGANSA_PRESENCE_TOKEN', 'env-token')
    with cred_engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO app_settings (setting_key, setting_value) VALUES ('sagansa_presence_token', 'db-token')"
        ))
    with cred_engine.connect() as conn:
        value, source = credentials_service.get_credential(conn, 'sagansa_presence_token')
    assert value == 'db-token'
    assert source == 'db'


def test_env_fallback_saaat_db_kosong(cred_engine, monkeypatch):
    monkeypatch.setenv('TELEGRAM_BOT_TOKEN', 'env-tok')
    with cred_engine.connect() as conn:
        value, source = credentials_service.get_credential(conn, 'telegram_bot_token')
    assert value == 'env-tok'
    assert source == 'env'


def test_ai_api_key_tanpa_env_fallback(cred_engine):
    with cred_engine.connect() as conn:
        value, source = credentials_service.get_credential(conn, 'ai_api_key')
    assert value == ''
    assert source == ''


def test_clear_sentinel_menghapus_dan_strip_whitespace(cred_engine, monkeypatch):
    # Test ini mengasumsikan tidak ada fallback env (lihat komentar di bawah);
    # load_dotenv dari backend.db.session bisa men-set SMTP_PASS dari .env asli.
    monkeypatch.delenv('SMTP_PASS', raising=False)
    with cred_engine.begin() as conn:
        status = credentials_service.save_credentials(conn, {
            'smtp_pass': '  rahasia  ',
            'smtp_host': 'smtp.example.com',
        })
    by_key = {c['key']: c for c in status}
    assert by_key['smtp_pass']['set'] is True
    assert by_key['smtp_pass']['source'] == 'db'
    assert by_key['smtp_host']['set'] is True

    with cred_engine.begin() as conn:
        status = credentials_service.save_credentials(conn, {'smtp_pass': '__CLEAR__'})
    by_key = {c['key']: c for c in status}
    assert by_key['smtp_pass']['set'] is False
    # nilai kosong di DB → fallback env (tidak diset di test ini) → source env/None, bukan db
    assert by_key['smtp_pass']['source'] != 'db'


def test_get_status_masking_secret(cred_engine, monkeypatch):
    monkeypatch.setenv('SAGANSA_PRESENCE_TOKEN', 'env-token')
    with cred_engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO app_settings (setting_key, setting_value) VALUES ('smtp_host', 'smtp.example.com')"
        ))
    status = credentials_service.get_status(cred_engine.connect())
    by_key = {c['key']: c for c in status}

    for key in SECRET_KEYS:
        assert 'value' not in by_key[key], f'secret {key} tidak boleh punya value'
    assert by_key['smtp_host']['value'] == 'smtp.example.com'
    assert by_key['sagansa_presence_token']['set'] is True
    assert by_key['sagansa_presence_token']['source'] == 'env'
    # tiap kredensial punya metadata UI
    assert by_key['sagansa_presence_token']['group'] == 'sagansa'
    assert by_key['ai_api_key']['group'] == 'ai'
    assert by_key['smtp_pass']['test'] == 'smtp'
    assert by_key['integration_api_key']['test'] is None


def test_get_credential_value_fail_soft_tanpa_db(monkeypatch):
    monkeypatch.setattr(db_session, 'get_db_engine', lambda: (None, 'db down'))
    monkeypatch.setenv('SAGANSA_STOCK_MONITORING_TOKEN', 'env-tok')
    assert credentials_service.get_credential_value('sagansa_stock_monitoring_token') == 'env-tok'


def test_get_credential_value_db_priority_via_short_conn(cred_engine, monkeypatch):
    monkeypatch.setattr(db_session, 'get_db_engine', lambda: (cred_engine, None))
    monkeypatch.setenv('SAGANSA_PRESENCE_TOKEN', 'env-token')
    with cred_engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO app_settings (setting_key, setting_value) VALUES ('sagansa_presence_token', 'db-token')"
        ))
    assert credentials_service.get_credential_value('sagansa_presence_token') == 'db-token'


def test_get_credential_value_fail_soft_tabel_hilang(monkeypatch):
    engine = create_engine('sqlite:///:memory:')  # tanpa tabel app_settings
    monkeypatch.setattr(db_session, 'get_db_engine', lambda: (engine, None))
    monkeypatch.setenv('SAGANSA_PRESENCE_TOKEN', 'env-tok')
    assert credentials_service.get_credential_value('sagansa_presence_token') == 'env-tok'
    engine.dispose()


def test_unknown_key_raise():
    with pytest.raises(ValueError):
        credentials_service.get_credential_value('bukan_kredensial')
    with pytest.raises(ValueError):
        credentials_service.save_credentials(None, {'bukan_kredensial': 'x'})
