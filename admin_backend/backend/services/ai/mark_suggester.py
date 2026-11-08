"""Saran mark berbasis LLM lokal untuk transaksi bank statement.

Prinsip: **AI menyarankan, manusia memutuskan.** Saran hanya mengisi kolom ai_*
di transactions dengan ai_status='pending'; mark_id baru berubah setelah user
menerima saran melalui endpoint ai-decision.
"""

import json
from datetime import datetime

from sqlalchemy import text

from backend.db.schema import get_table_columns
from backend.errors import BadRequestError, NotFoundError
from backend.services.ai import llm_client

# Batas kandidat mark yang dikirim ke LLM (hemat context window model kecil).
MAX_CANDIDATE_MARKS = 40
MAX_REASON_LENGTH = 500

SYSTEM_PROMPT = (
    'Anda asisten akuntansi untuk kategorisasi transaksi rekening koran bank di Indonesia. '
    'Tugas Anda memilih satu mark (kategori akuntansi) yang paling sesuai dari daftar yang diberikan. '
    'Perhatikan arah transaksi: DB = uang keluar (beban/pembelian/transfer keluar), '
    'CR = uang masuk (pendapatan/penerimaan/transfer masuk). '
    'Jawab HANYA JSON valid tanpa teks lain.'
)

JSON_INSTRUCTION = (
    'Balas HANYA JSON dengan bentuk persis: '
    '{"mark_id": "<id dari daftar>", "confidence": <angka 0.0-1.0>, '
    '"reason": "<alasan singkat dalam bahasa Indonesia>"}'
)


def _clean_text(value):
    return str(value or '').strip()


def build_mark_label(mark):
    """Label gabungan ala frontend: internal_report / personal_use / tax_report."""
    parts = []
    for field in ('internal_report', 'personal_use', 'tax_report'):
        value = _clean_text(mark.get(field))
        if value and value not in parts:
            parts.append(value)
    return ' / '.join(parts)


def load_candidate_marks(conn, db_cr):
    """Semua mark berlabel sebagai kandidat, diurutkan agar mark dengan arah wajar
    yang cocok tampil lebih dulu (lalu tanpa arah, lalu berlawanan).

    Mark berlawanan arah tetap ikut: menurut desain `natural_direction` (migration 043),
    transaksi yang berlawanan dengan arah wajar mark tetap sah (tanda dibalik sistem).
    """
    rows = conn.execute(text(
        'SELECT id, internal_report, personal_use, tax_report, natural_direction '
        'FROM marks ORDER BY created_at'
    )).fetchall()
    direction = str(db_cr or '').strip().upper()
    matching, neutral, opposing = [], [], []
    for row in rows:
        mark = dict(row._mapping)
        label = build_mark_label(mark)
        if not label:
            continue
        item = {'id': str(mark.get('id') or ''), 'label': label}
        natural = _clean_text(mark.get('natural_direction')).upper()
        if natural in ('DB', 'CR') and direction in ('DB', 'CR'):
            (matching if natural == direction else opposing).append(item)
        else:
            neutral.append(item)
    return (matching + neutral + opposing)[:MAX_CANDIDATE_MARKS]


def build_messages(txn, candidates):
    """Prompt per transaksi: konteks transaksi + daftar kandidat bernomor id."""
    day_of_month = ''
    txn_date = _clean_text(txn.get('txn_date'))
    if len(txn_date) >= 10:
        day_of_month = txn_date[8:10]

    lines = [
        f'Deskripsi: {_clean_text(txn.get("description")) or "-"}',
        f'Arah: {_clean_text(txn.get("db_cr")) or "-"} (DB = uang keluar, CR = uang masuk)',
        f'Nominal: {txn.get("amount")}',
        f'Tanggal (hari): {day_of_month or "-"}',
        f'Bank: {_clean_text(txn.get("bank_code")) or "-"}',
        '',
        'Daftar mark tersedia (urutan atas = arah wajarnya paling cocok):',
    ]
    for candidate in candidates:
        lines.append(f'- {candidate["id"]} | {candidate["label"]}')
    lines.append('')
    lines.append('Pilih mark yang PALING SESUAI dengan makna bisnis transaksi. '
                 'Jika arah transaksi berlawanan dengan arah wajar mark, mark tersebut '
                 'tetap boleh dipilih (pembalikan tanda ditangani otomatis oleh sistem).')
    lines.append('')
    lines.append(JSON_INSTRUCTION)
    return [
        {'role': 'system', 'content': SYSTEM_PROMPT},
        {'role': 'user', 'content': '\n'.join(lines)},
    ]


def _extract_json_object(raw):
    """Ambil objek JSON pertama dari jawaban LLM (toleran code fence / teks liar)."""
    text_body = str(raw or '').strip()
    text_body = text_body.replace('```json', '```')
    if '```' in text_body:
        chunks = [chunk.strip() for chunk in text_body.split('```') if chunk.strip()]
        text_body = '\n'.join(chunks)
    start = text_body.find('{')
    end = text_body.rfind('}')
    if start == -1 or end == -1 or end <= start:
        raise ValueError(
            'Jawaban AI tidak mengandung JSON valid. '
            'Model mungkin model-thinking yang kehabisan token sebelum menjawab — '
            'coba model non-thinking (mis. qwen2.5:7b).'
        )
    return json.loads(text_body[start:end + 1])


def parse_suggestion_response(raw, candidates):
    """Validasi jawaban LLM terhadap kandidat; balikan dict saran yang aman disimpan."""
    data = _extract_json_object(raw)
    by_id = {candidate['id']: candidate for candidate in candidates}

    mark_id = _clean_text(data.get('mark_id'))
    candidate = by_id.get(mark_id)
    if candidate is None and mark_id:
        # Model kadang menjawab label, bukan id — cocokkan case-insensitive.
        wanted = mark_id.casefold()
        for item in candidates:
            label = item['label'].casefold()
            if label == wanted or wanted in label or label in wanted:
                candidate = item
                break
    if candidate is None:
        raise ValueError(
            f'AI memilih mark yang tidak ada di daftar kandidat: "{mark_id[:80]}". '
            'Coba minta saran lagi atau pilih mark manual.'
        )

    try:
        confidence = float(data.get('confidence'))
    except (TypeError, ValueError):
        confidence = 0.5
    confidence = max(0.0, min(1.0, confidence))

    reason = _clean_text(data.get('reason'))[:MAX_REASON_LENGTH] or None

    return {
        'mark_id': candidate['id'],
        'mark_label': candidate['label'],
        'confidence': confidence,
        'reason': reason,
    }


def suggest_for_transaction(txn, candidates, config):
    """Panggil LLM lokal untuk satu transaksi; balikan dict saran tervalidasi."""
    messages = build_messages(txn, candidates)
    raw = llm_client.chat_completion(
        base_url=config.get('base_url'),
        model=config.get('model'),
        messages=messages,
        temperature=0.1,
        timeout=config.get('timeout') or llm_client.DEFAULT_TIMEOUT,
        max_tokens=800,  # beri ruang untuk model reasoning agar sampai ke jawaban JSON
    )
    return parse_suggestion_response(raw, candidates)


def ensure_ai_columns(conn):
    """Pastikan kolom ai_* sudah ada (migration 072 sudah jalan)."""
    txn_columns = get_table_columns(conn, 'transactions')
    required = {
        'ai_suggested_mark_id', 'ai_confidence', 'ai_source',
        'ai_reason', 'ai_status', 'ai_suggested_at', 'ai_decided_at',
    }
    if not required.issubset(txn_columns):
        raise BadRequestError(
            'Kolom AI di transactions belum lengkap. Jalankan migrasi database terbaru.',
            code='ai_schema_missing',
        )


def ensure_markable(conn, txn_id):
    """Guard yang sama dengan assign-mark: tolak transaksi manual journal & split parent."""
    linked_to_manual = conn.execute(text(
        'SELECT 1 FROM manual_journal_links WHERE linked_txn_id = :txn_id LIMIT 1'
    ), {'txn_id': txn_id}).fetchone()
    if linked_to_manual:
        raise BadRequestError(
            'Transaksi ini sudah menjadi referensi manual journal. '
            'Ubah dari manual journal agar tidak terjadi double accounting.'
        )

    txn_columns = get_table_columns(conn, 'transactions')
    if 'parent_id' in txn_columns:
        has_children = conn.execute(text(
            'SELECT 1 FROM transactions WHERE parent_id = :txn_id LIMIT 1'
        ), {'txn_id': txn_id}).fetchone()
        if has_children:
            raise BadRequestError(
                'Transaksi ini sudah memiliki multi mark (split). '
                'Ubah mark pada split, bukan parent.'
            )


def get_transaction(conn, txn_id):
    """Ambil satu transaksi untuk konteks prompt; None bila tidak ada."""
    row = conn.execute(text(
        'SELECT id, txn_date, description, amount, db_cr, bank_code, mark_id '
        'FROM transactions WHERE id = :txn_id'
    ), {'txn_id': txn_id}).fetchone()
    if row is None:
        return None
    return dict(row._mapping)


def store_suggestion(conn, txn_id, suggestion, source='llm'):
    """Simpan saran ke kolom ai_* — mark_id TIDAK disentuh."""
    conn.execute(text(
        'UPDATE transactions SET '
        'ai_suggested_mark_id = :mark_id, '
        'ai_confidence = :confidence, '
        'ai_source = :source, '
        'ai_reason = :reason, '
        'ai_status = :status, '
        'ai_suggested_at = :suggested_at, '
        'ai_decided_at = NULL '
        'WHERE id = :txn_id'
    ), {
        'txn_id': txn_id,
        'mark_id': suggestion['mark_id'],
        'confidence': suggestion['confidence'],
        'source': source,
        'reason': suggestion.get('reason'),
        'status': 'pending',
        'suggested_at': datetime.now(),
    })


def apply_decision(conn, txn_id, decision):
    """Terima/tolak saran. accept mengisi mark_id dari ai_suggested_mark_id."""
    if decision not in ('accept', 'reject'):
        raise BadRequestError('Keputusan tidak valid. Gunakan "accept" atau "reject".')

    row = conn.execute(text(
        'SELECT id, ai_suggested_mark_id, ai_status FROM transactions WHERE id = :txn_id'
    ), {'txn_id': txn_id}).fetchone()
    if row is None:
        raise NotFoundError('Transaction not found')
    txn = dict(row._mapping)

    if not _clean_text(txn.get('ai_suggested_mark_id')):
        raise BadRequestError('Transaksi ini belum memiliki saran AI.', code='ai_no_suggestion')
    if decision == 'accept' and _clean_text(txn.get('ai_status')) == 'accepted':
        return txn  # idempoten: sudah diterima sebelumnya

    now = datetime.now()
    if decision == 'accept':
        ensure_markable(conn, txn_id)
        conn.execute(text(
            'UPDATE transactions SET '
            'mark_id = ai_suggested_mark_id, '
            "ai_status = 'accepted', "
            'ai_decided_at = :decided_at, '
            'updated_at = :decided_at '
            'WHERE id = :txn_id'
        ), {'txn_id': txn_id, 'decided_at': now})
    else:
        conn.execute(text(
            'UPDATE transactions SET '
            "ai_status = 'rejected', "
            'ai_decided_at = :decided_at '
            'WHERE id = :txn_id'
        ), {'txn_id': txn_id, 'decided_at': now})

    updated = conn.execute(text(
        'SELECT id, mark_id, ai_suggested_mark_id, ai_confidence, ai_source, '
        'ai_reason, ai_status, ai_suggested_at, ai_decided_at '
        'FROM transactions WHERE id = :txn_id'
    ), {'txn_id': txn_id}).fetchone()
    return dict(updated._mapping)
