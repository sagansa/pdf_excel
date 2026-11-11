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
