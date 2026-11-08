"""Saran mark berbasis data existing + LLM lokal untuk transaksi bank statement.

Prinsip: **AI menyarankan, manusia memutuskan.** Saran hanya mengisi kolom ai_*
di transactions dengan ai_status='pending'; mark_id baru berubah setelah user
menerima saran melalui endpoint ai-decision.

Rekomendasi selalu berangkat dari data existing user:
1. Rule engine — deskripsi dinormalisasi lalu dicocokkan ke riwayat transaksi yang
   sudah di-mark user. Pola kuat → saran langsung (source='rule', tanpa LLM).
2. LLM lokal — bila tidak ada kecocokan kuat, prompt menyertakan contoh nyata
   dari riwayat marking user (few-shot) agar saran mengikuti konvensi user.
"""

import json
import re
from datetime import datetime

from sqlalchemy import text

from backend.db.schema import get_table_columns
from backend.errors import BadRequestError, NotFoundError
from backend.services.ai import llm_client

# Batas kandidat mark yang dikirim ke LLM. Diurutkan mark arah-cocok lebih dulu,
# jadi bila jumlah mark sangat besar yang terpotong adalah yang arahnya berlawanan.
MAX_CANDIDATE_MARKS = 120
MAX_REASON_LENGTH = 500
# Batas contoh riwayat user yang dikirim ke LLM sebagai few-shot.
MAX_FEW_SHOT_EXAMPLES = 8
# Di bawah dominasi ini pola riwayat dianggap terlalu berbelit → serahkan ke LLM.
RULE_MIN_DOMINANCE = 0.5

SYSTEM_PROMPT = (
    'Anda asisten akuntansi untuk kategorisasi transaksi rekening koran bank di Indonesia. '
    'Tugas Anda memilih satu mark (kategori akuntansi) yang paling sesuai dari daftar yang diberikan. '
    'Perhatikan arah transaksi: DB = uang keluar (beban/pembelian/transfer keluar), '
    'CR = uang masuk (pendapatan/penerimaan/transfer masuk). '
    'Utamakan konsistensi dengan pola penandaan user pada contoh riwayat yang diberikan. '
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


def normalize_description(desc):
    """Normalisasi deskripsi bank: buang nomor referensi/tanggal/simbol.

    'TRSF E-BANKING DB 2102/FTSCY/WS95271 2315326.00 FLIPTECH'
      → 'TRSF E BANKING DB FTSCY WS FLIPTECH'
    """
    value = str(desc or '').upper()
    value = re.sub(r'\b\d{2}/\d{2}(/\d{2,4})?\b', ' ', value)  # tanggal 21/02(/2026)
    value = re.sub(r'\d{4,}', ' ', value)                      # nomor referensi panjang
    value = re.sub(r'[^A-Z\s]', ' ', value)                    # simbol & sisa angka
    return re.sub(r'\s+', ' ', value).strip()


def build_history_index(conn):
    """Riwayat transaksi ber-mark sebagai basis rekomendasi (sekali query per request).

    Balikan list dict: {normalized, mark_id, db_cr, company_id}.
    """
    txn_columns = get_table_columns(conn, 'transactions')
    company_select = ', t.company_id' if 'company_id' in txn_columns else ''
    has_parent = 'parent_id' in txn_columns
    parent_clause = ' AND (t.parent_id IS NULL OR t.parent_id = :no_parent)' if has_parent else ''
    rows = conn.execute(text(
        'SELECT t.description, t.mark_id, t.db_cr' + company_select + ' '
        'FROM transactions t '
        'WHERE t.mark_id IS NOT NULL AND t.description IS NOT NULL '
        "AND TRIM(t.description) <> ''" + parent_clause
    ), {'no_parent': None}).fetchall()

    index = []
    for row in rows:
        mapping = dict(row._mapping)
        normalized = normalize_description(mapping.get('description'))
        if not normalized:
            continue
        index.append({
            'normalized': normalized,
            'raw_description': str(mapping.get('description') or ''),
            'mark_id': str(mapping.get('mark_id') or ''),
            'db_cr': str(mapping.get('db_cr') or '').strip().upper(),
            'company_id': str(mapping.get('company_id') or '') if mapping.get('company_id') else '',
        })
    return index


def _match_history(index, txn, direction, company_id):
    """Cari entri riwayat dengan deskripsi ternormalisasi sama.

    Skor: kecocokan persis +2 bila company sama, +1 bila arah sama.
    Balikan (matched_list, {mark_id: total_skor}) atau (None, None) bila kosong.
    """
    normalized = normalize_description(txn.get('description'))
    if not normalized:
        return None, None
    company = str(company_id or '')
    matched = [entry for entry in index if entry['normalized'] == normalized]
    if not matched:
        return None, None
    scores = {}
    for entry in matched:
        score = 1.0
        if company and entry['company_id'] == company:
            score += 2.0
        if direction and entry['db_cr'] == direction:
            score += 1.0
        scores[entry['mark_id']] = scores.get(entry['mark_id'], 0.0) + score
    return matched, scores


def match_history_rule(index, txn, candidates, db_cr, company_id):
    """Saran berbasis riwayat user. None bila tidak ada pola yang cukup jelas."""
    matched, scores = _match_history(index, txn, db_cr, company_id)
    if not matched or not scores:
        return None

    total = sum(scores.values())
    dominant_mark_id, dominant_score = max(scores.items(), key=lambda item: item[1])
    dominance = dominant_score / total if total else 0.0
    if dominance < RULE_MIN_DOMINANCE:
        return None

    candidate = next((c for c in candidates if c['id'] == dominant_mark_id), None)
    if candidate is None:
        return None

    samples = len(matched)
    confidence = min(0.95, 0.65 + 0.25 * dominance + min(0.05, 0.01 * samples))
    label = candidate['label']
    reason = (
        f'Mengikuti pola {samples} transaksi serupa yang sudah Anda tandai "{label}".'
        if samples > 1 else
        f'Deskripsi identik dengan transaksi sebelumnya yang Anda tandai "{label}".'
    )
    return {
        'mark_id': candidate['id'],
        'mark_label': label,
        'confidence': round(confidence, 3),
        'reason': reason,
        'source': 'rule',
        'matched': matched,
    }


def pick_history_examples(index, txn, db_cr, company_id, matched=None):
    """Contoh riwayat user untuk few-shot prompt (prefer kemiripan, lalu terbaru)."""
    if matched is None:
        matched, _scores = _match_history(index, txn, db_cr, company_id)
    examples = []
    if matched:
        for entry in matched[:MAX_FEW_SHOT_EXAMPLES]:
            examples.append({'description': entry['raw_description'], 'mark_id': entry['mark_id']})
        return examples

    # Tanpa kecocokan persis: pakai contoh terbaru dengan arah yang sama agar
    # LLM tetap melihat konvensi penandaan user.
    direction = str(db_cr or '').strip().upper()
    for entry in reversed(index):  # index terurut ASC (urutan query) → ambil dari akhir
        if direction and entry['db_cr'] and entry['db_cr'] != direction:
            continue
        examples.append({'description': entry['raw_description'], 'mark_id': entry['mark_id']})
        if len(examples) >= MAX_FEW_SHOT_EXAMPLES:
            break
    return examples


def build_messages(txn, candidates, examples=None):
    """Prompt per transaksi: konteks transaksi + contoh riwayat user + daftar kandidat."""
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
    ]

    if examples:
        lines.append('')
        lines.append('Pola penandaan dari data Anda sendiri (deskripsi mentah → mark yang Anda pakai):')
        for example in examples:
            lines.append(f'- "{example["description"]}" → {example["mark_id"]}')
        lines.append('Ikuti pola di atas bila deskripsi serupa; pilih mark yang sama seperti yang sudah Anda pakai.')

    lines.append('')
    lines.append('Daftar mark tersedia (urutan atas = arah wajarnya paling cocok):')
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


def suggest_for_transaction(txn, candidates, config, examples=None):
    """Panggil LLM lokal untuk satu transaksi; balikan dict saran tervalidasi."""
    messages = build_messages(txn, candidates, examples=examples)
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
        'SELECT id, txn_date, description, amount, db_cr, bank_code, company_id, mark_id '
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
