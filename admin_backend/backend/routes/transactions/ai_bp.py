"""Endpoint AI mark assist: konfigurasi LLM lokal, tes koneksi, saran mark, keputusan review.

Semua endpoint dilindungi guard auth global di server.py (before_request).
"""

from flask import Blueprint, jsonify, request

from backend.errors import BadRequestError, ServiceUnavailableError
from backend.routes.accounting_utils import require_db_engine
from backend.routes.route_utils import _parse_bool
from backend.services.ai import llm_client, mark_suggester

ai_bp = Blueprint('ai_bp', __name__)

# Batas transaksi per request: tiap transaksi = 1 panggilan LLM lokal.
MAX_SUGGEST_BATCH = 15


def _validate_settings_payload(data):
    enabled = _parse_bool(data.get('enabled'))
    provider = str(data.get('provider') or '').strip().lower()
    if provider not in llm_client.ALLOWED_PROVIDERS:
        raise BadRequestError('Provider tidak dikenal. Pilih LM Studio, Ollama, z.ai, atau Custom.')

    base_url = llm_client.normalize_base_url(data.get('base_url'))
    if not base_url:
        raise BadRequestError('Base URL server AI wajib diisi.')
    if not (base_url.startswith('https://') or base_url.startswith('http://')):
        raise BadRequestError('Base URL harus berupa URL http/https yang valid.')

    model = str(data.get('model') or '').strip()
    if len(model) > 120:
        raise BadRequestError('Nama model terlalu panjang (maksimal 120 karakter).')

    auto_apply = _parse_bool(data.get('auto_apply'))
    try:
        threshold = float(data.get('auto_apply_threshold'))
    except (TypeError, ValueError):
        threshold = llm_client.DEFAULT_AUTO_APPLY_THRESHOLD
    threshold = max(0.0, min(1.0, threshold))

    payload = {
        'enabled': enabled,
        'provider': provider,
        'base_url': base_url,
        'model': model,
        'auto_apply': auto_apply,
        'auto_apply_threshold': threshold,
    }

    api_key = data.get('api_key')
    if api_key is not None:
        api_key = str(api_key)
        if api_key not in (llm_client.API_KEY_CLEAR_SENTINEL,):
            api_key = api_key.strip()
        payload['api_key'] = api_key  # '' / sentinel / nilai baru; None berarti tidak diubah
    return payload


@ai_bp.route('/api/ai/settings', methods=['GET'])
def get_ai_settings():
    engine = require_db_engine()
    with engine.connect() as conn:
        settings = llm_client.get_ai_settings(conn)
    settings.pop('api_key', None)  # nilai kunci tidak pernah diekspos ke klien
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
    api_key = str(data.get('api_key') or '').strip() or None
    if not base_url:
        with engine.connect() as conn:
            settings = llm_client.get_ai_settings(conn)
        base_url = settings['base_url']
        api_key = api_key or settings.get('api_key') or None
    if not base_url:
        raise BadRequestError('Base URL server AI belum diatur.')

    try:
        models = llm_client.list_models(base_url, api_key=api_key)
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
    results = []

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

        # Indeks riwayat marking user: basis rekomendasi (rule match + contoh LLM).
        history_index = mark_suggester.build_history_index(conn)
        for txn_id in txn_ids:
            results.append(mark_suggester.process_transaction(
                conn, txn_id, config,
                history_index=history_index,
            ))

    suggested_count = sum(1 for item in results if item['status'] == 'suggested')
    auto_applied_count = sum(1 for item in results if item['status'] == 'auto_applied')
    skipped_count = sum(1 for item in results if item['status'] == 'skipped')
    failed_count = sum(1 for item in results if item['status'] == 'failed')
    return jsonify({
        'results': results,
        'suggested_count': suggested_count,
        'auto_applied_count': auto_applied_count,
        'skipped_count': skipped_count,
        'failed_count': failed_count,
        'message': (
            f'{auto_applied_count} transaksi ter-mark otomatis, '
            f'{suggested_count} saran menunggu review.'
        ),
    })


@ai_bp.route('/api/transactions/ai-decision-bulk', methods=['POST'])
def ai_decision_bulk():
    """Terima/tolak banyak saran AI sekaligus.

    Body: {decision: 'accept'|'reject', transaction_ids?: [..]}
    transaction_ids dihilangkan → accept semua pending / reject semua pending+auto_applied.
    """
    data = request.json or {}
    decision = str(data.get('decision') or '').strip().lower()
    if decision not in ('accept', 'reject'):
        raise BadRequestError('Keputusan tidak valid. Gunakan "accept" atau "reject".')

    txn_ids = data.get('transaction_ids')
    if txn_ids is not None and not isinstance(txn_ids, list):
        raise BadRequestError('transaction_ids wajib berupa daftar id transaksi.')

    engine = require_db_engine()
    with engine.begin() as conn:
        mark_suggester.ensure_ai_columns(conn)
        summary = mark_suggester.bulk_decision(conn, decision, txn_ids)

    label = 'diterima' if decision == 'accept' else 'ditolak/dibatalkan'
    return jsonify({
        'message': f"{summary['updated']} saran AI {label}.",
        **summary,
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
