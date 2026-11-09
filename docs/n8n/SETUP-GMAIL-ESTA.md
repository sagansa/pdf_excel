# Setup: Gmail → n8n → esta (auto-import e-statement bank)

Alur: email e-statement masuk di Gmail → workflow n8n men-download lampiran →
menyimpan salinan di server → mengirimkannya ke endpoint integrasi esta →
transaksi otomatis masuk database (termasuk AI mark pass, sama seperti upload
manual).

```
Gmail ──(poll 5 menit)──> n8n "Gmail → esta: auto-import e-statement"
  │ 1. Mapping Pengirim   : cocokkan pengirim → bank_type/password/company_id
  │ 2. Simpan ke Disk     : /home/gargar/docker/n8n/data/files/gmail/
  │ 3. Kirim ke esta      : POST http://172.21.0.1:8090/api/integrations/statement
  └ 4. Cek Hasil          : imported/duplicate = sukses, selain itu = gagal
```

Yang sudah disiapkan di repo ini:

| Perubahan | File |
|---|---|
| Endpoint integrasi (API key) | `admin_backend/backend/routes/integrations/n8n_bp.py` |
| Registrasi endpoint | `admin_backend/server.py` |
| Template env | `admin_backend/.env.example` (var `INTEGRATION_API_KEY`) |
| Test | `admin_backend/tests/test_integrations_bp.py` |
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
   Poll default 5 menit; filter default hanya email **unread**.
2. **Kirim ke esta** → ganti nilai header `X-API-Key` dengan nilai
   `INTEGRATION_API_KEY` dari `admin_backend/.env`:
   ```bash
   grep INTEGRATION_API_KEY /home/gargar/esta/admin_backend/.env
   ```
   URL default `http://172.21.0.1:8090/api/integrations/statement` (jalur
   internal docker host → sudah diverifikasi konektifnya). Alternatif:
   `https://esta.sagansa.id/api/integrations/statement`.
3. **Mapping Pengirim** → isi `SENDER_MAP`:
   ```js
   const SENDER_MAP = {
     'notification@livin.mandiri.com': { bank_type: 'mandiri_email', password: 'password-pdf', company_id: '' },
     'e-statement@bank.com':           { bank_type: 'bca',           password: '',            company_id: '' },
   };
   ```
   - Key = substring alamat pengirim (dicocokkan longgar, huruf kecil).
   - `bank_type` valid: `bca, mandiri, mandiri_email, dbs, ccbca, ccmandiri,
     bri, saqu, blu` (BRI = CSV saja; bank lain = PDF).
   - `password` = password PDF (kosongkan jika tidak terkunci).
   - `company_id` = UUID company di esta (opsional).

Email dari pengirim yang **tidak** ada di map akan diabaikan. Lampiran non
PDF/CSV diabaikan.

## Langkah 6 — Aktifkan

Toggle **Active** di workflow. Selesai.

---

## Pengujian end-to-end

1. Kirim email ke Gmail yang dipantau, lampirkan PDF/CSV e-statement (bisa
   dari akun lain), biarkan **unread**.
2. Tunggu maksimal ±5 menit, lalu cek:
   - **n8n → Executions**: harus ada eksekusi sukses (jalur hijau ke
     "Sukses — terimport ke esta").
   - **File**: `ls -la /home/gargar/docker/n8n/data/files/gmail/` — ada
     salinan lampiran.
   - **esta**: login → halaman History — transaksi baru muncul dengan
     `source_file` = nama lampiran.
   - **Log**: `docker logs esta --tail 20` → baris `Integrasi n8n: menerima ...`.
3. Kirim ulang email yang sama → eksekusi berikutnya berakhir `duplicate`
   (aman, tidak ada transaksi ganda).

## Troubleshooting

| Gejala | Penyebab & solusi |
|---|---|
| HTTP 401 di node Kirim ke esta | `X-API-Key` belum diganti / beda dengan `.env`. |
| HTTP 503 | `INTEGRATION_API_KEY` tidak terbaca — jalankan ulang `deploy.sh` (container harus di-recreate). |
| HTTP 400 `parse_failed` | `bank_type` tidak cocok dengan isi file, atau format file berubah. Cek parser di `admin_backend/bank_parsers/`. |
| HTTP 400 `require_password` | PDF terkunci tapi `password` di SENDER_MAP kosong/salah. |
| Node Simpan ke Disk error ENOENT | Folder arsip hilang — ulangi Langkah 2. |
| Email tidak memicu workflow | Email sudah terbaca sebelumnya (trigger default hanya unread — ubah filter *Read Status* ke *Both* untuk tes), atau pengirim tidak ada di `SENDER_MAP`, atau workflow belum Active. |
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
