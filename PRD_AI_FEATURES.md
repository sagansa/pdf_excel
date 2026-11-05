# PRD: AI-Powered Transaction Enrichment & Auto-Marking

> **Proyek:** esta (StatementX)
> **Tanggal:** 2026-07-21
> **Status:** Draft
> **Penulis:** —

---

## 1. Ringkasan Eksekutif

Saat ini semua transaksi dari bank statement PDF di-parse mentah apa adanya, lalu user harus mengisi mark (kategori akuntansi) satu per satu secara manual. Ini repetitive, rawan salah, dan tidak konsisten.

Dua fitur AI berbasis **LM Studio lokal** akan mengotomatisasi proses ini:

| Fitur | Tujuan | Dampak |
|-------|--------|--------|
| **Fitur 1: Enrichment Deskripsi** | Membersihkan raw description hasil parser bank pakai LLM | Description konsisten, mudah dibaca, rule matching jadi akurat |
| **Fitur 2: Auto-Mark Suggestion** | Menyarankan mark_id untuk setiap transaksi berdasarkan deskripsi yang sudah bersih | Marking 1 klik, konsisten, audit trail terjamin |

**Target:** 80% transaksi bisa di-mark otomatis, sisa 20% butuh review manual.

---

## 2. Fitur 1: Enrichment Deskripsi — AI Description Cleaner

### 2.1 Masalah

Output bank parser saat ini menyisakan banyak noise:

```
TRSF E-BANKING 0829347123 GOJEK       ← nomor referensi 10 digit
PEMBAYARAN LISTRIK PLN 9876543210123  ← ID pelanggan 13 digit
TARIKAN TUNAI 123456 ATM BCA          ← nomor unik 6 digit
PURCHASE APPLE.COM/BILL 0.99 USD      ← nominal tercampur
TRSF E-BANKING 0829347555 GOJEK       ← transaksi sama tapi beda nomor
```

Akibatnya:
- Rule matching gagal karena `0829347123` ≠ `0829347555`
- User sulit membaca & mengelompokkan transaksi
- Data drift: deskripsi yang sama secara bisnis tapi berbeda secara string

### 2.2 Solusi

Pipeline enrichment baru setelah `parse_statement()`, sebelum `save_transactions_to_db()`:

```
Parse → Normalize → ENRICH → Save
                      ↓
                LM Studio (lokal)
                Batch 30-50 transaksi
```

### 2.3 Output yang Dihasilkan

| Field | Contoh | Kegunaan |
|-------|--------|----------|
| `description` (overwrite) | `Transfer Gojek` | Bersih, seragam, bisa di-match |
| `merchant_name` (baru) | `Gojek` | Untuk filtering/reporting |
| `transaction_category` (baru) | `transportasi` | Metadata tambahan |
| `raw_description` (baru) | `TRSF E-BANKING 0829347123 GOJEK` | Audit trail |

### 2.4 Prompt LM Studio

```
Anda asisten akuntansi. Bersihkan deskripsi transaksi bank berikut.
Ikuti aturan:
- Hapus semua nomor referensi, ID pelanggan, nomor rekening, nominal
- Pertahankan nama merchant/vendor
- Gunakan Title Case, bahasa Indonesia
- Jika deskripsi hanya berisi huruf tanpa noise, outputkan apa adanya

Transaksi:
  raw: "{description}"
  bank: {bank_code}
  arah: {db_cr}
  nominal: {amount}

Jawab JSON SAJA tanpa teks lain:
{
  "cleaned": "...",
  "merchant": "...",
  "category": "transfer|pembayaran|belanja|tarik_tunai|pendapatan|lainnya"
}
```

### 2.5 Strategi Caching

```sql
CREATE TABLE description_cache (
    raw_hash VARCHAR(64) PRIMARY KEY,  -- SHA256(raw_description + bank_code)
    cleaned_description TEXT,
    merchant_name VARCHAR(255),
    transaction_category VARCHAR(50),
    created_at DATETIME
);
```

- Cek cache dulu sebelum panggil LM Studio
- Transaksi berulang (Gojek, PLN, dll) hanya kena LLM 1x
- Cache bisa di-warmup untuk data history yang sudah ada

### 2.6 Mode Operasi

| Mode | Cara Kerja | Use Case |
|------|------------|----------|
| **sync** | Enrich sebelum response dikirim | Upload < 10 transaksi |
| **async** | Enrich background, user dapat notifikasi | Upload > 10 transaksi |
| **hybrid** (default) | 10 transaksi pertama sync, sisanya async | Upload normal (ratusan transaksi) |

### 2.7 Daftar Kolom Baru di `transactions`

```sql
-- Migration 070_add_ai_enrichment.sql
ALTER TABLE transactions ADD COLUMN raw_description TEXT AFTER description;
ALTER TABLE transactions ADD COLUMN merchant_name VARCHAR(255) AFTER raw_description;
ALTER TABLE transactions ADD COLUMN transaction_category VARCHAR(50) AFTER merchant_name;
ALTER TABLE transactions ADD COLUMN enriched_at DATETIME AFTER transaction_category;
```

### 2.8 Success Metrics

| Metrik | Target |
|--------|--------|
| Description yang berubah setelah enrichment | > 60% dari total transaksi baru |
| Konsistensi deskripsi (transaksi bisnis sama → string sama) | > 90% |
| Cache hit rate | > 80% setelah 1 bulan pemakaian |
| Waktu enrichment batch 50 transaksi (async) | < 2 menit |

---

## 3. Fitur 2: Auto-Mark Suggestion

### 3.1 Masalah

Setelah transaksi masuk ke database, user harus:
1. Buka halaman History
2. Baca deskripsi transaksi
3. Pilih mark yang sesuai dari dropdown
4. Ulangi untuk setiap baris — ratusan transasi per bulan

Proses ini:
- **Repetitif**: transaksi yang sama muncul berkali-kali (gaji, sewa, listrik)
- **Rawan human error**: mark berbeda untuk transaksi yang sama
- **Tidak scalable**: makin banyak data, makin lama marking

### 3.2 Solusi Berjenjang (Hybrid Cascade)

Mengadopsi arsitektur hybrid dari AI_RECOMMENDATIONS.md §2:

```
Transaksi baru → [1] Rule Engine → confidence ≥ 0.9 → auto-apply
                                      ↓ < 0.9
                                  [2] ML Classifier → confidence ≥ 0.8 → suggest
                                      ↓ < 0.8
                                  [3] LLM (LM Studio) → confidence ≥ 0.6 → suggest
                                      ↓ < 0.6
                                  Manual review
```

### 3.3 Level 1: Rule Engine (Non-AI, Quick Win)

Mencocokkan description yang sudah di-normalisasi dengan history transaksi.

```
Input: "Transfer Gojek" (sudah di-enrich oleh Fitur 1)
  ↓
Normalize: lowercase, hapus spasi berlebih
  ↓
Cari di history: description LIKE '%transfer gojek%' AND db_cr = 'CR'
  ↓
Result: { mark_id: "gaji_direksi", confidence: 0.95, sample_count: 47 }
  ↓
confidence ≥ 0.9 → auto-apply
```

**Threshold:**
- Auto-apply: `confidence ≥ 0.9` AND `sample_count ≥ 3`
- Suggest: `confidence ≥ 0.7` AND `sample_count ≥ 1`

### 3.4 Level 2: ML Classifier (Scikit-learn)

Untuk transaksi yang tidak match persis tapi punya pola mirip.

- **Model:** Complement Naive Bayes / Logistic Regression
- **Fitur:** TF-IDF description (ngram 1-2) + amount_log + day_of_month + db_cr + bank_code
- **Training:** Semua data berlabel (mark_id IS NOT NULL), retrain mingguan
- **Inference:** < 10ms per transaksi — instan

### 3.5 Level 3: LLM (LM Studio)

Untuk transaksi yang tidak dikenal oleh rule engine & ML classifier (cold start, pola baru).

```
Kirim ke LM Studio:
  Deskripsi: "Transfer Gojek"
  Arah: CR
  Nominal: 1.500.000
  Tanggal: 28

Daftar mark tersedia (di-filter by direction):
  - "Pendapatan Jasa" (CR)
  - "Pendapatan Bunga" (CR)
  - "Pendapatan Lain-lain" (CR)

LLM jawab:
  {"mark": "Pendapatan Jasa", "confidence": 0.85, "alasan": "Gojek = platform jasa"}
```

**Penting:** Daftar mark yang dikirim ke LLM **tidak semua** — hanya yang sesuai `db_cr` (natural_direction) dan `company_id`. Ini mengurangi token dan meningkatkan akurasi.

**Cache:**
```sql
CREATE TABLE llm_suggestion_cache (
    feature_hash VARCHAR(64) PRIMARY KEY,  -- SHA256(description + db_cr + amount_bucket)
    mark_id CHAR(36),
    confidence DECIMAL(4,3),
    reason TEXT,
    created_at DATETIME
);
```

### 3.6 Audit Trail

**Kolom baru di transactions** (migration):

```sql
ALTER TABLE transactions ADD COLUMN ai_suggested TINYINT(1) DEFAULT 0;
ALTER TABLE transactions ADD COLUMN ai_confidence DECIMAL(4,3);
ALTER TABLE transactions ADD COLUMN ai_source VARCHAR(20);
-- ai_source: 'rule' | 'ml' | 'llm' | NULL (manual)
```

**Tabel baru:**

```sql
CREATE TABLE ai_mark_suggestions (
    id CHAR(36) PRIMARY KEY,
    transaction_id CHAR(36) NOT NULL,
    suggested_mark_id CHAR(36),
    accepted_mark_id CHAR(36),
    confidence DECIMAL(4,3),
    source VARCHAR(20),
    reason TEXT,
    status ENUM('pending','accepted','rejected','overridden') DEFAULT 'pending',
    user_id CHAR(36),
    created_at DATETIME,
    decided_at DATETIME,
    FOREIGN KEY (transaction_id) REFERENCES transactions(id)
);

CREATE TABLE ai_model_runs (
    id CHAR(36) PRIMARY KEY,
    model_type VARCHAR(20),
    version VARCHAR(50),
    metrics_json TEXT,
    training_rows INT,
    trained_at DATETIME,
    is_active TINYINT(1) DEFAULT 0
);
```

### 3.7 Anti-Patterns (Wajib Manual Mark)

Transaksi berikut TIDAK BOLEH di-auto-mark:

| Kriteria | Alasan |
|----------|--------|
| `transaction_splits` exists | Butuh alokasi multi-mark |
| `amount > threshold_config` (default 50jt) | Transaksi material |
| `is_asset / is_service / is_salary_component` | Berdampak ke perhitungan khusus |
| `bank_code = 'MANUAL'` | Manual journal entry |
| `parent_id IS NOT NULL` | Anak dari split |
| Rentang 5 hari awal & akhir bulan (custom) | Rentan salah mark |

### 3.8 Success Metrics

| Metrik | Target |
|--------|--------|
| Transaksi auto-marked (tanpa intervensi) | ≥ 60% |
| Acceptance rate user terhadap suggestion | ≥ 85% |
| False positive rate | < 2% |
| Waktu marking 100 transaksi | < 5 menit (sekarang 30-60 menit) |

---

## 4. Alur Sistem Lengkap

```
USER UPLOAD PDF
  │
  ▼
┌─────────────────────────────────────┐
│ 1. Parse (existing)                 │
│    - Bank parser → raw DataFrame    │
└────────────┬────────────────────────┘
             ▼
┌─────────────────────────────────────┐
│ 2. Normalize (existing)             │
│    - Date, amount, db_cr, company   │
└────────────┬────────────────────────┘
             ▼
┌─────────────────────────────────────┐      ┌──────────────────┐
│ 3. ENRICH Descriptions (NEW!)       │─────▶│ LM Studio        │
│    - Batch 30-50 descriptions       │◀─────│ (async, cached)  │
│    - Simpan raw_description         │      └──────────────────┘
│    - Overwrite description          │
└────────────┬────────────────────────┘
             ▼
┌─────────────────────────────────────┐
│ 4. Save to DB (existing)            │
│    - transactions table dengan     │
│      description yg sudah bersih    │
└────────────┬────────────────────────┘
             ▼
┌─────────────────────────────────────┐      ┌──────────────────────┐
│ 5. AUTO-MARK SUGGEST (NEW!)         │─────▶│ Rule → ML → LM Studio│
│    - Cascade pipeline               │      └──────────────────────┘
│    - Simpan ai_suggested dll        │
│    - auto-apply jika confidence≥0.9 │
└────────────┬────────────────────────┘
             ▼
┌─────────────────────────────────────┐
│ 6. User Review (History page)       │
│    - Terima/tolak/ubah suggestion   │
│    - Feedback loop → improve model  │
└─────────────────────────────────────┘
```

---

## 5. Kebutuhan Hardware & Environment

### 5.1 LM Studio

- **Endpoint:** `http://localhost:1234/v1` (OpenAI-compatible)
- **Model rekomendasi:** Gemma 4 12B Instruct — Q4_K_M (~7.5 GB RAM)
- **Context:** 4096 tokens
- **Temperature:** 0.1 (deterministic)
- **Keep-alive:** "Always loaded" ON (cold start 10-20 detik)

### 5.2 Backend (Flask)

**Library baru:**
```
openai>=1.0.0           # OpenAI-compatible client untuk LM Studio
scikit-learn>=1.3.0     # ML classifier (Level 2)
joblib>=1.3.0           # Model serialization
```

**Service baru:**
```
backend/services/ai/
├── __init__.py
├── llm_client.py         # OpenAI-compatible client untuk LM Studio
├── description_enricher.py  # Fitur 1: enrichment deskripsi
├── mark_classifier.py    # Fitur 2: cascade classifier (rule → ml → llm)
├── rule_engine.py        # Rule-based matching
├── ml_classifier.py      # TF-IDF + Logistic Regression
├── cache.py              # Redis / SQLite caching layer
├── audit.py              # Audit trail helper
└── prompts.py            # Template prompt
```

### 5.3 Konfigurasi `.env`

```bash
# LLM / LM Studio
LLM_ENABLED=true
LLM_PROVIDER=lmstudio
LLM_BASE_URL=http://localhost:1234/v1
LLM_MODEL=gemma-4-12b-it
LLM_TIMEOUT=60
LLM_MAX_BATCH=50
LLM_TEMPERATURE=0.1

# Feature Flags
ENRICHMENT_ENABLED=true
AUTO_MARK_ENABLED=true
AUTO_MARK_THRESHOLD_APPLY=0.9
AUTO_MARK_THRESHOLD_SUGGEST=0.7

# Resource Limits
ENRICHMENT_BATCH_SIZE=50
ML_ENABLED=true
```

---

## 6. UI / UX Perubahan

### 6.1 Halaman Upload/Converter

| Elemen | Perubahan |
|--------|-----------|
| Progress bar enrichment | "Membersihkan deskripsi... (45/100)" |
| Status enrichment | Badge: "Deskripsi telah dibersihkan AI" |
| Toggle enrichment | Switch: "Aktifkan AI enrichment" (ON default) |

### 6.2 Halaman History

| Elemen | Perubahan |
|--------|-----------|
| Kolom Mark | Badge: ⚡ + source (`Rule` / `ML` / `AI`) + confidence % |
| Tombol baru | "✨ AI Suggest" per baris |
| Bulk action baru | "Auto-mark (High Confidence)" |
| Filter baru | "AI-marked only" / "Needs review" |
| Warna baris | Hijau muda (auto-applied) / Kuning (suggested) / Putih (manual) |

### 6.3 Halaman Baru: AI Review Queue

> Route: `/ai-review`

Menampilkan semua transaksi dengan `ai_suggested=1` dan `status=pending`, untuk review bulk oleh akuntan.

| Kolom | Aksi |
|-------|------|
| Deskripsi (clean) | — |
| AI suggestion | Mark + confidence + source + alasan |
| Accept | Tombol ✓ (simpan mark) |
| Reject | Tombol ✗ (tandai rejected) |
| Override | Dropdown pilih mark lain |

### 6.4 Notifikasi

| Event | Notifikasi |
|-------|------------|
| Enrichment selesai | Toast: "50 deskripsi telah dibersihkan" |
| Auto-mark selesai | Toast: "35 transaksi di-mark otomatis" |
| Saran baru | Badge di sidebar: "12 saran baru untuk di-review" |

---

## 7. Risiko & Mitigasi

| Risiko | Dampak | Mitigasi |
|--------|--------|----------|
| LM Studio crash / OOM | Enrichment & suggestion gagal | Fallback ke raw description / no suggestion, jangan blokir upload |
| LLM hallucination | Mark salah (false positive) | Auto-apply hanya confidence ≥ 0.9, wajib audit trail |
| Kinerja lambat | Upload terasa berat | Mode async + progress bar, user bisa download dulu |
| Model drift | Akurasi turun seiring waktu | Retrain ML mingguan + monitoring acceptance rate |
| RAM terbatas (16GB) | Swap/throttle | Batch kecil (30-50), jeda antar batch, keep-alive model |
| Data privacy | Description mengandung PII | LLM lokal = data stay in machine, aman |

---

## 8. Prioritas Implementasi (Roadmap)

### Fase 0 — Fondasi (1-2 hari)
- [ ] Setup LM Studio + verifikasi koneksi dari Flask
- [ ] Migration: kolom baru di `transactions` + tabel `ai_mark_suggestions`
- [ ] Konfigurasi `.env`

### Fase 1 — Description Enrichment (3-5 hari) ⭐ MULAI DI SINI
- [ ] `llm_client.py` — wrapper OpenAI-compatible
- [ ] `description_enricher.py` — batch enrichment pipeline
- [ ] Integrasi di `pdf_helpers.py` setelah `normalize_statement_dataframe()`
- [ ] `description_cache.py` — SQLite cache

### Fase 2 — Rule Engine + UI (3-5 hari)
- [ ] `rule_engine.py` — normalisasi + query history
- [ ] `ai_bp.py` — endpoint suggest-mark & bulk-suggest
- [ ] Frontend: tombol suggest + badge confidence di History
- [ ] Backend: cascade pipeline (rule → fallback)

### Fase 3 — ML Classifier (3-5 hari)
- [ ] `scripts/train_mark_classifier.py`
- [ ] Integrasi ke cascade pipeline
- [ ] Retrain cron

### Fase 4 — LLM Suggestion + Feedback (3-5 hari)
- [ ] LLM fallback di cascade (transaksi yang tidak dikenal)
- [ ] `llm_suggestion_cache.py`
- [ ] Halaman AI Review Queue
- [ ] Feedback loop: accept/reject → training data

### Fase 5 — Optimasi & Monitoring (ongoing)
- [ ] Dashboard acceptance rate
- [ ] Threshold tuning
- [ ] Alert: akurasi turun

---

## 9. Glossary

| Term | Definisi |
|------|----------|
| **Mark** | Label kategori transaksi yang menghubungkan ke Chart of Accounts (COA) |
| **Mark COA Mapping** | Relasi mark → akun COA (DEBIT/CREDIT) untuk auto-journal |
| **Description** | Teks deskripsi transaksi dari bank statement |
| **Enrichment** | Proses pembersihan & ekstraksi metadata dari description |
| **Cascade** | Pipeline berjenjang: Rule → ML → LLM → Manual |
| **Confidence** | Skor 0.0 - 1.0 seberapa yakin sistem dengan suggestion |
| **Auto-apply** | Mark diterapkan otomatis tanpa konfirmasi user |
| **Suggest** | Mark disarankan, user harus konfirmasi |

---

## 10. Dokumen Terkait

- `AI_RECOMMENDATIONS.md` — Detail teknis implementasi AI (600 baris)
- `admin_backend/backend/routes/uploads/pdf_bp.py` — Entry point konversi PDF
- `admin_backend/backend/routes/uploads/pdf_helpers.py` — Pipeline konversi
- `admin_backend/backend/services/transactions/transaction_utils.py` — Build record
- `admin_backend/bank_parsers/bca.py` — Contoh bank parser
- `admin_backend/backend/routes/transactions/history_bp.py` — History & mark endpoints
- `admin_backend/backend/routes/master_data/mark_bp.py` — CRUD marks
