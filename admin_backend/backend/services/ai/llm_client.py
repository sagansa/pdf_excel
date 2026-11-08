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

DEFAULT_TIMEOUT = 60
LIST_MODELS_TIMEOUT = 15

# URL default per provider (endpoint OpenAI-compatible masing-masing).
PROVIDER_DEFAULT_BASE_URL = {
    'lmstudio': 'http://localhost:1234/v1',
    'ollama': 'http://localhost:11434/v1',
    'custom': '',
}

# Kunci yang disimpan/dibaca di tabel app_settings.
SETTING_KEYS = ('ai_enabled', 'ai_provider', 'ai_base_url', 'ai_model')
ALLOWED_PROVIDERS = ('lmstudio', 'ollama', 'custom')


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


def _request_json(url, payload=None, timeout=DEFAULT_TIMEOUT):
    """POST/GET JSON ke server AI lokal; balikan (status_code, data-dict)."""
    headers = {'Accept': 'application/json'}
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


def list_models(base_url, timeout=LIST_MODELS_TIMEOUT):
    """Ambil daftar model dari endpoint OpenAI-compatible {base_url}/models."""
    url = normalize_base_url(base_url)
    if not url:
        raise LLMConnectionError('Base URL server AI belum diatur.')
    _, data = _request_json(f'{url}/models', timeout=timeout)
    items = data.get('data') if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise LLMConnectionError('Respons daftar model tidak dikenali.')
    models = []
    for item in items:
        model_id = str(item.get('id') or '') if isinstance(item, dict) else str(item)
        if model_id:
            models.append(model_id)
    return models


def chat_completion(base_url, model, messages, temperature=0.1, timeout=DEFAULT_TIMEOUT, max_tokens=300):
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
    _, data = _request_json(f'{url}/chat/completions', payload=payload, timeout=timeout)
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
    """Baca konfigurasi AI dari app_settings, dengan fallback .env dan default provider."""
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

    return {
        'enabled': enabled,
        'provider': provider,
        'base_url': base_url,
        'model': model,
        'timeout': DEFAULT_TIMEOUT,
    }


def save_ai_settings(conn, payload):
    """Simpan konfigurasi AI ke app_settings (upsert, aman untuk MySQL & SQLite)."""
    values = {
        'ai_enabled': 'true' if payload.get('enabled') else 'false',
        'ai_provider': payload.get('provider'),
        'ai_base_url': payload.get('base_url'),
        'ai_model': payload.get('model'),
    }
    for key in SETTING_KEYS:
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
    return get_ai_settings(conn)
