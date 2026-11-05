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
                    'display_name = :display_name, is_active = 1, '
                    'credential_version = credential_version + 1 WHERE id = :id'
                ),
                {'password_hash': password_hash, 'display_name': display_name, 'id': existing[0]},
            )
            conn.execute(
                text('DELETE FROM password_reset_tokens WHERE user_id = :id'),
                {'id': existing[0]},
            )
            print(f'User {email} diperbarui (password direset, token reset dihapus, akun diaktifkan).')
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
