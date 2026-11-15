# Sidebar Nav Config + Accordion — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Memindahkan definisi menu sidebar ke satu file config, menjadikan section berlabel sebagai accordion, memperbaiki bug judul header & halaman gelap — sesuai spec `docs/superpowers/specs/2026-11-15-sidebar-nav-config-design.md`.

**Architecture:** Data flow satu arah: `src/config/navigation.js` (data murni) → `AppSidebar.vue` (brand, footer akun, state collapse/mobile, state accordion) → `SidebarSection.vue` (render satu section, tanpa state sendiri). `MainLayout.vue` menyederhanakan switch-case `pageTitle` menjadi `route.meta.title`.

**Tech Stack:** Vue 3 (script setup) + vue-router 4 + Tailwind CSS 3 + bootstrap-icons. Tanpa dependency baru.

**Spec:** `docs/superpowers/specs/2026-11-15-sidebar-nav-config-design.md`

## Global Constraints

- Tanpa dependency/package baru — project tidak punya test runner; verifikasi **manual via dev server** sesuai spec section 10.
- Visual: hanya variabel token `--color-*`, `--shadow-soft`, dan pola warna yang sudah ada (mis. `rgba(15, 118, 110, …)` untuk tint primary). Dilarang mengarang warna baru.
- Label menu ditulis apa adanya (campuran bahasa, keputusan user) — teks persis seperti di config Task 2.
- Style scoped yang berpindah komponen: `.app-sidebar`, `.brand-mark`, `.brand-wordmark`, `.sidebar-section-label`, `.sidebar-footer`, `.account-chip`, `.sidebar-item` → pindah ke `AppSidebar.vue`. `.app-header`, `.nav-divider`, `.header-eyebrow`, `.header-icon-button` → tetap di `MainLayout.vue`. `.section-dots` → dihapus.
- Jangan menyentuh file lain yang sedang diubah di working tree (pekerjaan payroll sedang berjalan); commit hanya file yang tercantum per task.
- 16 item menu final: Dashboard, Converter, History & DB, Review Saran AI, Upload Summary, Upload Checklist, HRD Presences, Companies, Marks, Chart of Accounts, Locations & Stores, Financial Reports, Trial Balance, General Ledger, Cek Kontinuitas Saldo, Settings.

---

### Task 1: Judul header dari route meta

**Files:**
- Modify: `admin_frontend/src/router/index.js`
- Modify: `admin_frontend/src/layouts/MainLayout.vue:225-244` (blok switch-case pageTitle)

**Interfaces:**
- Consumes: tidak ada (task pertama).
- Produces: `route.meta.title` bertipe `string` di 17 route aplikasi — dipakai `MainLayout.vue` Task 1 dan tidak lagi oleh siapa pun; Task 2 tidak mengubah mekanisme ini.

- [ ] **Step 1: Tambah `meta.title` ke semua route aplikasi di `router/index.js`**

Pola untuk setiap route (contoh satu route lengkap):

```js
{
  path: '/converter',
  name: 'converter',
  component: ConverterView,
  meta: { title: 'Bank Statement Converter' }
},
```

Nilai `title` untuk semua route aplikasi (route public — `login`, `forgot-password`, `reset-password` — tidak perlu meta):

| name | title |
|---|---|
| `dashboard` | `Dashboard Overview` |
| `converter` | `Bank Statement Converter` |
| `history` | `Transaction History` |
| `companies` | `Company Management` |
| `marks` | `Mark Management` |
| `chart-of-accounts` | `Chart of Accounts` |
| `reports` | `Financial Reports` |
| `upload-summary` | `Upload Summary` |
| `upload-checklist` | `Upload Checklist` |
| `settings` | `System Settings` |
| `management` | `Locations & Stores` |
| `initial-capital` | `Initial Capital` |
| `general-ledger` | `General Ledger` |
| `balance-check` | `Cek Kontinuitas Saldo` |
| `trial-balance` | `Trial Balance` |
| `ai-review` | `Review Saran AI` |
| `hrd` | `HRD Presences` |

- [ ] **Step 2: Ganti switch-case di `MainLayout.vue`**

Hapus seluruh blok `const pageTitle = computed(() => { switch(route.name) { … } })` (baris 225-244) dan ganti dengan:

```js
const pageTitle = computed(() => route.meta.title ?? 'StatementX');
```

- [ ] **Step 3: Verifikasi manual**

```bash
cd /Users/dityo/Codings/saas/esta/admin_frontend && npm run dev
```

Buka `http://localhost:5173`, login, lalu cek header kanan-atas di: `/ai-review` → "Review Saran AI", `/trial-balance` → "Trial Balance", `/balance-check` → "Cek Kontinuitas Saldo" (3 route yang sebelumnya menampilkan "StatementX"). Spot-check 3 halaman lain, mis. `/` → "Dashboard Overview", `/reports` → "Financial Reports", `/settings` → "System Settings".

- [ ] **Step 4: Commit**

```bash
git add admin_frontend/src/router/index.js admin_frontend/src/layouts/MainLayout.vue
git commit -m "fix: judul header sidebar dari route.meta.title + tambal 3 judul halaman hilang"
```

---

### Task 2: Nav config + komponen sidebar (semua mode: expanded, collapsed, mobile)

**Files:**
- Create: `admin_frontend/src/config/navigation.js`
- Create: `admin_frontend/src/components/layout/AppSidebar.vue`
- Create: `admin_frontend/src/components/layout/SidebarSection.vue`
- Modify: `admin_frontend/src/layouts/MainLayout.vue` (buang markup `<aside>` + footer + overlay tetap, buang state/logic/styles yang pindah, render `<AppSidebar/>`)

**Interfaces:**
- Consumes: `route.meta.title` (Task 1) tidak dipakai langsung di sini, tapi perilaku header harus tetap utuh setelah Task 2.
- Produces:
  - `navigation`: `Array<{ label: string|null, items: Array<{ title: string, to: string, icon: string, badgeKey?: string, roles?: string[]|null }> }>` dari `config/navigation.js`.
  - `isRouteActive(to: string, currentPath: string): boolean` dari `config/navigation.js` — exact match `currentPath === to`.
  - Props `AppSidebar`: `collapsed: Boolean`, `mobileOpen: Boolean`, `isDesktop: Boolean`; emit `close-mobile`.
  - Props `SidebarSection`: `section: Object`, `expanded: Boolean`, `collapsed: Boolean`; emit `toggle`, `close-mobile`.

- [ ] **Step 1: Buat `admin_frontend/src/config/navigation.js`**

```js
// Single source of truth menu sidebar (spec: docs/superpowers/specs/2026-11-15-sidebar-nav-config-design.md).
// label: null  -> item di-render langsung sebagai top-level (dengan ikon)
// label: '...' -> section accordion (ikon representasi = ikon item pertama)
// badgeKey / roles hanya skema — belum dirender (fase 2 & 3 spec).
export const navigation = [
  {
    label: null,
    items: [
      { title: 'Dashboard', to: '/', icon: 'bi-grid-fill' },
      { title: 'Converter', to: '/converter', icon: 'bi-file-earmark-medical' },
      { title: 'History & DB', to: '/history', icon: 'bi-database-fill' },
      { title: 'Review Saran AI', to: '/ai-review', icon: 'bi-stars' },
      { title: 'Upload Summary', to: '/upload-summary', icon: 'bi-file-check-fill' },
      { title: 'Upload Checklist', to: '/upload-checklist', icon: 'bi-check2-square' },
      { title: 'HRD Presences', to: '/hrd', icon: 'bi-calendar-check' },
    ],
  },
  {
    label: 'Management',
    items: [
      { title: 'Companies', to: '/companies', icon: 'bi-building' },
      { title: 'Marks', to: '/marks', icon: 'bi-tags-fill' },
      { title: 'Chart of Accounts', to: '/chart-of-accounts', icon: 'bi-journal-text' },
      { title: 'Locations & Stores', to: '/management', icon: 'bi-geo-alt' },
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
  {
    label: null,
    items: [
      { title: 'Settings', to: '/settings', icon: 'bi-gear' },
    ],
  },
];

// Exact-match: semua route aplikasi flat, tidak ada nesting path.
// (Menggantikan active-class prefix bawaan router-link yang membuat '/' aktif di semua halaman.)
export const isRouteActive = (to, currentPath) => currentPath === to;
```

- [ ] **Step 2: Buat `admin_frontend/src/components/layout/SidebarSection.vue`**

```vue
<template>
  <!-- Section tanpa label: item langsung, gaya top-level -->
  <template v-if="!section.label">
    <router-link
      v-for="item in section.items"
      :key="item.to"
      :to="item.to"
      class="sidebar-item"
      :class="{ active: isRouteActive(item.to, route.path) }"
      :data-tip="item.title"
      @click="$emit('close-mobile')"
    >
      <i class="bi text-lg flex-shrink-0" :class="item.icon"></i>
      <span v-if="!collapsed" class="ml-3 font-medium">{{ item.title }}</span>
    </router-link>
  </template>

  <!-- Section berlabel: accordion -->
  <div v-else class="nav-section-labeled">
    <button
      type="button"
      class="sidebar-item sidebar-section-toggle"
      :aria-expanded="expanded && !collapsed"
      :aria-controls="sectionId"
      :data-tip="section.label"
      @click="onToggle"
    >
      <i class="bi text-lg flex-shrink-0" :class="section.items[0].icon"></i>
      <template v-if="!collapsed">
        <span class="ml-3 font-medium flex-1 text-left">{{ section.label }}</span>
        <i
          class="bi text-xs transition-transform duration-200"
          :class="expanded ? 'bi-chevron-down' : 'bi-chevron-right'"
        ></i>
      </template>
      <i v-else class="bi bi-chevron-right text-[10px] text-muted"></i>
    </button>

    <ul v-show="expanded && !collapsed" :id="sectionId" class="nav-sub-list space-y-1">
      <li v-for="item in section.items" :key="item.to">
        <router-link
          :to="item.to"
          class="sidebar-item sidebar-sub-item"
          :class="{ active: isRouteActive(item.to, route.path) }"
          @click="$emit('close-mobile')"
        >
          <span class="font-medium">{{ item.title }}</span>
        </router-link>
      </li>
    </ul>

    <!-- Flyout saat collapsed (desktop) — terbuka via :hover / :focus-within, lihat CSS -->
    <div v-if="collapsed" class="sidebar-flyout" :aria-label="section.label">
      <p class="sidebar-section-label px-2 pb-2">{{ section.label }}</p>
      <router-link
        v-for="item in section.items"
        :key="item.to"
        :to="item.to"
        class="sidebar-item sidebar-flyout-item"
        :class="{ active: isRouteActive(item.to, route.path) }"
        @click="$emit('close-mobile')"
      >
        <span class="font-medium">{{ item.title }}</span>
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useRoute } from 'vue-router';
import { isRouteActive } from '../../config/navigation';

const props = defineProps({
  section: { type: Object, required: true },
  expanded: { type: Boolean, default: false },
  collapsed: { type: Boolean, default: false },
});

const emit = defineEmits(['toggle', 'close-mobile']);

const route = useRoute();

const sectionId = computed(() =>
  `nav-section-${String(props.section.label || '').toLowerCase().replace(/\s+/g, '-')}`
);

const onToggle = () => {
  if (!props.collapsed) {
    emit('toggle');
  }
  // Saat collapsed, klik tidak melipat — flyout muncul via hover/focus (CSS).
};
</script>
```

- [ ] **Step 3: Buat `admin_frontend/src/components/layout/AppSidebar.vue`**

```vue
<template>
  <aside
    class="app-sidebar flex flex-col h-full z-50 transition-all duration-300 ease-in-out transform lg:translate-x-0"
    :class="[
      isDesktop
        ? 'static translate-x-0'
        : (mobileOpen ? 'fixed translate-x-0' : '-translate-x-full fixed'),
      collapsed && isDesktop ? 'w-20 sidebar-collapsed' : 'w-64'
    ]"
  >
    <div class="px-5 py-5 mb-4 flex items-center gap-3 overflow-hidden whitespace-nowrap">
      <div class="brand-mark flex-shrink-0">
        <i class="bi bi-lightning-fill text-xl"></i>
      </div>
      <span
        class="text-xl font-bold brand-wordmark transition-opacity duration-300"
        :class="{ 'opacity-0 w-0': collapsed && isDesktop, 'opacity-100': !(collapsed && isDesktop) }"
      >StatementX</span>
    </div>

    <nav class="flex-1 px-3 pb-4 space-y-1 overflow-x-hidden overflow-y-auto">
      <SidebarSection
        v-for="(section, index) in navigation"
        :key="index"
        :section="section"
        :expanded="expandedSections.has(index)"
        :collapsed="collapsed && isDesktop"
        @toggle="toggleSection(index)"
        @close-mobile="$emit('close-mobile')"
      />
    </nav>

    <div class="p-4 border-t sidebar-footer overflow-hidden">
      <div class="surface-card-muted rounded-2xl p-4 flex items-center gap-3">
        <div class="account-chip flex-shrink-0">{{ userInitials }}</div>
        <div class="overflow-hidden transition-opacity duration-300" :class="{ 'opacity-0 w-0 hidden': collapsed && isDesktop }">
          <p class="text-xs font-bold text-theme truncate">{{ auth.user?.display_name || 'Admin' }}</p>
          <p class="text-[10px] text-muted uppercase tracking-[0.18em] truncate">{{ auth.user?.email || '' }}</p>
        </div>
        <button
          class="ml-auto flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center text-muted hover:text-theme hover:bg-black/5 dark:hover:bg-white/10 transition-colors"
          :class="{ 'opacity-0 w-0 hidden': collapsed && isDesktop }"
          title="Logout"
          :disabled="isLoggingOut"
          @click="handleLogout"
        >
          <i class="bi bi-box-arrow-right"></i>
        </button>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '../../stores/auth';
import { navigation, isRouteActive } from '../../config/navigation';
import SidebarSection from './SidebarSection.vue';

const props = defineProps({
  collapsed: { type: Boolean, default: false },
  mobileOpen: { type: Boolean, default: false },
  isDesktop: { type: Boolean, default: false },
});

const emit = defineEmits(['close-mobile']);

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const isLoggingOut = ref(false);

const userInitials = computed(() => {
  const name = auth.user?.display_name || auth.user?.email || 'A';
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join('');
});

const handleLogout = async () => {
  isLoggingOut.value = true;
  try {
    await auth.logout();
    router.push('/login');
  } finally {
    isLoggingOut.value = false;
  }
};

// Auto-open: section yang berisi item aktif selalu terbuka saat route berubah
// (termasuk deep-link). Section yang tidak relevan tidak pernah ditutup otomatis —
// keputusan manual user dihormati sampai dia sendiri menutupnya.
const expandedSections = ref(new Set());

const toggleSection = (index) => {
  const next = new Set(expandedSections.value);
  if (next.has(index)) {
    next.delete(index);
  } else {
    next.add(index);
  }
  expandedSections.value = next;
};

watch(
  () => route.path,
  () => {
    const next = new Set(expandedSections.value);
    navigation.forEach((section, index) => {
      if (section.label && section.items.some((item) => isRouteActive(item.to, route.path))) {
        next.add(index);
      }
    });
    expandedSections.value = next;
  },
  { immediate: true }
);
</script>

<style scoped>
.app-sidebar {
    background: var(--color-panel);
    border-right: 1px solid var(--color-border);
    backdrop-filter: blur(14px);
}

.brand-mark {
    @apply flex h-11 w-11 items-center justify-center rounded-2xl text-white;
    background: linear-gradient(135deg, var(--color-primary), var(--color-primary-strong));
    box-shadow: 0 16px 32px rgba(15, 118, 110, 0.22);
}

.brand-wordmark {
    background: linear-gradient(135deg, var(--color-text), var(--color-text-muted));
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
}

.sidebar-section-label {
    @apply text-[10px] font-bold uppercase tracking-[0.24em];
    color: var(--color-text-muted);
}

.sidebar-footer {
    border-color: var(--color-border);
}

.account-chip {
    @apply flex h-9 w-9 items-center justify-center rounded-full text-xs font-bold;
    background: rgba(15, 118, 110, 0.12);
    color: var(--color-primary);
}

.sidebar-item {
    @apply mb-1 flex items-center rounded-2xl px-3 py-2.5 transition-all duration-200 cursor-pointer relative;
    color: var(--color-text-muted);
}

.sidebar-item:hover {
    background: var(--color-surface-muted);
    color: var(--color-primary);
}

.sidebar-item.active {
    @apply font-semibold;
    background: rgba(15, 118, 110, 0.12);
    color: var(--color-primary);
    border: 1px solid rgba(15, 118, 110, 0.18);
    box-shadow: var(--shadow-soft);
}

/* Accordion */
.sidebar-section-toggle {
    @apply w-full appearance-none bg-transparent border-0;
}

.nav-sub-list {
    margin-left: 14px;
    padding-left: 12px;
    border-left: 1px solid var(--color-border);
}

.sidebar-sub-item {
    @apply px-3 py-2 text-sm;
}

/* Mode collapsed */
.sidebar-collapsed .sidebar-item {
    justify-content: center;
}

.sidebar-collapsed .sidebar-item:hover::after,
.sidebar-collapsed .sidebar-item:focus-visible::after {
    content: attr(data-tip);
    position: absolute;
    left: calc(100% + 10px);
    top: 50%;
    transform: translateY(-50%);
    @apply px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap pointer-events-none;
    background: var(--color-panel-strong);
    color: var(--color-text);
    border: 1px solid var(--color-border);
    box-shadow: var(--shadow-soft);
    z-index: 60;
}

.nav-section-labeled {
    position: relative;
}

.sidebar-flyout {
    display: none;
    position: absolute;
    left: calc(100% + 10px);
    top: 0;
    min-width: 220px;
    @apply rounded-2xl p-3;
    background: var(--color-panel-strong);
    border: 1px solid var(--color-border);
    box-shadow: var(--shadow-soft);
    z-index: 60;
}

.sidebar-collapsed .nav-section-labeled:hover .sidebar-flyout,
.sidebar-collapsed .nav-section-labeled:focus-within .sidebar-flyout {
    display: block;
}

.sidebar-flyout-item {
    @apply text-sm px-3 py-2;
    color: var(--color-text-muted);
}
</style>
```

- [ ] **Step 4: Rewire `MainLayout.vue`**

Di template:

1. Ganti seluruh blok `<aside class="app-sidebar …">…</aside>` (baris 4-146) dengan:

```html
    <!-- Sidebar -->
    <AppSidebar
        :collapsed="isSidebarCollapsed"
        :mobile-open="isSidebarOpenMobile"
        :is-desktop="isDesktop"
        @close-mobile="isSidebarOpenMobile = false"
    />
```

2. Overlay mobile (baris 148-153) **tetap ada** di `MainLayout` — tidak berubah.

Di `<script setup>`:

3. Hapus import `useAuthStore`, `auth`, `isLoggingOut`, `userInitials`, `handleLogout`, `closeMobileSidebar` — semuanya pindah ke `AppSidebar`. Import yang ditambah:

```js
import AppSidebar from '../components/layout/AppSidebar.vue';
```

4. State yang tetap di MainLayout (tidak berubah dari sekarang): `isSidebarCollapsed`, `isSidebarOpenMobile`, `isDesktop`, `route`, `pageTitle` (dari Task 1), `syncViewportState`, `toggleSidebarControl`, `onMounted`/`onBeforeUnmount`.

Di `<style scoped>`:

5. Hapus rule yang pindah/digugurkan: `.app-sidebar`, `.brand-mark`, `.brand-wordmark`, `.sidebar-section-label`, `.section-dots`, `.sidebar-footer`, `.account-chip`, `.sidebar-item`, `.sidebar-item:hover`, `.sidebar-item.active`.
6. Pertahankan: `.app-header`, `.nav-divider`, `.header-eyebrow`, `.header-icon-button`.

- [ ] **Step 5: Verifikasi manual — expanded mode**

Dev server masih jalan (`npm run dev`). Checklist:

1. Sidebar ter-render dengan 16 item; Management & Reports tampil sebagai accordion (klik label → buka/tutup, chevron berputar).
2. HRD Presences dan Settings tampil sebagai item biasa tanpa label section.
3. Klik "Trial Balance" → section Reports terbuka, item aktif ter-highlight; Dashboard TIDAK ikut ter-highlight (exact-match, bukan prefix).
4. Deep-link: paste langsung `http://localhost:5173/general-ledger` → sidebar terbuka dengan Reports expanded & General Ledger aktif (halaman yang sebelumnya tidak bisa diakses dari UI).
5. Logout dari footer sidebar tetap berfungsi → kembali ke `/login`.

- [ ] **Step 6: Verifikasi manual — collapsed & mobile**

1. Desktop: klik tombol toggle di header → sidebar menyusut jadi icon-only; hover ikon apa pun → tooltip custom muncul di kanan (bukan tooltip kuning browser); hover ikon Management/Reports → flyout berisi item section muncul; klik item di flyout → navigasi jalan.
2. Klik toggle lagi → kembali expanded, state accordion konsisten (Reports tetap terbuka bila item aktifnya Reports).
3. Sempitkan jendela < 1024px (atau device toolbar) → ikon toggle jadi hamburger, sidebar overlay dengan latar gelap; klik item mana pun → sidebar menutup dan navigasi jalan.
4. Dark mode: ulang langkah 1-3 dengan tema gelap — tooltip/flyout/accordion ikut token tema.

- [ ] **Step 7: Commit**

```bash
git add admin_frontend/src/config/navigation.js admin_frontend/src/components/layout/AppSidebar.vue admin_frontend/src/components/layout/SidebarSection.vue admin_frontend/src/layouts/MainLayout.vue
git commit -m "feat: sidebar render dari nav config tunggal + accordion section, tooltip & flyout mode collapsed"
```

---

### Task 3: Verifikasi akhir terhadap checklist spec

**Files:**
- Modify: hanya bila verifikasi menemukan cacat — perbaiki di file terkait Task 1/2.

**Interfaces:**
- Consumes: seluruh hasil Task 1 & 2.
- Produces: keputusan go/no-go; tidak ada interface baru.

- [ ] **Step 1: Jalankan checklist lengkap spec section 10**

Dev server jalan. Periksa satu per satu, centang bila lolos:

1. Semua 16 item menu ter-render dan bisa dinavigasi dari sidebar (15 item lama + General Ledger).
2. Active state benar di tiap halaman, termasuk General Ledger (sebelumnya tidak punya highlight).
3. Accordion auto-open saat deep-link langsung ke `/trial-balance`.
4. Collapse/expand desktop smooth; tooltip muncul di semua item collapsed.
5. Mobile overlay buka/tutup, item klik menutup sidebar.
6. Dark mode tetap konsisten (token `--color-*`).
7. Header title benar di semua halaman termasuk `ai-review`, `trial-balance`, `balance-check`.

- [ ] **Step 2: Bila ada cacat**

Perbaiki di file Task 1/2 yang terkait, ulangi langkah verifikasi yang gagal, lalu commit perbaikan:

```bash
git add -A admin_frontend/src/config admin_frontend/src/components/layout admin_frontend/src/layouts admin_frontend/src/router
git commit -m "fix: perbaikan hasil verifikasi akhir sidebar"
```

- [ ] **Step 3: Bila semua lolos**

Laporkan ringkas ke user: checklist 7 poin ✅, commit yang sudah dibuat, dan sisa roadmap (badge dinamis → roles → command palette) menunggu fase berikutnya. Tidak ada commit tambahan.

---

## Self-Review (sudah dijalankan saat penulisan)

1. **Spec coverage:** meta.title (spec §7) → Task 1; nav config + accordion + auto-open + a11y (§5, §6) → Task 2; collapsed tooltip & flyout (§8) → Task 2; mobile & dark mode (§8) → Task 2 Step 6 & Task 3; checklist testing (§10) → Task 3; badgeKey/roles skema-only (§5) → ada di config Task 2, tidak dirender; `/initial-capital` out of scope (§11) → tidak disentuh. ✅
2. **Placeholder scan:** tidak ada TBD/TODO/"similar to"; semua langkah kode berisi kode lengkap. ✅
3. **Type consistency:** `navigation` + `isRouteActive(to, currentPath)` didefinisikan Task 2 Step 1 dan dipakai identik di Step 2 & 3; props/emit `AppSidebar`↔`MainLayout` dan `SidebarSection`↔`AppSidebar` konsisten. ✅
