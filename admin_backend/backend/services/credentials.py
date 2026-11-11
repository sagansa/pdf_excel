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
            return False, f'HTTP {exc.code} — token ditolak server (tidak valid atau tidak berlaku).'
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
