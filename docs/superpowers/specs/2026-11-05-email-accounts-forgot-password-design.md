# Design: Akun Email + Forgot Password

Tanggal: 2026-11-05
Status: Disetujui (brainstorming selesai)

## Ringkasan

Mengubah sistem akun StatementX dari username ke **email** sebagai identifier login, dan menambahkan fitur **forgot password**: user menerima email berisi link reset password (token sekali pakai, berlaku 30 menit).

## Keputusan (dari sesi brainstorming)

| Keputusan | Pilihan |
|---|---|
| Pengiriman email | SMTP via `smtplib` (stdlib, tanpa dependency baru) |
| Identifier login | Email sepenuhnya menggantikan username |
| Akun lama | Dibuat ulang via `scripts/create_user.py` (tabel users di-drop & dibuat ulang) |
| Mekanisme token reset | Tabel DB `password_reset_tokens` (single-use, revocable, tahan restart & multi-worker) |
| Framework | Tetap custom Flask mengikuti pola `auth_bp.py` yang ada (bukan Flask-Security-Too / migrasi Laravel) |

Alasan menolak alternatif:
- **Laravel/Django (auth bawaan):** backend ini ~152 route Flask dengan seluruh logika bisnis; migrasi framework demi satu fitur tidak sebanding.
- **Flask-Security-Too:** mensyaratkan ORM model + Flask-Login, sedangkan codebase memakai raw SQL (`text()`) dan sesi custom yang baru di-commit — pemasangannya lebih invasif daripada menulis 2 endpoint mengikuti pola yang ada.
- **Token stateless (signed serializer):** single-use sulit dijamin tanpa storage; tidak bisa dicabut.
- **OTP 6 digit:** tetap butuh storage, UX lebih ribet, lebih rentan brute-force.

## 1. Database & Akun

### Migrasi `071_email_accounts.sql` (MySQL)

1. **Drop & buat ulang `users`** (disepakati: data lama dibuang, akun dibuat ulang via script):
   ```sql
   DROP TABLE IF EXISTS users;
   CREATE TABLE users (
       id INT AUTO_INCREMENT PRIMARY KEY,
       email VARCHAR(255) NOT NULL UNIQUE,
       password_hash VARCHAR(255) NOT NULL,
       display_name VARCHAR(128) NOT NULL,
       is_active TINYINT(1) NOT NULL DEFAULT 1,
       credential_version INT NOT NULL DEFAULT 0,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
   );
   ```
   Email selalu disimpan lowercase (dinormalisasi di semua titik input).

   `credential_version` dipakai untuk mematikan sesi lama setelah password di-reset (lihat §2).

2. **Tabel baru `password_reset_tokens`:**
   ```sql
   CREATE TABLE password_reset_tokens (
       id INT AUTO_INCREMENT PRIMARY KEY,
       user_id INT NOT NULL,
       token_hash CHAR(64) NOT NULL UNIQUE,
       expires_at TIMESTAMP NOT NULL,
       used_at TIMESTAMP NULL,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       CONSTRAINT fk_password_reset_user
           FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
       INDEX idx_password_reset_user (user_id)
   );
   ```
   `token_hash` = SHA-256 hex dari token mentah. Token mentah tidak pernah disimpan — hanya ada di email penerima.

### `scripts/create_user.py`

- Argumen berubah: `<email> <display_name>`; validasi format email sederhana + normalisasi lowercase.
- Perilaku lain tetap: prompt password tersembunyi, min 8 karakter, update bila email sudah ada.

### Login

- Lookup berubah dari `WHERE username = ?` menjadi `WHERE email = ?` (input di-lowercase).
- Payload login: `{email, password}`. Respons `/api/auth/me`: `{id, email, display_name}`.

## 2. Alur Forgot/Reset Password & Keamanan

Kedua endpoint baru ditambahkan ke `PUBLIC_API_PATHS` di `server.py`.

### `POST /api/auth/forgot-password` — body `{email}`

- Normalisasi email (trim + lowercase). **Selalu `200` dengan pesan generis** ("Jika akun terdaftar, link reset telah dikirim") — mencegah email enumeration.
- Rate limit: 3 permintaan / (IP, email) / 15 menit, memakai pola throttling in-memory yang sudah ada.
- Jika akun aktif ditemukan:
  1. Hapus semua token lama user tersebut.
  2. Buat token `secrets.token_urlsafe(32)`; simpan SHA-256 hex + `expires_at = now + 30 menit`.
  3. Kirim email berisi link `{base_url}/reset-password?token=...`.
- `base_url` dari `request.url_root`, dapat di-override via env `APP_BASE_URL`.

### `POST /api/auth/reset-password` — body `{token, new_password}`

- Hash token → cari `token_hash` cocok dengan `used_at IS NULL AND expires_at > NOW()`.
- Token salah/kedaluwarsa → `400 invalid_token` (pesan generis; token 32-byte acak sehingga tidak ada risiko enumerasi).
- Validasi password min 8 karakter (konsisten `create_user.py`).
- Sukses: update `password_hash`, naikkan `credential_version` +1, hapus semua token user tersebut (termasuk token yang barusan dipakai).

### Invalidasi sesi lama

- Sesi menyimpan `credential_version` saat login.
- Guard `get_user_if_active` (cache 5 menit, sudah ada) membandingkan versi sesi vs DB — tidak cocok → sesi dimatikan.
- Efek: semua sesi lain user mati maksimal ~5 menit setelah reset password (batas cache guard, dapat diterima untuk aplikasi internal).

### Modul baru `backend/services/mailer.py`

- `smtplib` + `email.message` (stdlib). Fungsi: `send_reset_email(to_email, reset_link, display_name)`.
- Konfigurasi `.env`: `SMTP_HOST`, `SMTP_PORT` (default 587), `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`, `SMTP_USE_TLS` (default true).
- **Mode dev:** jika `SMTP_HOST` kosong → email tidak dikirim; link reset ditulis ke logger (level warning) supaya bisa diuji lokal.

## 3. Frontend

UI bahasa Inggris, mengikuti halaman login yang ada.

1. **`LoginView.vue`** — label & field jadi Email (`type="email"`, `autocomplete="email"`), payload `{email, password}`; tambah link "Forgot password?" → `/forgot-password`.
2. **`ForgotPasswordView.vue`** (baru, publik) — form email → sukses menampilkan pesan generis yang sama untuk semua kasus.
3. **`ResetPasswordView.vue`** (baru, publik) — baca `?token=` dari URL; form password baru + konfirmasi (min 8) → sukses: redirect `/login` dengan pesan "Password changed, please sign in"; token invalid: pesan error + tombol "Request new link".
4. **`router/index.js`** — dua route publik baru. **`api/index.js`** — `forgotPassword()`, `resetPassword()`. **`stores/auth.js`** — `login(email, password)`.

## 4. Testing

- **Backend (pytest, struktur `admin_backend/tests/` yang ada):**
  - Login by email: valid, invalid, case-insensitive (input `Foo@Bar.com` → cocok `foo@bar.com`).
  - Forgot-password: selalu 200 (email terdaftar & tidak), rate limit → 429.
  - Token: single-use (pemakaian kedua ditolak), kedaluwarsa ditolak, token salah ditolak, password <8 ditolak.
  - `credential_version` naik saat reset; sesi lama mati setelah reset.
- **Manual e2e:** curl endpoint + browser — lupa password → link (mode dev via log) → reset → login password baru.
- **Mailer:** mode tanpa `SMTP_HOST` menulis ke log; SMTP asli diuji manual dengan kredensial.

## 5. File yang Berubah

| File | Perubahan |
|---|---|
| `admin_backend/database/migrations/071_email_accounts.sql` | baru |
| `admin_backend/backend/routes/auth_bp.py` | login by email, 2 endpoint baru, cek credential_version |
| `admin_backend/backend/services/mailer.py` | baru |
| `admin_backend/server.py` | `PUBLIC_API_PATHS` + 2 |
| `admin_backend/scripts/create_user.py` | argumen email + validasi |
| `admin_backend/.env.example` | variabel SMTP + APP_BASE_URL |
| `admin_backend/requirements.txt` | tidak berubah (stdlib saja) |
| `admin_frontend/src/views/LoginView.vue` | field email + link forgot |
| `admin_frontend/src/views/ForgotPasswordView.vue` | baru |
| `admin_frontend/src/views/ResetPasswordView.vue` | baru |
| `admin_frontend/src/router/index.js` | route publik baru |
| `admin_frontend/src/api/index.js` | 2 fungsi API |
| `admin_frontend/src/stores/auth.js` | login(email, ...) |

## 6. Extension Points (non-binding, dibahas saat brainstorming)

Dokumentasi arah pengembangan — **tidak dibangun sekarang** (YAGNI), dan desain ini tidak mengunci ketiganya:

1. **Role/multi-user** — murah ditambah: kolom `role`, role di sesi & cache guard, decorator `@require_role`. Syarat: logika auth tetap terpusat di `auth_bp.py` (dipenuhi desain ini).
2. **Multi-tenant (SaaS)** — proyek besar tersendiri: `tenant_id` di seluruh skema bisnis + filter di semua query + konteks tenant di sesi. Baru dibangun saat ada kontrak penjualan nyata; butuh brainstorming & migrasi khusus. Desain ini menjaga: PK `users.id` konvensional, auth terisolasi.
3. **Login Google (OAuth/OIDC)** — arsitektur sesi berbasis `user_id` tidak peduli metode login; cukup tambah endpoint start/callback yang mengisi `session['user_id']`. Perkiraan ~1 hari kerja: verifikasi `id_token`, link akun by email (wajib `email_verified`), `password_hash` nullable bila mengizinkan akun Google-only.

## Out of Scope

- Registrasi mandiri (akun tetap dibuat admin via CLI).
- UI manajemen user.
- Role, multi-tenant, OAuth Google (lihat §6).
- Pengiriman email via API service (SendGrid dkk.) — dapat ditambah belakangan sebagai backend mailer alternatif.
