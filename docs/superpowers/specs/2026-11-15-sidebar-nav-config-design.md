# Desain: Sidebar Nav Config + Accordion

Tanggal: 2026-11-15
Status: Disetujui (menunggu review spec)
Scope: `admin_frontend` — sidebar, layout, router. Tanpa perubahan backend, tanpa perubahan token visual.

## 1. Latar Belakang & Masalah

Sidebar admin (`admin_frontend/src/layouts/MainLayout.vue`) saat ini:

- **15 menu hardcoded di template** — menambah halaman berarti mengedit 3 tempat: `MainLayout.vue`, `router/index.js`, dan switch-case `pageTitle`.
- **Struktur flat dengan label section** — tidak siap menghadapi pertumbuhan menu (Reports/HRD masih berkembang, payroll baru ditambahkan).
- **Bug `pageTitle`:** switch-case di `MainLayout.vue:225-244` tidak punya entri untuk `ai-review`, `trial-balance`, `balance-check` → header menampilkan "StatementX" di halaman tersebut.
- **Halaman "gelap":** `/general-ledger` tidak bisa diakses dari UI mana pun (tidak ada link yang menunjuk; hanya lewat ketik URL). Saat dibuka, tidak ada item sidebar yang aktif.
- **Orphan route:** `/initial-capital` juga tidak ditunjuk link mana pun — fitur initial capital sudah ter-embed di Settings lewat `components/settings/InitialCapitalSettings.vue`.
- **Mode collapsed** menggunakan titik-titik `...` sebagai pengganti label section dan atribut `title` bawaan browser untuk tooltip.
- **Section 1-item:** "HRD" hanya berisi Presences; "Configuration" hanya berisi Settings — buang ruang vertikal.

### Pain point yang dipilih user

1. Scalability — menu terus bertambah.
2. Visual & konsistensi UI.
3. Kemudahan maintenance — definisi menu tersebar di 3 tempat.

Role/permission **bukan** prioritas kali ini, tapi fondasinya disiapkan di skema config (slot `roles`). Label menu **tetap campuran bahasa** (keputusan user) — hanya ditulis konsisten di satu tempat.

## 2. Pendekatan yang Dipilih

Dari 3 pendekatan yang diusulkan (A: nav config + accordion; B: polish minimal; C: icon rail + command palette), user memilih **Pendekatan A**. Pendekatan C dapat diadopsi bertahap di kemudian hari karena nav config sudah menjadi fondasinya.

## 3. Arsitektur

```
src/
├── config/navigation.js          ← BARU: single source of truth menu
├── components/layout/
│   ├── AppSidebar.vue            ← BARU: sidebar (dipecah dari MainLayout)
│   └── SidebarSection.vue        ← BARU: satu accordion section
├── layouts/MainLayout.vue        ← DISEDERHANAKAN: render <AppSidebar/>,
│                                    hapus markup nav + switch-case pageTitle
└── router/index.js               ← TAMBAH meta.title per route
```

Data flow satu arah: `navigation.js` → `AppSidebar.vue` → `SidebarSection.vue`. Tidak ada state global baru. Status buka/tutup accordion hidup di `AppSidebar` (ref lokal), dan keputusan buka-awal di-derive dari route aktif.

Setiap unit punya satu tanggung jawab:

- `navigation.js` — data murni, tanpa logika. Bisa diimpor siapa pun (sidebar sekarang, command palette nanti).
- `AppSidebar.vue` — brand, footer akun, collapse/mobile state, iterasi sections.
- `SidebarSection.vue` — render satu section: label + chevron + daftar item. Tanpa state sendiri; menerima prop `expanded` dan emit event toggle — pemilik keputusan tetap `AppSidebar`.

## 4. Struktur Menu Final

| Section | Item | Perubahan dari sekarang |
|---|---|---|
| *(top-level)* | Dashboard, Converter, History & DB, Review Saran AI, Upload Summary, Upload Checklist | Tetap |
| **HRD** | Presences | **Revisi 2026-11-16 (keputusan user):** section dipertahankan sebagai accordion berisi "Presences" — awalnya direncanakan demote ke item top-level "HRD Presences", dikembalikan karena pengelompokan dirasa lebih baik dan section ini siap menampung menu HRD lain (payroll, karyawan) |
| **Management** | Companies, Marks, Chart of Accounts, Locations & Stores | Jadi accordion |
| **Reports** | Financial Reports, Trial Balance, **General Ledger**, Cek Kontinuitas Saldo | General Ledger masuk menu (sebelumnya unreachable); jadi accordion |
| *(top-level)* | Settings | Section "Configuration" 1-item dihapus |

Keterangan:

- `/initial-capital` **tidak** dimasukkan menu — tetap orphan, tercatat sebagai kandidat penghapusan route di luar scope ini.
- Label ditulis apa adanya (campuran bahasa sesuai keputusan user).

### Revisi 2026-11-16 (b) — Coming soon

- Flag baru di config: `soon: true` — item **tanpa `to`**, dirender **nonaktif** (bukan router-link) dengan badge kecil **"Segera"**. Item ini tidak pernah aktif dan tidak punya route.
- Tiga item coming-soon ditambahkan untuk menyiapkan kelompok menu masa depan:
  - Section **HRD**, setelah Presences: **Payroll** (`bi-cash-coin`) dan **Karyawan** (`bi-people-fill`).
  - Section **Management**, setelah Locations & Stores: **Products** (`bi-box-seam`).
- Tujuan: struktur kelompok HRD & Management terlihat utuh sejak sekarang, sehingga saat menu aslinya dibangun tinggal menambahkan `to:` pada config — tidak ada perubahan UI tambahan.
- Render: semua jalur (top-level, accordion sub-list, flyout collapsed) menampilkan item soon sebagai `<span aria-disabled="true">` ber-class `sidebar-soon` + badge; tooltip collapsed tetap menampilkan judul item.

## 5. Skema Config

```js
// src/config/navigation.js
export const navigation = [
  {
    label: null, // null = item top-level tanpa judul section
    items: [
      { title: 'Dashboard', to: '/', icon: 'bi-grid-fill' },
      // ...
    ],
  },
  {
    label: 'Reports',
    items: [
      { title: 'Financial Reports', to: '/reports', icon: 'bi-file-earmark-bar-graph' },
      { title: 'Trial Balance', to: '/trial-balance', icon: 'bi-columns-gap' },
      { title: 'General Ledger', to: '/general-ledger', icon: 'bi-journal-bookmark' },
      { title: 'Cek Kontinuitas Saldo', to: '/balance-check', icon: 'bi-shield-check' },
    ],
  },
  // ...
]
```

Aturan skema:

- `label: null` → semua item di-render langsung sebagai top-level (tanpa judul section).
- Section dengan `label` → accordion. Ikon yang dipakai saat collapsed adalah **ikon item pertama** di section tersebut.
- `badgeKey` (optional, string) — ditambahkan ke skema sekarang tetapi **belum di-render**; Phase 2 baru menghidupkannya. AppSidebar mengabaikan key yang tidak dikenal, jadi menambah skema sekarang tidak berisiko.
- `roles` (optional, array | null) — juga hanya disiapkan; null = tampil untuk semua. Tidak ada filter yang berjalan sampai ada konsep role di auth store.

## 6. Perilaku Accordion

- Section accordion **auto-terbuka** saat salah satu item di dalamnya aktif, termasuk saat page di-load langsung via URL (deep-link).
- User bisa menutup section yang itemnya aktif; keputusan manual user dihormati sampai route berubah lagi.
- Transisi buka/tutup memakai transisi CSS yang sudah jadi gaya aplikasi (duration-300 ease-in-out).
- Aksesibilitas: tombol header section adalah `<button>` dengan `aria-expanded` dan `aria-controls`; daftar item dalam `<ul>`.

## 7. Header Title dari Route Meta

Switch-case 20 baris di `MainLayout.vue:225-244` diganti dengan:

```js
const pageTitle = computed(() => route.meta.title ?? 'StatementX')
```

Setiap route di `router/index.js` mendapat `meta: { title: '...' }` — sekaligus menambal 3 route yang lupa (`ai-review`, `trial-balance`, `balance-check`).

## 8. Mode Collapsed & Detail Visual

- Sidebar collapse (desktop, `w-20`): icon-only. Tooltip **custom** (CSS absolut di kanan ikon, muncul saat hover/focus) menggantikan atribut `title` bawaan browser — agar konsisten dengan tema dan muncul instan.
- Titik-titik `...` pengganti label section dihapus. Saat collapsed:
  - Item top-level tampil sebagai ikon saja (dengan tooltip custom).
  - Accordion section tampil sebagai **ikon item pertamanya** + chevron mini; klik memunculkan **flyout** di samping berisi item section (bukan membuka panel sidebar).
  - **Fallback** bila flyout terbukti ribet saat implementasi: saat collapsed, accordion auto-terbuka semua sebagai daftar ikon. Keputusan final di ambil saat implementasi; keduanya memenuhi tujuan (tidak ada label gantung `...`).
- Mobile: perilaku overlay sekarang dipertahankan apa adanya (fixed + overlay gelap); accordion bekerja sama baiknya.
- Token visual tidak berubah — tetap memakai variabel `--color-*` dan kelas `sidebar-item` / `sidebar-section-label` yang ada. Tambahan hanya: chevron, indentasi sub-item, tooltip.

## 9. Error Handling

- Config adalah data statis; tidak ada fetch di jalur render menu. Menu tidak bisa gagal karena jaringan.
- `badgeKey` di masa depan: badge gagal fetch → disembunyikan, tidak pernah memblokir render menu.
- Route `to:` typo di config → perilaku Vue Router default (navigate gagal secara terkontrol), tidak crash. Checklist testing mencakup verifikasi semua 15 route dari config.

## 10. Testing (verifikasi manual via dev server)

Checklist:

1. Semua 16 item menu ter-render dan bisa dinavigasi dari sidebar (15 item lama + General Ledger).
2. Active state benar di tiap halaman, termasuk General Ledger (sebelumnya tidak punya highlight).
3. Accordion auto-open saat deep-link langsung ke `/trial-balance` dsb.
4. Collapse/expand desktop smooth; tooltip muncul di semua item collapsed.
5. Mobile overlay buka/tutup, item klik menutup sidebar.
6. Dark mode tetap konsisten (token `--color-*`).
7. Header title benar di semua halaman termasuk `ai-review`, `trial-balance`, `balance-check`.

## 11. Out of Scope

- Penghapusan orphan route `/initial-capital` (dicatat sebagai kandidat; diskusi terpisah).
- Render badge dinamis dan filter roles (fondasi skema saja).
- Command palette / pencarian sidebar (Phase 4).
- Perubahan token visual atau gaya halaman di luar sidebar.

## 12. Roadmap Kedepannya

| Phase | Isi | Nilai |
|---|---|---|
| **1 — Fondasi** (spec ini) | Nav config, accordion, fix bug pageTitle & halaman gelap, tooltip custom | Maintenance 1 tempat, struktur siap tumbuh |
| **2 — Live data** | Badge dinamis via `badgeKey`: pending AI review, item checklist belum lengkap, dokumen gagal konversi | Sidebar jadi "kertas kerja", bukan cuma daftar link |
| **3 — Role** | Filter `roles` di config; menu tampil sesuai role dari backend | Prasyarat kalau SaaS dibuka ke user non-admin |
| **4 — Power user** | Pin favorit / pencarian sidebar, lalu `Cmd+K` command palette | Navigasi tetap cepat walau menu 30+; Pendekatan C diadopsi tanpa buang kerja |
