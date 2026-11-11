"""Endpoint vault kredensial: list status, bulk save, test koneksi.

Semua endpoint dilindungi guard login global (server.py before_request).
Nilai secret tidak pernah dikirim balik ke klien — lihat services/credentials.py.
"""

from flask import Blueprint, jsonify, request

from backend.errors import BadRequestError
from backend.routes.accounting_utils import require_db_engine
from backend.services import credentials as credentials_service

credentials_bp = Blueprint('credentials_bp', __name__)


@credentials_bp.route('/api/credentials', methods=['GET'])
def list_credentials():
    return jsonify({'credentials': credentials_service.get_status()})


@credentials_bp.route('/api/credentials', methods=['PUT'])
def update_credentials():
    updates = (request.json or {}).get('updates')
    if not isinstance(updates, dict) or not updates:
        raise BadRequestError(
            'Body harus berisi updates: {key: nilai baru atau "__CLEAR__"}',
            code='credentials_updates_missing',
        )
    unknown = set(updates) - credentials_service.CREDENTIAL_KEYS
    if unknown:
        raise BadRequestError(
            f'Kredensial tidak dikenal: {", ".join(sorted(unknown))}',
            code='credentials_unknown_key',
        )
    engine = require_db_engine()
    with engine.begin() as conn:
        status = credentials_service.save_credentials(conn, updates)
    return jsonify({'credentials': status, 'message': 'Kredensial tersimpan.'})


@credentials_bp.route('/api/credentials/<key>/test', methods=['POST'])
def test_credential(key):
    if key not in credentials_service.CREDENTIAL_KEYS:
        raise BadRequestError(f'Kredensial tidak dikenal: {key}', code='credentials_unknown_key')
    data = request.json or {}
    ok, message = credentials_service.run_test(
        key, value=data.get('value'), extra=data.get('extra'),
    )
    return jsonify({'ok': ok, 'message': message})
