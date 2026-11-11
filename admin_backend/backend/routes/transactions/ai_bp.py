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


def _parse_txn_ids(data):
    """Validasi transaction_ids body: daftar string non-kosong, dedup, maks batch."""
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
    return txn_ids


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

    # api_key tidak diterima di sini — AI key dikelola vault (PUT /api/credentials,
    # setting ai_api_key). Nilai asing diabaikan agar tidak menimpa kunci vault.
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
    txn_ids = _parse_txn_ids(data)

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


@ai_bp.route('/api/transactions/ai-suggest/prepare', methods=['POST'])
def ai_suggest_prepare():
    """Tahap bridge 1/2: kaskade rule TANPA LLM.

    Rule match langsung disimpan (instan & deterministik); sisanya dikembalikan
    sebagai prompt siap pakai untuk dipanggilkan ke server AI lokal oleh browser.
    """
    txn_ids = _parse_txn_ids(request.json or {})
    engine = require_db_engine()

    results, pending = [], []
    with engine.begin() as conn:
        mark_suggester.ensure_ai_columns(conn)
        config = llm_client.get_ai_settings(conn)
        if not config['enabled']:
            raise BadRequestError('Fitur AI belum diaktifkan di pengaturan.', code='ai_disabled')
        if not config['model']:
            raise BadRequestError('Model AI belum diatur di pengaturan.', code='ai_model_missing')

        history_index = mark_suggester.build_history_index(conn)
        candidates_by_direction = {}
        for txn_id in txn_ids:
            resolved = mark_suggester.resolve_transaction_rules(
                conn, txn_id, config,
                history_index=history_index,
                candidates_by_direction=candidates_by_direction,
            )
            if resolved['kind'] == 'done':
                results.append(resolved['result'])
            else:
                pending.append(resolved['prompt'])  # tanpa api_key — provider lokal

    return jsonify({
        'results': results,
        'pending': pending,
        'message': (
            f'{len(results)} selesai via aturan riwayat, '
            f'{len(pending)} menunggu jawaban server AI lokal.'
        ),
    })


@ai_bp.route('/api/transactions/ai-suggest/submit', methods=['POST'])
def ai_suggest_submit():
    """Tahap bridge 2/2: parse & simpan jawaban mentah server AI lokal.

    Browser mengirim jawaban mentah (atau error per item); server memvalidasi
    terhadap kandidat DB. Shape agregat identik dengan endpoint lama.
    """
    data = request.json or {}
    items = data.get('items')
    if not isinstance(items, list) or not items:
        raise BadRequestError('items wajib berupa daftar {id, raw|error}.')

    engine = require_db_engine()
    if len(items) > MAX_SUGGEST_BATCH:
        raise BadRequestError(
            f'Maksimal {MAX_SUGGEST_BATCH} transaksi per permintaan. '
            'Kirim dalam beberapa batch kecil.'
        )
    results = []
    with engine.begin() as conn:
        mark_suggester.ensure_ai_columns(conn)
        for item in items[:MAX_SUGGEST_BATCH]:
            if not isinstance(item, dict):
                raise BadRequestError('Setiap item wajib objek {id, raw|error}.')
            txn_id = str(item.get('id') or '').strip()
            if not txn_id:
                raise BadRequestError('Setiap item wajib memiliki id transaksi.')
            error = item.get('error')
            if error:
                results.append({'id': txn_id, 'status': 'failed', 'error': str(error)[:500]})
                continue
            results.append(mark_suggester.parse_bridge_submission(conn, txn_id, item.get('raw')))

    suggested_count = sum(1 for r in results if r['status'] == 'suggested')
    auto_applied_count = sum(1 for r in results if r['status'] == 'auto_applied')
    skipped_count = sum(1 for r in results if r['status'] == 'skipped')
    failed_count = sum(1 for r in results if r['status'] == 'failed')
    return jsonify({
        'results': results,
        'suggested_count': suggested_count,
        'auto_applied_count': auto_applied_count,
        'skipped_count': skipped_count,
        'failed_count': failed_count,
        'message': (
            f'{suggested_count} saran AI menunggu review, '
            f'{failed_count} gagal.'
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


# ------------------------------------------------- Fase 3: review queue & enrichment


REVIEW_QUEUE_LIMIT = 200


@ai_bp.route('/api/transactions/ai-review-queue', methods=['GET'])
def ai_review_queue():
    """Transaksi menunggu review: ai_status pending dengan confidence di bawah
    threshold auto-apply (default 0.9, bisa dioverride ?threshold=)."""
    engine = require_db_engine()

    threshold = None
    threshold_raw = (request.args.get('threshold') or '').strip()
    if threshold_raw:
        try:
            threshold = float(threshold_raw)
        except ValueError:
            raise BadRequestError(f'Invalid threshold "{threshold_raw}".')

    with engine.connect() as conn:
        from backend.db.schema import get_table_columns

        if threshold is None:
            try:
                config = llm_client.get_ai_settings(conn)
                threshold = float(config.get('auto_apply_threshold')
                                  or llm_client.DEFAULT_AUTO_APPLY_THRESHOLD)
            except Exception:
                threshold = llm_client.DEFAULT_AUTO_APPLY_THRESHOLD

        columns = get_table_columns(conn, 'transactions')
        if 'ai_status' not in columns:
            return jsonify({'items': [], 'total': 0, 'threshold': threshold})

        clean_select = ', t.clean_description' if 'clean_description' in columns else ''
        rows = conn.execute(_review_queue_query(clean_select), {
            'threshold': threshold,
            'limit': REVIEW_QUEUE_LIMIT,
        }).fetchall()

    items = [
        {
            'id': row.id,
            'txn_date': str(row.txn_date) if row.txn_date else None,
            'description': row.description,
            'clean_description': getattr(row, 'clean_description', None),
            'amount': float(row.amount) if row.amount is not None else None,
            'db_cr': row.db_cr,
            'bank_code': row.bank_code,
            'ai_suggested_mark_id': row.ai_suggested_mark_id,
            'suggested_mark_name': row.suggested_mark_name,
            'ai_confidence': float(row.ai_confidence) if row.ai_confidence is not None else None,
            'ai_source': row.ai_source,
            'ai_reason': row.ai_reason,
        }
        for row in rows
    ]
    return jsonify({'items': items, 'total': len(items), 'threshold': threshold})


def _review_queue_query(clean_select):
    from sqlalchemy import text
    return text(f"""
        SELECT t.id, t.txn_date, t.description{clean_select}, t.amount, t.db_cr,
               t.bank_code, t.ai_suggested_mark_id, t.ai_confidence,
               t.ai_source, t.ai_reason,
               m.internal_report AS suggested_mark_name
        FROM transactions t
        LEFT JOIN marks m ON t.ai_suggested_mark_id = m.id
        WHERE t.ai_status = 'pending'
          AND (t.ai_confidence IS NULL OR t.ai_confidence < :threshold)
        ORDER BY t.txn_date DESC, t.id DESC
        LIMIT :limit
    """)


@ai_bp.route('/api/transactions/enrich-descriptions', methods=['POST'])
def enrich_descriptions():
    """Jalankan enrichment deskripsi (rule-based; LLM utk server provider).

    Body: {transaction_ids?: [..]} — tanpa ids memakai 1000 baris terbaru yang
    belum punya clean_description.
    """
    from backend.services.ai import description_enricher

    data = request.json or {}
    txn_ids = data.get('transaction_ids')
    if txn_ids is not None and not isinstance(txn_ids, list):
        raise BadRequestError('transaction_ids wajib berupa daftar id transaksi.')

    engine = require_db_engine()
    if not txn_ids:
        from sqlalchemy import text as _text
        with engine.connect() as conn:
            from backend.db.schema import get_table_columns
            if 'clean_description' not in get_table_columns(conn, 'transactions'):
                return jsonify({'message': 'Kolom clean_description belum ada (jalankan migrasi).',
                                'enriched': 0, 'llm_used': False})
            txn_ids = [
                str(row[0]) for row in conn.execute(_text(
                    'SELECT id FROM transactions '
                    'WHERE clean_description IS NULL OR TRIM(clean_description) = "" '
                    'ORDER BY created_at DESC LIMIT 1000'
                )).fetchall()
            ]
        if not txn_ids:
            return jsonify({'message': 'Tidak ada deskripsi yang perlu di-enrich.',
                            'enriched': 0, 'llm_used': False})

    def _llm_complete(conn, requests):
        config = llm_client.get_ai_settings(conn)
        if not config.get('enabled') or config.get('provider') in llm_client.BRIDGE_PROVIDERS:
            return {}
        return description_enricher.llm_clean_batch(conn, requests, config)

    result = description_enricher.enrich_transactions(engine, txn_ids, llm_complete=_llm_complete)
    return jsonify({
        'message': f"{result['enriched']} deskripsi di-enrich.",
        **result,
    })
