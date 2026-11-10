"""Pass penandaan AI di latar belakang setelah konversi PDF.

Dijalankan sebagai daemon thread (pola threading pertama di repo ini — dipilih
karena tidak ada infrastruktur job/queue yang sudah ada). Rule layer instan untuk
semua baris; LLM fallback hanya untuk yang tanpa kecocokan riwayat. Kegagalan
pass TIDAK PERNAH memengaruhi hasil konversi — upload tetap sukses.
"""

import logging
import threading

from backend.db.session import get_db_engine
from backend.services.ai import llm_client, mark_suggester

logger = logging.getLogger(__name__)

# Provider lokal dijalankan dari BROWSER (laptop user) — server tidak dapat
# menjangkau localhost user, jadi pass latar belakang dilewati untuk mereka.
BRIDGE_PASS_ID_LIMIT = 100


def resolve_ai_pass_mode(config):
    """Putuskan jalur pass AI setelah konversi PDF berdasarkan settings AI.

    'skip'   — provider lokal (browser-bridge): server tidak dapat memanggil
               LLM di laptop user; pengguna menjalankan saran dari browser.
    'thread' — jalur lama: queue daemon thread (z.ai/custom; thread sendiri
               me-skip bila AI disabled atau model belum diatur).
    """
    if config.get('enabled') and config.get('provider') in llm_client.BRIDGE_PROVIDERS:
        return 'skip'
    return 'thread'


def queue_ai_mark_pass(txn_ids):
    """Jadwalkan pass AI untuk daftar id transaksi; balikan tanpa memblokir."""
    if not txn_ids:
        return False
    thread = threading.Thread(
        target=run_ai_mark_pass,
        args=(list(txn_ids),),
        name='ai-mark-pass',
        daemon=True,
    )
    thread.start()
    return True


def run_ai_mark_pass(txn_ids):
    """Proses kaskade AI (rule + LLM) untuk sekumpulan transaksi baru.

    One-shot per chunk agar satu transaksi gagal tidak menggagalkan chunk lain;
    setiap chunk memakai koneksi dan konfigurasinya sendiri.
    """
    engine, error_msg = get_db_engine()
    if engine is None:
        logger.warning('AI mark pass dilewati: DB tidak tersedia (%s)', error_msg)
        return

    CHUNK_SIZE = 15
    try:
        for start in range(0, len(txn_ids), CHUNK_SIZE):
            chunk = txn_ids[start:start + CHUNK_SIZE]
            try:
                with engine.begin() as conn:
                    config = llm_client.get_ai_settings(conn)
                    if not config.get('enabled'):
                        logger.info('AI mark pass dilewati: fitur AI nonaktif.')
                        return
                    if not config.get('model'):
                        logger.info('AI mark pass dilewati: model AI belum diatur.')
                        return
                    mark_suggester.ensure_ai_columns(conn)
                    history_index = mark_suggester.build_history_index(conn)
                    for txn_id in chunk:
                        result = mark_suggester.process_transaction(
                            conn, txn_id, config, history_index=history_index,
                        )
                        logger.info('AI mark pass %s: %s', txn_id, result.get('status'))
            except Exception:
                logger.exception('AI mark pass gagal pada chunk %s-%s', start, start + CHUNK_SIZE)

            # Enrichment deskripsi rule-based untuk semua provider (tanpa model,
            # jadi aman juga bila pass mark dilewati bridge browser nanti).
            try:
                from backend.services.ai import description_enricher
                result = description_enricher.enrich_transactions(engine, chunk)
                if result['enriched']:
                    logger.info('Description enrichment: %d baris chunk %s', result['enriched'], start)
            except Exception:
                logger.exception('Description enrichment gagal pada chunk %s (tidak fatal)', start)
    except Exception:
        logger.exception('AI mark pass gagal total')
