# esta: Ingestion Reliability + Accounting Integrity + AI Deepening

Tanggal: 2026-11-10
Status: Disetujui (brainstorming selesai, plan disetujui user)
Branch: `feature/ingestion-reliability-ai-accounting`

## Latar Belakang

esta baru saja menjalankan pipeline otomatis Gmail→n8n→esta (Nov 2026), tetapi pipeline
itu tanpa safety net:

- Kedua node akhir workflow n8n adalah NoOp — kegagalan parse/password tidak memberi
  tahu siapa pun sampai dicek manual di n8n Executions. Parser Mandiri Consolidated
  bahkan masih eksperimental per SETUP doc.
- `n8n_bp.py` menerima `email_from/subject/date/message_id` tetapi hanya me-log-nya;
  idempotency bertumpu sendirian pada MD5 `file_hash`. Bank yang me-regenerate PDF
  dengan byte berbeda untuk periode sama akan ter-import dua kali.
- Kolom `balance`/`currency` sudah diparse semua parser tetapi dibuang di
  `build_transaction_record` (`transaction_utils.py`) — peluang verifikasi integritas hilang.
- GL summary tidak punya opening balance (temuan review FY2025) → belum ada true trial balance.
- `PRD_AI_FEATURES.md` (description enrichment + auto-marking) belum diimplementasi.

User memilih satu spec besar dieksekusi bertahap 3 fase.

## Keputusan Desain (locked dengan user)

1. **Notifikasi**: Telegram Bot API, **hanya event bermasalah** (parse_failed, password
   salah, error DB, statement bulanan hilang). Import sukses/duplicate didiamkan.
2. **Idempotency**: `email_message_id` dicek **sebelum** `file_hash` → cegah double-import
   saat bank regenerate PDF beda byte. Keduanya tetap return HTTP 200 status `duplicate`.
3. **Kontinuitas saldo**: dihitung on-the-fly per halaman (tanpa kolom flag di DB),
   ditampilkan sebagai halaman laporan. Import **tidak pernah diblok** (flag-only).
4. **AI enrichment**: kolom baru `clean_description`; deskripsi asli tetap utuh (audit trail).
5. **HTTP client**: `urllib.request` mengikuti pola `llm_client.py` — tanpa dependency baru.
6. **Scheduling tetap di n8n** — tidak menambah scheduler di Python app.
7. **True trial balance**: dengan UI input saldo awal (per company × tahun, validasi D=C).

## Fase 1 — Ingestion Reliability

Migrasi `073_email_metadata_on_transactions.sql`: `email_from VARCHAR(300)`,
`email_subject VARCHAR(300)`, `email_date VARCHAR(60)`, `email_message_id VARCHAR(300)`
di tabel `transactions`.

1. **TelegramNotifier** — `backend/services/notifications/telegram.py`
   - Env: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` (fail-soft: log warning, tidak
     pernah gagalkan import; tanpa env → no-op).
   - `notify_import_problem(bank_type, filename, error_code, detail, email_meta)`.
2. **Persist metadata + idempotency** — `n8n_bp.py`:
   - Duplikat `email_message_id` dicek dulu (query di `pdf_queries.py`), baru `file_hash`.
   - `email_meta` diteruskan ke `save_transactions_to_db` → `build_transaction_record`.
3. **Hook notifikasi** di semua path error `ingest_statement()` — try/except terpisah
   agar kegagalan notifikasi tidak menelan error asli.
4. **Alert statement bulanan hilang**:
   - `backend/services/transactions/statement_expectations.py`: ekstrak logika dari
     upload-checklist; per akun bank aktif, statement bulan sebelumnya ada/tidak;
     grace period default tanggal ≥5.
   - `POST /api/integrations/statement-check` (API key) → evaluasi + Telegram.
   - Update `docs/n8n/gmail-esta-e-statement.json` (node panggilan harian) +
     perbaiki SETUP doc yang stale ("poll 5 menit", maxResults 200→50).
5. **Test**: `test_integrations_bp.py` (extend), `test_telegram.py`, `test_statement_expectations.py`.

## Fase 2 — Accounting Integrity

1. **Persist balance** — migrasi `074_running_balance_currency.sql`
   (`running_balance DECIMAL(18,2) NULL`, `currency VARCHAR(8) NULL`); diisi dari kolom
   `balance`/`currency` DataFrame. Hanya data ke depan (backfill tidak dilakukan —
   keterbatasan didokumentasikan).
2. **Cek kontinuitas saldo** — `backend/services/reporting/balance_continuity.py`:
   per akun bank urut `txn_date`, recompute running balance vs tersimpan; klasifikasi
   break: saldo lompat / gap tanggal antar statement / mismatch tolerance rounding.
   Route + halaman `/balance-check`.
3. **True trial balance**:
   - Migrasi `075_opening_balances.sql` (tabel `opening_balances`).
   - UI input saldo awal (validasi debit=kredit).
   - `backend/services/reporting/trial_balance.py` + route + halaman: opening + mutasi
     = closing per akun, cek total D=C, PDF export ikut pola `xhtml2pdf` yang ada.
4. **Test**: `test_balance_continuity.py`, `test_trial_balance.py`.

## Fase 3 — AI Deepening (lanjutan PRD_AI_FEATURES.md)

1. **Description enrichment**:
   - Migrasi `076_clean_description.sql` (`clean_description VARCHAR(500)`).
   - `backend/services/ai/description_enricher.py`: rule-based cleanup dulu (nomor
     referensi, tanggal, boilerplate bank) → LLM hanya untuk sisa ambigu via
     `llm_client` + bridge browser yang ada. Pass terpisah setelah AI mark pass.
   - Frontend History: tampilkan `clean_description` + tooltip asli; tombol re-run bulk.
2. **Review queue confidence rendah**: preset `ai-review` (ai_status=pending +
   confidence < threshold); bulk accept/reject.
3. **Test**: `test_description_enricher.py`, extend `test_ai_bp.py`.

## Eksekusi & Verifikasi

Fase 1 → 2 → 3 berurutan, commit per fase, TDD per fase.

1. `pytest admin_backend/tests/` hijau semua.
2. E2E Fase 1: POST statement dua kali dengan `email_message_id` sama → imported lalu
   duplicate (keduanya 200); tanpa env Telegram → import tetap sukses.
3. E2E Fase 2: dua statement nyambung → `/balance-check` bersih; satu statement
   disengkangkan → break terdeteksi; TB seimbang D=C.
4. E2E Fase 3: deskripsi kotor → `clean_description` terisi + muncul di review queue.
5. UI walkthrough manual via `admin_backend/run.sh`.
