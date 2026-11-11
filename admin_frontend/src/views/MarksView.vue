<template>
  <div class="max-w-6xl mx-auto space-y-6">
    <PageHeader
      title="Transaction classification rules"
      subtitle="Definisikan mark untuk kategorisasi transaksi dan mapping COA."
    >
      <template #actions>
        <span class="stat-pill">
          <i class="bi bi-tags-fill"></i>
          {{ totalMarks }} marks
        </span>
        <span class="stat-pill">
          <i class="bi bi-tag"></i>
          {{ unmappedCount }} tanpa mapping
        </span>
        <span class="stat-pill stat-pill--mono">Real {{ realMappedCount }}/{{ totalMarks }}</span>
        <span class="stat-pill stat-pill--mono">Coretax {{ coretaxMappedCount }}/{{ totalMarks }}</span>
        <button @click="openAddModal" class="btn-primary gap-2 min-h-[44px] px-5">
          <i class="bi bi-plus-lg"></i>
          <span>Add New Mark</span>
        </button>
      </template>
    </PageHeader>

    <TableShell>
      <template #toolbar>
        <div class="marks-toolbar">
          <div class="ui-input-shell marks-search">
            <span class="ui-input-shell__icon"><i class="bi bi-search"></i></span>
            <input
              v-model="searchQuery"
              type="search"
              class="marks-search__input"
              placeholder="Cari mark…"
              aria-label="Cari mark"
            />
            <button
              v-if="searchQuery"
              @click="searchQuery = ''"
              class="ui-clear-button"
              aria-label="Hapus pencarian"
            >
              <i class="bi bi-x-lg"></i>
            </button>
          </div>

          <div class="marks-filters" role="group" aria-label="Filter mark">
            <button
              v-for="filter in FILTERS"
              :key="filter.key"
              type="button"
              class="filter-chip"
              :class="{ 'filter-chip--active': activeFilter === filter.key }"
              :aria-pressed="activeFilter === filter.key ? 'true' : 'false'"
              @click="activeFilter = filter.key"
            >
              {{ filter.label }}
              <span v-if="filter.key === 'unmapped' && unmappedCount > 0" class="filter-chip__count">{{ unmappedCount }}</span>
            </button>
          </div>

          <select
            v-model="activeFiscal"
            class="fiscal-select"
            aria-label="Filter kategori fiskal"
          >
            <option value="">Semua fiskal</option>
            <option v-for="fiscal in FISCAL_FILTERS" :key="fiscal.key" :value="fiscal.key">
              {{ fiscal.label }}
            </option>
          </select>

          <span v-if="isFiltering" class="marks-toolbar__meta">
            {{ visibleMarks.length }} dari {{ totalMarks }} mark
          </span>
        </div>
      </template>

      <table class="min-w-full w-full marks-table">
        <thead>
          <tr>
            <th class="marks-table__chevron-col" aria-hidden="true"></th>
            <th>Rule</th>
            <th>Traits</th>
            <th>Mapping COA</th>
            <th class="marks-table__actions-col text-right">Aksi</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="store.isLoading">
            <td colspan="5" class="marks-table__state">
              <span class="spinner-border w-6 h-6" style="color: var(--color-primary)" role="status"></span>
            </td>
          </tr>

          <tr v-else-if="store.error">
            <td colspan="5" class="marks-table__state">
              <span class="text-danger text-sm font-medium">Gagal memuat marks: {{ store.error }}</span>
              <button type="button" class="btn-secondary !py-1.5 !px-3 text-xs" @click="store.fetchMarks()">
                <i class="bi bi-arrow-clockwise mr-1"></i> Coba lagi
              </button>
            </td>
          </tr>

          <tr v-else-if="store.marks.length === 0">
            <td colspan="5" class="marks-table__state">
              <i class="bi bi-tags marks-table__state-icon" aria-hidden="true"></i>
              <p class="text-sm font-semibold text-theme">Belum ada mark</p>
              <p class="text-xs text-muted mt-1">Buat mark pertama untuk mulai mengklasifikasi transaksi.</p>
              <button type="button" class="btn-primary !py-1.5 !px-3 text-xs mt-3" @click="openAddModal">
                <i class="bi bi-plus-lg mr-1"></i> Buat Mark
              </button>
            </td>
          </tr>

          <tr v-else-if="visibleMarks.length === 0">
            <td colspan="5" class="marks-table__state">
              <i class="bi bi-search marks-table__state-icon" aria-hidden="true"></i>
              <p class="text-sm font-semibold text-theme">Tidak ada mark yang cocok</p>
              <p class="text-xs text-muted mt-1">Ubah kata kunci atau filter, lalu coba lagi.</p>
              <button type="button" class="btn-secondary !py-1.5 !px-3 text-xs mt-3" @click="clearFilters">
                <i class="bi bi-x-lg mr-1"></i> Hapus pencarian &amp; filter
              </button>
            </td>
          </tr>

          <template v-else>
            <template v-for="m in visibleMarks" :key="m.id">
              <tr
                class="mark-row"
                :class="{ 'mark-row--open': expandedId === m.id, 'mark-row--unmapped': isMarkUnmapped(m) }"
                @click="toggleExpand(m)"
              >
                <td class="marks-table__chevron-col">
                  <button
                    type="button"
                    class="mark-expand"
                    :class="{ 'mark-expand--open': expandedId === m.id }"
                    :aria-expanded="expandedId === m.id ? 'true' : 'false'"
                    :aria-controls="`mark-detail-${m.id}`"
                    :aria-label="expandedId === m.id ? `Tutup detail ${m.internal_report}` : `Buka detail ${m.internal_report}`"
                    @click.stop="toggleExpand(m)"
                  >
                    <i class="bi bi-chevron-down"></i>
                  </button>
                </td>
                <td class="mark-row__names-cell">
                  <div class="mark-row__names">
                    <div class="mark-row__internal">
                      <span class="mark-row__internal-name">{{ m.internal_report }}</span>
                      <span v-if="isMarkUnmapped(m)" class="mark-row__unmapped-tag">Tanpa mapping</span>
                    </div>
                    <span v-if="m.personal_use" class="mark-row__personal">{{ m.personal_use }}</span>
                  </div>
                </td>
                <td>
                  <MarkTraitChips :mark="m" show-fiscal-inherit />
                </td>
                <td class="mark-row__mapping-cell">
                  <template v-if="expandedId !== m.id">
                    <MarkMappingChips label="Real" :mappings="getRealMappings(m)" />
                    <MarkMappingChips label="Coretax" :mappings="getCoretaxMappings(m)" />
                  </template>
                </td>
                <td class="marks-table__actions-col">
                  <button @click.stop="openEditModal(m)" class="action-link action-link--primary" aria-label="Edit mark">
                    <i class="bi bi-pencil-square"></i>
                  </button>
                  <button @click.stop="deleteMark(m.id)" class="action-link action-link--danger" aria-label="Hapus mark">
                    <i class="bi bi-trash3"></i>
                  </button>
                </td>
              </tr>

              <Transition name="band">
                <tr v-if="expandedId === m.id" class="mark-band-row">
                  <td colspan="5" class="mark-band-cell">
                    <div :id="`mark-detail-${m.id}`" class="band-wrap" role="region" :aria-label="`Detail mark ${m.internal_report}`">
                      <div class="band-clip">
                        <div class="band">
                          <div class="band__flags">
                            <span class="band__label">Flags</span>
                            <MarkFlagSwitch
                              v-for="flag in FLAGS"
                              :key="flag.key"
                              :model-value="Boolean(m[flag.key])"
                              :label="flag.label"
                              :loading="isToggleLoading(m.id, flag.key)"
                              @update:model-value="toggleMarkFlag(m, flag.key)"
                            />
                          </div>
                          <MarkMappingGroup label="Real" :mappings="getRealMappings(m)" />
                          <MarkMappingGroup label="Coretax" :mappings="getCoretaxMappings(m)" />
                        </div>
                        <div class="band__footer">
                          <span class="band__impact" :class="{ 'band__impact--muted': impactAreas(m).length === 0 }">
                            <i :class="impactAreas(m).length > 0 ? 'bi bi-diagram-3' : 'bi bi-slash-circle'"></i>
                            {{ impactAreas(m).length > 0 ? 'Dipakai di: ' + impactAreas(m).join(' · ') : 'Tanpa mapping COA — tidak tampil di laporan.' }}
                          </span>
                          <span class="band__footer-actions">
                            <button type="button" class="mark-coa-button" @click.stop="openMappingModal(m)">
                              <i class="bi bi-link-45deg"></i> Kelola COA
                            </button>
                            <button type="button" class="mark-edit-button" @click.stop="openEditModal(m)">
                              <i class="bi bi-pencil-square"></i> Edit
                            </button>
                          </span>
                        </div>
                      </div>
                    </div>
                  </td>
                </tr>
              </Transition>
            </template>
          </template>
        </tbody>
      </table>
    </TableShell>

    <MarkFormModal
        :isOpen="showModal"
        :markToEdit="selectedMark"
        @close="showModal = false"
        @saved="handleMarkSaved"
    />

    <CoaMappingModal
        :isOpen="showMappingModal"
        :mark="selectedMarkForMapping"
        @close="showMappingModal = false"
        @updated="handleMappingUpdated"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { useMarksStore } from '../stores/marks';
import { useNotifications } from '../composables/useNotifications';
import { getRealMappings, getCoretaxMappings, isMarkUnmapped, getMarkImpactAreas } from '../utils/marks';
import MarkFormModal from '../components/marks/MarkFormModal.vue';
import CoaMappingModal from '../components/marks/CoaMappingModal.vue';
import MarkTraitChips from '../components/marks/MarkTraitChips.vue';
import MarkMappingChips from '../components/marks/MarkMappingChips.vue';
import MarkMappingGroup from '../components/marks/MarkMappingGroup.vue';
import MarkFlagSwitch from '../components/marks/MarkFlagSwitch.vue';
import PageHeader from '../components/ui/PageHeader.vue';
import TableShell from '../components/ui/TableShell.vue';

const store = useMarksStore();
const notify = useNotifications();

const FILTERS = [
  { key: 'all', label: 'Semua' },
  { key: 'unmapped', label: 'Tanpa Mapping' },
  { key: 'is_salary_component', label: 'Gaji' },
  { key: 'is_rental', label: 'Sewa' },
  { key: 'is_asset', label: 'Aset' },
  { key: 'is_service', label: 'Jasa' }
];

const FISCAL_FILTERS = [
  { key: 'DEDUCTIBLE', label: 'Deductible' },
  { key: 'NON_DEDUCTIBLE', label: 'Non-Deductible' },
  { key: 'NON_TAXABLE_INCOME', label: 'Non-Taxable' }
];

const FLAGS = [
  { key: 'is_coretax', label: 'Coretax' },
  { key: 'is_asset', label: 'Aset' },
  { key: 'is_service', label: 'Jasa' },
  { key: 'is_salary_component', label: 'Salary' },
  { key: 'is_rental', label: 'Sewa Tempat' }
];

const showModal = ref(false);
const selectedMark = ref(null);
const showMappingModal = ref(false);
const selectedMarkForMapping = ref(null);
const togglingFlags = reactive({});
const expandedId = ref(null);
const searchQuery = ref('');
const activeFilter = ref('all');
const activeFiscal = ref('');

const marks = computed(() => store.sortedMarks || []);
const totalMarks = computed(() => marks.value.length);
const unmappedCount = computed(() => marks.value.filter(isMarkUnmapped).length);
const realMappedCount = computed(() => marks.value.filter((m) => getRealMappings(m).length > 0).length);
const coretaxMappedCount = computed(() => marks.value.filter((m) => getCoretaxMappings(m).length > 0).length);

const isFiltering = computed(() => (
  searchQuery.value.trim() !== '' || activeFilter.value !== 'all' || activeFiscal.value !== ''
));

const visibleMarks = computed(() => marks.value.filter((mark) => {
  const query = searchQuery.value.trim().toLowerCase();
  if (query) {
    const haystack = `${mark.internal_report || ''} ${mark.personal_use || ''}`.toLowerCase();
    if (!haystack.includes(query)) return false;
  }
  if (activeFilter.value === 'unmapped') {
    if (!isMarkUnmapped(mark)) return false;
  } else if (activeFilter.value !== 'all' && !Boolean(mark[activeFilter.value])) {
    return false;
  }
  if (activeFiscal.value) {
    const fiscal = String(mark.fiscal_category || '');
    if (activeFiscal.value === 'NON_DEDUCTIBLE') {
      if (!fiscal.startsWith('NON_DEDUCTIBLE')) return false;
    } else if (fiscal !== activeFiscal.value) {
      return false;
    }
  }
  return true;
}));

const impactAreas = (mark) => getMarkImpactAreas(mark);

const toggleExpand = (mark) => {
  expandedId.value = expandedId.value === mark.id ? null : mark.id;
};

const getToggleKey = (markId, flagKey) => `${markId}:${flagKey}`;

const isToggleLoading = (markId, flagKey) => Boolean(togglingFlags[getToggleKey(markId, flagKey)]);

const toggleMarkFlag = async (mark, flagKey) => {
  const toggleKey = getToggleKey(mark.id, flagKey);
  if (togglingFlags[toggleKey]) return;

  togglingFlags[toggleKey] = true;
  try {
    await store.updateMarkFlag(mark.id, flagKey, !Boolean(mark[flagKey]));
  } catch (error) {
    notify.error('Gagal update status mark: ' + (error.response?.data?.error || error.message));
  } finally {
    delete togglingFlags[toggleKey];
  }
};

const clearFilters = () => {
  searchQuery.value = '';
  activeFilter.value = 'all';
  activeFiscal.value = '';
};

const openAddModal = () => {
    selectedMark.value = null;
    showModal.value = true;
};

const openEditModal = async (mark) => {
    // First refresh the marks data to ensure we have the latest from database
    await store.fetchMarks();
    // Then get the fresh mark data from the refreshed store
    const freshMark = store.marks.find(m => m.id === mark.id);
    selectedMark.value = freshMark;
    showModal.value = true;
};

const openMappingModal = (mark) => {
    selectedMarkForMapping.value = mark;
    showMappingModal.value = true;
};

const handleMappingUpdated = async () => {
    // Refresh marks to show new mappings
    await store.fetchMarks();
};

const handleMarkSaved = async () => {
    // Refresh marks to show updated data
    await store.fetchMarks();
    showModal.value = false;
};

const deleteMark = async (id) => {
    if (confirm('Are you sure you want to delete this mark?')) {
        try {
            await store.deleteMark(id);
            if (expandedId.value === id) expandedId.value = null;
            notify.success('Mark dihapus.');
        } catch (error) {
            notify.error('Gagal menghapus mark: ' + (error.response?.data?.error || error.message));
        }
    }
};

onMounted(() => {
    store.fetchMarks();
});
</script>

<style scoped>
/* ---- header pills ---- */
.stat-pill--mono {
  font-family: var(--font-mono);
  font-size: 11px;
}

/* ---- toolbar ---- */
.marks-toolbar {
  @apply flex w-full flex-wrap items-center gap-3;
}

.marks-search {
  @apply w-full lg:w-64 shrink-0;
}

.marks-search__input {
  @apply w-full bg-transparent py-1.5 pl-10 pr-8 text-sm outline-none;
  color: var(--color-text);
}

.marks-search__input::placeholder {
  color: var(--color-text-muted);
}

.marks-filters {
  @apply flex flex-wrap items-center gap-1.5;
}

.marks-filters__label {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--color-text-muted);
  margin-right: 2px;
}

.filter-chip {
  @apply inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold transition-colors;
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
  color: var(--color-text-muted);
}

.filter-chip:hover {
  border-color: var(--color-border-strong);
  color: var(--color-text);
}

.filter-chip--active {
  background: color-mix(in srgb, var(--color-primary) 12%, transparent);
  border-color: color-mix(in srgb, var(--color-primary) 35%, transparent);
  color: var(--color-primary);
}

.filter-chip:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.filter-chip__count {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 700;
}

.marks-toolbar__meta {
  @apply ml-auto shrink-0 text-xs;
  font-family: var(--font-mono);
  color: var(--color-text-muted);
}

.fiscal-select {
  @apply shrink-0 rounded-xl pl-3 py-1.5 text-xs font-semibold cursor-pointer transition-colors;
  appearance: none;
  -webkit-appearance: none;
  padding-right: 32px;
  background-color: var(--color-surface-raised);
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath d='M2.5 4.5L6 8l3.5-3.5' fill='none' stroke='%23667085' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 10px center;
  border: 1px solid var(--color-border);
  color: var(--color-text);
}

.fiscal-select:hover {
  border-color: var(--color-border-strong);
}

.fiscal-select:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

/* ---- table ---- */
.marks-table {
  min-width: 1020px;
}

.marks-table thead th {
  @apply px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider;
  color: var(--color-text-muted);
  background: var(--color-surface-muted);
  border-bottom: 1px solid var(--color-border);
}

.marks-table tbody td {
  @apply px-4 py-3 text-sm align-middle;
  border-bottom: 1px solid var(--color-border);
}

.marks-table__chevron-col {
  @apply w-10 pr-0;
}

.marks-table__actions-col {
  @apply w-24 text-right;
}

.mark-row {
  cursor: pointer;
  transition: background-color 160ms ease;
}

.mark-row:hover td {
  background: color-mix(in srgb, var(--color-primary) 4%, transparent);
}

.mark-row--open td,
.mark-row--open:hover td {
  background: color-mix(in srgb, var(--color-primary) 6%, transparent);
  border-bottom-color: transparent;
}

.mark-expand {
  @apply inline-flex h-7 w-7 items-center justify-center rounded-lg transition-all duration-200;
  background: transparent;
  border: 1px solid transparent;
  color: var(--color-text-muted);
}

.mark-expand:hover {
  background: var(--color-surface-muted);
  border-color: var(--color-border);
  color: var(--color-text);
}

.mark-expand:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.mark-expand i {
  transition: transform 200ms cubic-bezier(0.22, 1, 0.36, 1);
}

.mark-expand--open i {
  transform: rotate(180deg);
}

.mark-row__names-cell {
  min-width: 220px;
}

.mark-row__names {
  @apply flex flex-col gap-0.5 min-w-0;
}

.mark-row__internal {
  @apply text-sm font-bold;
  color: var(--color-text);
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.mark-row__internal-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.mark-row__mapping-cell {
  min-width: 330px;
}

.mark-row__unmapped-tag {
  @apply inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-[11px] font-semibold;
  background: transparent;
  border: 1px dashed var(--color-border-strong);
  color: var(--color-text-muted);
  white-space: nowrap;
}

.mark-row__personal {
  @apply text-xs truncate;
  color: var(--color-text-muted);
}

.marks-table__state {
  @apply py-10 text-center;
}

.marks-table__state .btn-primary,
.marks-table__state .btn-secondary {
  @apply inline-flex;
}

.marks-table__state-icon {
  @apply mb-2 block text-2xl;
  color: var(--color-text-muted);
}

/* ---- expansion band: the one authored motion moment ---- */
.band-wrap {
  display: grid;
  grid-template-rows: 1fr;
}

.band-clip {
  min-height: 0;
  overflow: hidden;
}

.band-enter-active .band-wrap {
  transition: grid-template-rows 260ms cubic-bezier(0.22, 1, 0.36, 1);
}

.band-leave-active .band-wrap {
  transition: grid-template-rows 220ms cubic-bezier(0.22, 1, 0.36, 1);
}

.band-enter-from .band-wrap,
.band-leave-to .band-wrap {
  grid-template-rows: 0fr;
}

.band-enter-active .band-clip,
.band-leave-active .band-clip {
  transition: opacity 180ms ease;
}

.band-enter-from .band-clip,
.band-leave-to .band-clip {
  opacity: 0;
}

.mark-band-row td {
  padding: 0 !important;
  background: var(--color-surface-muted);
}

.band {
  @apply grid gap-6 px-5 pt-4 pb-3;
  grid-template-columns: 240px 1fr 1fr;
  border-bottom: 1px solid var(--color-border);
}

.band__flags {
  @apply flex flex-col gap-2.5;
}

.band__label {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--color-text-muted);
}

.band__footer {
  @apply flex flex-col gap-2 px-5 py-3 sm:flex-row sm:items-center sm:justify-between;
}

.band__impact {
  @apply inline-flex items-center gap-2 text-xs;
  color: var(--color-text-muted);
}

.band__impact--muted {
  opacity: 0.75;
}

.band__footer-actions {
  @apply flex items-center gap-2 shrink-0;
}

.mark-coa-button {
  @apply inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors;
  background: color-mix(in srgb, var(--color-primary) 12%, transparent);
  color: var(--color-primary);
}

.mark-coa-button:hover {
  background: color-mix(in srgb, var(--color-primary) 18%, transparent);
}

.mark-coa-button:focus-visible,
.mark-edit-button:focus-visible,
.action-link:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
  border-radius: 8px;
}

.mark-edit-button {
  @apply inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors;
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border);
  color: var(--color-text);
}

.mark-edit-button:hover {
  border-color: var(--color-border-strong);
}

/* ---- action links (kept from incumbent) ---- */
.action-link {
  @apply inline-flex h-8 w-8 items-center justify-center rounded-lg transition-colors;
}

.action-link--primary {
  color: var(--color-primary);
}

.action-link--primary:hover {
  background: color-mix(in srgb, var(--color-primary) 10%, transparent);
}

.action-link--danger {
  color: var(--color-danger);
}

.action-link--danger:hover {
  background: color-mix(in srgb, var(--color-danger) 10%, transparent);
}

@media (max-width: 900px) {
  .band {
    grid-template-columns: 1fr;
    gap: 16px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .band-enter-active .band-wrap,
  .band-leave-active .band-wrap,
  .band-enter-active .band-clip,
  .band-leave-active .band-clip,
  .mark-expand i,
  .mark-row {
    transition: none;
  }
}
</style>
