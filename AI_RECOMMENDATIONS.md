# 🤖 Rekomendasi Pemanfaatan AI untuk Pengisian Marking

> Fokus: **History & DB → Transactions** (auto/smart-marking bank statement transactions).
> Dibuat: 2026-06-18 | Konteks: `esta` (StatementX) — Flask + Vue 3, MySQL/SQLite.

---

## 0. Ringkasan Eksekutif

Saat ini penandaan (marking) transaksi di History bersifat **100% manual**:
setiap baris `transactions.description` harus di-assign ke `marks.id` oleh user,
baik satu per satu (`POST /api/transactions/<id>/assign-mark`) maupun bulk
(`POST /api/transactions/bulk-mark`). Karena `description` bank statement sangat
berulang (gaji, sewa, listrik, top-up, transfer antar akun, merchant yang sama),
proses ini **repetitif, rawan typo, dan memakan waktu**.

**Tujuan AI di sini:** membantu *mengisi* (suggest / auto-apply) mark berdasarkan
pola yang sudah dipelajari dari data yang **sudah di-mark user sebelumnya**, tanpa
mengorbankan akurasi akuntansi dan audit trail.

> ❗ Prinsip utama: **AI menyarankan, manusia memutuskan.** Semua auto-mark wajib
> ber-flag `ai_suggested` dan dapat di-review/di-undo.

---

## 1. Pemahaman Domain (mengapa ini cocok untuk AI)

| Data tersedia di `transactions` | Relevansi untuk klasifikasi mark |
|---------------------------------|----------------------------------|
| `description` (raw bank text)   | Fitur utama — pembeda paling kuat |
| `amount`                         | Cluster nominal (gaji, sewa, utilitas cenderung stabil) |
| `db_cr` (DB/CR)                 | Membatasi kandidat mark (mark punya `natural_direction`) |
| `bank_code`, `bank_account_number` | Merchant/akun sumber → pola berulang |
| `txn_date` (day-of-month)       | Tanggal jatuh tempo (sewa, cicilan, gaji) |
| `company_id`                    | Konteks bisnis (beda entity → beda mark) |
| `mark_id` (yang sudah di-assign)| **Label training** — supervised learning |

Kombinasi ini sangat ideal untuk **supervised classification** karena:
1. Label (`mark_id`) sudah ada dari kerja manual user — **gratis labeled dataset**.
2. Kelas (marks) jumlahnya terbatas (puluhan, bukan ribuan).
3. Distribusi tidak seimbang → beberapa mark (gaji, sewa) akan dominan.

---

## 2. Empat Level Solusi (dari paling sederhana ke paling canggih)

> Pilih level sesuai **ROI**: mulai dari Level 1 (1–2 hari, non-AI), baru naik
> bertahap. **Tidak perlu langsung ke LLM.**

### 🥇 Level 1 — Rule-Based Smart Matching (Quick Win, NON-AI)

**Ide:** Transaksi baru dengan description mirip → mark yang sama. Pola sederhana,
tetapi menangkap **60–80% kasus berulang**.

**Cara kerja:**
1. Normalisasi `description` (hapus angka referensi, tanggal, whitespace, uppercase).
2. Cari di history: description yang sama/persis sudah di-mark ke `X`?
3. Bila match kuat → suggest `X`.

```python
# Contoh normalisasi
import re
def normalize_description(desc: str) -> str:
    s = (desc or '').upper()
    s = re.sub(r'\d{6,}', '', s)              # hapus nomor referensi panjang
    s = re.sub(r'\b\d{2}/\d{2}/\d{4}\b', '', s)  # hapus tanggal
    s = re.sub(r'[^A-Z\s]', '', s)            # hapus angka & simbol
    s = re.sub(r'\s+', ' ', s).strip()
    return s

# "TRSF E-BANKING 0829347123 GOJEK"  →  "TRSF E BANKING GOJEK"
# "TRSF E-BANKING 0829347555 GOJEK"  →  "TRSF E BANKING GOJEK"  (match!)
```

**Implementasi backend (baru, ringan):**
- Endpoint: `POST /api/transactions/<id>/suggest-mark`
- Query:
  ```sql
  SELECT mark_id, COUNT(*) AS freq
  FROM transactions
  WHERE description REGEXP :normalized_pattern
    AND mark_id IS NOT NULL
    AND db_cr = :db_cr
    AND company_id = :company_id
  GROUP BY mark_id
  ORDER BY freq DESC
  LIMIT 1;
  ```
- Return: `{ mark_id, confidence (0..1), sample_count, source: 'rule_exact' }`

**Threshold:** hanya suggest bila `confidence >= 0.9` DAN `sample_count >= 2`.

**Frontend:** tombol **"✨ Suggest"** per baris + **"Auto-mark All (High Confidence)"**
pada bulk action.

---

### 🥈 Level 2 — ML Classifier (TF-IDF + Classifier)

**Ide:** Latih classifier ringan dari seluruh data berlabel.

**Stack (on-prem, murah, tidak butuh GPU):**
- `scikit-learn` (sudah ekosistem Python, cocok dengan Flask)
- Pipeline: `TfidfVectorizer` + `LogisticRegression` / `LinearSVC` / `ComplementNaiveBayes`
  (ComplementNB bagus untuk kelas tidak seimbang)
- Fitur tambahan: `amount_bin` (log-scale), `db_cr`, `day_of_month`, `bank_code`

**Training (batch, offline):**
```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
import joblib

preprocessor = ColumnTransformer([
    ('desc', TfidfVectorizer(ngram_range=(1,2), min_df=2), 'description'),
    ('amt',  'passthrough', ['amount_log', 'day_of_month']),
    ('cat',  OneHotEncoder(handle_unknown='ignore'), ['db_cr', 'bank_code']),
])
clf = Pipeline([
    ('pre', preprocessor),
    ('clf', LogisticRegression(max_iter=1000, class_weight='balanced')),
])
# X = transactions[description, amount_log, day_of_month, db_cr, bank_code]
# y = transactions.mark_id   (hanya yang tidak NULL)
clf.fit(X_train, y_train)
joblib.dump(clf, 'models/mark_classifier_v1.joblib')
```

**Inference (online):**
- Endpoint: `POST /api/transactions/bulk-suggest-marks`
- Payload: `{ transaction_ids: [...], threshold: 0.75 }`
- Model di-load sekali di `app.config` / singleton.
- Return per transaksi: `{ txn_id, mark_id, confidence, top_3: [...] }`

**Retraining:**
- Cron / manual trigger: ambil semua data berlabel → retrain → versioning
  (`mark_classifier_v1.joblib`, `v2`, ...).
- Simpan metrik (accuracy, F1 macro, per-class precision/recall) di tabel
  `ai_model_runs(id, version, metric_json, trained_at, row_count)`.

**Output yang lebih kaya:** top-3 kandidat mark + confidence → frontend bisa tampilkan
dropdown dengan confidence bar.

---

### 🥉 Level 3 — LLM-Based Classification (high accuracy, high cost)

**Ide:** Gunakan LLM untuk deskripsi yang ambigu / belum pernah dilihat model
(zero-shot dengan konteks Chart of Accounts).

**Kapan dipakai:**
- Level 1 & 2 confidence < threshold.
- Mark baru belum punya contoh training (cold-start).
- User meminta "jelaskan kenapa".

**Dua strategi biaya:**

| Strategi | Pro | Kontra |
|----------|-----|--------|
| **API cloud** (OpenAI / Anthropic / Gemini) | Cepat, akurat | Biaya per-request, privacy concern, latensi |
| **LLM lokal** (LM Studio / Ollama + Gemma 4 12B, Llama 3, Qwen) | Gratis, privacy aman, offline | Butuh RAM/VRAM, setup awal |

> 💡 **Catatan untuk setup Anda:** LM Studio + Gemma 4 12B di MacBook Air M5 16GB
> **cukup** dengan kuantisasi Q4_K_M — lihat analisis lengkap di **§6 Hardware &
> Deployment**.

**Prompt pattern (few-shot):**
```
Kamu asisten akuntansi. Pilih SATU "mark" yang paling cocok untuk transaksi berikut.
Jika tidak yakin, jawab "UNKNOWN".

Daftar mark tersedia (nama internal + arah natural):
- "Gaji Karyawan" (DB)
- "Sewa Kantor" (DB)
- "Pendapatan Jasa" (CR)
- "Pembayaran Listrik PLN" (DB)
...

Transaksi:
- deskripsi: "TRSF E-BANKING GOJEK 2094820123"
- arah: CR
- nominal: 1.500.000
- tanggal: 28

Jawab JSON: {"mark": "...", "confidence": 0.x, "alasan": "..."}
```

**Implementasi:**
- Service terpisah: `backend/services/ai/llm_classifier.py`
- Caching: hash(description) → result (Redis / SQLite cache table)
- Batch: 1 request berisi 20 transaksi → hemat token
- **Privacy filter** sebelum kirim ke cloud: mask nomor rekening, NPWP, nama orang
  bila sensitif (atau pakai LLM lokal untuk data sensitif).

**Output LLM lebih kaya:** `alasan` → bisa ditampilkan ke user sebagai tooltip
(explainability → meningkatkan trust).

---

### 🏆 Level 4 — Hybrid (Direkomendasikan untuk Produksi)

**Alur per transaksi:**

```
                ┌─────────────────────────┐
 unmarked txn → │ Rule Engine (Level 1)   │
                └────────────┬────────────┘
                  confidence │
            ┌────────────────┼────────────────┐
            ▼                ▼                ▼
       ≥ 0.95           0.0–0.95          no match
            │                │                │
            ▼                ▼                ▼
   auto-apply        ┌──────────────┐   ┌──────────────┐
   (flag review)     │ ML (Level 2) │   │ LLM (Level 3)│
                     └──────┬───────┘   └──────┬───────┘
                       confidence │        confidence │
                  ┌───────────────┼───────────────┐
                  ▼               ▼               ▼
              ≥ 0.80         0.5–0.79          < 0.5
              suggest         uncertain        human review
              (user 1-click)  (show top-3)     (manual)
```

**Kenapa hybrid?**
- Level 1 cepat & murah, tangkap mayoritas.
- Level 2 tangkap pola tak persis tapi mirip.
- Level 3 tangkap kasus baru/ambigu — biaya hanya untuk minoritas.
- **Cost LLM turun drastis** (hanya untuk transaksi yang Level 1+2 tidak yakin).

---

## 3. Desain Skema & Audit Trail (WAJIB untuk akuntansi)

Setiap auto-mark harus **terlacak**. Tambahkan tabel + kolom berikut.

### 3.1 Kolom baru di `transactions` (migration baru)

```sql
-- 069_add_ai_mark_tracking.sql (ganti 068 yg sudah dipakai jika perlu)
ALTER TABLE transactions ADD COLUMN ai_suggested TINYINT(1) DEFAULT 0;
ALTER TABLE transactions ADD COLUMN ai_confidence DECIMAL(4,3) DEFAULT NULL;
ALTER TABLE transactions ADD COLUMN ai_source VARCHAR(20) DEFAULT NULL;
-- ai_source: 'rule' | 'ml_v1' | 'llm' | NULL (manual)
```

### 3.2 Tabel feedback loop

```sql
CREATE TABLE ai_mark_suggestions (
    id CHAR(36) PRIMARY KEY,
    transaction_id CHAR(36) NOT NULL,
    suggested_mark_id CHAR(36),
    accepted_mark_id CHAR(36),          -- NULL jika ditolak
    confidence DECIMAL(4,3),
    source VARCHAR(20),                 -- rule/ml_v1/llm
    reason TEXT,                        -- alasan dari LLM (bila ada)
    status ENUM('pending','accepted','rejected','overridden') DEFAULT 'pending',
    user_id CHAR(36),                   -- siapa yang konfirmasi (dari sagansa_user)
    created_at DATETIME,
    decided_at DATETIME,
    FOREIGN KEY (transaction_id) REFERENCES transactions(id)
);
```

**Gunanya:**
- Audit: tahu transaksi mana yang di-mark AI vs manual.
- Training ulang: `accepted_mark_id` → label positif; `rejected` → negatif.
- Metrik: `accept_rate` per source → evaluasi Level mana yang paling akurat.

### 3.3 Tabel model registry

```sql
CREATE TABLE ai_model_runs (
    id CHAR(36) PRIMARY KEY,
    model_type VARCHAR(20),             -- 'ml' / 'llm'
    version VARCHAR(50),                -- 'ml_v1', 'llm_qwen_7b'
    metrics_json TEXT,                  -- {accuracy, f1_macro, ...}
    training_rows INT,
    trained_at DATETIME,
    is_active TINYINT(1) DEFAULT 0
);
```

---

## 4. UX / Frontend yang Direkomendasikan

Sesuaikan dengan `admin_frontend/src/views/` dan `stores/history.js`.

### 4.1 Komponen baru
- **`AiSuggestButton.vue`** — per-baris, panggil `POST /api/transactions/<id>/suggest-mark`.
- **`BulkAiMarkModal.vue`** — preview semua suggestion sebelum apply, dengan
  filter confidence (hanya ≥ threshold).
- **`AiConfidenceBadge.vue`** — tampilkan confidence + source (`rule`/`ML`/`AI`)
  di kolom Mark.
- **`AiReviewQueue.vue`** (view baru) — filter `ai_suggested=1 AND status='pending'`,
  untuk review berkala oleh akuntan.

### 4.2 Integrasi dengan store yang sudah ada
Tambah di `stores/history.js`:
```js
async suggestMark(id) {
  const res = await historyApi.suggestMark(id); // endpoint baru
  return res.data; // { mark_id, confidence, source, reason }
},
async applyAiSuggestions(ids, threshold = 0.8) {
  const res = await historyApi.bulkSuggest(ids, threshold);
  // res.data.suggestions: [{ txn_id, mark_id, confidence }]
  // user preview → confirm → assignMark per item
}
```

### 4.3 Indicator visual
- Baris yang di-mark AI: ikon ⚡ + tooltip "AI: 92% (ML v1)".
- Baris di-mark manual: tanpa ikon.
- Filter baru: "AI-marked only" / "Needs review".

---

## 5. Pertimbangan KRITIS (jangan dilewati)

### 5.1 Akurasi & Threshold
- **False positive lebih buruk** daripada no-suggestion di akuntansi → mulai dengan
  threshold tinggi (≥ 0.9 untuk auto-apply, ≥ 0.7 untuk suggest-only).
- Pisahkan "auto-apply" (tanpa klik) vs "suggest" (perlu konfirmasi) — hanya
  enable auto-apply setelah akurasi validasi ≥ target.

### 5.2 Privacy & Data Sensitif
- `description` bank statement bisa mengandung: nama orang, nomor rekening, NPWP,
  info karyawan.
- **Untuk LLM cloud**: wajib mask PII sebelum kirim, atau **pakai LLM lokal**.
- PII masker: regex nomor rekening (10–16 digit), NPWP (15 digit), email, telepon.
- Alternatif: hanya kirim `description` yang sudah di-normalisasi (Level 1-style).

### 5.3 Compliance dengan `.clinerules`
- Aturan global: user & auth memakai database `sagansa_user`. Kolom `user_id` di
  tabel feedback **wajib** diisi dari `sagansa_user.users.id` (tanpa mengubah
  struktur tabel `users`).
- Migration tetap di `admin_backend/database/migrations/` untuk `esta`, atau bila
  sudah align ke `sagansa_2026`, pindahkan ke `services/migration`.

### 5.4 Cost Control (untuk LLM)
- Cache berdasarkan hash(description + db_cr + amount_bin).
- Batch request (20–50 transaksi per call).
- Fallback: bila budget habis / API error → fallback ke ML/Rule, jangan gagal total.
- Log token usage di `ai_model_runs` / tabel `ai_usage_log`.

### 5.5 Bias & Drift
- Distribusi mark tidak seimbang → pakai `class_weight='balanced'` / `ComplementNB`.
- **Data drift**: pola transaksi berubah seiring waktu (merchant baru, produk baru)
  → retrain berkala (bulanan) + monitoring akurasi per mark.
- Alert bila akurasi turun > X% → trigger review.

### 5.6 Jangan Auto-Mark Transaksi Sensitif
Exclude dari auto-mark (wajib manual):
- `amount > threshold` (mis. > 50jt) — transaksi besar.
- Mark dengan flag `is_asset`, `is_service`, `is_salary_component`, `is_rental`
  (berdampak ke perhitungan khusus: amortisasi, PPh, payroll).
- Transaksi `bank_code = 'MANUAL'` (manual journal).
- Transaksi yang sudah di-split (`parent_id IS NOT NULL`).

---

## 6. 🖥️ Hardware & Deployment: Gemma 4 12B di MacBook Air M5 16GB

> **Jawaban singkat: YA, CUKUP** — dengan kuantisasi Q4_K_M (atau Q5_K_M) via LM
> Studio. Performa untuk klasifikasi marking sangat memadai.

### 6.1 Matematika Memori (Gemma 4 12B)

| Format | Ukuran Model | RAM yang dibutuhkan (model + runtime) | Status di M5 16GB |
|--------|-------------|----------------------------------------|------------------|
| FP16 (asli) | ~24 GB | ~26 GB | ❌ Tidak muat |
| Q8 (8-bit) | ~12.5 GB | ~14 GB | ⚠️ Swap/thrash, lambat |
| Q6_K | ~10 GB | ~11.5 GB | ⚠️ Sempit, context kecil |
| **Q5_K_M** | **~8.5 GB** | **~10 GB** | ✅ **Bagus** (context 4–8K) |
| **Q4_K_M** ⭐ | **~7.5 GB** | **~9 GB** | ✅ **Optimal** (context 8–16K) |
| Q3_K_M | ~6 GB | ~7.5 GB | ⚠️ Kualitas turun |

**Budget memori di M5 16GB (unified memory):**
```
Total unified memory:      16.0 GB
─ OS macOS + apps:        ~5.0 GB
─ LM Studio runtime:      ~1.0 GB
─ Flask backend + DB:     ~0.5 GB
────────────────────────────────────
Tersedia untuk model:     ~9.5 GB  → Q4_K_M (7.5GB) atau Q5_K_M (8.5GB) PAS
```

### 6.2 Rekomendasi Konfigurasi LM Studio

**Pilih salah satu (urut prioritas akurasi vs kecepatan):**

| Prioritas | File GGUF | Estimasi VRAM | Estimasi Speed (M5) | Context Max | Keterangan |
|-----------|-----------|---------------|---------------------|-------------|------------|
| ⭐ #1 | `gemma-4-12b-it-Q4_K_M.gguf` | ~7.5 GB | 20–35 tok/s | 8–16K | **Sweet spot** |
| #2 | `gemma-4-12b-it-Q5_K_M.gguf` | ~8.5 GB | 15–25 tok/s | 4–8K | Akurasi ↑, context ↓ |
| #3 | `gemma-4-12b-it-Q6_K.gguf` | ~10 GB | 10–18 tok/s | 2–4K | Hanya bila RAM bersih |

**Setingan di LM Studio (tab "Advanced Configuration"):**
- **GPU Offload:** Max (Apple Silicon = semua layer ke Metal, otomatis)
- **Context Length:** `4096` (cukup untuk batch 20–50 transaksi)
- **Threads:** `8` (sesuai core efisiensi M5)
- **Temperature:** `0.1` (akuntansi butuh deterministik, bukan kreatif)
- **Top-P:** `0.9`
- **Repeat Penalty:** `1.1`
- **Backend:** `Metal` (Apple Silicon) — atau `MLX` bila tersedia (lebih efisien)

### 6.3 Estimasi Throughput untuk Use-Case Marking

Klasifikasi marking = **prompt pendek, output pendek (JSON)**.

| Skenario | Token in | Token out | Estimasi waktu (Q4_K_M) |
|----------|----------|-----------|--------------------------|
| 1 transaksi (single) | ~200 | ~30 | **~2 detik** |
| Batch 20 transaksi | ~1.500 | ~600 | **~35 detik** |
| Batch 50 transaksi | ~3.500 | ~1.500 | **~90 detik** |

> Untuk 100 transaksi ambigu (yang lolos Level 1+2) ≈ **2–3 menit**.
> Bandingkan dengan manual ~30–60 menit. ✅ **Worth it.**

### 6.4 Mode Operasi yang Direkomendasikan

Karena ini **bukan real-time** (user tidak menunggu per-ketik), gunakan **mode async**:

```
User klik "AI Suggest (Batch)" 
   → Backend enqueue job (background thread / Celery)
   → Kirim batch 20 txn ke LM Studio (localhost:1234)
   → Simpan hasil ke ai_mark_suggestions (status=pending)
   → Frontend poll / SSE untuk progress
   → User review di AiReviewQueue
```

**Kenapa async?**
- LM Studio single-request di M5 16GB (tidak bisa parallel banyak request).
- User bisa lanjut kerja lain sambil AI memproses.
- Bila LM Studio mati/lemot → fallback ke Rule/ML (Level 1+2).

### 6.5 Konfigurasi `.env` Backend

```bash
# admin_backend/.env
LLM_PROVIDER=lmstudio           # opsi: lmstudio | ollama | openai | anthropic | disabled
LLM_BASE_URL=http://localhost:1234/v1   # default LM Studio
LLM_MODEL=gemma-4-12b-it        # nama model di LM Studio
LLM_TIMEOUT=60                  # detik, per request
LLM_MAX_BATCH=20                # max transaksi per request
LLM_TEMPERATURE=0.1
LLM_ENABLED=true                # toggle on/off tanpa hapus config
```

LM Studio menyediakan **OpenAI-compatible API** di `http://localhost:1234/v1`,
jadi backend cukup pakai library `openai` Python dengan `base_url` lokal — **tidak
perlu SDK khusus**.

### 6.6 Pertimbangan & Limitasi M5 16GB

| Aspek | Kondisi | Mitigasi |
|-------|---------|----------|
| RAM terbatas | Bila buka banyak app (browser berat, Docker) → swap | Tutup app berat saat batch AI |
| Thermal | MacBook Air (tanpa fan) → throttling saat batch panjang | Batch 20 → jeda 5 detik → batch lagi |
| Single-user | LM Studio lokal hanya untuk 1 user concurrent | Untuk multi-user → pindah ke server GPU |
| Cold-start | Load model 7.5GB pertama ≈ 10–20 detik | Keep-alive: LM Studio "Always loaded" ON |
| Model size vs akurasi | Q4 sedikit turun vs FP16 | Untuk klasifikasi sederhana, drop < 2% — acceptable |

### 6.7 Kapan Upgrade?

Setup saat ini **cukup** untuk volume < 500 transaksi ambigu/bulan.
Pertimbangkan upgrade bila:
- Volume > 1.000 transaksi ambigu/bulan → **Mac Mini M4 Pro 24GB/32GB** atau **cloud GPU**.
- Multi-user concurrent (>3 orang) → **dedicated server** (RTX 4090 / Mac Studio).
- Butuh model lebih besar (Gemma 4 27B+) → **32GB+ RAM**.

---

## 7. Roadmap Implementasi (urut prioritas)

### Fase 0 — Fondasi (1 hari)
- [ ] Tambah migration: kolom `ai_suggested`, `ai_confidence`, `ai_source` di `transactions`.
- [ ] Buat tabel `ai_mark_suggestions` + `ai_model_runs`.
- [ ] Logging helper: `services/ai/audit.py` untuk catat semua saran AI.

### Fase 1 — Rule Engine (1–2 hari) ⭐ **mulai di sini**
- [ ] `services/ai/rule_engine.py` — normalisasi description + query history.
- [ ] Endpoint `POST /api/transactions/<id>/suggest-mark` + `bulk-suggest-marks`.
- [ ] Frontend: tombol "Suggest" per baris + bulk preview.
- [ ] **Ukur**: berapa % transaksi tertangani, berapa acceptance rate user.

### Fase 2 — ML Classifier (3–5 hari)
- [ ] Training script: `scripts/train_mark_classifier.py`.
- [ ] Integrasikan ke endpoint existing (fallback bila Rule < threshold).
- [ ] Versioning model di `ai_model_runs`.
- [ ] Retrain cron (mingguan/bulanan).

### Fase 3 — LLM Fallback (3–5 hari, optional)
- [ ] Setup Ollama lokal ATAU API key (`.env`: `LLM_PROVIDER`, `LLM_API_KEY`).
- [ ] `services/ai/llm_classifier.py` dengan PII masking + cache.
- [ ] Tampilkan "alasan" AI di UI (explainability).

### Fase 4 — Feedback Loop & Tuning (ongoing)
- [ ] Capture accept/reject di `ai_mark_suggestions`.
- [ ] Dashboard sederhana: acceptance rate, per-source accuracy, transaksi pending review.
- [ ] Tuning threshold berdasarkan data nyata.

---

## 8. Estimasi Dampak (indikatif)

| Metrik | Saat ini (manual) | Setelah Fase 1 | Setelah Fase 2+3 |
|--------|-------------------|----------------|-------------------|
| Waktu marking 100 transaksi | ~30–60 menit | ~5–10 menit | ~2–5 menit |
| Typo / mark salah | tinggi (manual) | rendah (auto, review cepat) | sangat rendah |
| Konsistensi (transaksi sama → mark sama) | tidak konsisten | konsisten | konsisten |
| Onboarding transaksi baru | lambat | cepat untuk pola umum | cepat + adaptif |

---

## 9. Lampiran: Contoh Endpoint (Level 1 + Level 2)

```python
# backend/services/ai/rule_engine.py
import re
from sqlalchemy import text

def normalize_description(desc: str) -> str:
    s = (desc or '').upper()
    s = re.sub(r'\d{6,}', '', s)
    s = re.sub(r'\b\d{1,2}[\/\-]\d{1,2}([\/\-]\d{2,4})?\b', '', s)
    s = re.sub(r'[^A-Z\s]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

def suggest_mark_by_rule(conn, txn, min_samples=2, min_confidence=0.9):
    norm = normalize_description(txn.get('description', ''))
    if not norm or len(norm) < 3:
        return None
    pattern = f"%{norm}%"
    row = conn.execute(text("""
        SELECT mark_id, COUNT(*) AS freq,
               COUNT(*) / (
                 SELECT COUNT(*) FROM transactions
                 WHERE description LIKE :p AND mark_id IS NOT NULL
                   AND db_cr = :dbc AND company_id IS NOT DISTINCT FROM :cid
               ) AS confidence
        FROM transactions
        WHERE description LIKE :p
          AND mark_id IS NOT NULL
          AND db_cr = :dbc
          AND company_id IS NOT DISTINCT FROM :cid
        GROUP BY mark_id
        ORDER BY freq DESC
        LIMIT 1
    """), {'p': pattern, 'dbc': txn.get('db_cr'), 'cid': txn.get('company_id')}).fetchone()
    if not row or row.freq < min_samples or row.confidence < min_confidence:
        return None
    return {
        'mark_id': str(row.mark_id),
        'confidence': float(row.confidence),
        'source': 'rule',
        'sample_count': int(row.freq),
    }
```

```python
# backend/routes/transactions/ai_bp.py (Blueprint baru)
from flask import Blueprint, jsonify, request
from backend.routes.accounting_utils import require_db_engine
from backend.services.ai.rule_engine import suggest_mark_by_rule

ai_bp = Blueprint('ai_bp', __name__)

@ai_bp.route('/api/transactions/<txn_id>/suggest-mark', methods=['POST'])
def suggest_mark(txn_id):
    engine = require_db_engine()
    with engine.connect() as conn:
        txn = conn.execute(text("SELECT * FROM transactions WHERE id = :id"),
                           {'id': txn_id}).fetchone()
        if not txn:
            return jsonify({'error': 'not found'}), 404
        suggestion = suggest_mark_by_rule(conn, dict(txn._mapping))
    return jsonify({'suggestion': suggestion})  # None bila tidak yakin
```

---

## 10. Catatan Akhir

- **Mulai dari Level 1 (rule engine)** — murah, cepat, langsung kelihatan dampaknya,
  dan menjadi baseline untuk mengukur apakah Level 2/3 worth it.
- **Jangan pernah auto-apply tanpa audit trail** di domain akuntansi.
- **Privacy first**: description bank statement = data sensitif. Pertimbangkan LLM
  lokal bila tidak boleh keluar dari infrastruktur.
- **Feedback loop adalah kunci** — model membaik karena user mengoreksi. Tanpa itu,
  akurasi akan stagnant / drift.

_Dokumen ini adalah rekomendasi teknis. Validasi kebutuhan bisnis & compliance
dengan tim akuntansi sebelum implementasi._