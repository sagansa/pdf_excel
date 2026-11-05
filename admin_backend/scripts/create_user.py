"""Create or reset a login user for the esta admin backend.

Usage (from admin_backend/):
    venv/bin/python scripts/create_user.py <username> <display_name>

Prompts for a password (hidden input). If the username already exists,
the password and display name are updated and the account re-activated.
"""
import getpass
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


def main():
    if len(sys.argv) != 3:
        print(f'Usage: {sys.argv[0]} <username> <display_name>')
        sys.exit(1)

    username = sys.argv[1].strip()
    display_name = sys.argv[2].strip()
    if not username or not display_name:
        print('Username dan display name tidak boleh kosong.')
        sys.exit(1)

    password = getpass.getpass(f'Password untuk {username}: ')
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
            text('SELECT id FROM users WHERE username = :username'),
            {'username': username},
        ).first()
        if existing:
            conn.execute(
                text(
                    'UPDATE users SET password_hash = :password_hash, '
                    'display_name = :display_name, is_active = 1 WHERE id = :id'
                ),
                {'password_hash': password_hash, 'display_name': display_name, 'id': existing[0]},
            )
            print(f'User {username} diperbarui (password direset, akun diaktifkan).')
        else:
            conn.execute(
                text(
                    'INSERT INTO users (username, password_hash, display_name) '
                    'VALUES (:username, :password_hash, :display_name)'
                ),
                {'username': username, 'password_hash': password_hash, 'display_name': display_name},
            )
            print(f'User {username} dibuat.')


if __name__ == '__main__':
    main()
