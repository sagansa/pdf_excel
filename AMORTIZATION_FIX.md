# Perbaikan Sistem Amortization

## Ringkasan Perubahan

### 1. Migration Database
**File:** `database/migrations/029_update_mark_asset_mapping.sql`

Menambahkan kolom baru ke tabel `mark_asset_mapping`:
- `asset_group_id` (CHAR(36)) - Link langsung ke `amortization_asset_groups`
- `is_deductible_50_percent` (BOOLEAN) - Flag untuk deductible 50% atau 100%

### 2. Update Backend (server.py)

#### Fungsi `get_mark_based_assets` (line ~1850)
**Sebelumnya:** Menggunakan nilai hardcoded (Kelompok 2, Tangible, 5 tahun, 20%)

**Sekarang:** Mengambil konfigurasi dari:
1. `transactions.amortization_asset_group_id` (override di level transaction)
2. `mark_asset_mapping.asset_group_id` (mapping dari mark ke asset group)
3. Fallback ke default values jika tidak dikonfigurasi

**Priority order:**
```
transaction.amortization_asset_group_id
  ↓ (jika NULL)
mark_asset_mapping.asset_group_id
  ↓ (jika NULL)
Default values (Tangible, 5 tahun, 20%)
```

#### API Endpoint `create_mark_asset_mapping` (line ~3824)
Menambahkan field baru:
- `asset_group_id` - ID dari `amortization_asset_groups`
- `is_deductible_50_percent` - Flag untuk deductible

### 3. Update Frontend (src/stores/amortization.js)
Method `createMarkMapping` sekarang mengirim field tambahan:
- `asset_group_id`
- `is_deductible_50_percent`

## Cara Penggunaan

### Input Manual Amortization
Dapat dilakukan melalui:
1. Table `amortization_items` untuk manual entry
2. Field di transaction level:
   - `amortization_asset_group_id` - Asset group override
   - `use_half_rate` - Deductible 50% atau 100%
   - `amortization_start_date` - Tanggal mulai amortisasi
   - `amortization_useful_life` - Masa manfaat override
   - `amortization_notes` - Catatan tambahan

### Input dari Transactions (Mark-Based)
1. Tandai mark sebagai aset: `marks.is_asset = TRUE`
2. Konfigurasi mapping melalui API `/api/amortization/mark-mapping`:

```json
{
  "mark_id": "mark-id-here",
  "asset_type": "Tangible",
  "useful_life_years": 8,
  "amortization_rate": 12.50,
  "asset_group_id": "asset-group-id-here",
  "is_deductible_50_percent": false
}
```

3. Atau update di level transaction melalui API `/api/transactions/<transaction_id>/amortization-group`:

```json
{
  "asset_group_id": "asset-group-id-here",
  "is_amortizable": true,
  "use_half_rate": false,
  "amortization_start_date": "2025-01-01",
  "amortization_useful_life": 8,
  "amortization_notes": "Override note"
}
```

## Perhitungan Amortization

### Base Amount Calculation
```
Base Amount = (Acquisition Cost - Residual Value) × Deductible Multiplier

Dimana Deductible Multiplier:
- 1.0 untuk 100% Deductible (use_half_rate = FALSE)
- 0.5 untuk 50% Deductible (use_half_rate = TRUE)
```

### Annual Amortization
```
Annual Amortization = Base Amount × (Tarif Rate / 100) × Month Multiplier

Month Multiplier:
- 12/12 untuk tahun penuh
- months_active/12 untuk tahun pertama (partial year)
```

## Asset Groups (Kelompok Aset)

### Tangible Assets (Harta Berwujud)
- **Kelompok 1:** 4 tahun, 25% (full) / 12.5% (half)
- **Kelompok 2:** 8 tahun, 12.5% (full) / 6.25% (half)
- **Kelompok 3:** 16 tahun, 6.25% (full) / 3.13% (half)
- **Kelompok 4:** 20 tahun, 5% (full) / 2.5% (half)

### Intangible Assets (Harta Tidak Berwujud)
- **Kelompok 1:** 4 tahun, 25% (full) / 12.5% (half)
- **Kelompok 2:** 8 tahun, 12.5% (full) / 6.25% (half)
- **Kelompok 3:** 16 tahun, 6.25% (full) / 3.13% (half)
- **Kelompok 4:** 20 tahun, 5% (full) / 2.5% (half)

### Buildings (Bangunan)
- **Bangunan Permanen:** 20 tahun, 5% (full) / 2.5% (half)
- **Bangunan Non-Permanen:** 10 tahun, 10% (full) / 5% (half)

## Script Testing

### `test_mark_based_assets.py`
Menampilkan mark-based assets dan mapping konfigurasi.

### `demo_mark_mapping.py`
Demonstrasi lengkap cara konfigurasi mark ke asset group.

## API Endpoints

### GET `/api/amortization/asset-groups`
Mendapatkan semua asset groups.

### POST `/api/amortization/mark-mapping`
Membuat atau update mapping mark ke asset properties.

### PUT `/api/transactions/<transaction_id>/amortization-group`
Update konfigurasi amortization di level transaction.

### GET `/api/amortization/mark-settings`
Mendapatkan settings untuk mark-based amortization.

### POST `/api/amortization/mark-settings`
Save mark-based amortization settings.

## Perbaikan Utama

1. **Dinamis Asset Group Selection:** Tidak lagi hardcoded ke Kelompok 2
2. **Support Deductible Configuration:** 50% atau 100% deductible
3. **Priority-Based Configuration:** Transaction level → Mark mapping → Default
4. **Better Integration:** antara mark, mark_asset_mapping, dan amortization_asset_groups
