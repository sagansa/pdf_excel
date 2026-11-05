import logging
import time
from collections import defaultdict

from flask import Blueprint, jsonify, request, session
from sqlalchemy import text
from werkzeug.security import check_password_hash

from backend.errors import BadRequestError, TooManyRequestsError, UnauthorizedError
from backend.routes.accounting_utils import require_db_engine

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth_bp', __name__)

# Simple in-memory login throttling: max 5 failed attempts per (ip, username) per 5 minutes.
# Sufficient for a single-process gunicorn deployment; no external storage needed.
LOGIN_MAX_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 300
_failed_logins = defaultdict(list)

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


def _too_many_attempts(key):
    now = time.time()
    attempts = [t for t in _failed_logins[key] if now - t < LOGIN_WINDOW_SECONDS]
    _failed_logins[key] = attempts
    return len(attempts) >= LOGIN_MAX_ATTEMPTS


def _record_failed_attempt(key):
    _failed_logins[key].append(time.time())


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
    if _too_many_attempts(throttle_key):
        raise TooManyRequestsError(
            'Too many failed login attempts. Try again in a few minutes.'
        )

    user = _fetch_user_by_column('email', email)
    if not _is_active(user) or not check_password_hash(user['password_hash'], password):
        _record_failed_attempt(throttle_key)
        raise UnauthorizedError('Invalid email or password', code='invalid_credentials')

    _failed_logins.pop(throttle_key, None)
    session.clear()
    session.permanent = True
    session['user_id'] = int(user['id'])
    session['credential_version'] = int(user['credential_version'])
    return jsonify({'user': _session_user(user)})


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
