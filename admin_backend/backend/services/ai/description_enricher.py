"""Enrichment deskripsi transaksi (Fase 3, PRD_AI_FEATURES.md Fitur 1).

Dua lapis:
1. Rule-based (regex, tanpa model): buang noise — nomor referensi panjang,
   ID pelanggan, tanggal, nominal + mata uang — rapikan whitespace.
   Selalu aman dijalankan server-side untuk semua provider.
2. LLM fallback (opsional, injectable): untuk deskripsi yang tidak berubah
   oleh rule layer, diproses model via callback (server provider).

Deskripsi asli TIDAK PERNAH diubah — hasil bersih disimpan di kolom
clean_description supaya audit trail utuh.
"""

import logging
import re

logger = logging.getLogger(__name__)

# Run digit >= 5: nomor referensi e-banking, ID pelanggan, nomor rekening.
_LONG_DIGITS_RE = re.compile(r'\b\d{5,}\b')
# dd/mm atau dd/mm/yyyy (juga dengan titik).
_DATE_RE = re.compile(r'\b\d{1,2}[/.]\d{1,2}(?:[/.]\d{2,4})?\b')
# Nominal + mata uang (0.99 USD, RP 500.000, 1.234.567,89).
_CURRENCY_AMOUNT_RE = re.compile(
    r'\b(?:rp\.?\s*)?\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{2})?\b'
    r'|\b\d+[.,]\d{2}\s*(?:usd|sgd|eur|idr)\b',
    re.IGNORECASE,
)
_MULTI_SPACE_RE = re.compile(r'\s+')


def clean_description(raw):
    """Bersihkan noise dari deskripsi mentah. Return str, atau None kalau
    setelah dibersihkan tidak tersisa apa pun."""
    if raw is None:
        return None
    cleaned = str(raw)
    cleaned = _CURRENCY_AMOUNT_RE.sub(' ', cleaned)
    cleaned = _DATE_RE.sub(' ', cleaned)
    cleaned = _LONG_DIGITS_RE.sub(' ', cleaned)
    cleaned = _MULTI_SPACE_RE.sub(' ', cleaned).strip()
    return cleaned or None


def enrich_transactions(engine, txn_ids, llm_complete=None, chunk_size=30):
    """Enrich daftar transaksi: rule layer untuk semua, LLM untuk sisanya.

    llm_complete(conn, requests) -> {id: clean_str} — dipanggil sekali per
    chunk hanya untuk baris yang belum tersentuh rule layer. Kegagalan LLM
    tidak menggagalkan hasil rule layer.
    Return {'enriched': n, 'llm_used': bool}.
    """
    txn_ids = [str(t) for t in txn_ids or []]
    if not txn_ids:
        return {'enriched': 0, 'llm_used': False}

    enriched = 0
    llm_used = False
    for start in range(0, len(txn_ids), chunk_size):
        chunk = txn_ids[start:start + chunk_size]
        llm_requests = []
        try:
            with engine.begin() as conn:
                placeholders = ', '.join(f':id_{i}' for i in range(len(chunk)))
                params = {f'id_{i}': txn_id for i, txn_id in enumerate(chunk)}
                rows = conn.execute(text_wrap(f"""
                    SELECT id, description, clean_description
                    FROM transactions
                    WHERE id IN ({placeholders})
                """), params).fetchall()

                for row in rows:
                    existing_clean = (row.clean_description or '').strip()
                    if existing_clean:
                        continue  # idempotent: sudah pernah di-enrich
                    cleaned = clean_description(row.description)
                    if cleaned and cleaned != str(row.description or '').strip():
                        conn.execute(text_wrap(
                            'UPDATE transactions SET clean_description = :c, '
                            'updated_at = :u WHERE id = :id'
                        ), {
                            'c': cleaned[:500],
                            'u': _now_str(),
                            'id': row.id,
                        })
                        enriched += 1
                    else:
                        # Tidak ada noise yang bisa dihapus rule layer →
                        # kandidat LLM (kalau tersedia).
                        llm_requests.append({
                            'id': str(row.id),
                            'description': str(row.description or '')[:1000],
                        })
        except Exception:
            logger.exception('Description enrichment gagal pada chunk %s', start)
            continue

        if llm_requests and callable(llm_complete):
            try:
                with engine.begin() as conn:
                    results = llm_complete(conn, llm_requests) or {}
                    for request in llm_requests:
                        cleaned = str(results.get(request['id']) or '').strip()
                        if not cleaned or cleaned == request['description']:
                            continue
                        conn.execute(text_wrap(
                            'UPDATE transactions SET clean_description = :c, '
                            'updated_at = :u WHERE id = :id'
                        ), {
                            'c': cleaned[:500],
                            'u': _now_str(),
                            'id': request['id'],
                        })
                        enriched += 1
                llm_used = True
            except Exception:
                logger.exception('LLM fallback enrichment gagal — hasil rule layer tetap dipakai')

    return {'enriched': enriched, 'llm_used': llm_used}


def _now_str():
    from datetime import datetime
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def text_wrap(sql):
    from sqlalchemy import text as _text
    return _text(sql)


_CLEAN_PROMPT = """Anda asisten akuntansi. Bersihkan deskripsi transaksi bank berikut.
Aturan:
- Hapus nomor referensi, ID pelanggan, nomor rekening, tanggal, dan nominal
- Pertahankan nama merchant/vendor dan kata yang bermakna
- Bahasa Indonesia, jangan ubah casing akronim (PLN, BCA, GOJEK)
- Jika deskripsi sudah bersih, kembalikan apa adanya

Jawab HANYA JSON: {"results": [{"id": "<id>", "clean": "<deskripsi bersih>"}]}

Transaksi:
"""


def llm_clean_batch(conn, requests, config):
    """Panggil LLM server-provider untuk sekumpulan deskripsi (dipakai endpoint
    manual enrich). Return {id: clean_str}; kegagalan parse → dict kosong."""
    import json

    from backend.services.ai import llm_client

    lines = '\n'.join(
        f"- id={req['id']} raw=\"{req['description']}\"" for req in requests
    )
    messages = [
        {'role': 'system', 'content': 'Anda asisten akuntansi yang menjawab hanya JSON.'},
        {'role': 'user', 'content': _CLEAN_PROMPT + lines},
    ]
    content = llm_client.chat_completion(
        config.get('base_url'), config.get('model'), messages,
        temperature=0.0, max_tokens=1200, api_key=config.get('api_key'),
    )

    # Model kadang membungkus JSON dalam ```json ... ``` — cari blok JSON pertama.
    text = content.strip()
    if text.startswith('```'):
        text = text.strip('`')
        if text.lower().startswith('json'):
            text = text[4:]
    start = text.find('{')
    end = text.rfind('}')
    if start == -1 or end == -1:
        raise ValueError('Respons LLM tidak berisi JSON.')
    payload = json.loads(text[start:end + 1])

    results = {}
    for item in payload.get('results', []):
        item_id = str(item.get('id') or '').strip()
        clean = str(item.get('clean') or '').strip()
        if item_id and clean:
            results[item_id] = clean[:500]
    return results
