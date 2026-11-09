"""Klien LLM lokal OpenAI-compatible (LM Studio / Ollama / server custom).

Semua request memakai stdlib urllib (konvensi repo — tanpa dependency baru).
Server AI berjalan di laptop user; data transaksi tidak pernah keluar dari mesin.
"""

import json
import os
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest

from sqlalchemy import text

DEFAULT_TIMEOUT = 120
LIST_MODELS_TIMEOUT = 15

# URL default per provider. LM Studio & Ollama berjalan lokal; z.ai adalah layanan
# cloud OpenAI-compatible (API key wajib) — deskripsi transaksi terkirim ke servernya.
PROVIDER_DEFAULT_BASE_URL = {
    'lmstudio': 'http://localhost:1234/v1',
    'ollama': 'http://localhost:11434/v1',
    'zai': 'https://api.z.ai/api/paas/v4',
    'custom': '',
}
PROVIDERS_NEEDING_API_KEY = {'zai'}

# Kunci yang disimpan/dibaca di tabel app_settings.
SETTING_KEYS = (
    'ai_enabled', 'ai_provider', 'ai_base_url', 'ai_model', 'ai_api_key',
    'ai_auto_apply', 'ai_auto_apply_threshold',
)
ALLOWED_PROVIDERS = ('lmstudio', 'ollama', 'zai', 'custom')
# Provider lokal yang nanti dipanggil langsung dari browser user (bukan dari server).
BRIDGE_PROVIDERS = {'lmstudio', 'ollama'}
DEFAULT_AUTO_APPLY_THRESHOLD = 0.9
API_KEY_CLEAR_SENTINEL = '__CLEAR__'


class LLMConnectionError(Exception):
    """Server AI lokal tidak dapat dihubungi atau menjawab tidak valid."""


def normalize_base_url(value):
    """Bersihkan base URL: trim, tambahkan scheme, buang slash di akhir."""
    url = str(value or '').strip()
    if not url:
        return ''
    if url.startswith('ttps://'):
        url = f'https://{url[len("ttps://"):]}'  # typo umum "h" hilang
    elif url.startswith('//'):
        url = f'https:{url}'
    elif not (url.startswith('https://') or url.startswith('http://')):
        url = f'http://{url}'
    return url.rstrip('/')


def _request_json(url, payload=None, timeout=DEFAULT_TIMEOUT, api_key=None):
    """POST/GET JSON ke server AI; balikan (status_code, data-dict)."""
    headers = {'Accept': 'application/json'}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'
    if payload is not None:
        data = json.dumps(payload).encode('utf-8')
        headers['Content-Type'] = 'application/json'
        req = urlrequest.Request(url, data=data, headers=headers, method='POST')
    else:
        req = urlrequest.Request(url, headers=headers, method='GET')
    try:
        with urlrequest.urlopen(req, timeout=timeout) as response:
            body = response.read().decode('utf-8', errors='replace')
            status = int(getattr(response, 'status', 200))
    except urlerror.HTTPError as exc:
        try:
            detail = exc.read().decode('utf-8', errors='replace')[:500]
        except Exception:
            detail = ''
        raise LLMConnectionError(f'Server AI menjawab HTTP {exc.code}: {detail}') from exc
    except urlerror.URLError as exc:
        raise LLMConnectionError(f'Server AI tidak dapat dihubungi: {exc.reason}') from exc
    except TimeoutError as exc:
        raise LLMConnectionError('Server AI tidak menjawab tepat waktu (timeout).') from exc

    try:
        return status, json.loads(body)
    except json.JSONDecodeError as exc:
        raise LLMConnectionError('Server AI menjawab respons yang bukan JSON valid.') from exc


def list_models(base_url, timeout=LIST_MODELS_TIMEOUT, api_key=None):
    """Ambil daftar model dari endpoint OpenAI-compatible {base_url}/models."""
    url = normalize_base_url(base_url)
    if not url:
        raise LLMConnectionError('Base URL server AI belum diatur.')
    _, data = _request_json(f'{url}/models', timeout=timeout, api_key=api_key)
    items = data.get('data') if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise LLMConnectionError('Respons daftar model tidak dikenali.')
    models = []
    for item in items:
        model_id = str(item.get('id') or '') if isinstance(item, dict) else str(item)
        if model_id:
            models.append(model_id)
    return models


def chat_completion(base_url, model, messages, temperature=0.1, timeout=DEFAULT_TIMEOUT, max_tokens=300, api_key=None):
    """Panggil {base_url}/chat/completions, balikan isi teks pesan pertama."""
    url = normalize_base_url(base_url)
    if not url:
        raise LLMConnectionError('Base URL server AI belum diatur.')
    if not model:
        raise LLMConnectionError('Model AI belum diatur.')

    payload = {
        'model': model,
        'messages': messages,
        'temperature': temperature,
        'max_tokens': max_tokens,
        'stream': False,
    }
    _, data = _request_json(f'{url}/chat/completions', payload=payload, timeout=timeout, api_key=api_key)
    try:
        message = data['choices'][0]['message']
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMConnectionError('Respons chat completion tidak memiliki isi yang diharapkan.') from exc

    content = str(message.get('content') or '').strip()
    if content:
        return content
    # Model reasoning (mis. gemma thinking via Ollama) bisa menghabiskan seluruh
    # token untuk proses berpikir di field terpisah — parser mencari JSON di dalamnya.
    reasoning = str(message.get('reasoning') or '').strip()
    if reasoning:
        return reasoning
    raise LLMConnectionError('Server AI mengembalikan isi pesan kosong.')


def get_ai_settings(conn):
    """Baca konfigurasi AI dari app_settings, dengan fallback .env dan default provider.

    Nilai ai_api_key TIDAK PERNAH dikembalikan mentah — hanya indikator api_key_set.
    """
    rows = conn.execute(text('SELECT setting_key, setting_value FROM app_settings')).fetchall()
    stored = {}
    for row in rows:
        mapping = row._mapping
        stored[str(mapping['setting_key'])] = mapping['setting_value']

    provider = str(stored.get('ai_provider') or '').strip().lower()
    if provider not in ALLOWED_PROVIDERS:
        provider = 'lmstudio'

    base_url = normalize_base_url(stored.get('ai_base_url'))
    if not base_url:
        base_url = normalize_base_url(os.environ.get('LLM_BASE_URL'))
    if not base_url:
        base_url = PROVIDER_DEFAULT_BASE_URL.get(provider, '')

    model = str(stored.get('ai_model') or '').strip()
    if not model:
        model = str(os.environ.get('LLM_MODEL') or '').strip()

    enabled_raw = str(stored.get('ai_enabled') or '').strip().lower()
    enabled = enabled_raw in {'1', 'true', 'yes', 'y', 'on'}

    auto_apply_raw = str(stored.get('ai_auto_apply') or '').strip().lower()
    auto_apply = auto_apply_raw in {'1', 'true', 'yes', 'y', 'on'}

    try:
        threshold = float(stored.get('ai_auto_apply_threshold'))
    except (TypeError, ValueError):
        threshold = DEFAULT_AUTO_APPLY_THRESHOLD
    threshold = max(0.0, min(1.0, threshold))

    api_key = str(stored.get('ai_api_key') or '')

    return {
        'enabled': enabled,
        'provider': provider,
        'base_url': base_url,
        'model': model,
        'timeout': DEFAULT_TIMEOUT,
        'auto_apply': auto_apply,
        'auto_apply_threshold': threshold,
        'bridge': provider in BRIDGE_PROVIDERS,
        'api_key': api_key,           # untuk pemakaian internal server (LLM call)
        'api_key_set': bool(api_key),  # untuk frontend — nilai kunci tidak diekspos
    }


def save_ai_settings(conn, payload):
    """Simpan konfigurasi AI ke app_settings (upsert, aman untuk MySQL & SQLite).

    api_key: None → tidak diubah; API_KEY_CLEAR_SENTINEL → hapus; string lain → nilai baru.
    """
    values = {
        'ai_enabled': 'true' if payload.get('enabled') else 'false',
        'ai_provider': payload.get('provider'),
        'ai_base_url': payload.get('base_url'),
        'ai_model': payload.get('model'),
        'ai_auto_apply': 'true' if payload.get('auto_apply') else 'false',
        'ai_auto_apply_threshold': str(payload.get('auto_apply_threshold')),
    }
    for key in SETTING_KEYS:
        if key == 'ai_api_key':
            continue  # ditangani terpisah di bawah
        value = values.get(key)
        if conn.dialect.name == 'sqlite':
            conn.execute(text(
                'INSERT INTO app_settings (setting_key, setting_value) '
                'VALUES (:key, :value) '
                'ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value'
            ), {'key': key, 'value': value})
        else:
            conn.execute(text(
                'INSERT INTO app_settings (setting_key, setting_value) '
                'VALUES (:key, :value) '
                'ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)'
            ), {'key': key, 'value': value})

    api_key = payload.get('api_key')
    if api_key is not None:
        new_value = '' if api_key == API_KEY_CLEAR_SENTINEL else str(api_key)
        if conn.dialect.name == 'sqlite':
            conn.execute(text(
                'INSERT INTO app_settings (setting_key, setting_value) '
                'VALUES (:key, :value) '
                'ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value'
            ), {'key': 'ai_api_key', 'value': new_value})
        else:
            conn.execute(text(
                'INSERT INTO app_settings (setting_key, setting_value) '
                'VALUES (:key, :value) '
                'ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)'
            ), {'key': 'ai_api_key', 'value': new_value})

    settings = get_ai_settings(conn)
    settings.pop('api_key', None)  # jangan pernah balikkan kunci ke pemanggil
    return settings
