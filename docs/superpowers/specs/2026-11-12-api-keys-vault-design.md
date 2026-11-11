# Design: Vault Kredensial Terpusat — Tab "API Keys" di Settings

Tanggal: 2026-11-12
Status: Disetujui (brainstorming selesai)

## Ringkasan

Saat ini hampir semua kredensial aplikasi (token API Sagansa superadmin, SMTP,
Telegram, kunci integrasi n8n) hanya hidup sebagai **environment variable**.
Saat deployment berpindah / container dibuat ulang / var lupa diset, fitur terkait
gagal diam-diam: payroll tidak bisa tarik presensi, inventory kosong, email reset
password tidak terkirim, notifikasi Telegram senyap, endpoint n8n mati (503).

Solusi: satu tempat terpusat untuk meng-inject semua API key/token, dikelola dari
tab baru **"API Keys"** di Settings. Nilai disimpan di tabel `app_settings` yang
sudah ada (pattern yang sama dengan `ai_api_key` hari ini), dibaca
**DB dulu → fallback env**, dan **tidak pernah dikembalikan mentah ke frontend**
— hanya indikator terisi/belum.

## Keputusan (dari sesi brainstorming)

| Keputusan | Pilihan |
|---|---|
| Scope kredensial | **Semua token app + AI key dipindah** ke vault (tab AI jadi membaca dari vault) |
| Penyimpanan | **Plaintext di `app_settings`** — konsisten dengan `ai_api_key`; tanpa enkripsi supaya tidak ada risiko baru "kunci hilang karena secret enkripsi ikut hilang" |
| Tombol Test | **Ya, per kredensial keluar** (Presence, 4 token inventory, Telegram, SMTP). n8n tidak (kuncinya dipakai sistem luar untuk auth ke kita) |
| Pendekatan | **Central credentials service + tab baru** (menolak pendekatan ad-hoc per blueprint yang menduplikasi pola sentinel/masking 6–7 kali) |

Alternatif yang ditolak:
- **Fallback DB ad-hoc per blueprint**: pola masking/sentinel/test terduplikasi di
  banyak file, UI acak (kredensial bercampur setting lain), AI key tidak punya
  tempat seragam — justru melanggengkan masalah "hilang di beberapa tempat".
- **Enkripsi Fernet + SECRET_KEY**: lebih aman jika file DB bocor, tetapi
  `SECRET_KEY` env yang hilang/berubah membuat semua kredensial tak terbaca —
  risiko kehilangan baru yang justru ingin dihilangkan.

## 1. Registry Kredensial (`backend/services/credentials.py`)

Modul baru = *single source of truth*. Satu registry berisi definisi semua
kredensial: nama setting, label UI, grup, secret atau tidak, env fallback,
dan handler test (opsional). Kunci setting memakai **nama natural di
`app_settings` (1:1 dengan nama env var, tanpa prefix)** sehingga `ai_api_key`
yang sudah ada tidak butuh migrasi data.

| setting_key (`app_settings`) | env fallback | secret | grup UI | test |
|---|---|---|---|---|
| `sagansa_presence_token` | `SAGANSA_PRESENCE_TOKEN` | ya | Sagansa Superadmin API | GET presence API |
| `sagansa_remaining_storage_token` | `SAGANSA_REMAINING_STORAGE_TOKEN` | ya | Sagansa Superadmin API | GET `?per_page=1` |
| `sagansa_stock_monitoring_token` | `SAGANSA_STOCK_MONITORING_TOKEN` | ya | Sagansa Superadmin API | GET `?per_page=1` |
| `sagansa_sales_by_date_token` | `SAGANSA_SALES_BY_DATE_TOKEN` | ya | Sagansa Superadmin API | GET param default |
| `sagansa_stock_comparison_token` | `SAGANSA_STOCK_COMPARISON_TOKEN` | ya | Sagansa Superadmin API | GET |
| `telegram_bot_token` | `TELEGRAM_BOT_TOKEN` | ya | Telegram | kirim pesan test |
| `telegram_chat_id` | `TELEGRAM_CHAT_ID` | tidak | Telegram | (ikut test telegram) |
| `smtp_host` | `SMTP_HOST` | tidak | Email SMTP | ikut test SMTP |
| `smtp_port` | `SMTP_PORT` | tidak | Email SMTP | ikut test SMTP |
| `smtp_user` | `SMTP_USER` | tidak | Email SMTP | ikut test SMTP |
| `smtp_pass` | `SMTP_PASS` | ya | Email SMTP | ikut test SMTP |
| `smtp_from` | `SMTP_FROM` | tidak | Email SMTP | ikut test SMTP |
| `smtp_use_tls` | `SMTP_USE_TLS` | tidak | Email SMTP | ikut test SMTP |
| `integration_api_key` | `INTEGRATION_API_KEY` | ya | n8n Integration | tanpa test (incoming) |
| `ai_api_key` (sudah ada) | — | ya | AI Provider | via tab AI (`/api/ai/test-connection`) |

**Urutan resolusi** (`get_credential(conn, key)` / `get_credential_value(key)`):
nilai DB (`app_settings`) → fallback env → kosong. Versi dengan conn memakai
conn yang diberikan; versi tanpa conn membuka koneksi pendek dari engine global.

URL API Sagansa (bukan secret) tetap dibaca dari env/constants seperti sekarang —
di luar scope vault.

## 2. Endpoint Backend (`credentials_bp` — blueprint baru, 1 file)

Dilindungi guard login global yang sudah ada (`server.py` `before_request`) —
tanpa perubahan auth.

- `GET /api/credentials`
  → `{'credentials': [{key, label, group, secret, set, source, value?}]}`.
  `value` (nilai asli) hanya untuk field non-secret (chat_id, SMTP host/port/
  user/from/tls) agar form bisa di-prefill. Secret hanya `set: true/false`.
  `source: 'db' | 'env'` — UI menampilkan "dari env — klik Simpan untuk
  memindahkan ke database" (jalur migrasi deployment lama).
- `PUT /api/credentials` — **bulk save**: `{'updates': {key: nilai | '__CLEAR__'}}`.
  Sentinel `__CLEAR__` menghapus nilai. Konstanta canonical dipindah ke
  `credentials.py`; referensi sentinel di `ai_bp`/`llm_client` dihapus bersih —
  `/api/ai/settings` tidak lagi menerima `api_key` sama sekali. Response =
  daftar status terbaru, tanpa pernah memuat nilai secret. Key yang tidak dikenal
  → 400. Semua key di registry bersifat editable.
- `POST /api/credentials/<key>/test`
  → jalankan handler test milik kredensial itu; timeout 10–15 detik; selalu
  balik `{'ok': bool, 'message': str}` (tidak pernah raise ke 500). Test boleh
  menerima override nilai di body (untuk menguji nilai yang baru diketik
  sebelum disimpan): `{'value': ..., 'extra': {chat_id: ...}}` — jika tidak ada,
  pakai nilai tersimpan (DB→env).

## 3. Refactor Pemanggil (titik yang selama ini "kehilangan" kunci)

| File | Perubahan |
|---|---|
| `routes/transactions/payroll_bp.py` | `DEFAULT_PRESENCE_API_TOKEN` → baca via service per-request |
| `routes/inventory/remaining_storage_bp.py` | 2 konstanta token → service |
| `routes/inventory/hpp_bp.py` | 2 konstanta token → service |
| `routes/inventory/inventory_bp.py` | 2 konstanta token → service |
| `routes/inventory/sales_by_date_bp.py` | konstanta token → service |
| `routes/inventory/stock_comparison_bp.py` | konstanta token → service |
| `services/mailer.py` | `get_smtp_config(conn=None)`: DB→env; caller `auth_bp` mengirim conn |
| `services/notifications/telegram.py` | `_is_configured`/`_send_message` baca via service |
| `routes/integrations/n8n_bp.py` | expected key via service (tetap **fail-closed 503** jika kosong) |
| `services/ai/llm_client.py` | `save_ai_settings` tidak lagi menangani `ai_api_key` (milik vault); `get_ai_settings` tetap membaca `app_settings` tempat vault menyimpannya; konstanta sentinel + penanganan api_key dihapus dari `llm_client` dan `ai_bp` (endpoint AI tidak lagi menerima `api_key`) |

Konstanta URL (non-secret) tetap di env/constants. Duplikasi konstanta token di
5 blueprint inventory hilang — semuanya lewat satu registry.

## 4. Frontend — Tab "API Keys"

- Komponen baru `src/components/settings/CredentialsSettings.vue`; tombol tab
  baru di `SettingsView.vue` (icon `bi-key-fill`).
- **Satu kartu per grup**: Sagansa Superadmin API (5 token), AI Provider
  (`ai_api_key` + hint ke tab AI untuk provider/model), Telegram (token + chat
  id + Test), Email SMTP (6 field + Test), n8n Integration (key, tanpa test).
- Pola input secret mengikuti `AiSettings.vue` yang sudah ada: `type="password"`,
  placeholder "Tersimpan — isi untuk mengganti" / "Belum diisi", link "Hapus"
  saat terisi, `autocomplete="off"`. Field non-secret: text input ter-prefill.
- Tombol **Simpan per grup** (bulk PUT; hanya key yang berubah — secret hanya
  dikirim jika user mengetik atau menekan hapus), tombol **Test** per grup yang
  punya test, hasil inline hijau/merah dengan pesan dari server.
- Badge kecil per kredensial: `set` (terisi) + `source` (db / dari env — simpan
  untuk memindahkan).
- `AiSettings.vue`: input API key **dihapus**; diganti info box status kunci
  (terisi/belum) + tombol pindah ke tab API Keys. Provider/base URL/model/auto-
  apply tetap di tab AI, perilaku save/test tidak berubah.

## 5. Error Handling, Keamanan & Testing

**Keamanan**
- Secret tidak pernah masuk response GET/PUT, tidak pernah di-log.
- Nilai test yang diketik user tidak di-log.
- Akses ditolak untuk sesi tidak login (guard global ada).

**Error handling**
- Handler test menangkap semua exception → pesan jelas ("HTTP 401 — token
  salah/tidak berlaku", "tidak dapat dihubungi (timeout)", dst).
- GET/PUT tetap berjalan tanpa env sama sekali (dari DB saja).

**Testing**
- Backend: unit test pytest di `admin_backend/tests/` — resolusi DB→env,
  sentinel clear, masking GET/PUT (secret tidak pernah muncul), key tak dikenal,
  dan tiap handler test (HTTP di-mock).
- Frontend: verifikasi manual lewat browser — paste token, Simpan, Test, Hapus,
  fallback env, dan alur AI key dari tab AI.

## Dampak

- Deployment baru: buka Settings → API Keys → tempel token → Simpan → Test.
  Tidak perlu lagi set env satu per satu.
- Deployment lama yang env-nya masih ada: tetap jalan via fallback; UI menandai
  mana yang masih "dari env" agar bisa dipindahkan ke DB sekali klik.
- Kredensial baru di masa depan = tambah satu entri registry (+ handler test
  opsional), endpoint dan UI mengikuti otomatis.
