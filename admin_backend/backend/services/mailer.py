"""SMTP sender for transactional emails (currently: password reset).

Dev fallback: when SMTP_HOST is not configured the message is not sent;
the reset link is written to the log instead so the flow stays testable.
"""
import logging
import smtplib
from email.message import EmailMessage

from backend.services import credentials as credentials_service

logger = logging.getLogger(__name__)


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


def send_reset_email(to_email, reset_link, display_name=''):
    config = get_smtp_config()
    if not config['host']:
        logger.warning(
            'SMTP not configured (Settings → API Keys atau env); reset link for %s logged instead of emailed: %s',
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
