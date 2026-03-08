import json
from datetime import date, datetime
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest

from backend.routes.accounting_utils import normalize_iso_date_value


def _parse_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {'1', 'true', 'yes', 'y', 'on'}
    return False


def _normalize_iso_date(value):
    return normalize_iso_date_value(value)


def _normalize_db_cr(value, default='DB'):
    raw = str(value or '').strip().upper()
    if not raw:
        return default

    if raw in {'CR', 'CREDIT', 'KREDIT', 'K'}:
        return 'CR'
    if raw in {'DB', 'DEBIT', 'D', 'DE'}:
        return 'DB'

    if raw.startswith('CR') or 'CREDIT' in raw or raw.startswith('K'):
        return 'CR'
    if raw.startswith('DB') or raw.startswith('DE') or 'DEBIT' in raw:
        return 'DB'

    return default


def _safe_int(value, default=0):
    if value in (None, ''):
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _fetch_remote_json(api_url, token, query_params=None, resource_name='API'):
    params = {k: v for k, v in (query_params or {}).items() if v not in (None, '')}
    url = str(api_url or '').strip()
    if not url:
        raise RuntimeError(f'{resource_name} URL is required')

    if url.startswith('ttps://'):
        url = f"https://{url[len('ttps://'):]}"
    elif url.startswith('//'):
        url = f"https:{url}"
    elif not (url.startswith('https://') or url.startswith('http://')):
        url = f"https://{url.lstrip('/')}"

    if params:
        separator = '&' if '?' in url else '?'
        url = f"{url}{separator}{urlparse.urlencode(params)}"

    headers = {'Accept': 'application/json'}
    if token:
        headers['Authorization'] = f"Bearer {token}"

    req = urlrequest.Request(url, headers=headers, method='GET')
    try:
        with urlrequest.urlopen(req, timeout=60) as resp:
            raw_body = resp.read().decode('utf-8')
        return json.loads(raw_body)
    except urlerror.HTTPError as e:
        err_body = e.read().decode('utf-8', errors='ignore')
        raise RuntimeError(f"{resource_name} request failed ({e.code}): {err_body[:500]}")
    except urlerror.URLError as e:
        raise RuntimeError(f"{resource_name} connection failed: {e.reason}")
    except json.JSONDecodeError:
        raise RuntimeError(f'{resource_name} did not return valid JSON')


def _fetch_remote_presences(api_url, token, query_params=None):
    return _fetch_remote_json(
        api_url=api_url,
        token=token,
        query_params=query_params,
        resource_name='Presence API'
    )


def _to_float(value, default=0.0):
    if value in (None, ''):
        return default
    try:
        if isinstance(value, str):
            normalized = value.replace(',', '').strip()
            if normalized == '':
                return default
            return float(normalized)
        return float(value)
    except (TypeError, ValueError):
        return default
