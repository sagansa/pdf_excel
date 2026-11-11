# Admin Backend Structure

Runtime code is separated from tooling and archive material.

## Main entrypoints

- `server.py`: Flask app entrypoint
- `migrate.py`: primary migration runner
- `requirements.txt`: backend Python dependencies

## Kredensial (API Keys)

Semua API key/token aplikasi dikelola dari **Settings → API Keys** di admin panel:
token Sagansa superadmin (presence, remaining storage, stock monitoring, sales by
date, stock comparison), Telegram (bot token + chat id), SMTP (host/port/user/
password/from/TLS), kunci integrasi n8n, dan API key provider AI.

- Nilai disimpan di tabel `app_settings`; frontend hanya melihat status
  terisi/tidak — nilai secret tidak pernah ditampilkan kembali.
- **Environment variable tetap berfungsi sebagai fallback** (nama env = nama
  setting, mis. `SAGANSA_PRESENCE_TOKEN` = `sagansa_presence_token`). Nilai DB
  selalu menang atas env.
- Deployment lama: variabel env yang masih ada ditandai "dari env" di tab API
  Keys — tekan Simpan untuk memindahkannya ke database.
- Tombol **Test** menguji koneksi ke service tujuan (termasuk mengirim pesan tes
  Telegram / login SMTP) tanpa menyimpan nilai.
- Catatan upgrade: fallback implisit antar env (`SAGANSA_STOCK_MONITORING_TOKEN`
  yang dulu jatuh ke `SAGANSA_REMAINING_STORAGE_TOKEN`) sudah dihapus — setiap
  kunci sekarang berdiri sendiri, jadi set nilainya masing-masing.

## Runtime folders

- `backend/db`
  - database engine/session/schema helpers
- `backend/routes`
  - Flask blueprints grouped by domain:
  - `amortization/`
  - `inventory/`
  - `master_data/`
  - `reporting/`
  - `rental/`
  - `transactions/`
  - `uploads/`
  - shared helpers remain at route root when used across domains
- `backend/services`
  - service layer grouped by domain:
  - `reporting/`
  - `rental/`
  - `transactions/`
- `backend/utils`
  - shared non-route helpers such as:
  - `date_helpers.py`
  - `pdf_year_utils.py`
  - `pdf_unlock.py`
- `bank_parsers`
  - bank-specific PDF/CSV parsers plus `parser_common.py`
- `database`
  - SQL migrations and migration validation helpers
- `pdfs`
  - upload working directory

## Tooling folders

- `scripts/maintenance`
  - one-off maintenance and migration helper scripts
- `scripts/parsers`
  - parser-related manual utilities
- `tests`
  - retained active tests

## Archive

Archived investigation/debug/test scripts were moved out of runtime tree to:

- `pdf_excel/admin_backend_archive/scripts`

That archive is intentionally not treated as runtime-safe code.

## Naming note

There are two different PDF helper areas by design:

- `backend/routes/uploads/pdf_helpers.py`
  - upload workflow and parser orchestration
- `backend/utils/pdf_year_utils.py`
  - year inference utilities
