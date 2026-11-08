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

import difflib
import json
import re
import time
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
# Rule persis hanya berani menyimpulkan bila satu mark sangat dominan — di bawah
# itu deskripsi yang sama terbukti dipakai untuk mark berbeda (mis. transfer yang
# sama bisa gaji nominal besar / pembelian nominal kecil) → serahkan ke LLM yang
# menerima ringkasan mark berulang BESERTA rentang nominalnya.
RULE_EXACT_DOMINANCE = 0.75
# Ambang kemiripan (difflib ratio) untuk menyebut dua deskripsi "mirip".
FUZZY_MIN_RATIO = 0.65
# Minimal sampel fuzzy sebelum rule berani menyimpulkan dari kemiripan.
FUZZY_MIN_SAMPLES = 2
# Dominasi minimal untuk menyimpulkan dari kecocokan mirip (lebih ketat dari persis).
FUZZY_MIN_DOMINANCE = 0.7
# Batas entri mirip yang disimpan dalam konteks (untuk rule & few-shot).
MAX_FUZZY_MATCHES = 24

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


def _normalize_direction(value):
    raw = str(value or '').strip().upper()
    if raw in {'CR', 'CREDIT', 'KREDIT', 'K'}:
        return 'CR'
    if raw in {'DB', 'DEBIT', 'D', 'DE'}:
        return 'DB'
    return 'DB'


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

    Setiap entri memuat deskripsi ternormalisasi, mark (id + label), arah, nominal,
    company, dan token-set untuk prefilter fuzzy yang murah.
    """
    txn_columns = get_table_columns(conn, 'transactions')
    company_select = ', t.company_id' if 'company_id' in txn_columns else ''
    has_parent = 'parent_id' in txn_columns
    parent_clause = ' AND (t.parent_id IS NULL OR t.parent_id = :no_parent)' if has_parent else ''
    rows = conn.execute(text(
        'SELECT t.description, t.mark_id, t.db_cr, t.amount, '
        'm.internal_report, m.personal_use, m.tax_report' + company_select + ' '
        'FROM transactions t '
        'LEFT JOIN marks m ON t.mark_id = m.id '
        'WHERE t.mark_id IS NOT NULL AND t.description IS NOT NULL '
        "AND TRIM(t.description) <> ''" + parent_clause
    ), {'no_parent': None}).fetchall()

    index = []
    for row in rows:
        mapping = dict(row._mapping)
        normalized = normalize_description(mapping.get('description'))
        if not normalized:
            continue
        amount_raw = mapping.get('amount')
        try:
            amount = abs(float(amount_raw)) if amount_raw is not None else None
        except (TypeError, ValueError):
            amount = None
        index.append({
            'normalized': normalized,
            'tokens': set(normalized.split()),
            'raw_description': str(mapping.get('description') or ''),
            'mark_id': str(mapping.get('mark_id') or ''),
            'mark_label': build_mark_label(mapping) or '',
            'db_cr': str(mapping.get('db_cr') or '').strip().upper(),
            'amount': amount,
            'company_id': str(mapping.get('company_id') or '') if mapping.get('company_id') else '',
        })
    return index


def _score_entries(entries, direction, company_id, similarity_key=None):
    """Skor agregat per mark dari daftar entri kecocokan.

    Bobot per entri: 1.0 (+2 company sama) (+1 arah sama), dikali kemiripan bila fuzzy.
    """
    scores = {}
    company = str(company_id or '')
    for entry in entries:
        weight = 1.0
        if similarity_key and entry.get(similarity_key) is not None:
            weight *= float(entry[similarity_key])
        if company and entry['company_id'] == company:
            weight += 2.0
        if direction and entry['db_cr'] == direction:
            weight += 1.0
        scores[entry['mark_id']] = scores.get(entry['mark_id'], 0.0) + weight
    return scores


def build_history_context(index, txn, direction, company_id):
    """Analisis riwayat untuk satu transaksi: kecocokan persis + mirip (fuzzy).

    Kecocokan persis = deskripsi ternormalisasi identik. Mirip = difflib ratio
    >= FUZZY_MIN_RATIO (prefilter token overlap agar murah pada index besar).
    """
    normalized = normalize_description(txn.get('description'))
    if not normalized:
        return {'exact': [], 'fuzzy': []}
    txn_tokens = set(normalized.split())

    exact, fuzzy = [], []
    for entry in index:
        if entry['normalized'] == normalized:
            exact.append(entry)
            continue
        # Prefilter murah: minimal 40% token terpendek harus muncul di entri.
        common = len(txn_tokens & entry['tokens'])
        shorter = min(len(txn_tokens), len(entry['tokens'])) or 1
        if common / shorter < 0.4:
            continue
        ratio = difflib.SequenceMatcher(None, normalized, entry['normalized']).ratio()
        if ratio >= FUZZY_MIN_RATIO:
            fuzzy.append({**entry, 'similarity': round(ratio, 3)})

    fuzzy.sort(key=lambda e: -e['similarity'])
    return {'exact': exact, 'fuzzy': fuzzy[:MAX_FUZZY_MATCHES]}


def match_history_rule(context, candidates):
    """Saran berbasis riwayat user (kecocokan persis dahulu, lalu kemiripan).

    None bila tidak ada pola yang cukup jelas — transaksi lalu ditangani LLM
    dengan konteks mark berulang + contoh riwayat dari konteks yang sama.
    """
    exact = context.get('exact') or []
    fuzzy = context.get('fuzzy') or []

    # Lapis 1a: deskripsi persis sama dengan satu mark sangat dominan.
    if exact:
        scores = _score_entries(exact, None, None)
        total = sum(scores.values())
        dominant_mark_id, dominant_score = max(scores.items(), key=lambda item: item[1])
        dominance = dominant_score / total if total else 0.0
        candidate = next((c for c in candidates if c['id'] == dominant_mark_id), None)
        if candidate and dominance >= RULE_EXACT_DOMINANCE:
            samples = len(exact)
            confidence = min(0.95, 0.65 + 0.3 * dominance + min(0.05, 0.01 * samples))
            label = candidate['label']
            reason = (
                f'Mengikuti pola {samples} transaksi identik yang sudah Anda tandai "{label}".'
                if samples > 1 else
                f'Deskripsi identik dengan transaksi sebelumnya yang Anda tandai "{label}".'
            )
            return {
                'mark_id': candidate['id'],
                'mark_label': label,
                'confidence': round(confidence, 3),
                'reason': reason,
                'source': 'rule',
            }

    # Lapis 1b: TIDAK ada kecocokan persis sama sekali → coba kemiripan.
    # (Bila ada kecocokan persis tapi mark-nya terbagi, jangan paksa rule —
    # LLM lebih tepat memilah lewat konteks nominal dari blok mark berulang.)
    # Confidence dibatasi 0.85 sehingga tidak pernah auto-apply pada threshold
    # bawaan (0.9) — hasil kemiripan memang layak direview dulu.
    if exact:
        return None
    if len(fuzzy) >= FUZZY_MIN_SAMPLES:
        scores = _score_entries(fuzzy, None, None, similarity_key='similarity')
        total = sum(scores.values())
        dominant_mark_id, dominant_score = max(scores.items(), key=lambda item: item[1])
        dominance = dominant_score / total if total else 0.0
        candidate = next((c for c in candidates if c['id'] == dominant_mark_id), None)
        if candidate and dominance >= FUZZY_MIN_DOMINANCE:
            samples = len(fuzzy)
            avg_similarity = sum(float(e.get('similarity') or 0) for e in fuzzy) / samples
            confidence = min(0.85, 0.55 + 0.2 * dominance + min(0.1, 0.02 * samples))
            label = candidate['label']
            reason = (
                f'Mirip dengan {samples} transaksi yang Anda tandai "{label}" '
                f'(kemiripan deskripsi ~{round(avg_similarity * 100)}%).'
            )
            return {
                'mark_id': candidate['id'],
                'mark_label': label,
                'confidence': round(confidence, 3),
                'reason': reason,
                'source': 'rule',
            }

    return None


def summarize_recurring_marks(context, txn_amount=None):
    """Ringkasan mark untuk deskripsi yang PERSIS sama (untuk blok prompt).

    Balikan list [{label, mark_id, count, min_amount, max_amount, contains_amount}]
    terurut: mark yang rentang nominalnya memuat transaksi lebih dulu, lalu frekuensi.
    """
    exact = context.get('exact') or []
    if not exact:
        return []
    grouped = {}
    for entry in exact:
        item = grouped.setdefault(entry['mark_id'], {
            'mark_id': entry['mark_id'],
            'label': entry.get('mark_label') or '',
            'count': 0,
            'min_amount': None,
            'max_amount': None,
        })
        item['count'] += 1
        amount = entry.get('amount')
        if amount is not None:
            item['min_amount'] = amount if item['min_amount'] is None else min(item['min_amount'], amount)
            item['max_amount'] = amount if item['max_amount'] is None else max(item['max_amount'], amount)

    items = list(grouped.values())
    if txn_amount is not None:
        for item in items:
            lo, hi = item.get('min_amount'), item.get('max_amount')
            item['contains_amount'] = bool(
                lo is not None and lo <= float(txn_amount) <= hi
            )
        items.sort(key=lambda item: (not item.get('contains_amount'), -item['count']))
    else:
        items.sort(key=lambda item: -item['count'])
    return items


def match_amount_disambiguated_rule(context, txn, candidates):
    """Lapis rule tambahan: deskripsi identik dipakai banyak mark, tapi nominal
    transaksi hanya memuat rentang SATU mark yang cukup sering dipakai —
    pilih rentang paling sempit yang memuat (deterministik, tanpa LLM).

    Confidence dibatasi 0.88 → tetap menunggu review pada threshold bawaan.
    """
    exact = context.get('exact') or []
    if not exact:
        return None
    try:
        amount = abs(float(txn.get('amount'))) if txn.get('amount') is not None else None
    except (TypeError, ValueError):
        amount = None
    if amount is None:
        return None

    recurring = summarize_recurring_marks(context, txn_amount=amount)
    containing = [item for item in recurring if item.get('contains_amount')]
    # Sempit dulu (paling spesifik), minimal 3 sampel agar rentangnya berarti.
    containing = [item for item in containing if item['count'] >= 3]
    if not containing:
        return None

    def width(item):
        lo, hi = item.get('min_amount'), item.get('max_amount')
        return (hi - lo) if (lo is not None and hi is not None) else float('inf')

    best = min(containing, key=width)
    candidate = next((c for c in candidates if c['id'] == best['mark_id']), None)
    if candidate is None:
        return None

    span = width(best)
    confidence = round(min(0.88, 0.78 + 0.05 * min(1.0, 1 / (1 + span / max(amount, 1)))), 3)
    reason = (
        f'Deskripsi identik pernah Anda tandai {best["count"]}x ke "{best["label"]}" '
        f'({best["count"]} transaksi, nominal {_format_amount(best["min_amount"])}–'
        f'{_format_amount(best["max_amount"])}); nominal transaksi ini '
        f'({_format_amount(amount)}) paling pas di rentang tersebut.'
    )
    return {
        'mark_id': candidate['id'],
        'mark_label': candidate['label'],
        'confidence': confidence,
        'reason': reason,
        'source': 'rule',
    }


def pick_history_examples(context, index, txn, direction, company_id):
    """Contoh riwayat user untuk few-shot prompt — paling informatif dulu.

    Prioritas: (1) kecocokan persis, diambil beragam antar mark dan diurutkan
    menurut kedekatan nominal; (2) entri paling mirip (fuzzy); (3) transaksi
    terbaru dengan arah sama.
    """
    exact = context.get('exact') or []
    fuzzy = context.get('fuzzy') or []

    def to_example(entry):
        return {
            'description': entry['raw_description'],
            'mark_id': entry['mark_id'],
            'mark_label': entry.get('mark_label') or '',
            'db_cr': entry.get('db_cr') or '',
            'amount': entry.get('amount'),
        }

    try:
        target_amount = abs(float(txn.get('amount'))) if txn.get('amount') is not None else None
    except (TypeError, ValueError):
        target_amount = None

    if exact:
        # Contoh beragam antar mark: maksimal 3 per mark dari 3 mark terbanyak,
        # terdekat nominal dulu — agar LLM melihat rentang tiap pilihan.
        by_mark = {}
        for entry in exact:
            by_mark.setdefault(entry['mark_id'], []).append(entry)
        top_marks = sorted(by_mark.values(), key=len, reverse=True)[:3]
        chosen = []
        for entries in top_marks:
            if target_amount is not None:
                entries = sorted(
                    entries,
                    key=lambda e: abs((e.get('amount') or 0) - target_amount),
                )
            chosen.extend(entries[:3])
        return [to_example(e) for e in chosen[:MAX_FEW_SHOT_EXAMPLES]]

    if fuzzy:
        return [to_example(e) for e in fuzzy[:MAX_FEW_SHOT_EXAMPLES]]

    # Tanpa kecocokan apa pun: pakai contoh terbaru dengan arah yang sama agar
    # LLM tetap melihat konvensi penandaan user.
    direction = str(direction or '').strip().upper()
    examples = []
    for entry in reversed(index):  # index terurut ASC (urutan query) → ambil dari akhir
        if direction and entry['db_cr'] and entry['db_cr'] != direction:
            continue
        examples.append(to_example(entry))
        if len(examples) >= MAX_FEW_SHOT_EXAMPLES:
            break
    return examples


def _format_amount(amount):
    if amount is None:
        return '?'
    return f'{float(amount):,.0f}'.replace(',', '.')


def _safe_amount(txn):
    try:
        return abs(float(txn.get('amount'))) if txn.get('amount') is not None else None
    except (TypeError, ValueError):
        return None


def build_messages(txn, candidates, examples=None, recurring_marks=None):
    """Prompt per transaksi: konteks + pola riwayat user + daftar kandidat.

    Contoh riwayat memuat label mark, arah, dan nominal — bukan hanya id mentah —
    sehingga LLM bisa meniru konvensi user termasuk membedakan mark berdasarkan
    nominal (mis. transfer nominal kecil = pembelian, besar = gaji).
    """
    day_of_month = ''
    txn_date = _clean_text(txn.get('txn_date'))
    if len(txn_date) >= 10:
        day_of_month = txn_date[8:10]

    lines = [
        f'Deskripsi: {_clean_text(txn.get("description")) or "-"}',
        f'Arah: {_clean_text(txn.get("db_cr")) or "-"} (DB = uang keluar, CR = uang masuk)',
        f'Nominal: {_format_amount(txn.get("amount"))}',
        f'Tanggal (hari): {day_of_month or "-"}',
        f'Bank: {_clean_text(txn.get("bank_code")) or "-"}',
    ]

    if recurring_marks:
        lines.append('')
        lines.append('PERHATIAN — deskripsi yang PERSIS sama pernah Anda tandai ke:')
        for item in recurring_marks:
            amount_range = ''
            if item.get('min_amount') is not None and item.get('max_amount') is not None:
                amount_range = f' | nominal {_format_amount(item["min_amount"])}–{_format_amount(item["max_amount"])}'
            marker = ' ← MEMUAT nominal transaksi ini' if item.get('contains_amount') else ''
            lines.append(
                f'- {item["label"]} [{item["mark_id"]}] ({item["count"]}x{amount_range}){marker}'
            )
        lines.append(
            'Pilih di antara mark bertanda MEMUAT bila ada; jika tidak ada yang memuat, '
            'pilih rentang terdekat. Utamakan konsistensi nominal.'
        )

    if examples:
        lines.append('')
        lines.append('Pola penandaan dari data Anda sendiri (deskripsi mentah [arah nominal] → mark):')
        for example in examples:
            meta = ''
            if example.get('db_cr') or example.get('amount') is not None:
                meta = f' [{example.get("db_cr") or "-"} {_format_amount(example.get("amount"))}]'
            label = example.get('mark_label') or example.get('mark_id')
            lines.append(f'- "{example["description"]}"{meta} → {label} [{example["mark_id"]}]')
        lines.append(
            'Ikuti pola penandaan Anda di atas — contoh riwayat ini lebih mengikat '
            'daripada kesan umum dari kata-kata deskripsi (mis. "transfer" tidak '
            'selalu berarti transfer antar rekening bila riwayat Anda menandainya '
            'sebagai gaji/pembelian).'
        )

    lines.append('')
    lines.append('Daftar mark tersedia (urutan atas = arah wajarnya paling cocok):')
    for candidate in candidates:
        lines.append(f'- {candidate["id"]} | {candidate["label"]}')
    lines.append('')
    lines.append('Pilih mark yang PALING SESUAI dengan makna bisnis transaksi DAN '
                 'konsisten dengan riwayat Anda. '
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


def suggest_for_transaction(txn, candidates, config, examples=None, recurring_marks=None):
    """Panggil LLM lokal untuk satu transaksi; balikan dict saran tervalidasi.

    Satu kali percobaan ulang untuk kegagalan koneksi (model cold-load / server
    sedang sibuk) sebelum menyerah — kegagalan parsing JSON tidak diulang.
    """
    messages = build_messages(txn, candidates, examples=examples, recurring_marks=recurring_marks)
    kwargs = dict(
        base_url=config.get('base_url'),
        model=config.get('model'),
        messages=messages,
        temperature=0.1,
        timeout=config.get('timeout') or llm_client.DEFAULT_TIMEOUT,
        max_tokens=800,  # beri ruang untuk model reasoning agar sampai ke jawaban JSON
        api_key=config.get('api_key') or None,
    )
    try:
        raw = llm_client.chat_completion(**kwargs)
    except llm_client.LLMConnectionError:
        time.sleep(2)
        raw = llm_client.chat_completion(**kwargs)
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


def store_suggestion(conn, txn_id, suggestion, source='llm', auto_apply=False):
    """Simpan saran ke kolom ai_*.

    auto_apply=False → ai_status='pending', mark_id TIDAK disentuh (menunggu review).
    auto_apply=True  → mark_id langsung diisi dari saran, ai_status='auto_applied'
    (tetap bertanda AI sehingga bisa difilter, direview ulang, atau dibatalkan).
    Pemanggil wajib sudah memastikan transaksi markable (ensure_markable).
    """
    conn.execute(text(
        'UPDATE transactions SET '
        'ai_suggested_mark_id = :mark_id, '
        'ai_confidence = :confidence, '
        'ai_source = :source, '
        'ai_reason = :reason, '
        'ai_status = :status, '
        'ai_suggested_at = :suggested_at, '
        'ai_decided_at = :decided_at, '
        'mark_id = :mark_id_final '
        'WHERE id = :txn_id'
    ), {
        'txn_id': txn_id,
        'mark_id': suggestion['mark_id'],
        'confidence': suggestion['confidence'],
        'source': source,
        'reason': suggestion.get('reason'),
        'status': 'auto_applied' if auto_apply else 'pending',
        'suggested_at': datetime.now(),
        'decided_at': datetime.now() if auto_apply else None,
        'mark_id_final': suggestion['mark_id'] if auto_apply else None,
    })


def apply_decision(conn, txn_id, decision):
    """Terima/tolak saran.

    accept (pending)   → mark_id = ai_suggested_mark_id, ai_status='accepted'.
    reject (pending)   → ai_status='rejected' (mark tetap kosong).
    reject (auto_applied) → undo: mark_id dikosongkan lagi, ai_status='rejected'.
    accept (auto_applied) → idempoten: hanya konfirmasi status.
    """
    if decision not in ('accept', 'reject'):
        raise BadRequestError('Keputusan tidak valid. Gunakan "accept" atau "reject".')

    row = conn.execute(text(
        'SELECT id, mark_id, ai_suggested_mark_id, ai_status FROM transactions WHERE id = :txn_id'
    ), {'txn_id': txn_id}).fetchone()
    if row is None:
        raise NotFoundError('Transaction not found')
    txn = dict(row._mapping)

    if not _clean_text(txn.get('ai_suggested_mark_id')):
        raise BadRequestError('Transaksi ini belum memiliki saran AI.', code='ai_no_suggestion')

    status = _clean_text(txn.get('ai_status'))
    now = datetime.now()
    if decision == 'accept':
        if status == 'auto_applied':
            return txn  # idempoten: memang sudah ter-mark otomatis
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
            "mark_id = CASE WHEN ai_status = 'auto_applied' THEN NULL ELSE mark_id END, "
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


def process_transaction(conn, txn_id, config, history_index=None, candidates_by_direction=None):
    """Kaskade lengkap untuk satu transaksi: rule riwayat → (auto-apply) → LLM few-shot.

    Dipakai bersama oleh endpoint ai-suggest dan pass latar belakang saat konversi.
    Balikan dict result: {id, status: suggested|auto_applied|skipped|failed, ...}.
    """
    if candidates_by_direction is None:
        candidates_by_direction = {}

    txn = get_transaction(conn, txn_id)
    if txn is None:
        return {'id': txn_id, 'status': 'skipped', 'reason': 'Transaksi tidak ditemukan'}
    try:
        ensure_markable(conn, txn_id)
    except BadRequestError as exc:
        return {'id': txn_id, 'status': 'skipped', 'reason': exc.message}

    direction = _normalize_direction(txn.get('db_cr'))
    if direction not in candidates_by_direction:
        candidates_by_direction[direction] = load_candidate_marks(conn, direction)
    candidates = candidates_by_direction[direction]
    if not candidates:
        return {'id': txn_id, 'status': 'skipped', 'reason': 'Belum ada mark yang tersedia'}

    # Analisis riwayat marking user: kecocokan persis + mirip (fuzzy).
    context = build_history_context(history_index or [], txn, direction, txn.get('company_id'))

    # Lapis 1: pola dari riwayat user sendiri (instan, tanpa LLM).
    rule = match_history_rule(context, candidates)
    if rule:
        threshold = config.get('auto_apply_threshold')
        if threshold is None:
            threshold = llm_client.DEFAULT_AUTO_APPLY_THRESHOLD
        auto = bool(config.get('auto_apply')) and rule['confidence'] >= float(threshold)
        store_suggestion(conn, txn_id, rule, source='rule', auto_apply=auto)
        result = {
            'id': txn_id,
            'status': 'auto_applied' if auto else 'suggested',
            'ai_suggested_mark_id': rule['mark_id'],
            'mark_label': rule['mark_label'],
            'ai_confidence': rule['confidence'],
            'ai_reason': rule.get('reason'),
            'ai_source': 'rule',
        }
        if auto:
            result['auto_applied'] = True
        return result

    # Lapis 1c: deskripsi identik dipakai lintas mark, tapi nominal hanya muat di
    # rentang satu mark → simpulkan deterministik (kasus gaji vs pembelian warung).
    amount_rule = match_amount_disambiguated_rule(context, txn, candidates)
    if amount_rule:
        store_suggestion(conn, txn_id, amount_rule, source='rule', auto_apply=False)
        return {
            'id': txn_id,
            'status': 'suggested',
            'ai_suggested_mark_id': amount_rule['mark_id'],
            'mark_label': amount_rule['mark_label'],
            'ai_confidence': amount_rule['confidence'],
            'ai_reason': amount_rule.get('reason'),
            'ai_source': 'rule',
        }

    # Lapis 2: LLM dengan pola riwayat user (few-shot kaya + mark berulang) —
    # selalu menunggu review.
    examples = pick_history_examples(context, history_index or [], txn, direction, txn.get('company_id'))
    recurring_marks = summarize_recurring_marks(context, txn_amount=_safe_amount(txn))
    try:
        suggestion = suggest_for_transaction(
            txn, candidates, config, examples=examples, recurring_marks=recurring_marks,
        )
    except llm_client.LLMConnectionError as exc:
        return {'id': txn_id, 'status': 'failed', 'error': str(exc)}
    except ValueError as exc:
        return {'id': txn_id, 'status': 'failed', 'error': str(exc)}

    store_suggestion(conn, txn_id, suggestion, source='llm')
    return {
        'id': txn_id,
        'status': 'suggested',
        'ai_suggested_mark_id': suggestion['mark_id'],
        'mark_label': suggestion['mark_label'],
        'ai_confidence': suggestion['confidence'],
        'ai_reason': suggestion.get('reason'),
        'ai_source': 'llm',
    }


def bulk_decision(conn, decision, txn_ids=None):
    """Terima/tolak banyak saran sekaligus.

    txn_ids None → berlaku untuk SEMUA kandidat yang relevan:
      accept → semua ai_status='pending'; reject → semua 'pending' + 'auto_applied'.
    Baris yang gagal guard (split parent, manual journal) dilewati, bukan gagal total.
    """
    if decision not in ('accept', 'reject'):
        raise BadRequestError('Keputusan tidak valid. Gunakan "accept" atau "reject".')

    if decision == 'accept':
        status_filter = "ai_status = 'pending'"
    else:
        status_filter = "ai_status IN ('pending', 'auto_applied')"

    params = {}
    id_filter = ''
    if txn_ids:
        clean_ids = [str(value or '').strip() for value in txn_ids if str(value or '').strip()]
        if not clean_ids:
            raise BadRequestError('transaction_ids tidak berisi id yang valid.')
        placeholders = ', '.join(f':id{i}' for i in range(len(clean_ids)))
        id_filter = f' AND id IN ({placeholders})'
        params.update({f'id{i}': value for i, value in enumerate(clean_ids)})

    rows = conn.execute(text(
        f'SELECT id FROM transactions WHERE ai_suggested_mark_id IS NOT NULL '
        f'AND {status_filter}{id_filter}'
    ), params).fetchall()

    updated = 0
    skipped = []
    for row in rows:
        txn_id = str(dict(row._mapping)['id'])
        try:
            apply_decision(conn, txn_id, decision)
            updated += 1
        except (BadRequestError, NotFoundError) as exc:
            skipped.append({'id': txn_id, 'reason': exc.message})
    return {'updated': updated, 'skipped': skipped}
