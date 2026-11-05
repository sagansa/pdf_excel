# Rencana: Sistem Login StatementX (esta)

## Context

Aplikasi keuangan ini (Flask + Vue 3, 146 route) **tidak punya autentikasi sama sekali**: seluruh data transaksi bank, payroll, dan laporan keuangan bisa dibaca/dihapus siapa pun di jaringan (server bind `0.0.0.0`, CORS `origins: "*"`). Eksplorasi menegaskan: tidak ada tabel users lokal, tidak ada SECRET_KEY, tidak ada guard route di frontend. Keputusan user: **tabel users lokal (bcrypt-style hash) + multi-user satu level** (semua yang login akses penuh).

Mekanisme sesi: **cookie HttpOnly** (Flask signed session). Alasan: SPA + API same-origin (satu server gunicorn melayani keduanya), kebal XSS, tanpa dependency baru. JWT-di-header ditolak karena butuh token storage di JS + interceptor di 3 tempat axios terpisah.

## Desain Backend

### 1. Migrasi DB — `database/migrations/071_create_users.sql`
(Nomor menyesuaikan file migrasi terakhir saat implementasi; saat ini ada 70 file.)
```sql
CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(64) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  display_name VARCHAR(128) NOT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```
Migrasi otomatis dijalankan `run_migrations()` saat startup (pola `migrate.py` yang sudah ada).

### 2. Blueprint auth baru — `backend/routes/auth_bp.py`
- `POST /api/auth/login` `{username, password}` → cek hash via `werkzeug.security.check_password_hash` (scrypt — werkzeug 3.1.9 sudah terinstall, **tanpa dependency baru**), set `session.permanent = True`, simpan `session['user_id']` + `session['username']`. Balas `{user: {id, username, display_name}}`.
- `POST /api/auth/logout` → `session.clear()`.
- `GET /api/auth/me` → data user dari session atau 401.
- **Rate limit login**: dict in-memory `{(ip, username): [timestamps]}` — max 5 percobaan gagal / 5 menit, balas 429. Cukup untuk single-process gunicorn; tanpa flask-limiter.
- Error 401 konsisten dengan pola `backend/errors.py` yang ada.

### 3. Guard global — `server.py`
- `@app.before_request`: tolak **401 JSON** untuk semua `/api/*` kecuali `/api/auth/login` dan method `OPTIONS`. Non-`/api` path (SPA shell `/`, `/assets/*`) tetap terbuka agar halaman login bisa dimuat — proteksi data ada di lapisan API.
- Cek `session.get('user_id')` + verifikasi user masih `is_active` (cache hasil cek per request; query via `get_db_engine()` pola `backend/db/session.py`).
- **SECRET_KEY** dari env `SECRET_KEY` (tambah ke `.env` lokal + `.env.example`). Jika kosong di development: pakai `secrets.token_hex()` ephemeral + warning log.
- Session config: `SESSION_COOKIE_NAME='esta_session'`, `SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SAMESITE='Lax'` (mitigasi CSRF untuk cross-site POST), `PERMANENT_SESSION_LIFETIME=12h`, `SESSION_COOKIE_SECURE` dari env flag (off untuk localhost).
- **Perketat CORS** (server.py:38): ganti `origins: "*"` → dari env `CORS_ORIGINS` (default kosong = same-origin saja; dev pakai vite proxy sehingga tetap tidak butuh cross-origin).

### 4. Script seed user — `admin_backend/scripts/create_user.py`
CLI: `venv/bin/python scripts/create_user.py <username> <display_name>` → prompt password (getpass) → insert hash. Dipakai untuk membuat user pertama.

## Desain Frontend

### 5. Baru
- `src/views/LoginView.vue` — form username/password, pesan error, redirect ke tujuan awal (`?redirect=`). Style mengikuti tema Tailwind yang ada.
- `src/stores/auth.js` (Pinia) — state `{user, isAuthChecked}`; aksi `login()`, `logout()`, `fetchMe()`.

### 6. Modifikasi
- `src/router/index.js` — route `/login` (meta `public: true`) + `router.beforeEach`: fetchMe() sekali saat refresh (state session cookie), redirect `/login` bila belum auth, redirect `/` bila sudah auth tapi buka `/login`.
- `src/api/index.js` — tambah `authApi` + response interceptor 401 → reset store auth + `router.push('/login')` (tidak perlu request interceptor karena cookie dikirim otomatis).
- **Konsolidasi 3 titik API yang lolos dari interceptor** (prasyarat proteksi merata): `src/stores/coa.js:2-5` dan `src/stores/reports.js:3-6` ganti axios instance sendiri → import instance terpusat; `src/components/dashboard/StockComparisonWidget.vue:199-204` ganti `fetch()` → axios terpusat.
- `src/layouts/MainLayout.vue` — ganti chip dekoratif "Admin Account" (line 113-121) dengan `display_name` user nyata + tombol logout (ikon heroicons yang sudah dipakai).
- `package.json` — hapus dependency mati `jwt-decode` (tidak pernah diimport).

## Urutan Implementasi
1. Migrasi SQL + script seed → buat user pertama
2. `auth_bp.py` + guard `server.py` + env SECRET_KEY
3. Verifikasi backend via curl (lihat bawah)
4. Frontend: store auth → LoginView → router guard → interceptor → konsolidasi axios → MainLayout logout
5. Build + uji end-to-end via browser

## Verifikasi End-to-End
- **Backend (curl)**: `GET /api/transactions` tanpa cookie → 401; login salah 5x → 429; login benar → 200 + Set-Cookie; `GET /api/transactions` dengan cookie → 200 data; `POST /api/auth/logout` → request berikut 401; `GET /` (SPA shell) tetap 200 tanpa login.
- **Frontend (browser)**: buka `/` → redirect `/login`; login → dashboard; refresh halaman tetap login (cookie session); logout → kembali ke `/login`; akses langsung ke route manapun saat belum login → redirect.
- **Regressi**: `npm run build` lulus; `python -m compileall` + `import server` lulus (147 route terdaftar).
- Catatan: uji dengan `run.sh` (dev server) — perilaku sama di gunicorn karena auth ada di lapisan aplikasi.

## Di Luar Scope (saran tindak lanjut, tidak dikerjakan sekarang)
- HTTPS/reverse proxy (nginx) untuk produksi — `SESSION_COOKIE_SECURE` sudah disiapkan flag-nya.
- Role admin/viewer — skema `users` mudah diperluas kolom `role`.
- Rotasi token Sagansa (pengingat lama, tetap menunggu).