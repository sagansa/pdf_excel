import hashlib
import logging
import os
import secrets
import time
from collections import defaultdict
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request, session
from sqlalchemy import text
from werkzeug.security import check_password_hash, generate_password_hash

from backend.errors import BadRequestError, TooManyRequestsError, UnauthorizedError
from backend.routes.accounting_utils import require_db_engine
from backend.services.mailer import send_reset_email

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth_bp', __name__)

# Simple in-memory throttling, keyed per (ip, identifier).
# Sufficient for a single-process gunicorn deployment; no external storage needed.
LOGIN_MAX_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 300
_failed_logins = defaultdict(list)

FORGOT_MAX_ATTEMPTS = 3
FORGOT_WINDOW_SECONDS = 900
_forgot_requests = defaultdict(list)

RESET_TOKEN_TTL_MINUTES = 30
MIN_PASSWORD_LENGTH = 8

# Active-user cache used by the global auth guard: recheck the DB at most every 5 minutes
# per user so deactivation takes effect without querying on every request.
_ACTIVE_CHECK_INTERVAL = 300
_active_user_cache = {}


def _client_ip():
    forwarded = request.headers.get('X-Forwarded-For', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.remote_addr or 'unknown'


def _normalize_email(value):
    return str(value or '').strip().lower()


def _too_many_attempts(key, store, max_attempts, window_seconds):
    now = time.time()
    attempts = [t for t in store[key] if now - t < window_seconds]
    store[key] = attempts
    return len(attempts) >= max_attempts


def _record_attempt(key, store):
    store[key].append(time.time())


def _session_user(row):
    return {
        'id': int(row['id']),
        'email': row['email'],
        'display_name': row['display_name'],
    }


def _is_active(row):
    return bool(row and int(row.get('is_active') or 0))


def _fetch_user_by_column(column, value):
    engine = require_db_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text(
                'SELECT id, email, display_name, password_hash, is_active, credential_version '
                f'FROM users WHERE {column} = :value'
            ),
            {'value': value},
        )
        return result.mappings().first()


def get_user_if_active(user_id):
    """Return the active user row for a session user_id, or None.

    Used by the global before_request guard. Results are cached briefly so
    disabling a user takes effect within _ACTIVE_CHECK_INTERVAL.
    """
    if user_id is None:
        return None
    now = time.time()
    cached = _active_user_cache.get(user_id)
    if cached is not None and now - cached[0] < _ACTIVE_CHECK_INTERVAL:
        return cached[1]

    row = _fetch_user_by_column('id', user_id)
    if not _is_active(row):
        row = None
    _active_user_cache[user_id] = (now, row)
    return row


@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    payload = request.get_json(silent=True) or {}
    email = _normalize_email(payload.get('email'))
    password = str(payload.get('password') or '')
    if not email or not password:
        raise BadRequestError('Email and password are required', code='credentials_missing')

    throttle_key = (_client_ip(), email)
    if _too_many_attempts(throttle_key, _failed_logins, LOGIN_MAX_ATTEMPTS, LOGIN_WINDOW_SECONDS):
        raise TooManyRequestsError(
            'Too many failed login attempts. Try again in a few minutes.'
        )

    user = _fetch_user_by_column('email', email)
    if not _is_active(user) or not check_password_hash(user['password_hash'], password):
        _record_attempt(throttle_key, _failed_logins)
        raise UnauthorizedError('Invalid email or password', code='invalid_credentials')

    _failed_logins.pop(throttle_key, None)
    session.clear()
    session.permanent = True
    session['user_id'] = int(user['id'])
    session['credential_version'] = int(user['credential_version'])
    return jsonify({'user': _session_user(user)})


def _hash_token(token):
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


_FORGOT_GENERIC_MESSAGE = 'If an account exists for that email, a reset link has been sent.'


@auth_bp.route('/api/auth/forgot-password', methods=['POST'])
def forgot_password():
    payload = request.get_json(silent=True) or {}
    email = _normalize_email(payload.get('email'))
    if not email:
        raise BadRequestError('Email is required', code='email_missing')

    throttle_key = (_client_ip(), email)
    if _too_many_attempts(throttle_key, _forgot_requests, FORGOT_MAX_ATTEMPTS, FORGOT_WINDOW_SECONDS):
        raise TooManyRequestsError('Too many reset requests. Try again later.')
    _record_attempt(throttle_key, _forgot_requests)

    user = _fetch_user_by_column('email', email)
    if _is_active(user):
        try:
            token = secrets.token_urlsafe(32)
            engine = require_db_engine()
            with engine.begin() as conn:
                conn.execute(
                    text('DELETE FROM password_reset_tokens WHERE user_id = :uid'),
                    {'uid': int(user['id'])},
                )
                conn.execute(
                    text(
                        'INSERT INTO password_reset_tokens (user_id, token_hash, expires_at) '
                        'VALUES (:uid, :token_hash, :expires_at)'
                    ),
                    {
                        'uid': int(user['id']),
                        'token_hash': _hash_token(token),
                        'expires_at': datetime.now() + timedelta(minutes=RESET_TOKEN_TTL_MINUTES),
                    },
                )
            base_url = (os.environ.get('APP_BASE_URL', '').strip() or request.url_root).rstrip('/')
            send_reset_email(email, f'{base_url}/reset-password?token={token}', user['display_name'])
        except Exception:
            # Jangan bocorkan keberadaan akun lewat error pengiriman.
            logger.exception('Failed to process password reset request for %s', email)

    return jsonify({'ok': True, 'message': _FORGOT_GENERIC_MESSAGE})


@auth_bp.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    payload = request.get_json(silent=True) or {}
    token = str(payload.get('token') or '').strip()
    new_password = str(payload.get('new_password') or '')
    if not token or not new_password:
        raise BadRequestError('Token and new password are required', code='reset_fields_missing')
    if len(new_password) < MIN_PASSWORD_LENGTH:
        raise BadRequestError(
            f'Password must be at least {MIN_PASSWORD_LENGTH} characters', code='password_too_short'
        )

    engine = require_db_engine()
    with engine.begin() as conn:
        row = conn.execute(
            text(
                'SELECT id, user_id FROM password_reset_tokens '
                'WHERE token_hash = :token_hash AND used_at IS NULL AND expires_at > :now'
            ),
            {'token_hash': _hash_token(token), 'now': datetime.now()},
        ).mappings().first()
        if row is None:
            raise BadRequestError('This reset link is invalid or has expired', code='invalid_token')

        conn.execute(
            text(
                'UPDATE users SET password_hash = :password_hash, '
                'credential_version = credential_version + 1 WHERE id = :uid'
            ),
            {'password_hash': generate_password_hash(new_password), 'uid': int(row['user_id'])},
        )
        marked = conn.execute(
            text(
                'UPDATE password_reset_tokens SET used_at = :now '
                'WHERE id = :id AND used_at IS NULL'
            ),
            {'now': datetime.now(), 'id': int(row['id'])},
        )
        if marked.rowcount == 0:
            raise BadRequestError('This reset link is invalid or has expired', code='invalid_token')
        conn.execute(
            text('DELETE FROM password_reset_tokens WHERE user_id = :uid'),
            {'uid': int(row['user_id'])},
        )

    # Buang cache guard agar sesi lama (credential_version beda) mati segera.
    _active_user_cache.pop(int(row['user_id']), None)
    return jsonify({'ok': True, 'message': 'Password updated. Please sign in with your new password.'})


@auth_bp.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'ok': True})


@auth_bp.route('/api/auth/me', methods=['GET'])
def me():
    user = _fetch_user_by_column('id', session.get('user_id'))
    if not _is_active(user):
        session.clear()
        raise UnauthorizedError('Not authenticated', code='not_authenticated')
    return jsonify({'user': _session_user(user)})
