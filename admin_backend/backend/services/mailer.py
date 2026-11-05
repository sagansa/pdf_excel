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
