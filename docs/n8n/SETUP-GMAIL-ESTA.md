# Setup: Gmail → n8n → esta (auto-import e-statement bank)

Alur: email e-statement masuk di Gmail → workflow n8n men-download lampiran →
menyimpan salinan di server → mengirimkannya ke endpoint integrasi esta →
transaksi otomatis masuk database (termasuk AI mark pass, sama seperti upload
manual).

```
Gmail ──(poll harian 00:00)──> n8n "Gmail → esta: auto-import e-statement"
  │ 1. Mapping Pengirim   : cocokkan pengirim → bank_type/password/company_id
  │ 2. Simpan ke Disk     : /home/gargar/docker/n8n/data/files/gmail/
  │ 3. Kirim ke esta      : POST http://172.21.0.1:8090/api/integrations/statement
  └ 4. Cek Hasil          : imported/duplicate = sukses, selain itu = gagal

Jadwal 00:30 ──> "Cek Statement Hilang"
  └ POST http://172.21.0.1:8090/api/integrations/statement-check
    → esta mengecek statement bulan lalu per akun; yang belum masuk
      dikirim alert Telegram (jika dikonfigurasi).
```

Yang sudah disiapkan di repo ini:

| Perubahan | File |
|---|---|
| Endpoint integrasi (API key) | `admin_backend/backend/routes/integrations/n8n_bp.py` |
| Endpoint cek statement hilang | `admin_backend/backend/routes/integrations/n8n_bp.py` |
| Notifikasi Telegram (fail-soft) | `admin_backend/backend/services/notifications/telegram.py` |
| Registrasi endpoint | `admin_backend/server.py` |
| Template env | `admin_backend/.env.example` (var `INTEGRATION_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`) |
| Test | `admin_backend/tests/test_integrations_bp.py`, `test_telegram.py`, `test_statement_expectations.py` |
| Workflow n8n siap import | `docs/n8n/gmail-esta-e-statement.json` |

Endpoint esta membaca API key dari env `INTEGRATION_API_KEY` di
`admin_backend/.env`. Tanpa env tersebut endpoint **mati total** (503, fail
closed). File `.env` di server sudah diisi key-nya.

---

## Langkah 1 — Deploy esta

```bash
cd /home/gargar/docker/esta && ./deploy.sh
```

Deploy membawa kode baru + env `INTEGRATION_API_KEY` (container di-recreate,
jadi env terbaca). Verifikasi cepat:

```bash
curl -s -o /dev/null -w '%{http_code}\n' -X POST http://localhost:8090/api/integrations/statement
# 401 = benar (endpoint hidup, menolak tanpa API key)
```

## Langkah 2 — Folder arsip

Folder arsip lampiran sudah dibuat: `/home/gargar/docker/n8n/data/files/gmail/`
(di dalam container n8n: `/home/node/.n8n/files/gmail`). Jika suatu saat hilang:

```bash
mkdir -p /home/gargar/docker/n8n/data/files/gmail
```

## Langkah 3 — Kredensial Gmail OAuth2 di n8n

Gmail Trigger membutuhkan kredensial Google (sekali saja):

1. Buka [Google Cloud Console](https://console.cloud.google.com/) → buat/buka
   project (mis. `sagansa-n8n`).
2. **APIs & Services → Library** → cari **Gmail API** → **Enable**.
3. **APIs & Services → OAuth consent screen** → External → isi nama app →
   pada **Test users** tambahkan alamat Gmail yang akan dipantau.
4. **APIs & Services → Credentials → Create Credentials → OAuth client ID** →
   type **Web application** → **Authorized redirect URI** isi redirect URI yang
   ditampilkan n8n saat membuat kredensial (biasanya
   `https://n8n.sagansa.id/rest/oauth2-credential/callback`). Simpan Client
   ID/Secret.
5. Di n8n (`https://n8n.sagansa.id`): **Credentials → Add credential →
   "Gmail OAuth2"** → tempel Client ID/Secret → **Connect / Sign in with
   Google** → pilih akun → izinkan.

## Langkah 4 — Import workflow

Di n8n: **Workflows → ⋯ → Import from File** → pilih
`docs/n8n/gmail-esta-e-statement.json` dari repo ini (salin isinya ke komputer
Anda, atau paste lewat **Import from URL/Clipboard**).

## Langkah 5 — Konfigurasi workflow (3 titik)

1. **Gmail Trigger** → pilih kredensial Gmail dari Langkah 3.
   Poll: **sekali sehari jam 00:00** (mode *Every Day*, trigger menyimpan waktu
   poll terakhir sehingga tiap tengah malam otomatis mengambil seluruh email
   sejak poll terakhir). *Search Filter (q)* =
   `digibank OR "Consolidated Statement Bank Mandiri"` (hanya email
   e-statement yang discan — listing Gmail maks 100/halaman, tanpa filter ini
   mailbox ramai bisa menggeser e-statement keluar halaman), *Read Status* =
   **Both** (email yang sudah dibaca tetap ikut), *Max Emails per Poll* = 50.
   **Saat menambah bank baru: ubah filter `q` ini juga** (mis.
   `digibank OR livin`), selain `SENDER_MAP` di node Mapping.
   Ingin e-statement masuk lebih cepat? Kecilkan intervalnya (mis. *Every X*
   60 menit) — beban server polling Gmail sendiri sebenarnya sangat kecil.
2. **Kirim ke esta** → ganti nilai header `X-API-Key` dengan nilai
   `INTEGRATION_API_KEY` dari `admin_backend/.env`:
   ```bash
   grep INTEGRATION_API_KEY /home/gargar/esta/admin_backend/.env
   ```
   URL default `http://172.21.0.1:8090/api/integrations/statement` (jalur
   internal docker host → sudah diverifikasi konektivitasnya). Alternatif:
   `https://esta.sagansa.id/api/integrations/statement`.
   Node **Cek Statement Hilang** di branch bawah memakai key yang sama —
   ganti juga header `X-API-Key`-nya.
3. **Mapping Pengirim** → isi `SENDER_MAP` (lihat juga bagian
   [Meletakkan password PDF](#meletakkan-password-pdf) di bawah):
   ```js
   const SENDER_MAP = {
     'digibank': { bank_type: 'dbs', password: 'password-pdf', company_id: '' },
     'mandiri':  { bank_type: 'mandiri_email', password: 'password-pdf', company_id: '' },
   };
   ```
   Catatan: e-statement Mandiri "Consolidated Statement" dicoba dengan parser
   `mandiri_email` — jika formatnya berbeda dan gagal `parse_failed`, parser
   perlu disesuaikan di `admin_backend/bank_parsers/`.
   - Key = substring yang dicocokkan terhadap **nama+alamat pengirim DAN
     subjek email** (longgar, huruf kecil) — mis. key `digibank` cocok dengan
     subjek "CONFIDENTIAL - digibank Visa Travel Platinum Card e-Statement …".
   - `bank_type` valid: `bca, mandiri, mandiri_email, dbs, ccbca, ccmandiri,
     bri, saqu, blu` (BRI = CSV saja; bank lain = PDF).
   - `password` = password PDF (kosongkan jika tidak terkunci).
   - `company_id` = UUID company di esta (opsional).

Email yang tidak cocok dengan map akan diabaikan. Lampiran non
PDF/CSV diabaikan.

## Meletakkan password PDF

Password e-statement disimpan di **node "Mapping Pengirim"**, dalam tabel
`SENDER_MAP` — kolom `password`:

1. Buka workflow di n8n → klik node **Mapping Pengirim**.
2. Di editor kode, cari baris:
   ```js
   'digibank': { bank_type: 'dbs', password: 'GANTI-DENGAN-PASSWORD-PDF', company_id: '' },
   ```
3. Ganti `GANTI-DENGAN-PASSWORD-PDF` dengan password PDF Anda (tanpa tanda
   kutip diubah), lalu **Save**.

Password dikirim otomatis oleh workflow ke esta saat memproses lampiran —
sama seperti Anda mengetiknya di form upload manual. Kalau password salah,
eksekusi berakhir di cabang "Gagal" dengan respons
`require_password`/error dari esta, dan emailnya tinggal diproses manual
via UI esta seperti biasa.

### Menguji dengan email lama (sudah terbaca)

Gmail Trigger default hanya memicu email **unread**. Email e-statement lama
yang sudah terbaca tidak akan diproses. Cara mengujinya: **forward email
tersebut ke akun Gmail yang sama** (hasil forward = email unread baru dengan
lampiran tetap utuh), atau ubah sementara filter *Read Status* di node
Gmail Trigger ke *Both*.

## Backfill: memproses seluruh riwayat email lama sekali jalan

Workflow utama **hanya** mengambil email yang tiba setelah ia diaktifkan
(filter waktu `after:` di Gmail Trigger — email lama yang belum dibaca pun
dilewati). Untuk mengisi database dengan seluruh riwayat e-statement lama,
disediakan workflow terpisah: **"BACKFILL: Gmail → esta (riwayat
e-statement lama)"** (`docs/n8n/gmail-esta-backfill.json`).

Cara pakai:

1. Pastikan password PDF sudah benar di node **Mapping Pengirim** workflow
   backfill (salin dari workflow utama).
2. Buka workflow backfill → klik **Execute workflow** (manual, sekali saja;
   tidak perlu di-activate).
3. Node "Gmail: Ambil Riwayat" mencari email dengan query Gmail
   `digibank "e-Statement" has:attachment` — ubah `q` bila perlu mencakup
   bank lain.
4. Semua lampiran cocok diarsipkan + dikirim ke esta. Statement yang sudah
   pernah ada (manual maupun hasil backfill sebelumnya) otomatis dijawab
   `duplicate` — aman dijalankan berulang.
5. Setelah selesai, biarkan workflow utama yang menangani email baru.

Setelah backfill selesai, workflow backfill boleh dihapus atau disimpan
untuk dipakai lagi nanti (mis. setelah menambah bank baru di mapping —
jalankan ulang untuk menarik riwayat bank tersebut).

## Notifikasi Telegram (opsional, tapi disarankan)

esta mengirim alert Telegram saat ada masalah pipeline — **bukan** setiap
import sukses:

1. **Import gagal**: `parse_failed`, PDF tidak bisa dibuka (password salah),
   atau error database. Pesan berisi bank, nama file, kode error, dan
   Message-ID email sumber.
2. **Statement bulanan belum masuk**: dicek branch "Cek Statement Hilang"
   (jadwal harian 00:30). Untuk setiap akun di halaman *Management → akun
   bank* (`bank_account_definitions`) yang aktif bulan lalu tapi tidak punya
   transaksi bulan itu, dikirim satu baris alert — dengan grace period
   sampai tanggal 5 (bank butuh beberapa hari awal bulan untuk mengirim
   e-statement). Akun yang didefinisikan tapi belum pernah dipakai tidak
   di-alert.

Setup:

1. Buat bot via [@BotFather](https://t.me/BotFather) → dapatkan token.
2. Kirim pesan apa pun ke bot Anda, lalu buka
   `https://api.telegram.org/bot<TOKEN>/getUpdates` → salin `chat.id`.
3. Isi `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` di `admin_backend/.env`,
   lalu redeploy (`./deploy.sh --no-pull`).

**Fail-soft**: tanpa env Telegram, semua tetap jalan — notifikasi hanya
dilewati (tercatat di log). Kegagalan kirim tidak pernah menggagalkan import.

Cek manual kapan saja (mis. untuk bulan lalu):

```bash
curl -s -X POST -H "X-API-Key: $INTEGRATION_API_KEY" \
  http://localhost:8090/api/integrations/statement-check
```

## Idempotensi dua lapis

Import otomatis aman diulang berkat dua cek duplikat di endpoint integrasi:

| Lapis | Dasar | Menangani kasus |
|---|---|---|
| 1 | `email_message_id` (disimpan per transaksi sejak migrasi 073) | Bank **me-regenerate PDF** (byte berbeda → hash berbeda) untuk email yang sama |
| 2 | MD5 `file_hash` | Email yang sama ter-poll ulang / upload ulang file identik |

Keduanya dijawab HTTP 200 `{"status": "duplicate"}` sehingga re-poll workflow
tidak dianggap error.

## Langkah 6 — Aktifkan

Toggle **Active** di workflow. Selesai.

---

## Pengujian end-to-end

1. Kirim email ke Gmail yang dipantau, lampirkan PDF/CSV e-statement (bisa
   dari akun lain), biarkan **unread**.
2. Tunggu poll tengah malam berikutnya (atau klik **Execute workflow** untuk
   tes instan), lalu cek:
   - **n8n → Executions**: harus ada eksekusi sukses (jalur hijau ke
     "Sukses — terimport ke esta").
   - **File**: `ls -la /home/gargar/docker/n8n/data/files/gmail/` — ada
     salinan lampiran.
   - **esta**: login → halaman History — transaksi baru muncul dengan
     `source_file` = nama lampiran.
   - **Log**: `docker logs esta --tail 20` → baris `Integrasi n8n: menerima ...`.
3. Kirim ulang email yang sama → eksekusi berikutnya berakhir `duplicate`
   (aman, tidak ada transaksi ganda).
4. Uji notifikasi: `curl -s -X POST -H "X-API-Key: $INTEGRATION_API_KEY"
   http://localhost:8090/api/integrations/statement-check` → jika ada akun
   aktif tanpa statement bulan lalu, alert Telegram masuk dalam hitungan
   detik.

## Troubleshooting

| Gejala | Penyebab & solusi |
|---|---|
| HTTP 401 di node Kirim ke esta | `X-API-Key` belum diganti / beda dengan `.env`. |
| HTTP 503 | `INTEGRATION_API_KEY` tidak terbaca — jalankan ulang `deploy.sh` (container harus di-recreate). |
| HTTP 400 `parse_failed` | `bank_type` tidak cocok dengan isi file, atau format file berubah. Cek parser di `admin_backend/bank_parsers/`. |
| HTTP 400 `require_password` | PDF terkunci tapi `password` di SENDER_MAP kosong/salah. |
| Node Simpan ke Disk error ENOENT | Folder arsip hilang — ulangi Langkah 2. |
| Email terambil tapi tidak diproses / lampiran tidak muncul | Node Gmail/Trigger memakai **Simplify = ON**: pada mode itu opsi *Download Attachments* **diabaikan** oleh n8n (tersembunyi di balik `hide: {simple:[true]}` di kode node). Pastikan **Simplify = OFF** agar lampiran ikut ter-download (output JSON-nya jadi bentuk mentah — node Mapping sudah menanganinya). |
| Email tidak memicu workflow | Email tiba **sebelum workflow diaktifkan** (trigger hanya mengambil email yang masuk setelah aktif — filter waktu `after:`; email lama yang belum dibaca pun dilewati). Solusi: **forward emailnya ke akun sendiri** atau jalankan workflow BACKFILL. Kemungkinan lain: pengirim/subjek tidak cocok dengan `SENDER_MAP`, workflow belum Active, atau email datang **setelah jam 00:00 terakhir** dan baru akan diproses poll tengah malam berikutnya (poll harian). |
| Eksekusi kosong/tidak ada item | Mapping Pengirim mem-filter semuanya — cek output node di Executions. |
| Lampiran > 10 MB | esta menolak file > 10 MB (sama seperti upload manual). |

## Catatan keamanan

- `INTEGRATION_API_KEY` (di `.env`) dan password PDF (di `SENDER_MAP` workflow,
  tersimpan di SQLite n8n) disimpan **plaintext** di server — pastikan akses
  ke n8n.sagansa.id dan server dibatasi.
- Rotasi API key: ganti nilai di `admin_backend/.env`, lalu
  `cd /home/gargar/docker/esta && ./deploy.sh --no-pull`, lalu perbarui header
  di node **Kirim ke esta**.
- Endpoint hanya menerima `POST /api/integrations/statement` dengan key benar;
  seluruh route API lain tetap dilindungi session login.
