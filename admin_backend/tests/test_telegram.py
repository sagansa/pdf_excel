"""Test Telegram notifier: fail-soft, tanpa dependency baru (urllib)."""

import json

import pytest

from backend.services.notifications import telegram as telegram_module


@pytest.fixture()
def telegram_env(monkeypatch):
    monkeypatch.setenv('TELEGRAM_BOT_TOKEN', '123456:ABC-DEF')
    monkeypatch.setenv('TELEGRAM_CHAT_ID', '987654321')


@pytest.fixture()
def sent_requests(monkeypatch):
    """Tangkap panggilan urlopen; kembalikan list of (url, payload_dict)."""
    calls = []

    def _fake_urlopen(req, timeout=None):
        calls.append({
            'url': req.full_url,
            'payload': json.loads(req.data.decode('utf-8')),
            'timeout': timeout,
        })

        class _FakeResponse:
            status = 200

            def read(self):
                return b'{"ok": true}'

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        return _FakeResponse()

    monkeypatch.setattr(telegram_module, '_urlopen', _fake_urlopen)
    return calls


@pytest.fixture(autouse=True)
def _no_db(monkeypatch):
    from backend.db import session as db_session
    monkeypatch.setattr(db_session, 'get_db_engine', lambda: (None, 'no db in unit test'))


@pytest.fixture()
def cred_engine():
    from sqlalchemy import create_engine, text as _text

    engine = create_engine('sqlite:///:memory:')
    with engine.begin() as conn:
        conn.execute(_text(
            "CREATE TABLE app_settings (setting_key TEXT PRIMARY KEY, setting_value TEXT)"
        ))
    yield engine
    engine.dispose()


def test_noop_tanpa_env(monkeypatch, sent_requests):
    """Tanpa token/chat_id notifier tidak mengirim apa pun dan tidak error."""
    monkeypatch.delenv('TELEGRAM_BOT_TOKEN', raising=False)
    monkeypatch.delenv('TELEGRAM_CHAT_ID', raising=False)

    sent = telegram_module.notify_import_problem(
        'dbs', 'dbs-nov.pdf', 'parse_failed', detail='format tidak dikenal',
    )
    assert sent is False
    assert sent_requests == []


def test_kirim_notifikasi_masalah_import(telegram_env, sent_requests):
    sent = telegram_module.notify_import_problem(
        'dbs', 'dbs-nov.pdf', 'parse_failed',
        detail='format tidak dikenal',
        email_meta={'email_from': 'digibank@ dbs.example', 'email_subject': 'Statement November'},
    )
    assert sent is True
    assert len(sent_requests) == 1
    call = sent_requests[0]
    assert '123456:ABC-DEF' in call['url']
    assert call['url'].endswith('/sendMessage')
    assert call['payload']['chat_id'] == '987654321'
    text = call['payload']['text']
    assert 'dbs' in text
    assert 'dbs-nov.pdf' in text
    assert 'parse_failed' in text


def test_kirim_notifikasi_statement_hilang(telegram_env, sent_requests):
    sent = telegram_module.notify_missing_statements([
        {'bank_code': 'DBS', 'account_number': '1234567890',
         'display_name': 'digibank ops', 'month': '2026-10'},
        {'bank_code': 'BCA', 'account_number': '9876543210',
         'display_name': '', 'month': '2026-10'},
    ])
    assert sent is True
    text = sent_requests[0]['payload']['text']
    assert 'DBS' in text
    assert 'BCA' in text
    assert '2026-10' in text


def test_fail_soft_saat_network_error(telegram_env, monkeypatch):
    """Kegagalan jaringan tidak boleh melempar exception ke pemanggil."""

    def _explode(req, timeout=None):
        raise RuntimeError('connection refused')

    monkeypatch.setattr(telegram_module, '_urlopen', _explode)
    sent = telegram_module.notify_import_problem('dbs', 'dbs-nov.pdf', 'parse_failed')
    assert sent is False


def test_tidak_kirim_jika_tidak_ada_statement_hilang(telegram_env, sent_requests):
    sent = telegram_module.notify_missing_statements([])
    assert sent is False
    assert sent_requests == []


def test_db_token_menang_atas_env(cred_engine, monkeypatch, sent_requests):
    """Token dari app_settings dipakai lebih dulu daripada env."""
    from sqlalchemy import text as _text
    from backend.db import session as db_session
    from backend.services import credentials as credentials_service

    with cred_engine.begin() as conn:
        conn.execute(_text(
            "INSERT INTO app_settings (setting_key, setting_value) "
            "VALUES ('telegram_bot_token', 'db-token')"
        ))
    monkeypatch.setattr(db_session, 'get_db_engine', lambda: (cred_engine, None))
    monkeypatch.setenv('TELEGRAM_BOT_TOKEN', 'env-token')
    # Chat ID tidak ikut diuji di sini — cukup dari env supaya jalur kirim aktif;
    # yang ditegaskan: TOKEN dari DB menang atas TOKEN dari env.
    monkeypatch.setenv('TELEGRAM_CHAT_ID', 'env-chat-id')

    sent = telegram_module.notify_import_problem('dbs', 'f.pdf', 'parse_failed')
    assert sent is True
    assert 'db-token' in sent_requests[0]['url']
    assert 'env-token' not in sent_requests[0]['url']
