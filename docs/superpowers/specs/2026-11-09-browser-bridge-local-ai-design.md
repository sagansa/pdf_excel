# Design: Browser-Bridge AI Lokal (Ollama/LM Studio dari laptop user)

Tanggal: 2026-11-09
Status: Disetujui (brainstorming selesai)

## Ringkasan

Di production, backend Flask berjalan di Docker di VPS. Saat fitur AI memanggil
`http://localhost:11434/v1` (Ollama) secara server-side, `localhost` merujuk ke
container itu sendiri → `[Errno 111] Connection refused`.

Solusi: untuk provider AI **lokal** (LM Studio, Ollama), hop HTTP ke LLM **berpindah
ke browser** — satu-satunya pihak yang bisa menjangkau `localhost` di laptop user.
Backend tetap memiliki seluruh logika bisnis (indeks riwayat, fuzzy match, prompt
few-shot, parsing, penyimpanan). Browser hanya menjembatani panggilan LLM.

## Keputusan (dari sesi brainstorming)

| Keputusan | Pilihan |
|---|---|
| Pendekatan | **Browser-bridge relay** — hanya hop HTTP ke LLM yang pindah ke browser |
| Routing provider | bridge = `{lmstudio, ollama}`; server-side = `{zai, custom}` (perilaku lama utuh) |
| PDF auto-pass provider lokal | Dilewati; diganti banner + tombol "jalankan saran AI" dari user |
| Path kode | Satu path untuk dev & production (di dev browser & backend satu laptop) |
| Endpoint lama `/ai-suggest` | Tetap ada, dipakai provider non-bridge (z.ai/custom) |

Alternatif yang ditolak:
- **Pindah seluruh orkestrasi AI ke frontend**: refactor besar (846 baris
  `mark_suggester.py` + akses DB), logika bisnis terduplikasi di dua bahasa.
- **Tunnel VPS → laptop (Tailscale/ngrok)**: tiap user harus memelihara tunnel,
  VPS bergantung pada laptop yang online, permukaan keamanan baru.

## 1. Prinsip Routing

`llm_client.get_ai_settings()` menambah field komputasi **`bridge`**:

```python
'bridge': provider in {'lmstudio', 'ollama'},
```

| Provider | Hop LLM | Keterangan |
|---|---|---|
| `lmstudio`, `ollama` | Browser (laptop user) | Bridge baru |
| `zai`, `custom` | Server (VPS) | Tidak berubah |

Ollama mengizinkan origin `http://localhost:*` secara default → dev langsung jalan
tanpa konfigurasi. Production (origin https://...) memerlukan `OLLAMA_ORIGINS` di
laptop user atau toggle CORS di LM Studio (dipandu UI, lihat §5).

## 2. Backend: pecah `ai-suggest` menjadi prepare/submit

### 2a. Refactor `mark_suggester.py`

Ekstrak tahap rule dari `process_transaction` menjadi:

```python
def resolve_transaction_rules(conn, txn_id, config, history_index, candidates_by_direction=None):
    """Kaskade tanpa LLM: get_transaction → ensure_markable → kandidat →
    rule riwayat → rule disambiguasi nominal.
    Balikan {'kind': 'done', 'result': {...}}  (final: suggested|auto_applied|skipped)
         atau {'kind': 'llm', 'prompt': {id, model, messages, temperature, max_tokens}}.
    Rule match tetap langsung di-store (perilaku sekarang)."""
```

- `process_transaction` menjadi komposisi `resolve_transaction_rules` + eksekusi LLM
  (`suggest_for_transaction`) → dipakai thread z.ai (`run_ai_mark_pass`) dan endpoint
  lama; perilaku tidak berubah.
- `prepare` memakai `resolve_transaction_rules` saja.
- Prompt bridge TIDAK menyertakan `api_key` (provider lokal tidak butuh; kunci z.ai
  tidak pernah keluar dari server).

### 2b. Endpoint baru di `ai_bp.py`

**`POST /api/transactions/ai-suggest/prepare`** — body `{transaction_ids}` (dedup,
maks `MAX_SUGGEST_BATCH`, validasi identik dengan endpoint lama).

1. `ensure_ai_columns`, baca config, cek `enabled` (`ai_disabled`) dan `model`
   (`ai_model_missing`) — error codes sama dengan sekarang.
2. `build_history_index` sekali.
3. Loop `resolve_transaction_rules`: `done` → masuk `results`; `llm` → masuk `pending`
   (tidak ada yang disimpan untuk item pending).
4. Respons:
   ```json
   {
     "results": [ ...hasil final (suggested/auto_applied/skipped)... ],
     "pending": [{"id": "...", "model": "...", "messages": [...],
                  "temperature": 0.1, "max_tokens": 800}],
     "message": "..."
   }
   ```

**`POST /api/transactions/ai-suggest/submit`** — body
`{items: [{"id": "...", "raw": "..."} | {"id": "...", "error": "..."}]}`.

Per item di dalam satu transaksi DB:
- `error` → hasil `failed` (tidak menyimpan apa pun).
- `raw` → muat ulang transaksi + kandidat **dari DB**, `raw` dipotong maksimal
  64.000 karakter, `parse_suggestion_response(raw, candidates)`:
  - JSON tidak valid / mark di luar kandidat → `failed` (pesan dari parser).
  - Valid → `store_suggestion(conn, txn_id, suggestion, source='llm')` → `suggested`.
- Transaksi sudah tidak ada → `skipped`.

Respons: shape agregat **identik dengan endpoint lama**
(`results`, `suggested_count`, `auto_applied_count`, `skipped_count`, `failed_count`,
`message`). Saran LLM selalu menunggu review (tidak ada auto-apply — paritas dengan
perilaku sekarang).

### 2c. Endpoint lama tetap

`POST /api/transactions/ai-suggest` berjalan seperti sekarang (loop
`process_transaction`). Frontend hanya memakainya untuk provider non-bridge.

## 3. Frontend

### 3a. Modul relay baru: `src/services/localAiBridge.js`

```js
runSuggest(ids, settings):
  1. aiApi.prepareSuggest(ids)
  2. Untuk tiap pending (sekuensial — paritas dengan loop server):
     POST {base_url}/chat/completions
       body: {model, messages, temperature, max_tokens, stream: false}
       AbortController timeout 120s (paritas DEFAULT_TIMEOUT)
       Retry 1x pada network error (delay 2s — paritas retry backend)
  3. aiApi.submitSuggest(items) → balikan data submit apa adanya.
```

Deteksi kegagalan koneksi: `fetch` melempar `TypeError` tanpa response (CORS atau
server mati) → error terstruktur dengan pesan panduan per provider yang menyebut
`window.location.origin` (lihat §5).

### 3b. `aiApi.suggestMarks` menjadi dispatcher

- Baca `settings.bridge` (store `history.js` sudah memuat settings AI).
- `bridge=true` → `localAiBridge.runSuggest(ids, settings)`.
- Selain itu → `POST /ai-suggest` (path lama).
- Komponen (`HistoryTable.vue`, `TransactionDetailsModal.vue`) dan store **tidak
  berubah** — signature & shape respons dipertahankan.
- Primitive baru: `aiApi.prepareSuggest(ids)`, `aiApi.submitSuggest(items)`.

### 3c. Settings UI: test-connection & daftar model

- Provider bridge: `fetch(base_url + '/models')` **dari browser** (timeout 15s) —
  tombol tes koneksi browser-side, dropdown model terisi dari hasilnya.
- Provider non-bridge: `POST /api/ai/test-connection` seperti sekarang.

## 4. PDF Upload

`pdf_bp.py` (setelah `save_transactions_to_db` sukses):

| Kondisi settings AI | Perilaku |
|---|---|
| enabled & bridge | **Tidak queue thread**. Header `X-AI-Pass: skipped-local`, `X-AI-Pass-Count: N` |
| selain itu (disabled atau non-bridge) | `queue_ai_mark_pass(inserted_ids)` seperti sekarang — thread sendiri yang me-skip bila AI disabled (`mark_pass.py`), sehingga perilaku lama utuh |

Frontend upload: header `X-AI-Pass: skipped-local` → banner
**"N transaksi baru siap untuk saran AI"** + tombol yang memicu alur suggest yang
sama (via bridge).

## 5. Error Handling & Panduan CORS

| Kasus | Deteksi | Respons |
|---|---|---|
| Server AI mati / CORS ditolak | `fetch` `TypeError` tanpa response | Pesan satu kalimat mencakup keduanya: *"Pastikan Ollama/LM Studio berjalan di laptop Anda DAN mengizinkan origin {origin}..."* + panduan spesifik provider |
| Timeout | `AbortController` 120s | Pesan timeout |
| Parse JSON gagal / mark tidak dikenal | Server pada `submit` | Item → `failed` dengan pesan parser; item lain tetap diproses |
| Model berhenti di tengah batch | Retry gagal | Item → `error` di submit → `failed` |

Panel info di Settings (hanya tampil untuk provider bridge): petunjuk konfigurasi di
laptop user — Ollama: `OLLAMA_ORIGINS` memuat origin production (mis.
`OLLAMA_ORIGINS="https://domain-anda,http://localhost:*"`); LM Studio: aktifkan
**Enable CORS** di tab Developer — plus origin saat ini (`window.location.origin`).

Bahasa pesan mengikuti fitur AI yang ada (Indonesia).

## 6. Keamanan

- `prepare`/`submit` tercakup guard auth global `before_request` di `server.py`
  (sama seperti semua route).
- `ai_api_key` (z.ai) tidak pernah dikirim ke browser — tidak berubah.
- Browser tidak dipercaya: `submit` memvalidasi `mark_id` terhadap kandidat dari DB,
  bukan terhadap payload klien; `raw` dibatasi panjang.
- Tidak ada endpoint baru yang melewati auth; tidak ada perubahan CORS backend.

## 7. Testing

### Backend (pytest, mengikuti pola `tests/test_ai_bp.py`)

1. `prepare`: rule-match ter-resolve tanpa panggilan LLM; item tanpa rule → `pending`
   berisi `model` + `messages`; transaksi tak ditemukan → `skipped` di `results`.
2. `prepare`: `ai_disabled` / `ai_model_missing` tetap dipicu.
3. `submit`: `raw` valid → `suggested` tersimpan (source=llm); JSON rusak → `failed`;
   `mark_id` di luar kandidat → `failed`; id tak dikenal → `skipped`; item ber-`error`
   → `failed` tanpa store.
4. PDF upload dengan settings bridge → header `X-AI-Pass: skipped-local` + count.
5. Endpoint lama (z.ai, mock LLM) tetap berfungsi — regresi non-bridge.
6. `run_ai_mark_pass` (thread z.ai) masih menyelesaikan cascade penuh.

### Frontend (tanpa framework test di repo — checklist manual)

1. Dev + Ollama jalan: suggest sukses; Network tab menunjukkan fetch ke `localhost:11434`
   **dari browser**, bukan dari backend.
2. Dev + Ollama mati: pesan panduan muncul, UI tidak crash, item lain lanjut.
3. Settings: tes koneksi bridge → daftar model terisi; panel info CORS tampil.
4. Upload PDF (settings bridge) → banner "siap untuk saran AI" → tombol berfungsi.

### E2E production

`OLLAMA_ORIGINS` di laptop memuat origin production → suggest sukses dari browser
user; tes koneksi & daftar model dari Settings sukses.

## 8. Batasan

- Tanpa dependency baru (backend stdlib; frontend `fetch` native).
- Tanpa migrasi DB (kolom `ai_*` sudah ada dari migrasi 072).
- Perilaku z.ai/custom tidak berubah sama sekali.
- `custom` tetap server-side: bila user mengisi `custom` dengan localhost-nya sendiri,
  tetap gagal di production — dokumentasikan di UI bahwa URL custom harus dapat
  dijangkau dari server.
