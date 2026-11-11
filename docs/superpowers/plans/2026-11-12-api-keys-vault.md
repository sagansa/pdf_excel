# API Keys Vault (Tab "API Keys" di Settings) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Satu tempat terpusat untuk meng-inject semua API key/token aplikasi (Sagansa superadmin ×5, Telegram, SMTP, n8n, AI), dikelola dari tab "API Keys" baru di Settings, disimpan di `app_settings` dengan fallback env.

**Architecture:** Service `backend/services/credentials.py` = registry + resolusi DB→env + handler test koneksi. Blueprint `credentials_bp` dengan 3 endpoint generik (list/bulk-save/test). Semua pemanggil lama (payroll, 5 blueprint inventory, mailer, telegram, n8n, llm_client) refactor membaca via service. Frontend: `CredentialsSettings.vue` per grup + tab baru di SettingsView; input API key pindah dari tab AI.

**Tech Stack:** Flask + SQLAlchemy (stdlib urllib untuk HTTP test, smtplib untuk SMTP), Vue 3 `<script setup>` + axios, pytest. Tanpa dependency baru.

**Spec:** `docs/superpowers/specs/2026-11-12-api-keys-vault-design.md`

## Global Constraints

- Nilai secret TIDAK PERNAH muncul di response GET/PUT dan TIDAK PERNAH di-log.
- Urutan resolusi selalu: DB (`app_settings`) → env fallback → kosong; semua baca fail-soft (tabel hilang/DB mati → env).
- Sentinel hapus = `__CLEAR__` (konstanta canonical di `credentials.py`).
- Test koneksi selalu return `{'ok': bool, 'message': str}`, tidak pernah raise ke 500; timeout 15 detik.
- Konstanta URL API (non-secret) TIDAK berubah — tetap env/constants seperti sekarang.
- Komentar & pesan UI berbahasa Indonesia, mengikuti gaya file sekitar.
- `app_settings` sudah dibuat migration `072_ai_mark_assist.sql` — tidak ada migrasi DB baru.
- Backend test: `cd admin_backend && ./venv/bin/python -m pytest tests -q` (fallback `python3 -m pytest tests -q`).
- Frontend build check: `cd admin_frontend && npm run build`.

---

### Task 1: Credentials service — registry, resolusi DB→env, bulk save

**Files:**
- Create: `admin_backend/backend/services/credentials.py`
- Test: `admin_backend/tests/test_credentials_service.py`

**Interfaces:**
- Consumes: `backend.db.session.get_db_engine()` → `(engine | None, error_msg)`; tabel `app_settings(setting_key PK, setting_value)`.
- Produces (dipakai semua task berikutnya):
  - `CREDENTIAL_CLEAR_SENTINEL: str` (`'__CLEAR__'`)
  - `CREDENTIAL_KEYS: set[str]`
  - `get_status(conn=None) -> list[dict]` — tiap item `{key, label, group, secret, test, set, source, value?}`; `value` hanya untuk non-secret; `source` = `'db'|'env'|None`
  - `get_credential(conn, key) -> tuple[str, str]` — `(value, source)`; `source` ∈ `{'db','env',''}`
  - `get_credential_value(key) -> str` — buka koneksi pendek fail-soft, DB→env
  - `save_credentials(conn, updates: dict) -> list[dict]` — upsert + `__CLEAR__` hapus; balik `get_status(conn)`; raise `ValueError` untuk key tak dikenal

- [ ] **Step 1: Write the failing test**

Buat `admin_backend/tests/test_credentials_service.py`:

```python
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


def test_clear_sentinel_menghapus_dan_strip_whitespace(cred_engine):
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd admin_backend && ./venv/bin/python -m pytest tests/test_credentials_service.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.services.credentials'`

- [ ] **Step 3: Write the implementation**

Buat `admin_backend/backend/services/credentials.py`:

```python
"""Registry kredensial terpusat — satu tempat untuk semua API key/token.

Nilai selalu dibaca dengan urutan: DB (tabel app_settings) → fallback env → kosong.
Semua baca bersifat fail-soft: tabel belum ada / DB tidak dapat dihubungi → lanjut
ke env, tidak pernah meledak ke pemanggil.

Nilai secret TIDAK PERNAH dikembalikan ke frontend — hanya indikator `set`
(get_status). Menghapus nilai memakai sentinel CREDENTIAL_CLEAR_SENTINEL
(pattern yang sama dengan ai_api_key di llm_client sebelum vault ini).
"""

import json
import logging
import os
import smtplib
from datetime import date, timedelta
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest

from sqlalchemy import text

from backend.db import session as db_session

logger = logging.getLogger(__name__)

CREDENTIAL_CLEAR_SENTINEL = '__CLEAR__'
CREDENTIAL_TEST_TIMEOUT = 15

# URL test (non-secret) — env var sama dengan konstanta URL di blueprint terkait.
TEST_URLS = {
    'sagansa_presence_token': os.environ.get(
        'SAGANSA_PRESENCE_API_URL', 'https://superadmin.sagansa.id/api/presences'),
    'sagansa_remaining_storage_token': os.environ.get(
        'SAGANSA_REMAINING_STORAGE_API_URL', 'https://superadmin.sagansa.id/api/remaining-storages'),
    'sagansa_stock_monitoring_token': os.environ.get(
        'SAGANSA_STOCK_MONITORING_API_URL', 'https://superadmin.sagansa.id/api/stock-monitorings'),
    'sagansa_sales_by_date_token': os.environ.get(
        'SAGANSA_SALES_BY_DATE_API_URL', 'https://superadmin.sagansa.id/api/detail-sales-orders/sales-by-date'),
    'sagansa_stock_comparison_token': os.environ.get(
        'SAGANSA_STOCK_COMPARISON_API_URL', 'https://superadmin.sagansa.id/api/detail-stock-cards/compare-periods'),
}

# Registry: key = nama setting di app_settings (1:1 dengan nama env var).
# secret=True → nilai tidak pernah keluar dari server. test = nama handler koneksi.
CREDENTIALS = (
    {'key': 'sagansa_presence_token', 'label': 'Presence API token',
     'group': 'sagansa', 'secret': True, 'env': 'SAGANSA_PRESENCE_TOKEN', 'test': 'sagansa'},
    {'key': 'sagansa_remaining_storage_token', 'label': 'Remaining storage API token',
     'group': 'sagansa', 'secret': True, 'env': 'SAGANSA_REMAINING_STORAGE_TOKEN', 'test': 'sagansa'},
    {'key': 'sagansa_stock_monitoring_token', 'label': 'Stock monitoring API token',
     'group': 'sagansa', 'secret': True, 'env': 'SAGANSA_STOCK_MONITORING_TOKEN', 'test': 'sagansa'},
    {'key': 'sagansa_sales_by_date_token', 'label': 'Sales by date API token',
     'group': 'sagansa', 'secret': True, 'env': 'SAGANSA_SALES_BY_DATE_TOKEN', 'test': 'sagansa'},
    {'key': 'sagansa_stock_comparison_token', 'label': 'Stock comparison API token',
     'group': 'sagansa', 'secret': True, 'env': 'SAGANSA_STOCK_COMPARISON_TOKEN', 'test': 'sagansa'},
    {'key': 'telegram_bot_token', 'label': 'Bot token (dari @BotFather)',
     'group': 'telegram', 'secret': True, 'env': 'TELEGRAM_BOT_TOKEN', 'test': 'telegram'},
    {'key': 'telegram_chat_id', 'label': 'Chat ID tujuan',
     'group': 'telegram', 'secret': False, 'env': 'TELEGRAM_CHAT_ID'},
    {'key': 'smtp_host', 'label': 'SMTP host',
     'group': 'smtp', 'secret': False, 'env': 'SMTP_HOST'},
    {'key': 'smtp_port', 'label': 'SMTP port',
     'group': 'smtp', 'secret': False, 'env': 'SMTP_PORT'},
    {'key': 'smtp_user', 'label': 'SMTP user',
     'group': 'smtp', 'secret': False, 'env': 'SMTP_USER'},
    {'key': 'smtp_pass', 'label': 'SMTP password',
     'group': 'smtp', 'secret': True, 'env': 'SMTP_PASS', 'test': 'smtp'},
    {'key': 'smtp_from', 'label': 'Alamat pengirim (From)',
     'group': 'smtp', 'secret': False, 'env': 'SMTP_FROM'},
    {'key': 'smtp_use_tls', 'label': 'Gunakan STARTTLS',
     'group': 'smtp', 'secret': False, 'env': 'SMTP_USE_TLS'},
    {'key': 'integration_api_key', 'label': 'X-API-Key untuk endpoint integrasi n8n',
     'group': 'n8n', 'secret': True, 'env': 'INTEGRATION_API_KEY'},
    {'key': 'ai_api_key', 'label': 'API key provider AI (z.ai / custom)',
     'group': 'ai', 'secret': True, 'env': None},
)

CREDENTIAL_KEYS = {cred['key'] for cred in CREDENTIALS}
_BY_KEY = {cred['key']: cred for cred in CREDENTIALS}


def _fetch_stored_values(conn):
    """Baca semua setting; fail-soft → {} bila tabel belum ada / DB bermasalah."""
    try:
        rows = conn.execute(text('SELECT setting_key, setting_value FROM app_settings')).fetchall()
    except Exception:
        return {}
    return {str(row._mapping['setting_key']): row._mapping['setting_value'] for row in rows}


def _read_conn():
    """Koneksi pendek fail-soft dari engine global; None bila DB tidak siap."""
    try:
        engine, _ = db_session.get_db_engine()
        if engine is None:
            return None
        return engine.connect()
    except Exception:
        return None


def get_credential(conn, key):
    """Baca satu kredensial: (value, source) dengan source 'db' | 'env' | ''."""
    cred = _BY_KEY.get(key)
    if cred is None:
        raise ValueError(f'Kredensial tidak dikenal: {key}')
    try:
        rows = conn.execute(
            text('SELECT setting_value FROM app_settings WHERE setting_key = :key'),
            {'key': key},
        ).fetchall()
    except Exception:
        rows = []
    value = str(rows[0]._mapping['setting_value'] or '') if rows else ''
    if value.strip():
        return value, 'db'
    if cred['env']:
        return os.environ.get(cred['env'], ''), 'env'
    return '', ''


def get_credential_value(key):
    """Nilai siap pakai untuk pemanggil server; DB dulu, lalu env. Tanpa conn? buka sendiri."""
    conn = _read_conn()
    if conn is not None:
        try:
            value, _ = get_credential(conn, key)
            if value.strip():
                return value
        finally:
            conn.close()
    cred = _BY_KEY.get(key)
    if cred is None:
        raise ValueError(f'Kredensial tidak dikenal: {key}')
    if cred['env']:
        return os.environ.get(cred['env'], '')
    return ''


def get_status(conn=None):
    """Status semua kredensial untuk frontend — secret hanya set/source, tanpa nilai."""
    own_conn = None
    if conn is None:
        conn = own_conn = _read_conn()
    stored = _fetch_stored_values(conn) if conn is not None else {}
    if own_conn is not None:
        own_conn.close()

    items = []
    for cred in CREDENTIALS:
        raw = str(stored.get(cred['key']) or '')
        value = raw if raw.strip() else (os.environ.get(cred['env'], '') if cred['env'] else '')
        is_set = bool(str(value).strip())
        item = {
            'key': cred['key'],
            'label': cred['label'],
            'group': cred['group'],
            'secret': cred['secret'],
            'test': cred.get('test'),
            'set': is_set,
            'source': None,
        }
        if is_set:
            item['source'] = 'db' if raw.strip() else 'env'
        if not cred['secret']:
            item['value'] = str(value)
        items.append(item)
    return items


def save_credentials(conn, updates):
    """Simpan banyak kredensial sekaligus (upsert aman MySQL & SQLite).

    Nilai `CREDENTIAL_CLEAR_SENTINEL` menghapus (disimpan sebagai string kosong).
    Balikan: status terbaru dari get_status(conn).
    """
    unknown = set(updates) - CREDENTIAL_KEYS
    if unknown:
        raise ValueError(f'Kredensial tidak dikenal: {", ".join(sorted(unknown))}')
    for key, raw in updates.items():
        value = '' if raw == CREDENTIAL_CLEAR_SENTINEL else str(raw if raw is not None else '').strip()
        if conn.dialect.name == 'sqlite':
            conn.execute(text(
                'INSERT INTO app_settings (setting_key, setting_value) VALUES (:key, :value) '
                'ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value'
            ), {'key': key, 'value': value})
        else:
            conn.execute(text(
                'INSERT INTO app_settings (setting_key, setting_value) VALUES (:key, :value) '
                'ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)'
            ), {'key': key, 'value': value})
    return get_status(conn)
```

Catatan: file ini juga menyimpan fungsi test (`run_test`, handler) yang baru diisi di Task 2 — untuk Task 1 cukup kode di atas (tanpa `run_test`). Import `json`, `smtplib`, `urlerror`, `urlparse`, `urlrequest`, `date`, `timedelta`, `CREDENTIAL_TEST_TIMEOUT` akan terpakai di Task 2; boleh ditulis sekarang atau ditambah di Task 2 — yang penting di akhir Task 1 file lolos flake syntax (import belum terpakai tidak masalah).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd admin_backend && ./venv/bin/python -m pytest tests/test_credentials_service.py -q`
Expected: PASS semua (10 test)

- [ ] **Step 5: Commit**

```bash
git add admin_backend/backend/services/credentials.py admin_backend/tests/test_credentials_service.py
git commit -m "feat: credentials service — registry & resolusi DB→env untuk vault API Keys"
```

---

### Task 2: Credentials service — handler test koneksi (sagansa ×5, telegram, smtp)

**Files:**
- Modify: `admin_backend/backend/services/credentials.py` (tambah di akhir file)
- Test: `admin_backend/tests/test_credentials_service.py` (tambah test)

**Interfaces:**
- Consumes: registry Task 1 (`CREDENTIALS`, `get_credential_value`, `CREDENTIAL_TEST_TIMEOUT`, `TEST_URLS`)
- Produces: `run_test(key, value=None, extra=None) -> tuple[bool, str]` — dipakai blueprint (Task 3). `value` = nilai yang baru diketik user (belum disimpan); `extra` = dict field pendamping (mis. `telegram_chat_id`, field SMTP). Kunci modul `_TEST_HANDLERS: dict[str, callable]` (nama handler dari registry: `'sagansa'`, `'telegram'`, `'smtp'`) — perlu untuk monkeypatch di test.

- [ ] **Step 1: Write the failing test**

Tambahkan di akhir `admin_backend/tests/test_credentials_service.py`:

```python
# ===== Test handler koneksi (Task 2) =====

from urllib.error import HTTPError, URLError


def test_run_test_sagansa_sukses(cred_engine, monkeypatch):
    monkeypatch.setattr(db_session, 'get_db_engine', lambda: (cred_engine, None))
    monkeypatch.delenv('SAGANSA_PRESENCE_TOKEN', raising=False)
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
    ok, message = credentials_service.run_test('sagansa_presence_token', value='tok-123')
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
    ok, message = credentials_service.run_test('sagansa_presence_token', value='salah')
    assert ok is False
    assert '401' in message
    assert 'salah' not in message


def test_run_test_sagansa_token_kosong(cred_engine, monkeypatch):
    monkeypatch.setattr(db_session, 'get_db_engine', lambda: (cred_engine, None))
    monkeypatch.delenv('SAGANSA_PRESENCE_TOKEN', raising=False)
    ok, message = credentials_service.run_test('sagansa_presence_token')
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd admin_backend && ./venv/bin/python -m pytest tests/test_credentials_service.py -q`
Expected: FAIL — `AttributeError: module 'backend.services.credentials' has no attribute 'run_test'`

- [ ] **Step 3: Write the implementation**

Tambahkan di akhir `admin_backend/backend/services/credentials.py` (import `json`, `smtplib`, `urlerror`, `urlparse`, `urlrequest`, `date`, `timedelta` sudah di header file dari Task 1):

```python
# ===== Handler test koneksi =====

def _resolve_for_test(key, value, extra):
    """Nilai untuk test: extra/input user menang, lalu nilai tersimpan (DB→env)."""
    extra = extra or {}
    candidate = str(extra.get(key) or '').strip()
    if candidate:
        return candidate
    typed = str(value or '').strip()
    if typed:
        return typed
    return get_credential_value(key)


def _test_sagansa(key, value, extra):
    token = _resolve_for_test(key, value, extra)
    if not token:
        return False, 'Token belum diisi — tempel token atau isi kolomnya terlebih dahulu.'

    params = {'per_page': 1}
    if key == 'sagansa_sales_by_date_token':
        params = {'date': (date.today() - timedelta(days=1)).isoformat()}
    elif key == 'sagansa_stock_comparison_token':
        params = {'from_date': date.today().isoformat(), 'to_date': date.today().isoformat()}
    url = f"{TEST_URLS[key]}?{urlparse.urlencode(params)}"

    req = urlrequest.Request(url, headers={
        'Accept': 'application/json',
        'Authorization': f'Bearer {token}',  # header request, tidak di-log
    })
    try:
        with urlrequest.urlopen(req, timeout=CREDENTIAL_TEST_TIMEOUT) as resp:
            status = int(getattr(resp, 'status', 200))
    except urlerror.HTTPError as exc:
        if exc.code in (401, 403):
            return False, f'HTTP {exc.code} — token ditolak server (salah atau tidak berlaku).'
        return False, f'HTTP {exc.code} — server Sagansa menjawab error. Coba lagi nanti.'
    except urlerror.URLError as exc:
        return False, f'Tidak dapat dihubungi: {exc.reason}'
    except TimeoutError:
        return False, 'Server tidak menjawab tepat waktu (timeout).'
    return True, f'Koneksi berhasil (HTTP {status}).'


def _test_telegram(key, value, extra):
    token = _resolve_for_test(key, value, extra)
    if not token:
        return False, 'Bot token belum diisi.'
    chat_id = _resolve_for_test('telegram_chat_id', None, extra)
    if not chat_id:
        return False, 'Chat ID belum diisi — isi kolom Chat ID lalu test lagi.'

    url = f'https://api.telegram.org/bot{token}/sendMessage'
    payload = json.dumps({
        'chat_id': chat_id,
        'text': 'StatementX — tes koneksi API Keys berhasil.',
    }).encode('utf-8')
    req = urlrequest.Request(url, data=payload, headers={
        'Content-Type': 'application/json',
    }, method='POST')
    try:
        with urlrequest.urlopen(req, timeout=CREDENTIAL_TEST_TIMEOUT) as resp:
            int(getattr(resp, 'status', 200))
    except urlerror.HTTPError as exc:
        if exc.code == 401:
            return False, 'HTTP 401 — bot token salah atau dicabut.'
        return False, f'HTTP {exc.code} — Telegram menolak request. Periksa chat ID.'
    except urlerror.URLError as exc:
        return False, f'Tidak dapat dihubungi: {exc.reason}'
    except TimeoutError:
        return False, 'Server Telegram tidak menjawab tepat waktu (timeout).'
    return True, 'Pesan tes terkirim — cek Telegram Anda.'


_SMTP_FIELDS = ('smtp_host', 'smtp_port', 'smtp_user', 'smtp_pass', 'smtp_from', 'smtp_use_tls')


def _test_smtp(key, value, extra):
    values = {}
    for field in _SMTP_FIELDS:
        values[field] = _resolve_for_test(field, value if field == key else None, extra)

    if not values['smtp_host']:
        return False, 'SMTP host belum diisi.'
    if not values['smtp_user']:
        return False, 'SMTP user belum diisi.'
    if not values['smtp_pass']:
        return False, 'SMTP password belum diisi.'
    try:
        port = int(values['smtp_port'] or '587')
    except ValueError:
        return False, 'SMTP port harus angka.'
    use_tls = str(values['smtp_use_tls'] or 'true').strip().lower() not in {'0', 'false', 'no'}

    try:
        with smtplib.SMTP(values['smtp_host'], port, timeout=CREDENTIAL_TEST_TIMEOUT) as server:
            if use_tls:
                server.starttls()
            server.login(values['smtp_user'], values['smtp_pass'])
    except smtplib.SMTPAuthenticationError:
        return False, 'Login SMTP gagal — user atau password salah.'
    except (smtplib.SMTPException, OSError) as exc:
        return False, f'Tidak dapat terhubung ke SMTP: {exc}'
    return True, f'Login SMTP berhasil di {values["smtp_host"]}:{port}.'


_TEST_HANDLERS = {
    'sagansa': _test_sagansa,
    'telegram': _test_telegram,
    'smtp': _test_smtp,
}


def run_test(key, value=None, extra=None):
    """Jalankan test koneksi. Selalu (ok, message) — tidak pernah raise ke pemanggil HTTP.

    `value` = nilai yang baru diketik (belum disimpan); `extra` = field pendamping
    dari form (telegram_chat_id / field SMTP).
    """
    cred = _BY_KEY.get(key)
    if cred is None:
        raise ValueError(f'Kredensial tidak dikenal: {key}')
    handler = _TEST_HANDLERS.get(cred.get('test'))
    if handler is None:
        return False, 'Kredensial ini tidak punya test koneksi.'
    try:
        return handler(key, value, extra)
    except Exception as exc:  # pengaman terakhir: test tidak boleh memicu HTTP 500
        logger.warning('Test kredensial %s gagal tak terduga', key)  # nilai tidak di-log
        return False, f'Test gagal: {exc}'
```

Perbaikan kecil di `get_status` dari Task 1 — jika versi awal memakai walrus operator di dict literal, ganti dengan bentuk kondisional yang bersih (lihat Task 1 versi final).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd admin_backend && ./venv/bin/python -m pytest tests/test_credentials_service.py -q`
Expected: PASS semua

- [ ] **Step 5: Commit**

```bash
git add admin_backend/backend/services/credentials.py admin_backend/tests/test_credentials_service.py
git commit -m "feat: handler test koneksi credentials (sagansa/telegram/smtp)"
```

---

### Task 3: Blueprint `credentials_bp` — GET/PUT/POST + registrasi server.py

**Files:**
- Create: `admin_backend/backend/routes/credentials_bp.py`
- Modify: `admin_backend/server.py` (import + register, ikut pola blueprint lain)
- Test: `admin_backend/tests/test_credentials_bp.py`

**Interfaces:**
- Consumes: Task 1 & 2 — `credentials_service.get_status/save_credentials/run_test/CREDENTIAL_KEYS`.
- Produces: HTTP API — `GET /api/credentials`, `PUT /api/credentials` (body `{'updates': {key: value|'__CLEAR__'}}`), `POST /api/credentials/<key>/test` (body `{value?, extra?}` → `{ok, message}`). Dilindungi guard login global `server.py` (otomatis, tanpa kode tambahan).

- [ ] **Step 1: Write the failing test**

Buat `admin_backend/tests/test_credentials_bp.py`:

```python
"""Test endpoint /api/credentials: masking secret, bulk save, sentinel, test koneksi."""

import pytest
from flask import Flask
from sqlalchemy import create_engine, text

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
    monkeypatch.setattr(credentials_bp_module, 'require_db_engine', lambda: cred_engine)
    app = Flask(__name__)
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
    resp = cred_client.post('/api/credentials/sagansa_presence_token/test', json={'value': 'tok'})
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
    resp = cred_client.post('/api/credentials/sagansa_presence_token/test', json={})
    assert resp.status_code == 200
    assert resp.get_json()['ok'] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd admin_backend && ./venv/bin/python -m pytest tests/test_credentials_bp.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.routes.credentials_bp'`

- [ ] **Step 3: Write the implementation**

Buat `admin_backend/backend/routes/credentials_bp.py`:

```python
"""Endpoint vault kredensial: list status, bulk save, test koneksi.

Semua endpoint dilindungi guard login global (server.py before_request).
Nilai secret tidak pernah dikirim balik ke klien — lihat services/credentials.py.
"""

from flask import Blueprint, jsonify, request

from backend.errors import BadRequestError
from backend.routes.accounting_utils import require_db_engine
from backend.services import credentials as credentials_service

credentials_bp = Blueprint('credentials_bp', __name__)


@credentials_bp.route('/api/credentials', methods=['GET'])
def list_credentials():
    return jsonify({'credentials': credentials_service.get_status()})


@credentials_bp.route('/api/credentials', methods=['PUT'])
def update_credentials():
    updates = (request.json or {}).get('updates')
    if not isinstance(updates, dict) or not updates:
        raise BadRequestError(
            'Body harus berisi updates: {key: nilai baru atau "__CLEAR__"}',
            code='credentials_updates_missing',
        )
    unknown = set(updates) - credentials_service.CREDENTIAL_KEYS
    if unknown:
        raise BadRequestError(
            f'Kredensial tidak dikenal: {", ".join(sorted(unknown))}',
            code='credentials_unknown_key',
        )
    engine = require_db_engine()
    with engine.begin() as conn:
        status = credentials_service.save_credentials(conn, updates)
    return jsonify({'credentials': status, 'message': 'Kredensial tersimpan.'})


@credentials_bp.route('/api/credentials/<key>/test', methods=['POST'])
def test_credential(key):
    if key not in credentials_service.CREDENTIAL_KEYS:
        raise BadRequestError(f'Kredensial tidak dikenal: {key}', code='credentials_unknown_key')
    data = request.json or {}
    ok, message = credentials_service.run_test(
        key, value=data.get('value'), extra=data.get('extra'),
    )
    return jsonify({'ok': ok, 'message': message})
```

Edit `admin_backend/server.py` — tambah import (satu baris, mengikuti urutan import blueprint yang ada):

```python
from backend.routes.credentials_bp import credentials_bp
```

dan daftar registrasi (setelah `app.register_blueprint(ai_bp)`):

```python
app.register_blueprint(credentials_bp)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd admin_backend && ./venv/bin/python -m pytest tests/test_credentials_bp.py tests/test_credentials_service.py -q`
Expected: PASS semua

- [ ] **Step 5: Commit**

```bash
git add admin_backend/backend/routes/credentials_bp.py admin_backend/server.py admin_backend/tests/test_credentials_bp.py
git commit -m "feat: endpoint /api/credentials (list, bulk save, test koneksi)"
```

---

### Task 4: AI key pindah ke vault — llm_client & ai_bp berhenti menulis ai_api_key

**Files:**
- Modify: `admin_backend/backend/services/ai/llm_client.py:29-32` (SETTING_KEYS), `:192-240` (save_ai_settings), `:37` (sentinel)
- Modify: `admin_backend/backend/routes/transactions/ai_bp.py:71-76` (blok api_key di `_validate_settings_payload`)
- Test: `admin_backend/tests/test_ai_bp.py` (ubah 1 test)

**Interfaces:**
- Consumes: vault menulis `ai_api_key` ke `app_settings` (Task 1 `save_credentials`).
- Produces: `get_ai_settings` tetap membaca `ai_api_key` dari `app_settings` (ubah perilaku: TIDAK ada lagi) — semua pemanggil AI (mark_suggester, description_enricher, ai_bp test-connection) tidak berubah. `ai_api_key` kini hanya bisa berubah via `PUT /api/credentials`.

- [ ] **Step 1: Update test yang ada (perubahan perilaku disengaja)**

Di `admin_backend/tests/test_ai_bp.py`, ganti `test_settings_zai_provider_with_api_key` (sekitar baris 189–218) dengan:

```python
def test_settings_tidak_lagi_menerima_api_key(ai_client):
    """AI key kini milik vault (PUT /api/credentials) — /api/ai/settings mengabaikannya."""
    resp = ai_client.put('/api/ai/settings', json={
        'enabled': True,
        'provider': 'zai',
        'base_url': 'https://api.z.ai/api/paas/v4',
        'model': 'glm-4',
        'auto_apply': False,
        'auto_apply_threshold': 0.9,
        'api_key': 'secret-key-12345',
    })
    assert resp.status_code == 200
    settings = resp.get_json()['settings']
    assert settings['api_key_set'] is False  # kunci tidak ditulis lewat endpoint ini
    assert 'api_key' not in settings

    follow_up = ai_client.get('/api/ai/settings').get_json()['settings']
    assert follow_up['api_key_set'] is False
```

Perhatikan: jika ada test lain di file ini yang menyimpan via `api_key` atau memakai `llm_client.API_KEY_CLEAR_SENTINEL`, sesuaikan juga (api_key di payload dihapus; sentinel string `'__CLEAR__'` hanya relevan di vault). Baris `('ai_api_key', 'k')` yang di-insert langsung ke `app_settings` pada test lain BIAR tetap (vault menulis ke key yang sama, `get_ai_settings` tetap membacanya).

- [ ] **Step 2: Run test to verify it fails**

Run: `cd admin_backend && ./venv/bin/python -m pytest tests/test_ai_bp.py -q`
Expected: FAIL — test baru gagal karena `save_ai_settings` masih menulis `ai_api_key` (`api_key_set` masih `True`)

- [ ] **Step 3: Write the implementation**

`llm_client.py` — tiga perubahan:

1. Hapus `'ai_api_key'` dari `SETTING_KEYS`:

```python
# Kunci yang disimpan/dibaca di tabel app_settings.
# ai_api_key ditangani vault kredensial (services/credentials.py) — bukan di sini.
SETTING_KEYS = (
    'ai_enabled', 'ai_provider', 'ai_base_url', 'ai_model',
    'ai_auto_apply', 'ai_auto_apply_threshold',
)
```

2. Hapus konstanta `API_KEY_CLEAR_SENTINEL = '__CLEAR__'` (baris 37) — pengguna tunggalnya (ai_bp) ikut dibersihkan di langkah ini. `get_ai_settings` tetap membaca `stored.get('ai_api_key')` tanpa perubahan.

3. Di `save_ai_settings`, hapus seluruh blok penanganan api_key (`api_key = payload.get('api_key')` sampai akhir upsert kedua) — kini fungsi hanya meng-upsert `SETTING_KEYS` lalu `settings = get_ai_settings(conn)`; `settings.pop('api_key', None)` tetap.

`ai_bp.py` — di `_validate_settings_payload`, hapus blok:

```python
    api_key = data.get('api_key')
    if api_key is not None:
        api_key = str(api_key)
        if api_key not in (llm_client.API_KEY_CLEAR_SENTINEL,):
            api_key = api_key.strip()
        payload['api_key'] = api_key  # '' / sentinel / nilai baru; None berarti tidak diubah
```

dan ganti dengan komentar:

```python
    # api_key tidak diterima di sini — AI key dikelola vault (PUT /api/credentials,
    # setting ai_api_key). Nilai asing diabaikan agar tidak menimpa kunci vault.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd admin_backend && ./venv/bin/python -m pytest tests/test_ai_bp.py -q`
Expected: PASS semua

- [ ] **Step 5: Commit**

```bash
git add admin_backend/backend/services/ai/llm_client.py admin_backend/backend/routes/transactions/ai_bp.py admin_backend/tests/test_ai_bp.py
git commit -m "refactor: ai_api_key jadi milik vault kredensial (PUT /api/credentials)"
```

---

### Task 5: Refactor payroll + 5 blueprint inventory ke credentials service

**Files:**
- Modify: `admin_backend/backend/routes/transactions/payroll_bp.py:39` (hapus konstanta token), `:75-80` (fallback token)
- Modify: `admin_backend/backend/routes/inventory/remaining_storage_bp.py:41-47` (hapus 2 konstanta token), `:174`, `:291`, `:357`, `:634` (fallback)
- Modify: `admin_backend/backend/routes/inventory/hpp_bp.py:38-44` (hapus konstanta), `:97-98`, `:135-139` (fallback)
- Modify: `admin_backend/backend/routes/inventory/inventory_bp.py:40-52` (hapus 2 konstanta), `:74` (fallback)
- Modify: `admin_backend/backend/routes/inventory/sales_by_date_bp.py:13-15` (hapus konstanta), `:82` (fallback)
- Modify: `admin_backend/backend/routes/inventory/stock_comparison_bp.py:12-16` (hapus konstanta) + 1 lokasi fallback (lihat Step 1)

**Interfaces:**
- Consumes: `credentials_service.get_credential_value(key) -> str` (Task 1).
- Produces: perilaku fallback baru `payload/query token → DB → env` di semua endpoint terkait. Konstanta URL tidak berubah.

- [ ] **Step 1: Petakan lokasi pemakaian konstanta token**

Run: `cd admin_backend && grep -rn "DEFAULT_.*TOKEN" backend/routes --include="*.py" | grep -v __pycache__`
Catat setiap baris pemakaian (bukan definisi). Expected ≈: payroll 1 pakai; remaining_storage 4 pakai; hpp 2 pakai; inventory 1 pakai; sales_by_date 1 pakai; stock_comparison 1 pakai.

- [ ] **Step 2: Test lama sebagai jaring pengaman**

Run: `cd admin_backend && ./venv/bin/python -m pytest tests -q`
Expected: PASS semua (baseline sebelum refactor). Tidak ada unit test khusus per-token di blueprint ini — pengaman = test lama tetap hijau + verifikasi grep di Step 5.

- [ ] **Step 3: Refactor payroll_bp**

Di `payroll_bp.py`:

1. Tambah import:

```python
from backend.services import credentials as credentials_service
```

2. Hapus konstanta:

```python
DEFAULT_PRESENCE_API_TOKEN = os.environ.get('SAGANSA_PRESENCE_TOKEN', '')
```

3. Di `sync_payroll_presences`, ganti fallback:

```python
    token = str(
        payload.get('token')
        or payload.get('access_token')
        or payload.get('api_token')
        or credentials_service.get_credential_value('sagansa_presence_token')
        or ''
    ).strip()
```

4. Update pesan error token (di `_validate` sekitar baris 77) agar mencerminkan sumber baru:

```python
    if not token:
        raise BadRequestError(
            'Presence API token is required (payload.token, Settings → API Keys, atau env SAGANSA_PRESENCE_TOKEN)')
```

- [ ] **Step 4: Refactor 5 blueprint inventory**

Pola sama untuk tiap file — hapus konstanta `DEFAULT_*_TOKEN`, tambah import `from backend.services import credentials as credentials_service`, lalu ganti setiap pemakaian:

`remaining_storage_bp.py` — hapus `DEFAULT_REMAINING_STORAGE_API_TOKEN` dan `DEFAULT_STOCK_MONITORING_API_TOKEN`; di 3 lokasi fallback remaining storage (±174, 291, 357) ganti:

```python
        or DEFAULT_REMAINING_STORAGE_API_TOKEN
```

menjadi:

```python
        or credentials_service.get_credential_value('sagansa_remaining_storage_token')
```

dan di lokasi stock monitoring (±634):

```python
        or credentials_service.get_credential_value('sagansa_stock_monitoring_token')
```

`hpp_bp.py` — hapus `DEFAULT_STOCK_MONITORING_API_TOKEN`; di `_fetch_stock_monitoring_index` (±98):

```python
    token = credentials_service.get_credential_value('sagansa_stock_monitoring_token')
```

di `get_hpp_items` (±135) ganti bagian fallback token:

```python
    token = str(
        request.args.get('token')
        or request.args.get('access_token')
        or request.args.get('api_token')
        or credentials_service.get_credential_value('sagansa_stock_monitoring_token')
        or ''
    ).strip()
```

`inventory_bp.py` — hapus `DEFAULT_REMAINING_STORAGE_API_TOKEN` dan `DEFAULT_STOCK_MONITORING_API_TOKEN`; di `_fetch_stock_monitoring_index` (±74):

```python
    token = credentials_service.get_credential_value('sagansa_stock_monitoring_token')
```

(ganti juga pemakaian `DEFAULT_REMAINING_STORAGE_API_TOKEN` lain yang muncul di grep Step 1 dengan `credentials_service.get_credential_value('sagansa_remaining_storage_token')`.)

`sales_by_date_bp.py` — hapus `DEFAULT_SALES_BY_DATE_TOKEN`; di `get_dashboard_sales_by_date` (±82):

```python
    token = str(
        request.args.get('token')
        or request.args.get('access_token')
        or request.args.get('api_token')
        or credentials_service.get_credential_value('sagansa_sales_by_date_token')
        or ''
    ).strip()
```

`stock_comparison_bp.py` — hapus `DEFAULT_STOCK_COMPARISON_TOKEN`; di lokasi fallback (hasil grep Step 1, ± handler route) ganti dengan:

```python
        or credentials_service.get_credential_value('sagansa_stock_comparison_token')
```

- [ ] **Step 5: Verifikasi**

Run: `cd admin_backend && grep -rn "DEFAULT_.*TOKEN" backend/routes --include="*.py" | grep -v __pycache__; ./venv/bin/python -m pytest tests -q`
Expected: grep tidak menghasilkan baris apa pun (semua konstanta token hilang, konstanta URL tetap), pytest PASS semua.

- [ ] **Step 6: Commit**

```bash
git add -A admin_backend/backend/routes
git commit -m "refactor: token payroll & inventory baca via credentials service (DB→env)"
```

---

### Task 6: Refactor mailer, telegram, n8n ke credentials service

**Files:**
- Modify: `admin_backend/backend/services/mailer.py`
- Modify: `admin_backend/backend/services/notifications/telegram.py`
- Modify: `admin_backend/backend/routes/integrations/n8n_bp.py:60-76`
- Test: `admin_backend/tests/test_mailer.py` (tambah 1 test), `admin_backend/tests/test_telegram.py` (tambah 1 test), `tests/test_integrations_bp.py` (harus tetap PASS tanpa ubah)

**Interfaces:**
- Consumes: `get_credential_value(key)`, `get_credential(conn, key)` (Task 1).
- Produces: `mailer.get_smtp_config(conn=None)` — perilaku lama (env-only bila DB kosong) utuh; Telegram & n8n baca via service; n8n tetap fail-closed 503 saat kunci kosong.

- [ ] **Step 1: Write the failing tests**

Tambah di `admin_backend/tests/test_mailer.py` (file ini belum import pytest — tambahkan `import pytest` di atas, plus fixture isolasi DB agar `get_credential_value` tidak mencoba MySQL nyata; fixture ini juga melindungi test lama yang kini memanggil `get_smtp_config()` tanpa conn):

```python
@pytest.fixture(autouse=True)
def _no_db(monkeypatch):
    from backend.db import session as db_session
    monkeypatch.setattr(db_session, 'get_db_engine', lambda: (None, 'no db in unit test'))


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
```

Tambah di `admin_backend/tests/test_telegram.py`:

```python
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

    sent = telegram_module.notify_import_problem('dbs', 'f.pdf', 'parse_failed')
    assert sent is True
    assert 'db-token' in sent_requests[0]['url']
    assert 'env-token' not in sent_requests[0]['url']
```

Dan perluas file yang sama — fixture `cred_engine` untuk test baru + fixture isolasi `autouse` (melindungi test telegram lama dari percobaan MySQL nyata, karena `_is_configured`/`_send_message` kini lewat service):

```python
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
```

Catatan: fixture `autouse` dipatch duluan, lalu `test_db_token_menang_atas_env` mem-patch ulang `db_session.get_db_engine` ke `cred_engine` di dalam test — patch terakhir yang menang, dan `monkeypatch` mengembalikan semuanya setelah test.

- [ ] **Step 2: Run test to verify they fail**

Run: `cd admin_backend && ./venv/bin/python -m pytest tests/test_mailer.py tests/test_telegram.py -q`
Expected: 2 test baru FAIL (mailer.get_smtp_config belum punya param `conn`; telegram masih baca env mentah)

- [ ] **Step 3: Implement mailer**

`mailer.py` — ganti `get_smtp_config` dan tambah import:

```python
from backend.services import credentials as credentials_service


def get_smtp_config(conn=None):
    """Konfigurasi SMTP: DB (app_settings) dulu → env fallback.

    `conn` opsional — tanpa conn, service membuka koneksi pendek sendiri (fail-soft).
    """
    def _get(key):
        if conn is not None:
            value, _ = credentials_service.get_credential(conn, key)
            if value:
                return value
        return credentials_service.get_credential_value(key)

    try:
        port = int(_get('smtp_port') or '587')
    except ValueError:
        port = 587
    return {
        'host': _get('smtp_host').strip(),
        'port': port,
        'user': _get('smtp_user').strip(),
        'password': _get('smtp_pass'),
        'from': _get('smtp_from').strip(),
        'use_tls': (_get('smtp_use_tls') or 'true').strip().lower()
        not in {'0', 'false', 'no'},
    }
```

Catatan: `send_reset_email` tidak berubah (memanggil `get_smtp_config()` tanpa conn). Pesan dev-fallback "SMTP_HOST not set" diganti teks:

```python
        logger.warning(
            'SMTP not configured (Settings → API Keys atau env); reset link for %s logged instead of emailed: %s',
            to_email, reset_link,
        )
```

- [ ] **Step 4: Implement telegram**

`telegram.py` — update docstring bagian konfigurasi:

```python
Prinsip: notifikasi adalah pelengkap, bukan bagian kritis — kegagalan mengirim
apapun penyebabnya (kredensial belum diisi, jaringan, API Telegram) tidak boleh
menggagalkan import statement. Kredensial dibaca dari vault (DB → env fallback):
  - telegram_bot_token: token dari @BotFather
  - telegram_chat_id:   chat tujuan (dari @userinfobot atau getUpdates)
```

ganti import + kedua fungsi:

```python
from backend.services import credentials as credentials_service


def _is_configured():
    return bool(credentials_service.get_credential_value('telegram_bot_token').strip()) and bool(
        credentials_service.get_credential_value('telegram_chat_id').strip()
    )


def _send_message(text):
    """Kirim pesan teks via Bot API. Return True jika terkirim, False jika tidak."""
    token = credentials_service.get_credential_value('telegram_bot_token').strip()
    chat_id = credentials_service.get_credential_value('telegram_chat_id').strip()
    if not token or not chat_id:
        logger.info('Telegram belum dikonfigurasi — notifikasi dilewati')
        return False
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    data = json.dumps({'chat_id': chat_id, 'text': text}).encode('utf-8')
    request = _Request(  # URL dibangun dari kredensial vault, bukan input user
        url, data=data,
        headers={'Content-Type': 'application/json'}, method='POST',
    )
    try:
        with _urlopen(request, timeout=_TELEGRAM_TIMEOUT) as response:
            response.read()
            return int(getattr(response, 'status', 200)) == 200
    except Exception:
        logger.warning('Gagal mengirim notifikasi Telegram', exc_info=True)
        return False
```

(`import os` di dalam kedua fungsi dihapus — tidak dipakai lagi.)

- [ ] **Step 5: Implement n8n**

`n8n_bp.py` — tambah import:

```python
from backend.services import credentials as credentials_service
```

di `_require_api_key` ganti pembacaan env:

```python
    expected = credentials_service.get_credential_value('integration_api_key').strip()
```

dan update docstring fungsi:

```python
    """Autentikasi server-to-server: header X-API-Key vs kredensial integration_api_key.

    Sumber nilai: Settings → API Keys (app_settings) dengan fallback env
    INTEGRATION_API_KEY. Fail closed: tanpa kunci endpoint mati total (503),
    bukan terbuka tanpa autentikasi.
    """
```

Pesan log `logger.error('INTEGRATION_API_KEY belum diset ...')` diganti:

```python
        logger.error('integration_api_key belum diset — endpoint integrasi nonaktif')
```

- [ ] **Step 6: Run tests**

Run: `cd admin_backend && ./venv/bin/python -m pytest tests/test_mailer.py tests/test_telegram.py tests/test_integrations_bp.py -q`
Expected: PASS semua (termasuk test integrasi lama yang memakai env `INTEGRATION_API_KEY` — fallback env terjaga)

- [ ] **Step 7: Commit**

```bash
git add admin_backend/backend/services/mailer.py admin_backend/backend/services/notifications/telegram.py admin_backend/backend/routes/integrations/n8n_bp.py admin_backend/tests/test_mailer.py admin_backend/tests/test_telegram.py
git commit -m "refactor: mailer/telegram/n8n baca kredensial via credentials service"
```

---

### Task 7: Frontend — `credentialsApi` + komponen `CredentialsSettings.vue` + tab baru

**Files:**
- Modify: `admin_frontend/src/api/index.js` (tambah `credentialsApi` setelah `aiApi`)
- Create: `admin_frontend/src/components/settings/CredentialsSettings.vue`
- Modify: `admin_frontend/src/views/SettingsView.vue` (tombol tab, import, render)

**Interfaces:**
- Consumes: endpoint Task 3 — `GET /api/credentials`, `PUT /api/credentials`, `POST /api/credentials/<key>/test`.
- Produces: tab `apiKeys` di SettingsView. Task 8 menambah tombol "buka tab API Keys" dari AiSettings via event `go-to-api-keys` yang ditangani di sini.

- [ ] **Step 1: Tambah `credentialsApi` ke api client**

Di `admin_frontend/src/api/index.js`, setelah blok `aiApi` (± baris 585):

```js
export const credentialsApi = {
  list() {
    return api.get('/credentials');
  },
  save(updates) {
    return api.put('/credentials', { updates });
  },
  test(key, data = {}) {
    return api.post(`/credentials/${key}/test`, data);
  },
};
```

- [ ] **Step 2: Buat komponen `CredentialsSettings.vue`**

Buat `admin_frontend/src/components/settings/CredentialsSettings.vue`:

```vue
<template>
  <div class="space-y-6">
    <p v-if="isLoading" class="field-hint flex items-center gap-2" role="status">
      <i class="bi bi-arrow-repeat animate-spin"></i>
      Memuat kredensial...
    </p>

    <SectionCard
      v-for="group in groups"
      :key="group.id"
      :title="group.title"
      :subtitle="group.subtitle"
      body-class="p-6"
    >
      <div class="space-y-5">
        <div v-for="cred in byGroup[group.id] || []" :key="cred.key" class="field-stack">
          <label class="label-base" :for="`cred-${cred.key}`">{{ cred.label }}</label>
          <div class="flex flex-wrap items-center gap-2">
            <TextInput
              :id="`cred-${cred.key}`"
              v-model="form[cred.key]"
              :type="cred.secret ? 'password' : 'text'"
              autocomplete="off"
              :placeholder="placeholderFor(cred)"
              class="flex-1 min-w-[220px]"
            >
              <template #leading>
                <i class="bi bi-key-fill text-gray-400 dark:text-gray-500"></i>
              </template>
            </TextInput>
            <span
              v-if="cred.set"
              class="whitespace-nowrap rounded-full px-2.5 py-1 text-[11px] font-bold"
              :class="cred.source === 'env'
                ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200'
                : 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200'"
              :title="cred.source === 'env'
                ? 'Nilai masih dibaca dari environment — klik Simpan untuk memindahkan ke database.'
                : 'Tersimpan di database.'"
            >
              {{ cred.source === 'env' ? 'dari env' : 'tersimpan' }}
            </span>
            <button
              v-if="cred.test"
              type="button"
              class="text-xs font-bold text-primary hover:underline disabled:opacity-50"
              :disabled="isTesting === cred.key"
              @click="handleTest(cred)"
            >
              {{ isTesting === cred.key ? 'Menguji...' : 'Test' }}
            </button>
            <button
              v-if="cred.secret && cred.set && !isDirtySecret(cred)"
              type="button"
              class="text-xs font-bold text-danger hover:underline disabled:opacity-50"
              :disabled="isSaving"
              title="Hapus nilai yang tersimpan"
              @click="markClear(cred)"
            >
              Hapus
            </button>
          </div>
          <p class="field-hint">{{ hintFor(cred) }}</p>
          <p
            v-if="testStatus[cred.key]"
            class="text-xs font-bold flex items-center gap-1.5"
            :class="testStatus[cred.key].ok
              ? 'text-emerald-600 dark:text-emerald-400'
              : 'text-danger'"
          >
            <i :class="testStatus[cred.key].ok ? 'bi bi-check-circle' : 'bi bi-x-circle'"></i>
            {{ testStatus[cred.key].message }}
          </p>
        </div>

        <div class="flex items-center justify-between gap-3 pt-1">
          <p v-if="groupError[group.id]" class="text-xs font-bold text-danger">{{ groupError[group.id] }}</p>
          <span v-else></span>
          <button
            type="button"
            class="rounded-xl bg-primary px-4 py-2.5 text-sm font-bold text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="isSaving"
            @click="handleSaveGroup(group.id)"
          >
            {{ isSaving ? 'Menyimpan...' : 'Simpan' }}
          </button>
        </div>
      </div>
    </SectionCard>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue';

import { credentialsApi } from '../../api';
import SectionCard from '../ui/SectionCard.vue';
import TextInput from '../ui/TextInput.vue';
import { useNotifications } from '../../composables/useNotifications';

const notify = useNotifications();

const CLEAR = '__CLEAR__';

const groups = [
  {
    id: 'sagansa',
    title: 'Sagansa Superadmin API',
    subtitle: 'Token untuk menarik presensi, stok, dan data penjualan dari superadmin.sagansa.id.',
  },
  {
    id: 'ai',
    title: 'AI Provider',
    subtitle: 'API key provider AI cloud. Provider, base URL, dan model diatur di tab AI.',
  },
  {
    id: 'telegram',
    title: 'Telegram Notifikasi',
    subtitle: 'Notifikasi masalah pipeline e-statement ke chat Telegram Anda.',
  },
  {
    id: 'smtp',
    title: 'Email SMTP',
    subtitle: 'Dipakai untuk mengirim email reset password.',
  },
  {
    id: 'n8n',
    title: 'n8n Integration',
    subtitle: 'Kunci yang wajib dikirim n8n pada header X-API-Key. Tanpa kunci, endpoint integrasi nonaktif.',
  },
];

const credentials = ref([]);
const form = reactive({});
const originals = reactive({});
const clearFlags = reactive(new Set());
const testStatus = reactive({});
const groupError = reactive({});
const isLoading = ref(true);
const isSaving = ref(false);
const isTesting = ref('');

const byGroup = computed(() => {
  const map = {};
  for (const cred of credentials.value) {
    (map[cred.group] ||= []).push(cred);
  }
  return map;
});

const placeholderFor = (cred) => (cred.set
  ? 'Tersimpan — isi untuk mengganti'
  : 'Belum diisi — tempel nilai di sini');

const isDirtySecret = (cred) => Boolean(String(form[cred.key] || '').trim());

const hintFor = (cred) => {
  if (!cred.secret) return '';
  if (clearFlags.has(cred.key)) return 'Akan dihapus saat Anda menekan Simpan.';
  if (isDirtySecret(cred)) return 'Nilai baru akan tersimpan saat Anda menekan Simpan.';
  if (cred.set) return 'Kunci tersimpan di server dan tidak pernah ditampilkan kembali.';
  return 'Belum diisi — fitur terkait tidak berfungsi sampai kunci diisi.';
};

const applyStatus = (items) => {
  credentials.value = items;
  for (const cred of items) {
    originals[cred.key] = cred.secret ? '' : String(cred.value ?? '');
    if (!(cred.key in form)) {
      form[cred.key] = cred.secret ? '' : String(cred.value ?? '');
    }
    if (clearFlags.has(cred.key) && !cred.set) clearFlags.delete(cred.key);
  }
};

const load = async () => {
  isLoading.value = true;
  try {
    const { data } = await credentialsApi.list();
    applyStatus(data.credentials || []);
  } catch (err) {
    notify.error('Gagal memuat kredensial. Coba muat ulang halaman.');
  } finally {
    isLoading.value = false;
  }
};

const markClear = (cred) => {
  clearFlags.add(cred.key);
  form[cred.key] = '';
};

const buildUpdates = (groupId) => {
  const updates = {};
  for (const cred of byGroup.value[groupId] || []) {
    const value = String(form[cred.key] ?? '').trim();
    if (clearFlags.has(cred.key)) {
      updates[cred.key] = CLEAR;
    } else if (cred.secret) {
      if (value) updates[cred.key] = value;
    } else if (value !== String(originals[cred.key] ?? '')) {
      updates[cred.key] = value;
    }
  }
  return updates;
};

const handleSaveGroup = async (groupId) => {
  groupError[groupId] = '';
  const updates = buildUpdates(groupId);
  if (!Object.keys(updates).length) {
    notify.info('Tidak ada perubahan untuk disimpan.');
    return;
  }
  isSaving.value = true;
  try {
    const { data } = await credentialsApi.save(updates);
    applyStatus(data.credentials || []);
    // field secret kosongkan setelah simpan; nilai non-secret resinkron
    for (const cred of data.credentials || []) {
      form[cred.key] = cred.secret ? '' : String(cred.value ?? '');
    }
    for (const key of Object.keys(updates)) delete testStatus[key];
    notify.success('Kredensial tersimpan.');
  } catch (err) {
    groupError[groupId] = err.response?.data?.error || 'Gagal menyimpan kredensial. Coba lagi.';
  } finally {
    isSaving.value = false;
  }
};

const handleTest = async (cred) => {
  testStatus[cred.key] = null;
  isTesting.value = cred.key;
  try {
    const body = {};
    const typed = String(form[cred.key] ?? '').trim();
    if (typed) body.value = typed;
    const extra = {};
    if (cred.test === 'telegram') {
      const chatId = String(form.telegram_chat_id ?? '').trim();
      if (chatId) extra.telegram_chat_id = chatId;
    } else if (cred.test === 'smtp') {
      for (const key of ['smtp_host', 'smtp_port', 'smtp_user', 'smtp_pass', 'smtp_from', 'smtp_use_tls']) {
        const v = String(form[key] ?? '').trim();
        if (v) extra[key] = v;
      }
    }
    if (Object.keys(extra).length) body.extra = extra;
    const { data } = await credentialsApi.test(cred.key, body);
    testStatus[cred.key] = { ok: Boolean(data.ok), message: data.message };
  } catch (err) {
    testStatus[cred.key] = {
      ok: false,
      message: err.response?.data?.error || 'Test gagal dijalankan.',
    };
  } finally {
    isTesting.value = '';
  }
};

onMounted(load);
</script>
```

- [ ] **Step 3: Daftarkan tab di `SettingsView.vue`**

1. Tombol tab — sisipkan **sebelum** tab General (setelah blok tab "Report Details"):

```html
            <button
              @click="activeTab = 'apiKeys'"
              class="settings-tab"
              :class="{ 'settings-tab--active': activeTab === 'apiKeys' }"
            >
              <i class="bi bi-key-fill mr-2"></i>
              API Keys
            </button>
```

2. Import (bersama import komponen settings lain):

```js
import CredentialsSettings from '../components/settings/CredentialsSettings.vue';
```

3. Render (tambahkan blok `v-else-if` baru bersama blok tab lain):

```html
      <div v-else-if="activeTab === 'apiKeys'">
        <credentials-settings />
      </div>
```

4. Tambahkan listener event pada elemen `<ai-settings />` yang sudah ada (blok `activeTab === 'ai'`) — Task 8 akan men-emit event ini dari AiSettings:

```html
      <div v-else-if="activeTab === 'ai'">
        <ai-settings @go-to-api-keys="activeTab = 'apiKeys'" />
      </div>
```

- [ ] **Step 4: Verifikasi build**

Run: `cd admin_frontend && npm run build`
Expected: build sukses tanpa error (Peringatan ukuran chunk boleh diabaikan).

- [ ] **Step 5: Commit**

```bash
git add admin_frontend/src/api/index.js admin_frontend/src/components/settings/CredentialsSettings.vue admin_frontend/src/views/SettingsView.vue
git commit -m "feat(web): tab API Keys — kelola semua kredensial dari Settings"
```

---

### Task 8: Frontend — input API key pindah dari AiSettings ke vault

**Files:**
- Modify: `admin_frontend/src/components/settings/AiSettings.vue` (hapus field key + `clearApiKey` + pengiriman `api_key`; tambah info box + emit)

**Interfaces:**
- Consumes: `settings.api_key_set` dari `GET /api/ai/settings` (sudah ada); event `go-to-api-keys` ditangani SettingsView (Task 7).
- Produces: AiSettings tidak lagi mengirim/menerima `api_key` sama sekali.

- [ ] **Step 1: Template — ganti blok field API key dengan info box**

Di `AiSettings.vue`, hapus seluruh blok `<div v-if="needsApiKey" class="field-stack">` yang berisi label "API Key", `TextInput` `ai-api-key`, hint, dan tombol "Hapus kunci" (± baris 113–142). Ganti dengan:

```html
        <div
          v-if="needsApiKey"
          class="rounded-xl border p-4 transition-colors"
          :class="apiKeySet
            ? 'border-emerald-200 bg-emerald-50 dark:border-emerald-900/50 dark:bg-emerald-900/20'
            : 'border-amber-200 bg-amber-50 dark:border-amber-900/50 dark:bg-amber-900/20'"
        >
          <div class="flex flex-wrap items-center gap-3">
            <i class="bi text-base" :class="apiKeySet ? 'bi-shield-check text-emerald-600 dark:text-emerald-400' : 'bi-exclamation-triangle text-amber-600 dark:text-amber-400'"></i>
            <div class="flex-1 text-xs leading-relaxed" :class="apiKeySet ? 'text-emerald-800 dark:text-emerald-200' : 'text-amber-800 dark:text-amber-200'">
              <template v-if="apiKeySet">
                API key <strong>tersimpan</strong> dan tidak pernah ditampilkan kembali.
                Kelola (ganti/hapus) di tab <strong>API Keys</strong>.
              </template>
              <template v-else>
                API key <strong>belum diisi</strong> — provider cloud butuh kunci.
                Tempel kunci Anda di tab <strong>API Keys</strong>.
              </template>
            </div>
            <button
              type="button"
              class="text-xs font-bold text-primary hover:underline"
              @click="$emit('go-to-api-keys')"
            >
              Buka API Keys <i class="bi bi-arrow-right"></i>
            </button>
          </div>
        </div>
```

Dan tambahkan `defineEmits` di bagian script (sebelum/ sesudah `defineProps` jika ada; komponen ini `<script setup>` — tambahkan):

```js
defineEmits(['go-to-api-keys']);
```

- [ ] **Step 2: Script — bersihkan state api key**

1. Hapus dari `form`: `apiKey: ''` (biarkan properti lain).
2. Hapus `const API_KEY_CLEAR = '__CLEAR__';` dan `const apiKeyDirty = ref(false);`.
3. Hapus watch `form.apiKey` dan watch provider yang mengosongkan `form.apiKey`/`apiKeyDirty` (di watch provider, hapus dua baris itu; sisanya — reset model & testStatus — tetap).
4. Di `handleTestConnection`: hapus kondisi `if (needsApiKey.value && apiKeyDirty.value && form.apiKey.trim()) payload.api_key = form.apiKey.trim();` dan baris `if (needsApiKey.value && apiKeySet.value && form.apiKey.trim()) payload.api_key = form.apiKey.trim();` di `onMounted` (backend sudah otomatis memakai kunci tersimpan bila `api_key` tidak dikirim).
5. Di `handleSave`: hapus validasi `if (needsApiKey.value && !apiKeySet.value && !form.apiKey.trim())`, pengiriman `if (apiKeyDirty.value && form.apiKey.trim()) payload.api_key = ...`, dan `form.apiKey = ''` setelah sukses.
6. Hapus seluruh fungsi `clearApiKey`.

- [ ] **Step 3: Verifikasi build**

Run: `cd admin_frontend && npm run build`
Expected: build sukses tanpa error dan tanpa warning referensi variabel yang dihapus.

- [ ] **Step 4: Commit**

```bash
git add admin_frontend/src/components/settings/AiSettings.vue
git commit -m "refactor(web): API key AI dikelola di tab API Keys — tab AI menampilkan status"
```

---

### Task 9: Dokumentasi + verifikasi penuh + uji browser manual

**Files:**
- Modify: `admin_backend/README.md` (bagian kredensial)

**Interfaces:**
- Consumes: semua task sebelumnya sudah ter-commit.

- [ ] **Step 1: Update README backend**

Tambahkan bagian baru di `admin_backend/README.md` (setelah bagian setup/env yang ada; sesuaikan judul level dengan struktur file):

```markdown
## Kredensial (API Keys)

Semua API key/token aplikasi dikelola dari **Settings → API Keys** di admin panel:
token Sagansa superadmin (presence, remaining storage, stock monitoring, sales by
date, stock comparison), Telegram (bot token + chat id), SMTP (host/port/user/
password/from/TLS), kunci integrasi n8n, dan API key provider AI.

- Nilai disimpan di tabel `app_settings`; frontend hanya melihat status
  terisi/tidak — nilai secret tidak pernah ditampilkan kembali.
- **Environment variable tetap berfungsi sebagai fallback** (nama env = nama
  setting, mis. `SAGANSA_PRESENCE_TOKEN` = `sagansa_presence_token`). Nilai DB
  selalu menang atas env.
- Deployment lama: variabel env yang masih ada ditandai "dari env" di tab API
  Keys — tekan Simpan untuk memindahkannya ke database.
- Tombol **Test** menguji koneksi ke service tujuan (termasuk mengirim pesan tes
  Telegram / login SMTP) tanpa menyimpan nilai.
```

- [ ] **Step 2: Jalankan seluruh test backend**

Run: `cd admin_backend && ./venv/bin/python -m pytest tests -q`
Expected: PASS semua, tidak ada test gagal/skip baru.

- [ ] **Step 3: Build frontend**

Run: `cd admin_frontend && npm run build`
Expected: sukses.

- [ ] **Step 4: Uji browser manual end-to-end**

Jalankan dev servers: `cd admin_backend && ./venv/bin/python server.py` dan `cd admin_frontend && npm run dev`. Lalu di browser (login dulu):

1. Settings → tab **API Keys** muncul dengan 5 kartu grup.
2. Isi `telegram_chat_id` + tempel token Telegram (atau nilai dummy), klik **Simpan** → badge berubah "tersimpan", toast sukses.
3. Klik **Test** pada bot token → dengan token dummy: pesan gagal jelas (HTTP 401/bot token salah) — bukan error 500.
4. Klik **Hapus** pada secret lalu **Simpan** → badge hilang.
5. Tab **AI**: pilih provider z.ai → info box "API key belum diisi" + tombol **Buka API Keys** pindah tab; setelah kunci `ai_api_key` diisi via vault dan kembali ke tab AI → info box berubah "tersimpan".
6. Save AI settings dengan provider z.ai + kunci vault terisi → tersimpan tanpa error (regresi alur lama).
7. Bersihkan nilai uji yang tadi disimpan (Hapus + Simpan) agar DB dev bersih.

Expected: seluruh alur berjalan; tidak ada nilai secret yang tampil kembali di UI.

- [ ] **Step 5: Commit**

```bash
git add admin_backend/README.md
git commit -m "docs: kredensial dikelola via Settings → API Keys (env jadi fallback)"
```
