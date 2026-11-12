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
    'sagansa_api_token',
    'telegram_bot_token',
    'telegram_chat_id',
    'smtp_host', 'smtp_port', 'smtp_user', 'smtp_pass', 'smtp_from', 'smtp_use_tls',
    'integration_api_key',
    'ai_api_key',
}

SECRET_KEYS = {
    'sagansa_api_token', 'telegram_bot_token',
    'smtp_pass', 'integration_api_key', 'ai_api_key',
}

# Semua nama env Sagansa (baru + legacy) — .env asli bisa memuat nama lama.
SAGANSA_ENV_NAMES = (
    'SAGANSA_API_TOKEN',
    'SAGANSA_PRESENCE_TOKEN', 'SAGANSA_REMAINING_STORAGE_TOKEN',
    'SAGANSA_STOCK_MONITORING_TOKEN', 'SAGANSA_SALES_BY_DATE_TOKEN',
    'SAGANSA_STOCK_COMPARISON_TOKEN',
)


@pytest.fixture()
def no_sagansa_env(monkeypatch):
    """Hapus semua env Sagansa supaya resolusi tidak jatuh ke .env asli."""
    for name in SAGANSA_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)


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
    monkeypatch.setenv('SAGANSA_API_TOKEN', 'env-token')
    with cred_engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO app_settings (setting_key, setting_value) VALUES ('sagansa_api_token', 'db-token')"
        ))
    with cred_engine.connect() as conn:
        value, source = credentials_service.get_credential(conn, 'sagansa_api_token')
    assert value == 'db-token'
    assert source == 'db'


def test_env_utama_menang_atas_env_legacy(cred_engine, monkeypatch):
    monkeypatch.setenv('SAGANSA_API_TOKEN', 'env-baru')
    monkeypatch.setenv('SAGANSA_PRESENCE_TOKEN', 'env-lama')
    with cred_engine.connect() as conn:
        value, source = credentials_service.get_credential(conn, 'sagansa_api_token')
    assert value == 'env-baru'
    assert source == 'env'


def test_env_legacy_dipakai_saat_env_utama_kosong(cred_engine, monkeypatch, no_sagansa_env):
    """Deployment lama dengan env per-fitur tetap jalan tanpa ubah apa pun."""
    monkeypatch.setenv('SAGANSA_SALES_BY_DATE_TOKEN', 'env-legacy')
    with cred_engine.connect() as conn:
        value, source = credentials_service.get_credential(conn, 'sagansa_api_token')
    assert value == 'env-legacy'
    assert source == 'env'


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
    monkeypatch.setenv('SAGANSA_API_TOKEN', 'env-token')
    with cred_engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO app_settings (setting_key, setting_value) VALUES ('smtp_host', 'smtp.example.com')"
        ))
    status = credentials_service.get_status(cred_engine.connect())
    by_key = {c['key']: c for c in status}

    for key in SECRET_KEYS:
        assert 'value' not in by_key[key], f'secret {key} tidak boleh punya value'
    assert by_key['smtp_host']['value'] == 'smtp.example.com'
    assert by_key['sagansa_api_token']['set'] is True
    assert by_key['sagansa_api_token']['source'] == 'env'
    # tiap kredensial punya metadata UI
    assert by_key['sagansa_api_token']['group'] == 'sagansa'
    assert by_key['ai_api_key']['group'] == 'ai'
    assert by_key['smtp_pass']['test'] == 'smtp'
    assert by_key['integration_api_key']['test'] is None


def test_get_credential_value_fallback_env_legacy_tanpa_db(monkeypatch, no_sagansa_env):
    """Tanpa DB: kunci sagansa_api_token jatuh ke env legacy yang terisi."""
    monkeypatch.setattr(db_session, 'get_db_engine', lambda: (None, 'db down'))
    monkeypatch.setenv('SAGANSA_STOCK_MONITORING_TOKEN', 'env-tok')
    assert credentials_service.get_credential_value('sagansa_api_token') == 'env-tok'


def test_get_credential_value_db_priority_via_short_conn(cred_engine, monkeypatch):
    monkeypatch.setattr(db_session, 'get_db_engine', lambda: (cred_engine, None))
    monkeypatch.setenv('SAGANSA_API_TOKEN', 'env-token')
    with cred_engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO app_settings (setting_key, setting_value) VALUES ('sagansa_api_token', 'db-token')"
        ))
    assert credentials_service.get_credential_value('sagansa_api_token') == 'db-token'


def test_get_credential_value_fail_soft_tabel_hilang(monkeypatch):
    engine = create_engine('sqlite:///:memory:')  # tanpa tabel app_settings
    monkeypatch.setattr(db_session, 'get_db_engine', lambda: (engine, None))
    monkeypatch.setenv('SAGANSA_API_TOKEN', 'env-tok')
    assert credentials_service.get_credential_value('sagansa_api_token') == 'env-tok'
    engine.dispose()


def test_unknown_key_raise():
    with pytest.raises(ValueError):
        credentials_service.get_credential_value('bukan_kredensial')
    with pytest.raises(ValueError):
        credentials_service.save_credentials(None, {'bukan_kredensial': 'x'})


# ===== Test handler koneksi (Task 2) =====

from urllib.error import HTTPError, URLError


def test_run_test_sagansa_sukses(cred_engine, monkeypatch, no_sagansa_env):
    monkeypatch.setattr(db_session, 'get_db_engine', lambda: (cred_engine, None))
    calls = []

    def _fake_urlopen(req, timeout=None):
        calls.append({'url': req.full_url, 'auth': req.headers.get('Authorization')})
        class _Resp:
            status = 200
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self):
                return b'{"data": []}'
        return _Resp()

    monkeypatch.setattr(credentials_service.urlrequest, 'urlopen', _fake_urlopen)
    ok, message = credentials_service.run_test('sagansa_api_token', value='tok-123')
    assert ok is True
    assert 'superadmin.sagansa.id/api/presences' in calls[0]['url']
    assert 'per_page=1' in calls[0]['url']
    assert calls[0]['auth'] == 'Bearer tok-123'
    assert 'tok-123' not in message  # nilai token tidak bocor ke pesan


def test_run_test_sagansa_401_token_ditolak(cred_engine, monkeypatch):
    monkeypatch.setattr(db_session, 'get_db_engine', lambda: (cred_engine, None))

    def _fake_urlopen(req, timeout=None):
        raise HTTPError(req.full_url, 401, 'Unauthorized', hdrs=None, fp=None)

    monkeypatch.setattr(credentials_service.urlrequest, 'urlopen', _fake_urlopen)
    ok, message = credentials_service.run_test('sagansa_api_token', value='salah')
    assert ok is False
    assert '401' in message
    assert 'salah' not in message


def test_run_test_sagansa_token_kosong(cred_engine, monkeypatch, no_sagansa_env):
    monkeypatch.setattr(db_session, 'get_db_engine', lambda: (cred_engine, None))
    ok, message = credentials_service.run_test('sagansa_api_token')
    assert ok is False
    assert 'belum diisi' in message


def test_run_test_telegram_sukses(cred_engine, monkeypatch):
    monkeypatch.setattr(db_session, 'get_db_engine', lambda: (cred_engine, None))
    calls = []

    def _fake_urlopen(req, timeout=None):
        calls.append({'url': req.full_url, 'payload': req.data.decode('utf-8')})
        class _Resp:
            status = 200
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self):
                return b'{"ok": true}'
        return _Resp()

    monkeypatch.setattr(credentials_service.urlrequest, 'urlopen', _fake_urlopen)
    ok, message = credentials_service.run_test(
        'telegram_bot_token', value='123:ABC', extra={'telegram_chat_id': '98765'})
    assert ok is True
    assert calls[0]['url'].startswith('https://api.telegram.org/bot123:ABC/sendMessage')
    assert '98765' in calls[0]['payload']


def test_run_test_telegram_chat_id_dari_form_belum_diisi(cred_engine, monkeypatch):
    monkeypatch.setattr(db_session, 'get_db_engine', lambda: (cred_engine, None))
    ok, message = credentials_service.run_test('telegram_bot_token', value='123:ABC')
    assert ok is False
    assert 'Chat ID' in message


def test_run_test_smtp_sukses(cred_engine, monkeypatch):
    monkeypatch.setattr(db_session, 'get_db_engine', lambda: (cred_engine, None))
    sent = {}

    class _FakeSMTP:
        def __init__(self, host, port, timeout=None):
            sent['host'], sent['port'] = host, port
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def starttls(self):
            sent['tls'] = True
        def login(self, user, password):
            sent['login'] = (user, password)

    monkeypatch.setattr(credentials_service.smtplib, 'SMTP', _FakeSMTP)
    ok, message = credentials_service.run_test('smtp_pass', value='secret', extra={
        'smtp_host': 'smtp.example.com', 'smtp_port': '587',
        'smtp_user': 'noreply@example.com', 'smtp_use_tls': 'true',
    })
    assert ok is True
    assert sent['host'] == 'smtp.example.com'
    assert sent['login'] == ('noreply@example.com', 'secret')


def test_run_test_smtp_host_kosong(cred_engine, monkeypatch):
    monkeypatch.setattr(db_session, 'get_db_engine', lambda: (cred_engine, None))
    # .env asli ikut ke-load (load_dotenv) dan men-set SMTP_HOST — hapus agar
    # resolusi tidak jatuh ke env dan test tidak menyentuh SMTP sungguhan.
    monkeypatch.delenv('SMTP_HOST', raising=False)
    ok, message = credentials_service.run_test('smtp_pass', value='secret')
    assert ok is False
    assert 'host' in message.lower()


def test_run_test_key_tanpa_handler(cred_engine):
    ok, message = credentials_service.run_test('integration_api_key')
    assert ok is False
    assert 'tidak punya test' in message


def test_run_test_key_tak_dikenal():
    with pytest.raises(ValueError):
        credentials_service.run_test('bukan_kredensial')


def test_run_test_exception_tak_bocorkan_secret(cred_engine, monkeypatch):
    """Catch-all run_test tidak boleh menyertakan teks exception di pesan.

    Teks exception (mis. repr URLError berisi URL lengkap dengan token) bisa
    memuat secret — pesan balikan harus generik dan log hanya tipe exception.
    """

    def _handler_meledak(key, value, extra):
        raise RuntimeError('token super-rahasia')

    monkeypatch.setattr(credentials_service, '_TEST_HANDLERS', {'sagansa': _handler_meledak})
    ok, message = credentials_service.run_test('sagansa_api_token', value='tok-apa-saja')
    assert ok is False
    assert 'super-rahasia' not in message
