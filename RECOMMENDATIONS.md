# 📋 Rekomendasi Penanganan Aplikasi esta (StatementX)

> Hasil review arsitektur, keamanan, dan kualitas kode pada `admin_backend` (Flask) + `admin_frontend` (Vue 3).
> Dibuat: 2026-06-18

---

## 0. Ringkasan Eksekutif

Aplikasi ini adalah sistem akuntansi/internal-tool (bank statement converter → transactions → reports) yang sudah cukup matang fungsinya, namun memiliki **beberapa masalah kritis** yang wajib ditangani sebelum dipakai lebih luas:

| Prioritas | Temuan | Risiko |
|-----------|--------|--------|
| 🔴 Kritis | `.env` (berisi password DB + token API Sagansa) ter-commit ke git | Kebocoran kredensial |
| 🔴 Kritis | File database `.db`/`.sqlite` ter-commit ke git | Kebocoran data sensitif |
| 🔴 Kritis | Tidak ada autentikasi/otorisasi sama sekali di backend | Siapa pun bisa baca/tulis data |
| 🔴 Kritis | CORS `*` (semua origin, semua header) | Serangan cross-origin |
| 🟠 Tinggi | 10 prefix migration duplikat (012,013,017,018,020,026,027,028,043,045) | Migration tidak deterministik |
| 🟠 Tinggi | Default kredensial `root:root`, kredensial hardcoded | Kompromi DB |
| 🟡 Sedang | Client-side filtering (load semua transaksi) | Performa turun saat data besar |
| 🟡 Sedang | `console.log` debug tertinggal di production | Kebocoran info + noise |
| 🟡 Sedang | Frontend tanpa TypeScript | Bug runtime, refactoring sulit |
| 🟢 Rendah | API client monolitik (509 baris di 1 file) | Maintainability |

---

## 1. 🔴 KEAMANAN (Tangani SEKARANG)

### 1.1 Kebocoran Kredensial via Git

**Bukti:** `git ls-files` menunjukkan `admin_backend/.env` ter-track. Isinya:
```
DB_PASS=****
SAGANSA_PRESENCE_TOKEN=****   (nilai asli telah diredaksi)
SAGANSA_REMAINING_STORAGE_TOKEN=...   (token sama dipakai berulang)
```

**Tindakan:**
1. **Rotasi SEMUA token/kredensial yang ter-expose** (token Sagansa, password DB).
2. Hapus `.env` dari tracking (tapi simpan file lokalnya):
   ```bash
   git rm --cached admin_backend/.env
   ```
3. Tambahkan ke `.gitignore`:
   ```
   admin_backend/.env
   admin_backend/.env.*
   !admin_backend/.env.example
   ```
4. Buat `admin_backend/.env.example` berisi placeholder tanpa nilai rahasia.
5. Bersihkan history git (BFG atau `git filter-repo`) bila repo ini pernah push ke remote publik.

### 1.2 File Database Ter-commit

**Bukti:** `admin_backend/admin.db`, `database.db`, `database.sqlite`, `backend/statement_x.db` ter-track.

**Tindakan:**
- `git rm --cached` semua file `*.db`, `*.sqlite`, `*.sqlite3`.
- Tambahkan ke `.gitignore`:
  ```
  *.db
  *.sqlite
  *.sqlite3
  admin_backend/admin.db
  admin_backend/database.db
  admin_backend/database.sqlite
  admin_backend/backend/statement_x.db
  ```

### 1.3 Tidak Ada Autentikasi

**Bukti:** Search `before_request|jwt|login_required|@auth|token_required` → 0 hasil. CORS wide open. Semua endpoint `/api/*` dapat diakses publik.

**Tindakan:**
Sesuai `.clinerules`, autentikasi user wajib memakai database `sagansa_user`. Minimal:
1. Tambah middleware `@app.before_request` yang memvalidasi Bearer token (JWT atau token dari `sagansa_user`).
2. Implementasi role-based access (admin/accountant/viewer).
3. Tambah auth guard di `vue-router` (`router.beforeEach`) + halaman login.

### 1.4 CORS Terlalu Longgar

```python
CORS(app, resources={r"/*": {"origins": "*", "allow_headers": "*", "expose_headers": "*"}})
```

**Tindakan:** Batasi ke origin frontend yang valid via env:
```python
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
CORS(app, resources={r"/api/*": {"origins": ALLOWED_ORIGINS, "allow_headers": "Content-Type,Authorization"}})
```

### 1.5 SQL Injection (Tinjau Ulang)

Banyak query memakai f-string interpolation:
```python
result = conn.execute(text(f"SELECT ... {year_filter} ... {split_exclusion} ..."))
```
Saat ini fragmen datang dari helper internal (aman), **tetapi** pola ini rawan bila ada input user yang lolos. **Audit** semua `text(f"...")` dan pastikan tidak ada nilai dari `request.args`/`request.json` yang di-string-interpolate (semua harus via parameter `:param`).

---

## 2. 🟠 DATABASE & MIGRATION

### 2.1 Duplikasi Prefix Migration

**Bukti:** 10 prefix duplikat terdeteksi: `012, 013, 017, 018, 020, 026, 027, 028, 043, 045`. Contoh:
```
012_add_batch_date_to_hpp_batches.sql
012_add_transaction_notes.sql
013_add_initial_capital_settings.sql
013_create_user_filters.sql
...
```

`migration_index.py` memberi **warning** (bukan error) untuk duplikat → runner memilih salah satu secara alphabet, migration lain **never applied**.

**Tindakan:**
1. Renumber semua migration agar unik (mis. `012a`, `012b` → atau ubah ke `012_`, `013_`).
2. Ubah `duplicate_prefixes()` dari warning → **error** agar CI gagal bila ada duplikat.
3. Verifikasi table `pdf_excel_migrations` di setiap environment untuk memastikan semua migration yang seharusnya jalan sudah jalan.

### 2.2 Sesuaikan dengan `.clinerules`

Aturan global menyatakan: **seluruh data migration menggunakan `services/migration`**. Saat ini migration ada di `admin_backend/database/migrations` (custom runner).

**Tindakan (perlu keputusan strategis):**
- Pindahkan pipeline migration ke `services/migration` (Laravel) sesuai standar `sagansa_2026`.
- Atau, bila `esta` memang tool standalone, dokumentasikan pengecualian ini secara eksplisit di `README.md`.

### 2.3 Dialect Branching Manual

Banyak `if conn.dialect.name == 'sqlite': ... else: ...`. Ini menambah kompleksitas & risiko salah logika.

**Tindakan:** Pilih **satu** dialect untuk produksi (MySQL) dan jadikan SQLite hanya untuk test. Kapsulasi perbedaan di layer `db/compat.py`, bukan tersebar di tiap route.

### 2.4 Global Singleton Engine

```python
_db_engine = None
def get_db_engine(): ...  # cached globally
```
Tidak thread-safe untuk reset & sulit ditest.

**Tindakan:** Pakai Flask-SQLAlchemy atau dependency injection per-request via `g`/context.

---

## 3. 🟡 BACKEND (Flask)

### 3.1 Struktur sudah baik ✅
- Blueprints per domain (transactions, reporting, rental, inventory, amortization).
- Pemisahan `routes/` vs `services/` vs `db/`.
- Error handler terpusat.

### 3.2 Yang Perlu Diperbaiki
- **Validasi input**: tambahkan schema validation (mis. `pydantic` atau `marshmallow`) untuk POST/PUT. Saat ini parsing manual rentan typo.
- **Logging**: sudah ada `logging` tapi belum terlihat konfigurasi rotation/level via env. Tambahkan `LOG_LEVEL`, format JSON untuk produksi.
- **Health check**: tambahkan endpoint `/health` dan `/ready` (cek DB + Sagansa API) untuk monitoring/load balancer.
- **Rate limiting**: tambahkan `flask-limiter` terutama untuk endpoint import/upload PDF.
- **Testing**: ada `tests/` tapi belum ada CI config. Tambahkan GitHub Actions + coverage threshold.
- **Konfigurasi**: `app.config` hanya berisi `UPLOAD_FOLDER`. Pindah ke objek config class (`Config`, `ProductionConfig`).

### 3.3 PDF/Bank Parser
- Modul `bank_parsers/` mendukung BCA, BRI, Mandiri, DBS, BLU, SAQU. Bagus.
- **Saran**: tambahkan registry pattern + unit test per parser dengan fixture PDF anonim.
- Pastikan tidak menyimpan PDF hasil upload lebih lama dari yang dibutuhkan (retention policy + cleanup cron).

---

## 4. 🟡 FRONTEND (Vue 3)

### 4.1 Sudah Baik ✅
- Vue 3 `<script setup>`, Pinia, Vue Router, TailwindCSS.
- Komponen UI reusable di `components/ui/`.
- Dark mode via composable `useTheme`.

### 4.2 Yang Perlu Diperbaiki

#### a. Hapus `console.log` di Production
Banyak di `stores/history.js`:
```js
console.log('HistoryStore: sortedMarks computed, count:', marks.length);
console.log('HistoryStore: Sample transaction with parent_id:', ...);
```
**Tindakan:** Buat wrapper logger (`utils/log.js`) yang no-op di production, atau config Vite `drop_console`:
```js
// vite.config.js
build: { minify: 'terser', terserOptions: { compress: { drop_console: true } } }
```

#### b. Lazy Load Routes
`router/index.js` meng-import semua view eager → bundle besar.
```js
// Sebelum
import Dashboard from '../views/Dashboard.vue'
// Sesudah
const Dashboard = () => import('../views/Dashboard.vue')
```

#### c. API Client Monolitik
`src/api/index.js` = 509 baris berisi semua endpoint. **Pecah** per domain:
```
src/api/
  index.js          (axios instance + interceptor)
  auth.js
  transactions.js
  reports.js
  rental.js
  inventory.js
  hrd.js
```

#### d. Client-Side Filtering Berat
`stores/history.js` `loadData()` mengambil **semua transaksi** lalu filter di browser. Tidak scalable.

**Tindakan:** Pindahkan filter (year, date, bank, company, mark, coa, search, dbCr, amount) ke query param backend + paginasi server-side. Frontend hanya render page.

#### e. Migrasi ke TypeScript
Saat ini pure JS. Untuk app dengan domain kompleks (akuntansi, COA, marks), TypeScript sangat membantu. Mulai dengan file baru pakai TS, config `allowJs`.

#### f. Auth Guard & Intercept 401
- Tambah `router.beforeEach` untuk cek token.
- Tambah axios interceptor: pada 401 → redirect login + clear state.

#### g. Error Handling Konsisten
Banyak `catch (e) { console.error(e); throw e; }` tanpa user feedback. Pakai toast (`vue-toastification` sudah ada) untuk error umum, dan biarkan throw hanya untuk error yang butuh alur khusus.

#### h. Environment Variable
Belum ada `.env` frontend. Tambahkan `.env.development` / `.env.production` untuk `VITE_API_BASE_URL` (saat ini hardcoded `/api`).

---

## 5. 🟢 ARSITEKTUR & COMPLIANCE

### 5.1 `.clinerules` vs Realita
Aturan global menyatakan struktur `sagansa_2026`:
```
services/{api,api-admin,api-mobile,api-web,api-ops,migration}
apps/{admin,order,menu,ev,ops}
mobiles/{admin,point-of-sale,presence}
```
Saat ini `esta` adalah monorepo `admin_backend` + `admin_frontend` yang **di-luar** struktur itu.

**Keputusan yang perlu diambil:**
- Apakah `esta` akan di-integrasi sebagai `apps/admin` (laravel+filament) atau `services/api-ops`?
- Atau `esta` standalone tool yang konsumsi `sagansa_user` via API (seperti yang sudah dilakukan untuk presence/storage/sales)?

**Saran:** Karena `esta` sudah menggunakan koneksi DB sendiri + API Sagansa untuk data operasional, posisikan sebagai **`apps/admin` internal finance tool** dan migrasikan auth ke `sagansa_user`.

### 5.2 Observability
- Tidak terlihat metric/tracing (Sentry, OpenTelemetry). Tambahkan minimal Sentry untuk frontend & backend.
- Tambahkan structured logging + request ID correlation.

### 5.3 CI/CD
- Tidak ada `.github/workflows/`. Buat pipeline:
  1. Lint (ruff untuk Python, eslint untuk JS)
  2. Test (pytest, vitest)
  3. Build frontend
  4. Deploy (sesuai platform — saat ini `Procfile` mengindikasikan Heroku/Render-style)

### 5.4 Dokumentasi
- `README.md` sangat minim (28 baris). Lengkapi: arsitektur, setup DB, env vars, alur data, diagram ERD, cara tambah bank parser, cara tambah migration.

---

## 6. 📝 Rencana Aksi (Urut Prioritas)

### Sprint 1 — Mitigasi Risiko Kritis (1–2 hari)
- [ ] Rotasi token Sagansa + password DB
- [ ] `git rm --cached admin_backend/.env` + update `.gitignore`
- [ ] `git rm --cached` semua `*.db`/`*.sqlite`
- [ ] Buat `admin_backend/.env.example`
- [ ] Kunci CORS ke origin yang valid
- [ ] Tambah auth middleware minimal (validate Bearer token ke `sagansa_user`)

### Sprint 2 — Stabilisasi (3–5 hari)
- [ ] Renumber migration duplikat + jadikan duplikat = error
- [ ] Audit SQL injection di semua `text(f"...")`
- [ ] Tambah `/health`, `/ready`
- [ ] Hapus `console.log` + config Vite `drop_console`
- [ ] Lazy load routes frontend
- [ ] Pecah `api/index.js` per domain

### Sprint 3 — Peningkatan (1–2 minggu)
- [ ] Server-side filtering + pagination di History
- [ ] Migrasi frontend bertahap ke TypeScript
- [ ] CI/CD (GitHub Actions): lint + test + build
- [ ] Sentry / error tracking
- [ ] Dokumentasi README lengkap + ERD

### Sprint 4 — Alignment Strategis (perlu diskusi)
- [ ] Putuskan posisi `esta` di struktur `sagansa_2026`
- [ ] Bila ya → rencana migrasi auth + schema ke `sagansa_user`
- [ ] Pertimbangkan pindahkan migration ke `services/migration` (Laravel)

---

## 7. Lampiran: File Kunci yang Direkomendasikan Ditambah/Diubah

| File | Aksi |
|------|------|
| `.gitignore` | Tambah `.env`, `*.db`, `*.sqlite` |
| `admin_backend/.env.example` | Buat (placeholder) |
| `admin_backend/server.py` | CORS restricted, auth `before_request` |
| `admin_backend/backend/auth/` | Buat: middleware token validation |
| `admin_backend/database/migration_index.py` | Duplikat = error |
| `admin_backend/database/migrations/` | Renumber 10 duplikat |
| `admin_frontend/vite.config.js` | `drop_console`, env proxy |
| `admin_frontend/src/router/index.js` | Lazy load + auth guard |
| `admin_frontend/src/api/*` | Pecah per domain |
| `admin_frontend/.env.*` | Buat `VITE_API_BASE_URL` |
| `.github/workflows/ci.yml` | Buat pipeline |

---

_Dokumen ini adalah rekomendasi berdasarkan review statik kode. Validasi temuan kritis (terutama yang menyangkut produksi) bersama tim sebelum eksekusi._