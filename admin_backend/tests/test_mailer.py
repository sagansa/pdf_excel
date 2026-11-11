import logging

import pytest

from backend.services import mailer


@pytest.fixture(autouse=True)
def _no_db(monkeypatch):
    from backend.db import session as db_session
    monkeypatch.setattr(db_session, 'get_db_engine', lambda: (None, 'no db in unit test'))


def test_dev_mode_logs_reset_link_when_smtp_host_missing(caplog, monkeypatch):
    monkeypatch.delenv('SMTP_HOST', raising=False)

    with caplog.at_level(logging.WARNING, logger='backend.services.mailer'):
        mailer.send_reset_email('admin@example.com', 'http://x/reset-password?token=abc', 'Admin')

    assert 'http://x/reset-password?token=abc' in caplog.text
    assert 'admin@example.com' in caplog.text


def test_send_reset_email_uses_smtp_when_configured(monkeypatch):
    monkeypatch.setenv('SMTP_HOST', 'smtp.example.com')
    monkeypatch.setenv('SMTP_PORT', '587')
    monkeypatch.setenv('SMTP_USER', 'noreply@example.com')
    monkeypatch.setenv('SMTP_PASS', 'secret')
    monkeypatch.delenv('SMTP_FROM', raising=False)
    monkeypatch.setenv('SMTP_USE_TLS', 'true')

    sent = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout=None):
            sent['host'] = host
            sent['port'] = port

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def starttls(self):
            sent['starttls'] = True

        def login(self, user, password):
            sent['login'] = (user, password)

        def send_message(self, msg):
            sent['msg'] = msg

    monkeypatch.setattr(mailer.smtplib, 'SMTP', FakeSMTP)

    mailer.send_reset_email('admin@example.com', 'http://x/reset-password?token=abc', 'Admin')

    assert sent['host'] == 'smtp.example.com'
    assert sent['port'] == 587
    assert sent['starttls'] is True
    assert sent['login'] == ('noreply@example.com', 'secret')
    assert str(sent['msg']['To']) == 'admin@example.com'
    assert str(sent['msg']['From']) == 'noreply@example.com'
    assert 'http://x/reset-password?token=abc' in sent['msg'].get_content()


def test_use_tls_can_be_disabled(monkeypatch):
    monkeypatch.setenv('SMTP_HOST', 'smtp.example.com')
    monkeypatch.delenv('SMTP_USER', raising=False)
    monkeypatch.setenv('SMTP_USE_TLS', 'false')
    assert mailer.get_smtp_config()['use_tls'] is False


def test_get_smtp_config_db_priority(monkeypatch):
    """Nilai di app_settings menang atas env (conn diberikan pemanggil)."""
    from sqlalchemy import create_engine, text

    engine = create_engine('sqlite:///:memory:')
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE app_settings (setting_key TEXT PRIMARY KEY, setting_value TEXT)"
        ))
        conn.execute(text(
            "INSERT INTO app_settings (setting_key, setting_value) VALUES ('smtp_host', 'db.example.com')"
        ))
    monkeypatch.setenv('SMTP_HOST', 'env.example.com')

    with engine.connect() as conn:
        config = mailer.get_smtp_config(conn=conn)
    assert config['host'] == 'db.example.com'
    engine.dispose()
