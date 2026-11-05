# Akun Email + Forgot Password — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ganti identifier login dari username ke email, dan tambahkan alur forgot-password (email berisi link reset token sekali pakai, TTL 30 menit).

**Architecture:** Mengikuti pola auth yang ada (`auth_bp.py`, throttling in-memory, migrasi SQL bernomor). Token reset disimpan sebagai SHA-256 hash di tabel `password_reset_tokens`. Mailer SMTP via stdlib `smtplib`, mode dev menulis link ke log. Sesi lama dimatikan setelah reset via `credential_version`.

**Tech Stack:** Flask, SQLAlchemy raw SQL (`text()`), MySQL (migrasi) + SQLite in-memory (test), pytest, Vue 3 + Pinia + vue-router, axios.

**Spec:** `docs/superpowers/specs/2026-11-05-email-accounts-forgot-password-design.md`

## Global Constraints

- Tidak ada dependency runtime Python baru (`smtplib`, `hashlib`, `secrets`, `email.message` semua stdlib); pytest hanya masuk `requirements-dev.txt`.
- UI frontend bahasa Inggris, konsisten dengan `LoginView.vue` yang ada.
- Email selalu disimpan lowercase (`normalize`: trim + lower) di semua titik input.
- Token reset: `secrets.token_urlsafe(32)`, disimpan sebagai SHA-256 hex, TTL 30 menit, sekali pakai.
- Rate limit forgot-password: 3 permintaan per (IP, email) per 15 menit, dihitung untuk SETIAP permintaan (termasuk yang sukses).
- `POST /api/auth/forgot-password` SELALU 200 dengan pesan generis (anti email-enumeration); hanya rate limit yang bisa 429.
- Semua perintah test dijalankan dari `admin_backend/`: `cd admin_backend && venv/bin/python -m pytest ...`
- Build frontend dicek dengan `cd admin_frontend && npm run build`.
- Commit message mengikuti gaya repo (bahasa Indonesia ringkas, prefix `feat:`/`test:`/`docs:`).

---

### Task 1: Test scaffolding (pytest + fixtures)

**Files:**
- Create: `admin_backend/requirements-dev.txt`
- Create: `admin_backend/tests/conftest.py`
- Test: `admin_backend/tests/test_auth.py`

**Interfaces:**
- Consumes: `server.app` (aplikasi Flask asli dengan guard global), `backend.routes.auth_bp` (monkeypatch target `require_db_engine`).
- Produces: fixtures `engine` (SQLite in-memory dengan skema `users` + `password_reset_tokens`), `app`, `client`, `make_user(email, password, display_name, is_active) -> user_id`. Task berikutnya memakai fixtures ini tanpa mendefinisikan ulang.

- [ ] **Step 1: Install pytest ke venv + buat requirements-dev.txt**

```bash
cd admin_backend && venv/bin/pip install 'pytest>=8.0.0'
```

File `admin_backend/requirements-dev.txt`:

```
pytest>=8.0.0
```

- [ ] **Step 2: Buat conftest.py**

File `admin_backend/tests/conftest.py` (lengkap):

```python
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
```

- [ ] **Step 3: Tulis smoke test (harus pass langsung — memverifikasi fixtures, bukan fitur baru)**

File `admin_backend/tests/test_auth.py`:

```python
def test_me_requires_authentication(client):
    response = client.get('/api/auth/me')
    assert response.status_code == 401
    assert response.get_json()['code'] == 'not_authenticated'
```

- [ ] **Step 4: Run test**

Run: `cd admin_backend && venv/bin/python -m pytest tests/test_auth.py -v`
Expected: 1 PASSED. Kalau gagal dengan error import `server`, pastikan `.env` ada (server membacanya via load_dotenv) dan `SECRET_KEY` ter-set oleh conftest.

- [ ] **Step 5: Commit**

```bash
git add admin_backend/requirements-dev.txt admin_backend/tests/conftest.py admin_backend/tests/test_auth.py
git commit -m "test: scaffolding pytest untuk auth (sqlite in-memory + app fixtures)"
```

---

### Task 2: Migrasi 071 + create_user.py versi email

**Files:**
- Create: `admin_backend/database/migrations/071_email_accounts.sql`
- Modify: `admin_backend/scripts/create_user.py` (seluruh file diganti)
- Test: `admin_backend/tests/test_create_user.py`

**Interfaces:**
- Consumes: pola migrasi bernomor `database/migrations/NNN_*.sql` (auto-ditemukan `database/migration_index.py`).
- Produces: tabel `users` (kolom `email`, `credential_version`) dan `password_reset_tokens`; fungsi `normalize_email(value) -> str` dan `is_valid_email(value) -> bool` di `scripts/create_user.py`.

- [ ] **Step 1: Tulis failing test**

File `admin_backend/tests/test_create_user.py`:

```python
from scripts.create_user import is_valid_email, normalize_email


def test_normalize_email_trims_and_lowercases():
    assert normalize_email('  Admin@Example.COM  ') == 'admin@example.com'


def test_is_valid_email_accepts_normal_addresses():
    assert is_valid_email('admin@sagansa.com')
    assert is_valid_email('a.b+tag@sub.domain.co.id')


def test_is_valid_email_rejects_garbage():
    assert not is_valid_email('admin')
    assert not is_valid_email('admin@')
    assert not is_valid_email('admin@localhost')
    assert not is_valid_email('admin example.com')
    assert not is_valid_email('')
```

- [ ] **Step 2: Run test — expect fail**

Run: `cd admin_backend && venv/bin/python -m pytest tests/test_create_user.py -v`
Expected: FAIL `ImportError: cannot import name 'is_valid_email'`

- [ ] **Step 3: Buat file migrasi**

File `admin_backend/database/migrations/071_email_accounts.sql`:

```sql
-- Ganti akun dari username ke email + tabel token reset password.
-- Sesuai design spec: akun lama dibuang, dibuat ulang via scripts/create_user.py.
DROP TABLE IF EXISTS password_reset_tokens;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(128) NOT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    credential_version INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE password_reset_tokens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    token_hash CHAR(64) NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_password_reset_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_password_reset_user (user_id)
);
```

- [ ] **Step 4: Tulis ulang create_user.py**

Ganti seluruh isi `admin_backend/scripts/create_user.py`:

```python
"""Create or reset a login user (email-based) for the esta admin backend.

Usage (from admin_backend/):
    venv/bin/python scripts/create_user.py <email> <display_name>

Prompts for a password (hidden input). If the email already exists,
the password and display name are updated and the account re-activated.
"""
import getpass
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv

load_dotenv(BASE_DIR / '.env')

from sqlalchemy import text
from werkzeug.security import generate_password_hash

from backend.db.session import get_db_engine

MIN_PASSWORD_LENGTH = 8
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def normalize_email(value):
    return str(value or '').strip().lower()


def is_valid_email(value):
    return bool(EMAIL_RE.match(normalize_email(value)))


def main():
    if len(sys.argv) != 3:
        print(f'Usage: {sys.argv[0]} <email> <display_name>')
        sys.exit(1)

    email = normalize_email(sys.argv[1])
    display_name = sys.argv[2].strip()
    if not is_valid_email(email):
        print('Email tidak valid.')
        sys.exit(1)
    if not display_name:
        print('Display name tidak boleh kosong.')
        sys.exit(1)

    password = getpass.getpass(f'Password untuk {email}: ')
    confirm = getpass.getpass('Konfirmasi password: ')
    if len(password) < MIN_PASSWORD_LENGTH:
        print(f'Password minimal {MIN_PASSWORD_LENGTH} karakter.')
        sys.exit(1)
    if password != confirm:
        print('Password tidak cocok.')
        sys.exit(1)

    engine, error = get_db_engine()
    if engine is None:
        print(f'Database tidak tersedia: {error}')
        sys.exit(1)

    password_hash = generate_password_hash(password)
    with engine.begin() as conn:
        existing = conn.execute(
            text('SELECT id FROM users WHERE email = :email'),
            {'email': email},
        ).first()
        if existing:
            conn.execute(
                text(
                    'UPDATE users SET password_hash = :password_hash, '
                    'display_name = :display_name, is_active = 1 WHERE id = :id'
                ),
                {'password_hash': password_hash, 'display_name': display_name, 'id': existing[0]},
            )
            print(f'User {email} diperbarui (password direset, akun diaktifkan).')
        else:
            conn.execute(
                text(
                    'INSERT INTO users (email, password_hash, display_name) '
                    'VALUES (:email, :password_hash, :display_name)'
                ),
                {'email': email, 'password_hash': password_hash, 'display_name': display_name},
            )
            print(f'User {email} dibuat.')


if __name__ == '__main__':
    main()
```

- [ ] **Step 5: Run test — expect pass**

Run: `cd admin_backend && venv/bin/python -m pytest tests/test_create_user.py tests/test_auth.py -v`
Expected: semua PASSED

- [ ] **Step 6: Verifikasi migrasi terdeteksi oleh migration index**

Run: `cd admin_backend && venv/bin/python -c "from database.migration_index import list_mysql_migrations; print(list_mysql_migrations()[-1].name)"`
Expected output: `071_email_accounts.sql`

- [ ] **Step 7: Commit**

```bash
git add admin_backend/database/migrations/071_email_accounts.sql admin_backend/scripts/create_user.py admin_backend/tests/test_create_user.py
git commit -m "feat: migrasi 071 akun email + tabel token reset; create_user pakai email"
```

---

### Task 3: Login by email di auth_bp

**Files:**
- Modify: `admin_backend/backend/routes/auth_bp.py` (bagian imports, `_session_user`, `_fetch_user_by_column`, `login`, `me`)
- Test: `admin_backend/tests/test_auth.py`

**Interfaces:**
- Consumes: fixtures Task 1.
- Produces: `POST /api/auth/login` menerima `{"email": ..., "password": ...}`; sesi menyimpan `credential_version`; `GET /api/auth/me` mengembalikan `{"user": {"id", "email", "display_name"}}`; `_session_user(row) -> {"id": int, "email": str, "display_name": str}`; `_normalize_email(value) -> str`.

- [ ] **Step 1: Tulis failing tests** (tambahkan ke `admin_backend/tests/test_auth.py`)

```python
def test_login_with_email_succeeds(client, make_user):
    make_user(email='admin@example.com', password='password123')

    response = client.post('/api/auth/login', json={
        'email': 'admin@example.com', 'password': 'password123',
    })

    assert response.status_code == 200
    assert response.get_json()['user'] == {
        'id': 1, 'email': 'admin@example.com', 'display_name': 'Admin',
    }


def test_login_email_is_case_insensitive(client, make_user):
    make_user(email='admin@example.com', password='password123')

    response = client.post('/api/auth/login', json={
        'email': '  ADMIN@Example.COM ', 'password': 'password123',
    })

    assert response.status_code == 200


def test_login_wrong_password_rejected(client, make_user):
    make_user(email='admin@example.com', password='password123')

    response = client.post('/api/auth/login', json={
        'email': 'admin@example.com', 'password': 'wrongpassword',
    })

    assert response.status_code == 401
    assert response.get_json()['code'] == 'invalid_credentials'


def test_me_returns_email_after_login(client, make_user):
    make_user(email='admin@example.com', password='password123')
    client.post('/api/auth/login', json={
        'email': 'admin@example.com', 'password': 'password123',
    })

    response = client.get('/api/auth/me')

    assert response.status_code == 200
    assert response.get_json()['user']['email'] == 'admin@example.com'
```

- [ ] **Step 2: Run test — expect fail**

Run: `cd admin_backend && venv/bin/python -m pytest tests/test_auth.py -v`
Expected: 4 FAILED (login mengirim `username`, bukan `email`)

- [ ] **Step 3: Implementasi**

Di `admin_backend/backend/routes/auth_bp.py`:

3a. Tambah helper setelah `_client_ip`:

```python
def _normalize_email(value):
    return str(value or '').strip().lower()
```

3b. Ganti `_session_user`:

```python
def _session_user(row):
    return {
        'id': int(row['id']),
        'email': row['email'],
        'display_name': row['display_name'],
    }
```

3c. Di `_fetch_user_by_column`, ganti SELECT jadi:

```python
'SELECT id, email, display_name, password_hash, is_active, credential_version '
f'FROM users WHERE {column} = :value'
```

3d. Ganti isi `login()`:

```python
@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    payload = request.get_json(silent=True) or {}
    email = _normalize_email(payload.get('email'))
    password = str(payload.get('password') or '')
    if not email or not password:
        raise BadRequestError('Email and password are required', code='credentials_missing')

    throttle_key = (_client_ip(), email)
    if _too_many_attempts(throttle_key):
        raise TooManyRequestsError(
            'Too many failed login attempts. Try again in a few minutes.'
        )

    user = _fetch_user_by_column('email', email)
    if not _is_active(user) or not check_password_hash(user['password_hash'], password):
        _record_failed_attempt(throttle_key)
        raise UnauthorizedError('Invalid email or password', code='invalid_credentials')

    _failed_logins.pop(throttle_key, None)
    session.clear()
    session.permanent = True
    session['user_id'] = int(user['id'])
    session['credential_version'] = int(user['credential_version'])
    return jsonify({'user': _session_user(user)})
```

- [ ] **Step 4: Run test — expect pass**

Run: `cd admin_backend && venv/bin/python -m pytest tests/test_auth.py -v`
Expected: semua PASSED

- [ ] **Step 5: Commit**

```bash
git add admin_backend/backend/routes/auth_bp.py admin_backend/tests/test_auth.py
git commit -m "feat: login by email (case-insensitive) + credential_version di sesi"
```

---

### Task 4: Modul mailer + .env.example

**Files:**
- Create: `admin_backend/backend/services/mailer.py`
- Modify: `admin_backend/.env.example`
- Test: `admin_backend/tests/test_mailer.py`

**Interfaces:**
- Consumes: env `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`, `SMTP_USE_TLS`.
- Produces: `get_smtp_config() -> dict{host, port, user, password, from, use_tls}` dan `send_reset_email(to_email: str, reset_link: str, display_name: str = '') -> None`. Tanpa `SMTP_HOST`: tidak mengirim apa pun, menulis link ke log level WARNING.

- [ ] **Step 1: Tulis failing tests**

File `admin_backend/tests/test_mailer.py`:

```python
import logging

from backend.services import mailer


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
```

- [ ] **Step 2: Run test — expect fail**

Run: `cd admin_backend && venv/bin/python -m pytest tests/test_mailer.py -v`
Expected: FAIL `ModuleNotFoundError: No module named 'backend.services.mailer'`

- [ ] **Step 3: Implementasi mailer**

File `admin_backend/backend/services/mailer.py`:

```python
"""SMTP sender for transactional emails (currently: password reset).

Dev fallback: when SMTP_HOST is not configured the message is not sent;
the reset link is written to the log instead so the flow stays testable.
"""
import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)


def get_smtp_config():
    return {
        'host': os.environ.get('SMTP_HOST', '').strip(),
        'port': int(os.environ.get('SMTP_PORT', '587')),
        'user': os.environ.get('SMTP_USER', '').strip(),
        'password': os.environ.get('SMTP_PASS', ''),
        'from': os.environ.get('SMTP_FROM', '').strip(),
        'use_tls': os.environ.get('SMTP_USE_TLS', 'true').strip().lower()
        not in {'0', 'false', 'no'},
    }


def send_reset_email(to_email, reset_link, display_name=''):
    config = get_smtp_config()
    if not config['host']:
        logger.warning(
            'SMTP_HOST not set; reset link for %s logged instead of emailed: %s',
            to_email, reset_link,
        )
        return

    msg = EmailMessage()
    msg['Subject'] = 'Reset your StatementX password'
    msg['From'] = config['from'] or config['user']
    msg['To'] = to_email
    msg.set_content(
        f'Hello {display_name or to_email},\n\n'
        'We received a request to reset your password.\n\n'
        'Open the link below to choose a new password (valid for 30 minutes):\n'
        f'{reset_link}\n\n'
        'If you did not request this, you can ignore this email.\n'
    )

    with smtplib.SMTP(config['host'], config['port'], timeout=15) as server:
        if config['use_tls']:
            server.starttls()
        if config['user']:
            server.login(config['user'], config['password'])
        server.send_message(msg)
```

- [ ] **Step 4: Tambah variabel SMTP ke .env.example**

Tambahkan di akhir `admin_backend/.env.example`:

```
# SMTP for password reset emails. Leave SMTP_HOST empty in dev: reset links
# are written to the server log instead of being emailed.
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASS=
SMTP_FROM=
SMTP_USE_TLS=true
# Optional: override the base URL used in reset links (defaults to request origin)
APP_BASE_URL=
```

- [ ] **Step 5: Run test — expect pass**

Run: `cd admin_backend && venv/bin/python -m pytest tests/test_mailer.py -v`
Expected: 3 PASSED

- [ ] **Step 6: Commit**

```bash
git add admin_backend/backend/services/mailer.py admin_backend/.env.example admin_backend/tests/test_mailer.py
git commit -m "feat: modul mailer SMTP untuk email reset (+mode dev tulis ke log)"
```

---

### Task 5: Endpoint forgot-password

**Files:**
- Modify: `admin_backend/backend/routes/auth_bp.py` (generalisasi throttle + endpoint baru)
- Modify: `admin_backend/server.py:104` (`PUBLIC_API_PATHS`)
- Test: `admin_backend/tests/test_auth.py`

**Interfaces:**
- Consumes: `send_reset_email` (Task 4), `_normalize_email`, `_is_active`, fixtures Task 1.
- Produces: `POST /api/auth/forgot-password` body `{"email": ...}` → selalu `200 {"ok": true, "message": "If an account exists for that email, a reset link has been sent."}` kecuali 429 (3 permintaan/(IP,email)/15 menit, semua permintaan dihitung). Helper yang digeneralisasi: `_too_many_attempts(key, store, max_attempts, window_seconds) -> bool` dan `_record_attempt(key, store) -> None`. Konstanta: `FORGOT_MAX_ATTEMPTS = 3`, `FORGOT_WINDOW_SECONDS = 900`, `RESET_TOKEN_TTL_MINUTES = 30`, `MIN_PASSWORD_LENGTH = 8`.

- [ ] **Step 1: Tulis failing tests** (tambahkan ke `tests/test_auth.py`)

```python
import logging

from sqlalchemy import text


def _token_rows(engine, user_id):
    with engine.connect() as conn:
        return conn.execute(
            text('SELECT token_hash FROM password_reset_tokens WHERE user_id = :uid'),
            {'uid': user_id},
        ).fetchall()


def test_forgot_password_returns_generic_success_for_unknown_email(client):
    response = client.post('/api/auth/forgot-password', json={'email': 'nobody@example.com'})

    assert response.status_code == 200
    assert response.get_json() == {
        'ok': True,
        'message': 'If an account exists for that email, a reset link has been sent.',
    }


def test_forgot_password_creates_hashed_token_and_logs_link(client, make_user, engine, caplog):
    user_id = make_user(email='admin@example.com')

    with caplog.at_level(logging.WARNING, logger='backend.services.mailer'):
        response = client.post('/api/auth/forgot-password', json={'email': 'admin@example.com'})

    assert response.status_code == 200
    rows = _token_rows(engine, user_id)
    assert len(rows) == 1
    # Disimpan sebagai SHA-256 hex (64 char), bukan token mentah.
    assert len(rows[0][0]) == 64
    # Token mentah hanya muncul di link yang di-log (mode dev mailer).
    assert '/reset-password?token=' in caplog.text


def test_forgot_password_replaces_previous_tokens(client, make_user, engine):
    user_id = make_user(email='admin@example.com')
    client.post('/api/auth/forgot-password', json={'email': 'admin@example.com'})
    client.post('/api/auth/forgot-password', json={'email': 'ADMIN@example.com'})

    assert len(_token_rows(engine, user_id)) == 1


def test_forgot_password_ignores_inactive_user(client, make_user, engine):
    user_id = make_user(email='ghost@example.com', is_active=0)

    response = client.post('/api/auth/forgot-password', json={'email': 'ghost@example.com'})

    assert response.status_code == 200
    assert _token_rows(engine, user_id) == []


def test_forgot_password_rate_limited_after_three_requests(client):
    for _ in range(3):
        response = client.post('/api/auth/forgot-password', json={'email': 'nobody@example.com'})
        assert response.status_code == 200

    response = client.post('/api/auth/forgot-password', json={'email': 'nobody@example.com'})
    assert response.status_code == 429
```

- [ ] **Step 2: Run test — expect fail**

Run: `cd admin_backend && venv/bin/python -m pytest tests/test_auth.py -v`
Expected: 5 FAILED (404, endpoint belum ada)

- [ ] **Step 3: Implementasi di auth_bp.py**

3a. Update imports (bagian atas file):

```python
import hashlib
import logging
import os
import secrets
import time
from collections import defaultdict
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request, session
from sqlalchemy import text
from werkzeug.security import check_password_hash, generate_password_hash

from backend.errors import BadRequestError, TooManyRequestsError, UnauthorizedError
from backend.routes.accounting_utils import require_db_engine
from backend.services.mailer import send_reset_email
```

3b. Ganti throttle constants/helpers yang lama (hapus `LOGIN_MAX_ATTEMPTS`/`LOGIN_WINDOW_SECONDS` versi lama, `_too_many_attempts(key)`, `_record_failed_attempt(key)`) dengan versi generalisasi:

```python
# Simple in-memory throttling, keyed per (ip, identifier).
# Sufficient for a single-process gunicorn deployment; no external storage needed.
LOGIN_MAX_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 300
_failed_logins = defaultdict(list)

FORGOT_MAX_ATTEMPTS = 3
FORGOT_WINDOW_SECONDS = 900
_forgot_requests = defaultdict(list)

RESET_TOKEN_TTL_MINUTES = 30
MIN_PASSWORD_LENGTH = 8


def _too_many_attempts(key, store, max_attempts, window_seconds):
    now = time.time()
    attempts = [t for t in store[key] if now - t < window_seconds]
    store[key] = attempts
    return len(attempts) >= max_attempts


def _record_attempt(key, store):
    store[key].append(time.time())
```

3c. Update pemanggil di `login()`:

```python
    throttle_key = (_client_ip(), email)
    if _too_many_attempts(throttle_key, _failed_logins, LOGIN_MAX_ATTEMPTS, LOGIN_WINDOW_SECONDS):
        raise TooManyRequestsError(
            'Too many failed login attempts. Try again in a few minutes.'
        )

    user = _fetch_user_by_column('email', email)
    if not _is_active(user) or not check_password_hash(user['password_hash'], password):
        _record_attempt(throttle_key, _failed_logins)
        raise UnauthorizedError('Invalid email or password', code='invalid_credentials')

    _failed_logins.pop(throttle_key, None)
```

3d. Tambah helper hash + endpoint setelah `login`:

```python
def _hash_token(token):
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


_FORGOT_GENERIC_MESSAGE = 'If an account exists for that email, a reset link has been sent.'


@auth_bp.route('/api/auth/forgot-password', methods=['POST'])
def forgot_password():
    payload = request.get_json(silent=True) or {}
    email = _normalize_email(payload.get('email'))
    if not email:
        raise BadRequestError('Email is required', code='email_missing')

    throttle_key = (_client_ip(), email)
    if _too_many_attempts(throttle_key, _forgot_requests, FORGOT_MAX_ATTEMPTS, FORGOT_WINDOW_SECONDS):
        raise TooManyRequestsError('Too many reset requests. Try again later.')
    _record_attempt(throttle_key, _forgot_requests)

    user = _fetch_user_by_column('email', email)
    if _is_active(user):
        try:
            token = secrets.token_urlsafe(32)
            engine = require_db_engine()
            with engine.begin() as conn:
                conn.execute(
                    text('DELETE FROM password_reset_tokens WHERE user_id = :uid'),
                    {'uid': int(user['id'])},
                )
                conn.execute(
                    text(
                        'INSERT INTO password_reset_tokens (user_id, token_hash, expires_at) '
                        'VALUES (:uid, :token_hash, :expires_at)'
                    ),
                    {
                        'uid': int(user['id']),
                        'token_hash': _hash_token(token),
                        'expires_at': datetime.now() + timedelta(minutes=RESET_TOKEN_TTL_MINUTES),
                    },
                )
            base_url = (os.environ.get('APP_BASE_URL', '').strip() or request.url_root).rstrip('/')
            send_reset_email(email, f'{base_url}/reset-password?token={token}', user['display_name'])
        except Exception:
            # Jangan bocorkan keberadaan akun lewat error pengiriman.
            logger.exception('Failed to process password reset request for %s', email)

    return jsonify({'ok': True, 'message': _FORGOT_GENERIC_MESSAGE})
```

- [ ] **Step 4: Daftarkan endpoint publik di server.py:104**

```python
PUBLIC_API_PATHS = {
    '/api/auth/login',
    '/api/auth/forgot-password',
    '/api/auth/reset-password',
}
```

(`/api/auth/reset-password` didaftarkan sekaligus — endpoint-nya dibuat di Task 6.)

- [ ] **Step 5: Run semua test auth**

Run: `cd admin_backend && venv/bin/python -m pytest tests/test_auth.py -v`
Expected: semua PASSED (test lama + 5 baru)

- [ ] **Step 6: Commit**

```bash
git add admin_backend/backend/routes/auth_bp.py admin_backend/server.py admin_backend/tests/test_auth.py
git commit -m "feat: endpoint forgot-password (token hash SHA-256, TTL 30m, throttle 3/15m)"
```

---

### Task 6: Endpoint reset-password + invalidasi sesi

**Files:**
- Modify: `admin_backend/backend/routes/auth_bp.py` (endpoint baru + cache pop)
- Modify: `admin_backend/server.py` (guard cek `credential_version`)
- Test: `admin_backend/tests/test_auth.py`

**Interfaces:**
- Consumes: `_hash_token`, `MIN_PASSWORD_LENGTH` (Task 5), `generate_password_hash`, fixtures Task 1.
- Produces: `POST /api/auth/reset-password` body `{"token": str, "new_password": str}` → `200 {"ok": true, "message": "Password updated. Please sign in with your new password."}`; error `400 invalid_token` (token salah/kedaluwarsa/terpakai), `400 password_too_short`, `400 reset_fields_missing`. Semua sesi user lain mati segera setelah reset.

- [ ] **Step 1: Tulis failing tests** (tambahkan ke `tests/test_auth.py`)

```python
def _reset_token_from_log(caplog):
    for line in caplog.text.splitlines():
        if '/reset-password?token=' in line:
            return line.rsplit('token=', 1)[1].strip()
    raise AssertionError('reset token not found in logs')


def _request_reset(client, caplog, email='admin@example.com'):
    import logging as _logging
    with caplog.at_level(_logging.WARNING, logger='backend.services.mailer'):
        response = client.post('/api/auth/forgot-password', json={'email': email})
    assert response.status_code == 200
    return _reset_token_from_log(caplog)


def test_reset_password_flow(client, make_user, caplog):
    make_user(email='admin@example.com', password='oldpassword123')
    token = _request_reset(client, caplog)

    response = client.post('/api/auth/reset-password', json={
        'token': token, 'new_password': 'newpassword456',
    })

    assert response.status_code == 200
    # Password lama ditolak, yang baru diterima.
    old = client.post('/api/auth/login', json={'email': 'admin@example.com', 'password': 'oldpassword123'})
    assert old.status_code == 401
    new = client.post('/api/auth/login', json={'email': 'admin@example.com', 'password': 'newpassword456'})
    assert new.status_code == 200


def test_reset_token_is_single_use(client, make_user, caplog):
    make_user(email='admin@example.com', password='oldpassword123')
    token = _request_reset(client, caplog)
    first = client.post('/api/auth/reset-password', json={'token': token, 'new_password': 'newpassword456'})
    assert first.status_code == 200

    second = client.post('/api/auth/reset-password', json={'token': token, 'new_password': 'anotherpass789'})

    assert second.status_code == 400
    assert second.get_json()['code'] == 'invalid_token'


def test_reset_token_expired_is_rejected(client, make_user, engine):
    from datetime import datetime as _dt, timedelta as _td

    make_user(email='admin@example.com', password='oldpassword123')
    from backend.routes.auth_bp import _hash_token
    with engine.begin() as conn:
        conn.execute(
            text(
                'INSERT INTO password_reset_tokens (user_id, token_hash, expires_at) '
                'VALUES (1, :th, :exp)'
            ),
            {'th': _hash_token('expired-token'), 'exp': _dt.now() - _td(minutes=1)},
        )

    response = client.post('/api/auth/reset-password', json={
        'token': 'expired-token', 'new_password': 'newpassword456',
    })

    assert response.status_code == 400
    assert response.get_json()['code'] == 'invalid_token'


def test_reset_password_too_short_rejected(client, make_user, caplog):
    make_user(email='admin@example.com', password='oldpassword123')
    token = _request_reset(client, caplog)

    response = client.post('/api/auth/reset-password', json={
        'token': token, 'new_password': 'short',
    })

    assert response.status_code == 400
    assert response.get_json()['code'] == 'password_too_short'


def test_reset_password_invalidates_other_sessions(app, client, make_user, caplog):
    make_user(email='admin@example.com', password='oldpassword123')
    client.post('/api/auth/login', json={'email': 'admin@example.com', 'password': 'oldpassword123'})
    assert client.get('/api/auth/me').status_code == 200

    other = app.test_client()
    token = _request_reset(other, caplog)
    assert other.post('/api/auth/reset-password', json={
        'token': token, 'new_password': 'newpassword456',
    }).status_code == 200

    # Sesi lama (client pertama) harus mati.
    assert client.get('/api/auth/me').status_code == 401
```

- [ ] **Step 2: Run test — expect fail**

Run: `cd admin_backend && venv/bin/python -m pytest tests/test_auth.py -v`
Expected: 5 FAILED (404/401 untuk reset-password; sesi lama masih hidup)

- [ ] **Step 3: Implementasi endpoint reset di auth_bp.py** (tambahkan setelah `forgot_password`)

```python
@auth_bp.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    payload = request.get_json(silent=True) or {}
    token = str(payload.get('token') or '').strip()
    new_password = str(payload.get('new_password') or '')
    if not token or not new_password:
        raise BadRequestError('Token and new password are required', code='reset_fields_missing')
    if len(new_password) < MIN_PASSWORD_LENGTH:
        raise BadRequestError(
            f'Password must be at least {MIN_PASSWORD_LENGTH} characters', code='password_too_short'
        )

    engine = require_db_engine()
    with engine.begin() as conn:
        row = conn.execute(
            text(
                'SELECT id, user_id FROM password_reset_tokens '
                'WHERE token_hash = :token_hash AND used_at IS NULL AND expires_at > :now'
            ),
            {'token_hash': _hash_token(token), 'now': datetime.now()},
        ).mappings().first()
        if row is None:
            raise BadRequestError('This reset link is invalid or has expired', code='invalid_token')

        conn.execute(
            text(
                'UPDATE users SET password_hash = :password_hash, '
                'credential_version = credential_version + 1 WHERE id = :uid'
            ),
            {'password_hash': generate_password_hash(new_password), 'uid': int(row['user_id'])},
        )
        conn.execute(
            text('UPDATE password_reset_tokens SET used_at = :now WHERE id = :id'),
            {'now': datetime.now(), 'id': int(row['id'])},
        )

    # Buang cache guard agar sesi lama (credential_version beda) mati segera.
    _active_user_cache.pop(int(row['user_id']), None)
    return jsonify({'ok': True, 'message': 'Password updated. Please sign in with your new password.'})
```

- [ ] **Step 4: Guard server.py cek credential_version** (ganti `require_login` di `server.py:107-118`)

```python
@app.before_request
def require_login():
    if request.method == 'OPTIONS':
        return None
    if not request.path.startswith('/api/'):
        return None
    if request.path in PUBLIC_API_PATHS:
        return None
    user = get_user_if_active(session.get('user_id'))
    if user is None or session.get('credential_version') != int(user['credential_version']):
        session.clear()
        return jsonify({'error': 'Authentication required', 'code': 'not_authenticated'}), 401
    return None
```

- [ ] **Step 5: Run test — expect pass**

Run: `cd admin_backend && venv/bin/python -m pytest tests/test_auth.py -v`
Expected: semua PASSED (16 test)

- [ ] **Step 6: Commit**

```bash
git add admin_backend/backend/routes/auth_bp.py admin_backend/server.py admin_backend/tests/test_auth.py
git commit -m "feat: endpoint reset-password (single-use) + invalidasi sesi via credential_version"
```

---

### Task 7: Frontend — login by email

**Files:**
- Modify: `admin_frontend/src/views/LoginView.vue`
- Modify: `admin_frontend/src/stores/auth.js:13`
- Modify: `admin_frontend/src/api/index.js:34-44`
- Modify: `admin_frontend/src/layouts/MainLayout.vue:118,192`

**Interfaces:**
- Consumes: `POST /api/auth/login {"email", "password"}` (Task 3), `authApi` axios instance.
- Produces: `authApi.login(email, password)`, `authApi.forgotPassword(email)`, `authApi.resetPassword(token, newPassword)` (dua terakhir dipakai Task 8); store `auth.login(email, password)`; UI login memakai field email.

- [ ] **Step 1: Update api/index.js** — ganti blok `authApi`:

```javascript
export const authApi = {
  login(email, password) {
    return api.post('/auth/login', { email, password });
  },
  logout() {
    return api.post('/auth/logout');
  },
  me() {
    return api.get('/auth/me');
  },
  forgotPassword(email) {
    return api.post('/auth/forgot-password', { email });
  },
  resetPassword(token, newPassword) {
    return api.post('/auth/reset-password', { token, new_password: newPassword });
  },
};
```

- [ ] **Step 2: Update stores/auth.js** — ganti action `login`:

```javascript
    async login(email, password) {
      const response = await authApi.login(email, password);
      this.user = response.data.user;
      return this.user;
    },
```

- [ ] **Step 3: Update LoginView.vue** — template: label & input username jadi email, error 401 jadi "Invalid email or password", tambah link forgot + notice reset sukses:

Template bagian form (label, input, error, tombol, dan link forgot):

```html
        <div>
          <label for="email" class="block text-xs font-bold text-theme mb-1.5 uppercase tracking-wide">Email</label>
          <input
            id="email"
            v-model="email"
            type="email"
            autocomplete="email"
            class="input-base py-2.5"
            :disabled="isLoading"
            placeholder="you@company.com"
            required
            autofocus
          />
        </div>

        <!-- ... input password tetap ... -->

        <p v-if="resetNotice" class="text-sm text-green-600 dark:text-green-400">{{ resetNotice }}</p>
        <p v-if="error" class="text-sm text-red-500 dark:text-red-400">{{ error }}</p>

        <button
          type="submit"
          class="btn-primary w-full"
          :disabled="isLoading || !email || !password"
        >
          {{ isLoading ? 'Signing in…' : 'Sign In' }}
        </button>

        <div class="text-center">
          <router-link to="/forgot-password" class="text-xs text-muted hover:opacity-80">
            Forgot password?
          </router-link>
        </div>
```

Script setup (versi lengkap, ganti seluruh blok `<script setup>`):

```javascript
import { ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '../stores/auth';

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();

const email = ref('');
const password = ref('');
const isLoading = ref(false);
const error = ref('');
const resetNotice = ref(
  route.query.reset === 'success'
    ? 'Password changed. Please sign in with your new password.'
    : ''
);

const handleSubmit = async () => {
  isLoading.value = true;
  error.value = '';
  try {
    await auth.login(email.value.trim(), password.value);
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/';
    router.push(redirect);
  } catch (err) {
    const status = err.response?.status;
    if (status === 429) {
      error.value = err.response?.data?.error || 'Too many attempts. Try again in a few minutes.';
    } else if (status === 401) {
      error.value = err.response?.data?.error || 'Invalid email or password';
    } else {
      error.value = 'Login failed. Check your connection and try again.';
    }
  } finally {
    isLoading.value = false;
  }
};
```

- [ ] **Step 4: Update MainLayout.vue** — dua baris yang memakai `username`:

Baris 118: `<p class="text-[10px] text-muted uppercase tracking-[0.18em] truncate">{{ auth.user?.email || '' }}</p>`
Baris 192: `const name = auth.user?.display_name || auth.user?.email || 'A';`

- [ ] **Step 5: Verifikasi build**

Run: `cd admin_frontend && npm run build`
Expected: build sukses tanpa error

- [ ] **Step 6: Commit**

```bash
git add admin_frontend/src/views/LoginView.vue admin_frontend/src/stores/auth.js admin_frontend/src/api/index.js admin_frontend/src/layouts/MainLayout.vue
git commit -m "feat: frontend login by email + link forgot password + api reset"
```

---

### Task 8: Frontend — halaman Forgot & Reset password

**Files:**
- Create: `admin_frontend/src/views/ForgotPasswordView.vue`
- Create: `admin_frontend/src/views/ResetPasswordView.vue`
- Modify: `admin_frontend/src/router/index.js`

**Interfaces:**
- Consumes: `authApi.forgotPassword(email)`, `authApi.resetPassword(token, newPassword)` (Task 7), route `/login?reset=success` (Task 7), link email `{base}/reset-password?token=...` (Task 5).
- Produces: route publik `/forgot-password` dan `/reset-password`.

- [ ] **Step 1: Buat ForgotPasswordView.vue**

File `admin_frontend/src/views/ForgotPasswordView.vue`:

```vue
<template>
  <div class="login-page min-h-screen flex items-center justify-center p-4">
    <div class="w-full max-w-sm">
      <div class="text-center mb-8">
        <div class="mx-auto mb-4 w-12 h-12 rounded-2xl flex items-center justify-center text-white text-lg font-bold shadow-lg"
             style="background: linear-gradient(135deg, var(--color-primary), var(--color-primary-strong));">S</div>
        <h1 class="text-2xl font-bold text-theme">StatementX</h1>
        <p class="text-sm text-muted mt-1">Reset your password</p>
      </div>

      <form v-if="!sent" class="surface-card rounded-2xl p-6 space-y-4" @submit.prevent="handleSubmit">
        <div>
          <label for="email" class="block text-xs font-bold text-theme mb-1.5 uppercase tracking-wide">Email</label>
          <input
            id="email"
            v-model="email"
            type="email"
            autocomplete="email"
            class="input-base py-2.5"
            :disabled="isLoading"
            placeholder="you@company.com"
            required
            autofocus
          />
        </div>

        <p v-if="error" class="text-sm text-red-500 dark:text-red-400">{{ error }}</p>

        <button type="submit" class="btn-primary w-full" :disabled="isLoading || !email">
          {{ isLoading ? 'Sending…' : 'Send Reset Link' }}
        </button>
      </form>

      <div v-else class="surface-card rounded-2xl p-6 space-y-4">
        <p class="text-sm text-muted">
          If an account exists for that email, a reset link has been sent.
          Check your inbox (and spam folder). The link expires in 30 minutes.
        </p>
        <router-link to="/login" class="btn-primary w-full flex items-center justify-center py-2.5">
          Back to Sign In
        </router-link>
      </div>

      <p v-if="!sent" class="text-center mt-4">
        <router-link to="/login" class="text-xs text-muted hover:opacity-80">Back to sign in</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { authApi } from '../api';

const email = ref('');
const isLoading = ref(false);
const error = ref('');
const sent = ref(false);

const handleSubmit = async () => {
  isLoading.value = true;
  error.value = '';
  try {
    await authApi.forgotPassword(email.value.trim());
    sent.value = true;
  } catch (err) {
    const status = err.response?.status;
    if (status === 429) {
      error.value = err.response?.data?.error || 'Too many requests. Try again in a few minutes.';
    } else {
      error.value = 'Request failed. Check your connection and try again.';
    }
  } finally {
    isLoading.value = false;
  }
};
</script>
```

- [ ] **Step 2: Buat ResetPasswordView.vue**

File `admin_frontend/src/views/ResetPasswordView.vue`:

```vue
<template>
  <div class="login-page min-h-screen flex items-center justify-center p-4">
    <div class="w-full max-w-sm">
      <div class="text-center mb-8">
        <div class="mx-auto mb-4 w-12 h-12 rounded-2xl flex items-center justify-center text-white text-lg font-bold shadow-lg"
             style="background: linear-gradient(135deg, var(--color-primary), var(--color-primary-strong));">S</div>
        <h1 class="text-2xl font-bold text-theme">StatementX</h1>
        <p class="text-sm text-muted mt-1">Choose a new password</p>
      </div>

      <div v-if="!token" class="surface-card rounded-2xl p-6 space-y-4">
        <p class="text-sm text-muted">This reset link is missing its token.</p>
        <router-link to="/forgot-password" class="btn-primary w-full flex items-center justify-center py-2.5">
          Request a new link
        </router-link>
      </div>

      <div v-else-if="done" class="surface-card rounded-2xl p-6 space-y-4">
        <p class="text-sm text-muted">Password changed. Please sign in with your new password.</p>
        <router-link to="/login?reset=success" class="btn-primary w-full flex items-center justify-center py-2.5">
          Go to Sign In
        </router-link>
      </div>

      <form v-else class="surface-card rounded-2xl p-6 space-y-4" @submit.prevent="handleSubmit">
        <div>
          <label for="new-password" class="block text-xs font-bold text-theme mb-1.5 uppercase tracking-wide">New password</label>
          <input
            id="new-password"
            v-model="password"
            type="password"
            autocomplete="new-password"
            class="input-base py-2.5"
            :disabled="isLoading"
            placeholder="Minimum 8 characters"
            required
            minlength="8"
            autofocus
          />
        </div>
        <div>
          <label for="confirm-password" class="block text-xs font-bold text-theme mb-1.5 uppercase tracking-wide">Confirm password</label>
          <input
            id="confirm-password"
            v-model="confirm"
            type="password"
            autocomplete="new-password"
            class="input-base py-2.5"
            :disabled="isLoading"
            placeholder="Repeat new password"
            required
            minlength="8"
          />
        </div>

        <p v-if="error" class="text-sm text-red-500 dark:text-red-400">{{ error }}</p>

        <button type="submit" class="btn-primary w-full" :disabled="isLoading || !password || !confirm">
          {{ isLoading ? 'Saving…' : 'Reset Password' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';
import { useRoute } from 'vue-router';
import { authApi } from '../api';

const route = useRoute();
const token = computed(() => (typeof route.query.token === 'string' ? route.query.token : ''));

const password = ref('');
const confirm = ref('');
const isLoading = ref(false);
const error = ref('');
const done = ref(false);

const handleSubmit = async () => {
  error.value = '';
  if (password.value.length < 8) {
    error.value = 'Password must be at least 8 characters.';
    return;
  }
  if (password.value !== confirm.value) {
    error.value = 'Passwords do not match.';
    return;
  }
  isLoading.value = true;
  try {
    await authApi.resetPassword(token.value, password.value);
    done.value = true;
  } catch (err) {
    const code = err.response?.data?.code;
    if (code === 'invalid_token') {
      error.value = 'This reset link is invalid or has expired. Request a new one.';
    } else if (err.response?.status === 400) {
      error.value = err.response?.data?.error || 'Password must be at least 8 characters.';
    } else {
      error.value = 'Request failed. Check your connection and try again.';
    }
  } finally {
    isLoading.value = false;
  }
};
</script>
```

- [ ] **Step 3: Daftarkan routes di router/index.js**

Import (setelah baris LoginView):

```javascript
import ForgotPasswordView from '../views/ForgotPasswordView.vue'
import ResetPasswordView from '../views/ResetPasswordView.vue'
```

Routes (setelah route login):

```javascript
    {
      path: '/forgot-password',
      name: 'forgot-password',
      component: ForgotPasswordView,
      meta: { public: true }
    },
    {
      path: '/reset-password',
      name: 'reset-password',
      component: ResetPasswordView,
      meta: { public: true }
    },
```

Catatan: `router.beforeEach` sudah mengizinkan semua route dengan `meta.public`, dan kasus `to.name === 'login'` tidak menutup route baru. Tidak ada perubahan guard.

- [ ] **Step 4: Verifikasi build**

Run: `cd admin_frontend && npm run build`
Expected: build sukses tanpa error

- [ ] **Step 5: Commit**

```bash
git add admin_frontend/src/views/ForgotPasswordView.vue admin_frontend/src/views/ResetPasswordView.vue admin_frontend/src/router/index.js
git commit -m "feat: halaman forgot & reset password (route publik)"
```

---

### Task 9: Verifikasi end-to-end + migrasi DB

**Files:**
- Tidak ada file baru; verifikasi saja. (Jika e2e menemukan bug, perbaiki di file terkait dan commit terpisah.)

**Interfaces:**
- Consumes: seluruh Task 1-8.

- [ ] **Step 1: Full test suite + compile check**

```bash
cd admin_backend && venv/bin/python -m pytest tests/ -v
cd admin_backend && venv/bin/python -m compileall backend server.py scripts
cd admin_frontend && npm run build
```

Expected: semua test PASSED, compileall tanpa output error, build sukses.

- [ ] **Step 2: Jalankan migrasi 071 ke database MySQL**

```bash
cd admin_backend && venv/bin/python -c "from migrate import run_migrations; import sys; sys.exit(0 if run_migrations() else 1)"
```

Expected: migrasi `071_email_accounts.sql` tercatat applied. (Skrip menjalankan SEMUA migrasi yang belum applied — aman karena yang lama sudah applied.)

- [ ] **Step 3: Buat ulang akun admin (email)**

```bash
cd admin_backend && venv/bin/python scripts/create_user.py admin@<domain-anda> "Nama Admin"
```

Expected: prompt password, lalu `User admin@... dibuat.`

- [ ] **Step 4: E2e manual via browser (dev server)**

```bash
cd admin_backend && FLASK_ENV=development venv/bin/python server.py
cd admin_frontend && npm run dev
```

Checklist browser:
1. Buka halaman login → field sekarang "Email" + link "Forgot password?".
2. Login `admin@<domain>` + password → masuk dashboard; chip user menampilkan email.
3. Logout → klik "Forgot password?" → masukkan email → layar sukses generis muncul.
4. Cek log server Flask: baris WARNING berisi `/reset-password?token=...` — salin URL lengkap.
5. Buka URL token di browser → isi password baru (8+ char) → "Go to Sign In" → login dengan password baru → berhasil.
6. Buka URL token yang sama sekali lagi → ditolak "invalid or has expired".
7. Reset password sekali lagi, lalu coba sesi browser lain/tab incognito yang masih login dengan password lama → sesi tersebut ter-logout (401 → redirect login).

- [ ] **Step 5: Commit sisa perubahan (jika ada perbaikan e2e)**

```bash
git add -A && git commit -m "fix: perbaikan dari verifikasi e2e forgot password"
```

---

## Self-Review (hasil)

1. **Spec coverage:** semua butir spec tercakup — migrasi (Task 2), login by email (Task 3), mailer + .env (Task 4), forgot (Task 5), reset + invalidasi sesi (Task 6), frontend login/forgot/reset (Task 7-8), testing & e2e (Task 1, 9). Extension points & out-of-scope: tidak diimplementasi, sesuai spec.
2. **Placeholder scan:** tidak ada TBD/TODO; semua langkah berisi kode/perintah lengkap.
3. **Type consistency:** `send_reset_email(to_email, reset_link, display_name='')`, `_hash_token(token)`, `_too_many_attempts(key, store, max_attempts, window_seconds)`, `_record_attempt(key, store)`, `authApi.forgotPassword/resetPassword`, `auth.login(email, password)` konsisten antar task. `credential_version` dipakai konsisten di login/guard/reset.
