import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash

# Pastikan admin_backend/ ada di sys.path sebelum import server/backend.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Harus di-set sebelum `from server import app` (server membaca SECRET_KEY saat import).
os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('FLASK_ENV', 'development')
# Paksa mode dev mailer di semua test (link reset ditulis ke log, bukan dikirim).
os.environ.pop('SMTP_HOST', None)


def _create_schema(engine):
    with engine.begin() as conn:
        conn.execute(text('''CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            display_name TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            credential_version INTEGER NOT NULL DEFAULT 0
        )'''))
        conn.execute(text('''CREATE TABLE password_reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token_hash TEXT NOT NULL UNIQUE,
            expires_at TIMESTAMP NOT NULL,
            used_at TIMESTAMP NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )'''))


@pytest.fixture()
def engine():
    engine = create_engine('sqlite:///:memory:')
    _create_schema(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def app(monkeypatch, engine):
    from backend.routes import auth_bp as auth_bp_module
    monkeypatch.setattr(auth_bp_module, 'require_db_engine', lambda: engine)
    # Reset semua state module-level antar test.
    auth_bp_module._failed_logins.clear()
    if hasattr(auth_bp_module, '_forgot_requests'):
        auth_bp_module._forgot_requests.clear()
    auth_bp_module._active_user_cache.clear()
    from server import app as flask_app
    flask_app.config['TESTING'] = True
    yield flask_app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def make_user(engine):
    def _make(email='admin@example.com', password='password123', display_name='Admin', is_active=1):
        with engine.begin() as conn:
            result = conn.execute(
                text(
                    'INSERT INTO users (email, password_hash, display_name, is_active) '
                    'VALUES (:email, :password_hash, :display_name, :is_active)'
                ),
                {
                    'email': email.strip().lower(),
                    'password_hash': generate_password_hash(password),
                    'display_name': display_name,
                    'is_active': is_active,
                },
            )
            return int(result.inserted_primary_key[0])

    return _make
