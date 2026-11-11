"""Notifikasi Telegram untuk masalah pipeline e-statement (fail-soft).

Prinsip: notifikasi adalah pelengkap, bukan bagian kritis — kegagalan mengirim
apapun penyebabnya (kredensial belum diisi, jaringan, API Telegram) tidak boleh
menggagalkan import statement. Kredensial dibaca dari vault (DB → env fallback):
  - telegram_bot_token: token dari @BotFather
  - telegram_chat_id:   chat tujuan (dari @userinfobot atau getUpdates)
"""

import json
import logging
from urllib.request import Request as _Request, urlopen as _urlopen

from backend.services import credentials as credentials_service

logger = logging.getLogger(__name__)

_TELEGRAM_TIMEOUT = 10


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


def notify_import_problem(bank_type, filename, error_code, detail='', email_meta=None):
    """Notifikasi: import e-statement otomatis gagal. Return True jika terkirim."""
    email_meta = email_meta or {}
    lines = [
        '⚠️ Import e-statement gagal',
        f'Bank: {bank_type or "-"} | File: {filename or "-"}',
        f'Error: {error_code}',
    ]
    if detail:
        lines.append(f'Detail: {detail[:300]}')
    subject = (email_meta.get('email_subject') or '').strip()
    if subject:
        lines.append(f'Subject email: {subject}')
    message_id = (email_meta.get('email_message_id') or email_meta.get('message_id') or '').strip()
    if message_id:
        lines.append(f'Message-ID: {message_id}')
    lines.append('Cek n8n Executions / upload manual di esta.')
    return _send_message('\n'.join(lines))


def notify_missing_statements(missing):
    """Notifikasi: statement bulanan yang belum masuk. Return True jika terkirim."""
    if not missing:
        return False
    lines = ['📋 E-statement bulanan belum terdeteksi di esta:']
    for item in missing:
        label = item.get('display_name') or item.get('account_number') or '-'
        lines.append(
            f"• {item.get('month')} — {item.get('bank_code')} ({label})"
        )
    lines.append('Pastikan email statement masuk & workflow n8n sehat.')
    return _send_message('\n'.join(lines))
