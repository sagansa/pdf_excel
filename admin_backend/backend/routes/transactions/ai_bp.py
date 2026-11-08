"""Endpoint AI mark assist: konfigurasi LLM lokal, tes koneksi, saran mark, keputusan review.

Semua endpoint dilindungi guard auth global di server.py (before_request).
"""

from datetime import datetime

from flask import Blueprint, jsonify, request
from sqlalchemy import text

from backend.errors import BadRequestError, ServiceUnavailableError
from backend.routes.accounting_utils import require_db_engine
from backend.routes.route_utils import _normalize_db_cr, _parse_bool
from backend.services.ai import llm_client, mark_suggester

ai_bp = Blueprint('ai_bp', __name__)

# Batas transaksi per request: tiap transaksi = 1 panggilan LLM lokal.
MAX_SUGGEST_BATCH = 15


def _validate_settings_payload(data):
    enabled = _parse_bool(data.get('enabled'))
    provider = str(data.get('provider') or '').strip().lower()
    if provider not in llm_client.ALLOWED_PROVIDERS:
        raise BadRequestError('Provider tidak dikenal. Pilih LM Studio, Ollama, atau Custom.')

    base_url = llm_client.normalize_base_url(data.get('base_url'))
    if not base_url:
        raise BadRequestError('Base URL server AI wajib diisi.')
    if not (base_url.startswith('https://') or base_url.startswith('http://')):
        raise BadRequestError('Base URL harus berupa URL http/https yang valid.')

    model = str(data.get('model') or '').strip()
    if len(model) > 120:
        raise BadRequestError('Nama model terlalu panjang (maksimal 120 karakter).')

    return {
        'enabled': enabled,
        'provider': provider,
        'base_url': base_url,
        'model': model,
    }


@ai_bp.route('/api/ai/settings', methods=['GET'])
def get_ai_settings():
    engine = require_db_engine()
    with engine.connect() as conn:
        settings = llm_client.get_ai_settings(conn)
    return jsonify({'settings': settings})


@ai_bp.route('/api/ai/settings', methods=['PUT'])
def update_ai_settings():
    data = request.json or {}
    payload = _validate_settings_payload(data)
    engine = require_db_engine()
    with engine.begin() as conn:
        settings = llm_client.save_ai_settings(conn, payload)
    return jsonify({'settings': settings, 'message': 'Pengaturan AI tersimpan.'})


@ai_bp.route('/api/ai/test-connection', methods=['POST'])
def test_ai_connection():
    data = request.json or {}
    engine = require_db_engine()
    base_url = llm_client.normalize_base_url(data.get('base_url'))
    model = str(data.get('model') or '').strip()
    if not base_url:
        with engine.connect() as conn:
            settings = llm_client.get_ai_settings(conn)
        base_url = settings['base_url']
    if not base_url:
        raise BadRequestError('Base URL server AI belum diatur.')

    try:
        models = llm_client.list_models(base_url)
    except llm_client.LLMConnectionError as exc:
        raise ServiceUnavailableError(
            f'Tidak dapat terhubung ke server AI di {base_url}: {exc}',
            code='ai_unreachable',
        ) from exc

    model_found = bool(model) and model in models
    return jsonify({
        'ok': True,
        'base_url': base_url,
        'models': models,
        'model_found': model_found,
        'message': (
            f'Koneksi berhasil. {len(models)} model tersedia.'
            if models else 'Koneksi berhasil, namun belum ada model yang dimuat.'
        ),
    })


@ai_bp.route('/api/transactions/ai-suggest', methods=['POST'])
def ai_suggest_marks():
    data = request.json or {}
    raw_ids = data.get('transaction_ids')
    if not isinstance(raw_ids, list) or not raw_ids:
        raise BadRequestError('transaction_ids wajib berupa daftar id transaksi.')
    txn_ids = []
    for value in raw_ids:
        txn_id = str(value or '').strip()
        if txn_id and txn_id not in txn_ids:
            txn_ids.append(txn_id)
    if not txn_ids:
        raise BadRequestError('transaction_ids tidak berisi id yang valid.')
    if len(txn_ids) > MAX_SUGGEST_BATCH:
        raise BadRequestError(
            f'Maksimal {MAX_SUGGEST_BATCH} transaksi per permintaan. '
            'Kirim dalam beberapa batch kecil.'
        )

    engine = require_db_engine()
    now = datetime.now()
    results = []
    candidates_by_direction = {}

    with engine.begin() as conn:
        mark_suggester.ensure_ai_columns(conn)
        config = llm_client.get_ai_settings(conn)
        if not config['enabled']:
            raise BadRequestError(
                'Fitur AI belum diaktifkan di pengaturan.',
                code='ai_disabled',
            )
        if not config['model']:
            raise BadRequestError(
                'Model AI belum diatur di pengaturan.',
                code='ai_model_missing',
            )

        for txn_id in txn_ids:
            txn = mark_suggester.get_transaction(conn, txn_id)
            if txn is None:
                results.append({'id': txn_id, 'status': 'skipped', 'reason': 'Transaksi tidak ditemukan'})
                continue
            try:
                mark_suggester.ensure_markable(conn, txn_id)
            except BadRequestError as exc:
                results.append({'id': txn_id, 'status': 'skipped', 'reason': exc.message})
                continue

            direction = _normalize_db_cr(txn.get('db_cr'))
            if direction not in candidates_by_direction:
                candidates_by_direction[direction] = mark_suggester.load_candidate_marks(conn, direction)
            candidates = candidates_by_direction[direction]
            if not candidates:
                results.append({'id': txn_id, 'status': 'skipped', 'reason': 'Belum ada mark yang tersedia'})
                continue

            try:
                suggestion = mark_suggester.suggest_for_transaction(txn, candidates, config)
            except llm_client.LLMConnectionError as exc:
                results.append({'id': txn_id, 'status': 'failed', 'error': str(exc)})
                continue
            except ValueError as exc:
                results.append({'id': txn_id, 'status': 'failed', 'error': str(exc)})
                continue

            mark_suggester.store_suggestion(conn, txn_id, suggestion)
            results.append({
                'id': txn_id,
                'status': 'suggested',
                'ai_suggested_mark_id': suggestion['mark_id'],
                'mark_label': suggestion['mark_label'],
                'ai_confidence': suggestion['confidence'],
                'ai_reason': suggestion.get('reason'),
            })

    suggested_count = sum(1 for item in results if item['status'] == 'suggested')
    skipped_count = sum(1 for item in results if item['status'] == 'skipped')
    failed_count = sum(1 for item in results if item['status'] == 'failed')
    return jsonify({
        'results': results,
        'suggested_count': suggested_count,
        'skipped_count': skipped_count,
        'failed_count': failed_count,
        'message': f'{suggested_count} saran AI dibuat.',
    })


@ai_bp.route('/api/transactions/<txn_id>/ai-decision', methods=['POST'])
def ai_decide_suggestion(txn_id):
    data = request.json or {}
    decision = str(data.get('decision') or '').strip().lower()
    if decision not in ('accept', 'reject'):
        raise BadRequestError('Keputusan tidak valid. Gunakan "accept" atau "reject".')

    engine = require_db_engine()
    with engine.begin() as conn:
        mark_suggester.ensure_ai_columns(conn)
        txn = mark_suggester.apply_decision(conn, txn_id, decision)

    label = 'diterima' if decision == 'accept' else 'ditolak'
    return jsonify({
        'message': f'Saran AI {label}.',
        'transaction': txn,
    })
