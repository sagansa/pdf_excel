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
    ],
  },
  {
    label: 'HRD',
    items: [
      { title: 'Presences', to: '/hrd', icon: 'bi-calendar-check' },
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
