<template>
  <TableShell>
    <!-- Bar refresh tipis: data sudah pernah dimuat, tabel tetap tampil saat reload -->
    <div
      v-if="store.loadProgress.active && store.hasLoadedOnce"
      class="history-refreshbar"
      role="progressbar"
      :aria-valuenow="Math.round(store.loadProgress.percent)"
      aria-valuemin="0"
      aria-valuemax="100"
      :aria-label="`Memuat ulang data, ${Math.round(store.loadProgress.percent)}%`"
    >
      <div class="history-refreshbar__fill" :style="{ width: `${store.loadProgress.percent}%` }"></div>
    </div>

    <!-- Ledger header: select-all + sort -->
    <div class="history-head px-4 py-2.5 flex items-center gap-3 flex-wrap">
      <input
        type="checkbox"
        class="rounded border-[var(--color-border)] text-[var(--color-primary)] focus:ring-[var(--color-primary)]"
        :checked="isAllSelected"
        @change="toggleSelectAll"
      >
      <span class="history-head__label">Urutkan</span>
      <div class="flex items-center gap-1">
        <button
          v-for="col in sortColumns"
          :key="col.key"
          type="button"
          class="history-sort"
          :class="{ 'history-sort--active': store.sortConfig.key === col.key }"
          @click="store.toggleSort(col.key)"
        >
          {{ col.label }}
          <i
            v-if="store.sortConfig.key === col.key"
            class="bi"
            :class="store.sortConfig.direction === 'desc' ? 'bi-caret-down-fill' : 'bi-caret-up-fill'"
          ></i>
        </button>
      </div>
      <div class="flex-1"></div>
      <span
        v-if="store.loadProgress.active && store.hasLoadedOnce"
        class="history-refresh-status"
      >
        <i class="bi bi-arrow-repeat animate-spin"></i>
        {{ progressLabel }}
      </span>
      <span class="history-head__label hidden md:inline">Marking</span>
    </div>

    <!-- Ledger rows -->
    <div class="history-body">
      <!-- Muat pertama: progress nyata per fase + skeleton baris agar layout stabil -->
      <div v-if="isInitialLoading" class="history-loading">
        <div class="history-loading__status">
          <span class="history-loading__percent mono">{{ Math.round(store.loadProgress.percent) }}%</span>
          <div class="history-loading__bar">
            <div class="history-loading__fill" :style="{ width: `${store.loadProgress.percent}%` }"></div>
          </div>
          <span class="history-loading__meta">
            {{ store.loadProgress.message }}
            <template v-if="store.loadProgress.total > 0">
              · {{ formatAmount(store.loadProgress.loaded) }}/{{ formatAmount(store.loadProgress.total) }} transaksi
            </template>
          </span>
        </div>
        <div v-for="n in 8" :key="n" class="history-skeleton" aria-hidden="true">
          <span class="history-skeleton__check"></span>
          <div class="history-skeleton__lines">
            <span class="history-skeleton__bar" style="width: 52%"></span>
            <span class="history-skeleton__bar history-skeleton__bar--meta" style="width: 36%"></span>
          </div>
          <span class="history-skeleton__bar history-skeleton__bar--end" style="width: 140px"></span>
        </div>
      </div>
      <div v-else-if="store.error" class="history-empty py-14 text-center">
        <i class="bi bi-cloud-slash text-3xl mb-2 block" style="color: var(--color-danger)"></i>
        <p class="text-sm font-medium" style="color: var(--color-text-muted)">
          Gagal memuat data transaksi.
        </p>
        <button type="button" class="btn-secondary !mt-3 !rounded-xl !text-xs" @click="store.loadData()">
          <i class="bi bi-arrow-clockwise me-1"></i> Coba Lagi
        </button>
      </div>
      <div v-else-if="store.paginatedTransactions.length === 0" class="history-empty py-14 text-center">
        <i class="bi bi-inbox text-3xl mb-2 block" style="color: var(--color-text-muted)"></i>
        <p class="text-sm font-medium" style="color: var(--color-text-muted)">
          {{ store.activeFilterCount > 0 ? 'Tidak ada transaksi yang cocok dengan filter aktif' : 'Belum ada transaksi tercatat' }}
        </p>
        <p v-if="store.activeFilterCount > 0" class="mt-1 text-xs" style="color: var(--color-text-muted)">
          {{ store.activeFilterCount }} filter aktif membatasi hasil.
        </p>
        <button
          v-if="store.activeFilterCount > 0"
          type="button"
          class="btn-secondary !mt-3 !rounded-xl !text-xs"
          @click="store.resetFilters()"
        >
          <i class="bi bi-x-circle me-1"></i> Reset Filter
        </button>
      </div>

      <template v-else>
      <div
        v-for="t in store.paginatedTransactions"
        :key="t.id"
        class="history-row cursor-pointer"
        :class="{ 'history-row--selected': store.selectedTxnIds.includes(t.id) }"
        @click="$emit('view-details', t)"
      >
        <div class="flex flex-col gap-1.5 px-4 py-2.5 md:flex-row md:items-center md:gap-3">
          <input
            type="checkbox"
            class="mt-0.5 shrink-0 rounded border-[var(--color-border)] text-[var(--color-primary)] focus:ring-[var(--color-primary)]"
            :checked="store.selectedTxnIds.includes(t.id)"
            @click.stop
            @change="store.toggleSelection(t.id)"
          >

          <div class="min-w-0 flex-1">
            <!-- Baris baca: deskripsi + jumlah (tampilkan versi bersih AI bila ada;
                 tooltip menampilkan deskripsi asli untuk audit) -->
            <div class="flex items-baseline justify-between gap-4">
              <p
                class="min-w-0 flex-1 truncate text-[13px] font-medium"
                style="color: var(--color-text)"
                :title="t.clean_description ? `${t.clean_description}\n— asli —\n${t.description}` : t.description"
              >
                {{ t.clean_description || t.description }}
                <i
                  v-if="t.clean_description"
                  class="bi bi-stars text-[10px] text-primary ml-1 shrink-0"
                  title="Deskripsi bersih hasil AI — arahkan kursor untuk lihat deskripsi asli"
                ></i>
              </p>
              <span
                class="shrink-0 mono text-[13px] font-bold whitespace-nowrap"
                :class="getFlowColorClass(t.db_cr, 'text')"
                :title="`${getFlowLabel(t.db_cr)} · ${formatDate(t.txn_date)}`"
              >
                {{ getAmountSign(t.db_cr) }}{{ formatAmount(t.amount) }}
              </span>
            </div>

            <!-- Baris meta: tanggal · perusahaan · arah · bank · COA · sumber -->
            <div class="history-meta mt-1 flex min-w-0 items-center gap-1.5 truncate text-[11px]">
              <span class="shrink-0" :title="t.txn_date">{{ formatDateMeta(t.txn_date) }}</span>
              <span class="history-meta__dot">·</span>
              <span v-if="editingCompanyId !== t.id" class="shrink-0">
                <button
                  type="button"
                  class="font-semibold underline-offset-2 transition-all hover:text-[var(--color-primary)] hover:underline"
                  style="color: var(--color-text)"
                  :title="`${t.company_name || 'Tanpa company'} — klik untuk mengubah company`"
                  @click.stop="startCompanyEdit(t)"
                >
                  {{ t.company_short_name || '-' }}
                </button>
              </span>
              <span v-else class="shrink-0" @click.stop>
                <SearchableSelect
                  class="w-44"
                  size="sm"
                  :model-value="t.company_id || ''"
                  :options="companyOptions"
                  placeholder="Pilih company..."
                  @update:model-value="onCompanySelected(t, $event)"
                />
              </span>
              <span class="history-meta__dot">·</span>
              <span class="shrink-0 inline-flex items-center gap-0.5 font-semibold" :class="getFlowColorClass(t.db_cr, 'text')">
                <i :class="getFlowIcon(t.db_cr)" class="text-[10px]"></i>
                {{ getFlowLabel(t.db_cr) }}
              </span>
              <span class="history-meta__dot">·</span>
              <span class="shrink-0">{{ t.bank_code }}</span>
              <template v-if="coaRows(t).length > 0">
                <span class="history-meta__dot">·</span>
                <span
                  v-for="coa in visibleCoas(t)"
                  :key="coa.key"
                  class="history-coa-tag inline-flex shrink-0 items-center px-1.5 py-0.5 text-[10px] font-semibold"
                >
                  {{ coa.label }}
                </span>
                <span
                  v-if="hiddenCoaCount(t) > 0"
                  class="history-coa-more inline-flex shrink-0 items-center px-1.5 py-0.5 text-[10px] font-semibold"
                >
                  +{{ hiddenCoaCount(t) }}
                </span>
              </template>
              <span v-else class="shrink-0 history-meta__empty">Belum ada COA</span>
              <span v-if="t.is_linked_to_manual" class="shrink-0 inline-flex items-center text-primary" title="Referenced by manual journal">
                <i class="bi bi-link-45deg text-sm"></i>
              </span>
              <span class="history-meta__dot">·</span>
              <span class="min-w-0 truncate" :title="t.source_file">{{ t.source_file }}</span>
            </div>

            <!-- Rel aksi: marking + AI + split -->
          </div>

          <div class="flex flex-col gap-1.5 md:shrink-0 md:w-[300px]" @click.stop>
            <div class="flex w-full items-center gap-1.5">
              <SearchableSelect
                v-if="!t.is_split && !t.is_linked_to_manual"
                class="w-full min-w-0 flex-1"
                :model-value="t.mark_id || ''"
                :options="markOptions"
                placeholder="-- Unmarked --"
                size="sm"
                @update:model-value="onMarkSelected(t.id, $event)"
              />
              <div
                v-else-if="t.is_split"
                class="history-chip inline-flex min-w-0 flex-1 items-center gap-1.5 px-2 py-1 text-[10px] font-bold"
                :class="t.is_multi_marked ? 'history-chip--primary' : 'history-chip--warning'"
                :title="t.is_multi_marked ? 'Mixed Marks' : 'Split (No Active Mark)'"
              >
                <i class="bi bi-stack shrink-0"></i>
                <span class="truncate">{{ t.is_multi_marked ? 'Mixed Marks' : 'Split (No Active Mark)' }}</span>
              </div>
              <div
                v-else-if="t.is_linked_to_manual"
                class="history-chip history-chip--primary inline-flex min-w-0 flex-1 items-center gap-1.5 px-2 py-1 text-[10px] font-bold"
                :title="`Linked to: ${t.manual_mark_name || 'Manual Journal'}`"
              >
                <i class="bi bi-link-45deg shrink-0 text-sm"></i>
                <span class="truncate">{{ t.manual_mark_name || 'Manual Journal' }}</span>
              </div>

              <!-- Slot tombol berukuran tetap: kolom mark tetap sebaris antar baris,
                   meski tombol AI belum tampil / sudah berganti chip. -->
              <div class="flex w-[64px] shrink-0 items-center justify-end gap-0.5">
                <button
                  v-if="showAiRequest(t) || store.aiBusyTxnIds.includes(t.id)"
                  type="button"
                  @click.stop="requestSuggestion(t)"
                  class="p-1 transition-all active:scale-90"
                  :class="store.aiBusyTxnIds.includes(t.id) ? 'text-[var(--color-primary)]' : 'text-[var(--color-text-muted)] hover:text-[var(--color-primary)]'"
                  :title="store.aiBusyTxnIds.includes(t.id) ? 'Meminta saran AI...' : 'Minta saran AI untuk marking ini'"
                >
                  <i class="bi bi-stars text-sm" :class="{ 'bi-arrow-repeat animate-spin': store.aiBusyTxnIds.includes(t.id) }"></i>
                </button>
                <button
                  type="button"
                  @click.stop="$emit('split-transaction', t)"
                  class="p-1 transition-all active:scale-90"
                  :class="t.is_split ? 'text-[var(--color-primary)] hover:opacity-80' : 'text-[var(--color-text-muted)] hover:text-[var(--color-primary)]'"
                  :title="t.is_split ? 'Transaction is split into multiple parts' : 'Split this transaction'"
                >
                  <i class="bi bi-diagram-3-fill text-sm"></i>
                </button>
              </div>

            </div>

            <div v-if="isAiPending(t)" class="flex w-full items-start gap-1">
                <span
                  class="history-chip inline-flex min-w-0 flex-1 items-start gap-1 px-1.5 py-0.5 text-[10px] font-bold leading-snug"
                  :class="aiChipClass(t)"
                  :title="aiSuggestionTooltip(t)"
                >
                  <i class="bi bi-stars shrink-0 text-[9px] mt-0.5"></i>
                  <span class="min-w-0 break-words">AI: {{ aiSuggestionLabel(t) }} · {{ aiConfidencePercent(t) }}%</span>
                </span>
                <button
                  type="button"
                  @click.stop="acceptSuggestion(t)"
                  class="shrink-0 p-0.5 transition-all hover:opacity-75 text-[var(--color-success)]"
                  title="Terima saran AI — isi mark dengan saran ini"
                >
                  <i class="bi bi-check-lg text-sm"></i>
                </button>
                <button
                  type="button"
                  @click.stop="rejectSuggestion(t)"
                  class="shrink-0 p-0.5 transition-all hover:opacity-75 text-[var(--color-danger)]"
                  title="Tolak saran AI"
                >
                  <i class="bi bi-x-lg text-xs"></i>
                </button>
              </div>
            <div v-else-if="isAiAuto(t)" class="flex w-full items-start gap-1">
                <span
                  class="history-chip history-chip--primary inline-flex min-w-0 flex-1 items-start gap-1 px-1.5 py-0.5 text-[10px] font-bold leading-snug"
                  :title="aiAutoTooltip(t)"
                >
                  <i class="bi bi-stars shrink-0 text-[9px] mt-0.5"></i>
                  <span class="min-w-0 break-words">AI otomatis: {{ aiSuggestionLabel(t) }} · {{ aiConfidencePercent(t) }}%</span>
                </span>
                <button
                  type="button"
                  @click.stop="undoAutoMark(t)"
                  class="shrink-0 p-0.5 transition-all hover:opacity-75 text-[var(--color-danger)]"
                  title="Batalkan mark otomatis AI (hapus mark)"
                >
                  <i class="bi bi-x-lg text-xs"></i>
                </button>
              </div>
        </div>
      </div>
      </div>
      </template>
    </div>

    <!-- Strip total ringkas -->
    <div
      v-if="!isInitialLoading && store.filteredTransactions.length > 0"
      class="history-totals flex flex-wrap items-center gap-x-2 gap-y-1 px-4 py-2.5 text-xs"
    >
      <span class="history-totals__group">Halaman ini</span>
      <span class="history-totals__item">
        <i class="bi bi-arrow-up-circle-fill text-danger"></i>
        Keluar <b class="mono">{{ formatAmount(store.pageCreditTotal) }}</b>
      </span>
      <span class="history-totals__item">
        <i class="bi bi-arrow-down-circle-fill text-success"></i>
        Masuk <b class="mono">{{ formatAmount(store.pageDebitTotal) }}</b>
      </span>
      <span class="history-totals__item">
        Net <b class="mono" :class="store.pageTotal >= 0 ? 'text-success' : 'text-danger'">
          {{ store.pageTotal >= 0 ? '+' : '-' }}{{ formatAmount(Math.abs(store.pageTotal)) }}
        </b>
      </span>

      <span class="history-totals__sep" role="separator"></span>

      <span class="history-totals__group">Terfilter</span>
      <span class="history-totals__item">
        <i class="bi bi-arrow-up-circle-fill text-danger"></i>
        Keluar <b class="mono">{{ formatAmount(store.filteredCreditTotal) }}</b>
      </span>
      <span class="history-totals__item">
        <i class="bi bi-arrow-down-circle-fill text-success"></i>
        Masuk <b class="mono">{{ formatAmount(store.filteredDebitTotal) }}</b>
      </span>
      <span class="history-totals__item">
        Net <b class="mono" :class="store.filteredTotal >= 0 ? 'text-success' : 'text-danger'">
          {{ store.filteredTotal >= 0 ? '+' : '-' }}{{ formatAmount(Math.abs(store.filteredTotal)) }}
        </b>
      </span>
    </div>

    <template #footer>
      <div class="history-pagination px-6 py-4 flex items-center justify-between" v-if="!isInitialLoading && store.paginatedTransactions.length > 0">
        <div class="flex flex-col md:flex-row md:items-center gap-4 w-full justify-between">
          <p class="text-[10px] font-medium whitespace-nowrap" style="color: var(--color-text-muted)">
            Menampilkan {{ ((store.currentPage - 1) * store.itemsPerPage) + 1 }}–{{ Math.min(store.currentPage * store.itemsPerPage, store.filteredTransactions.length) }} dari {{ store.filteredTransactions.length }}
          </p>

          <div class="flex flex-wrap gap-2 items-center justify-center">
            <select class="input-base !w-auto !px-2 !py-1 !text-[10px]" v-model="store.itemsPerPage" @change="store.currentPage = 1">
              <option :value="10">10 / Halaman</option>
              <option :value="25">25 / Halaman</option>
              <option :value="50">50 / Halaman</option>
              <option :value="100">100 / Halaman</option>
            </select>

            <div class="flex gap-1">
              <button
                class="history-page-button"
                :disabled="store.currentPage === 1"
                @click="store.currentPage = 1"
                title="Halaman Pertama"
              >
                <i class="bi bi-chevron-double-left text-xs"></i>
              </button>
              <button
                class="history-page-button"
                :disabled="store.currentPage === 1"
                @click="store.currentPage--"
              >
                <i class="bi bi-chevron-left text-xs"></i>
              </button>

              <div class="flex gap-1">
                <template v-for="page in visiblePages" :key="page">
                  <button
                    v-if="page !== '...'"
                    class="history-page-button !w-8"
                    :class="{ 'history-page-button--active': store.currentPage === page }"
                    @click="store.currentPage = page"
                  >
                    {{ page }}
                  </button>
                  <span v-else class="w-8 h-8 flex items-center justify-center" style="color: var(--color-text-muted)">...</span>
                </template>
              </div>

              <button
                class="history-page-button"
                :disabled="store.currentPage === store.totalPages"
                @click="store.currentPage++"
              >
                <i class="bi bi-chevron-right text-xs"></i>
              </button>
              <button
                class="history-page-button"
                :disabled="store.currentPage === store.totalPages"
                @click="store.currentPage = store.totalPages"
                title="Halaman Terakhir"
              >
                <i class="bi bi-chevron-double-right text-xs"></i>
              </button>
            </div>
          </div>
        </div>
      </div>
    </template>
  </TableShell>

    <!-- Individual Delete Selection Modal -->
    <ConfirmModal
        :isOpen="isDeleteModalOpen"
        title="Delete Transaction"
        :message="`Are you sure you want to delete this transaction from ${formatDate(transactionToDelete?.txn_date)}?`"
        confirmText="Delete"
        :loading="isDeleting"
        variant="danger"
        @close="isDeleteModalOpen = false"
        @confirm="handleConfirmDelete"
    />
</template>

<script setup>
import { ref, computed } from 'vue';
import { useHistoryStore } from '../../stores/history';
import { getFlowLabel, getFlowIcon, getFlowColorClass, getAmountSign } from '../../composables/useBankDirection';
import ConfirmModal from '../ui/ConfirmModal.vue';
import SearchableSelect from '../ui/SearchableSelect.vue';
import TableShell from '../ui/TableShell.vue';
import { useNotifications } from '../../composables/useNotifications';

const store = useHistoryStore();
const notify = useNotifications();
const emit = defineEmits(['view-details', 'split-transaction']);

// Muat pertama = tampilkan skeleton + progress; reload berikutnya = tabel tetap tampil.
const isInitialLoading = computed(() => store.loadProgress.active && !store.hasLoadedOnce);

const progressLabel = computed(() => {
  const p = store.loadProgress;
  if (p.total > 0) return `${Math.round(p.percent)}% · ${formatAmount(p.loaded)}/${formatAmount(p.total)}`;
  return `${Math.round(p.percent)}%`;
});

// Individual Delete State
const isDeleteModalOpen = ref(false);
const isDeleting = ref(false);
const transactionToDelete = ref(null);

const sortColumns = [
  { key: 'txn_date', label: 'Tanggal' },
  { key: 'description', label: 'Deskripsi' },
  { key: 'amount', label: 'Jumlah' },
];

const promptDelete = (txn) => {
    transactionToDelete.value = txn;
    isDeleteModalOpen.value = true;
};

const handleConfirmDelete = async () => {
    if (!transactionToDelete.value) return;
    isDeleting.value = true;
    try {
        await store.deleteTransaction(transactionToDelete.value.id);
        isDeleteModalOpen.value = false;
    } catch (e) {
        console.error(e);
    } finally {
        isDeleting.value = false;
        transactionToDelete.value = null;
    }
};


const isAllSelected = computed(() => {
    return store.paginatedTransactions.length > 0 &&
           store.paginatedTransactions.every(t => store.selectedTxnIds.includes(t.id));
});

const visiblePages = computed(() => {
    const total = store.totalPages;
    if (total < 1) return [];
    const current = store.currentPage;
    const delta = 2;
    const range = [];
    const rangeWithDots = [];
    let l;

    if (total <= 7) {
        for (let i = 1; i <= total; i++) range.push(i);
        return range;
    }

    range.push(1);
    for (let i = current - delta; i <= current + delta; i++) {
        if (i < total && i > 1) {
            range.push(i);
        }
    }
    range.push(total);

    for (let i of range) {
        if (l) {
            if (i - l === 2) {
                rangeWithDots.push(l + 1);
            } else if (i - l !== 1) {
                rangeWithDots.push('...');
            }
        }
        rangeWithDots.push(i);
        l = i;
    }

    return rangeWithDots;
});

const markOptions = computed(() => {
    const options = [{ id: '__UNMARKED__', label: '-- Unmarked --' }];
    for (const m of store.sortedMarks || []) {
        options.push({
            id: m.id,
            label: buildMarkLabel(m)
        });
    }
    return options;
});

const toggleSelectAll = () => {
    if (isAllSelected.value) {
        store.deselectAll();
    } else {
        store.selectAll();
    }
};

const onMarkSelected = (txnId, selectedValue) => {
    const normalized = selectedValue === '__UNMARKED__' ? null : (selectedValue || null);
    store.assignMark(txnId, normalized);
};

// ---------------------------------------------------------------- AI mark assist

const aiEnabled = computed(() => Boolean(store.aiSettings?.enabled));

const isAiPending = (t) => t.ai_status === 'pending' && Boolean(t.ai_suggested_mark_id);

const isAiAuto = (t) => t.ai_status === 'auto_applied' && Boolean(t.ai_suggested_mark_id);

// ------------------------------------------------- ubah company langsung di tabel

const editingCompanyId = ref(null);

const companyOptions = computed(() => [
  { id: '__NONE__', label: 'Tanpa Company' },
  ...(store.companies || []).map(c => ({
    id: c.id,
    label: c.short_name ? `${c.name} (${c.short_name})` : c.name,
  })),
]);

const startCompanyEdit = (t) => {
  editingCompanyId.value = t.id;
};

const onCompanySelected = async (t, value) => {
  editingCompanyId.value = null;
  const companyId = value === '__NONE__' ? null : (value || null);
  if ((t.company_id || null) === companyId) return;
  try {
    await store.assignCompany(t.id, companyId);
    notify.success('Company diperbarui.');
  } catch (e) {
    notify.error(e.response?.data?.error || 'Gagal mengubah company.');
  }
};

const showAiRequest = (t) =>
    aiEnabled.value && !t.is_split && !t.is_linked_to_manual
    && !['pending', 'auto_applied', 'accepted'].includes(t.ai_status);

const aiSuggestionLabel = (t) => {
    const markId = String(t.ai_suggested_mark_id || '');
    const mark = (store.marks || []).find(m => String(m.id) === markId);
    return mark ? buildMarkLabel(mark) : 'Mark tidak dikenal';
};

const aiConfidencePercent = (t) => {
    const value = Number(t.ai_confidence);
    return Number.isFinite(value) ? String(Math.round(value * 100)) : '-';
};

const aiChipClass = (t) => {
    const value = Number(t.ai_confidence) || 0;
    if (value >= 0.8) return 'history-chip--success';
    if (value >= 0.5) return 'history-chip--warning';
    return 'history-chip--danger';
};

const aiSuggestionTooltip = (t) => {
    const reason = t.ai_reason ? ` — ${t.ai_reason}` : '';
    return `Saran AI, keyakinan ${aiConfidencePercent(t)}%${reason}`;
};

const aiAutoTooltip = (t) => {
    const reason = t.ai_reason ? ` — ${t.ai_reason}` : '';
    return `Ter-mark otomatis dari riwayat Anda (keyakinan ${aiConfidencePercent(t)}%).${reason}`;
};

const undoAutoMark = async (t) => {
    try {
        await store.decideSuggestion(t.id, 'reject');
        notify.info('Mark otomatis AI dibatalkan — mark dikosongkan.');
    } catch (e) {
        notify.error(e.response?.data?.error || 'Gagal membatalkan mark otomatis.');
    }
};

const requestSuggestion = async (t) => {
    try {
        await store.suggestMark(t.id);
    } catch (e) {
        notify.error(e.message || 'Gagal meminta saran AI.');
    }
};

const acceptSuggestion = async (t) => {
    try {
        await store.decideSuggestion(t.id, 'accept');
        notify.success('Saran AI diterima — mark tersimpan.');
    } catch (e) {
        notify.error(e.response?.data?.error || 'Gagal menerima saran AI.');
    }
};

const rejectSuggestion = async (t) => {
    try {
        await store.decideSuggestion(t.id, 'reject');
        notify.info('Saran AI ditolak.');
    } catch (e) {
        notify.error(e.response?.data?.error || 'Gagal menolak saran AI.');
    }
};

const buildMarkLabel = (mark) => {
    const parts = [mark?.internal_report, mark?.personal_use, mark?.tax_report]
        .map(value => String(value || '').trim())
        .filter(Boolean);
    const uniqueParts = [...new Set(parts)];
    return uniqueParts.length ? uniqueParts.join(' / ') : 'Marked';
};

// Utils
const formatDate = (dateStr) => {
    if (!dateStr || typeof dateStr !== 'string') return "-";
    try {
      return dateStr.split(" ")[0];
    } catch (e) { return dateStr; }
};

const MONTHS_ID = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'];

const formatDateMeta = (dateStr) => {
    const datePart = formatDate(dateStr);
    const parts = datePart.split('-');
    if (parts.length !== 3) return datePart;
    const [year, month, day] = parts;
    const monthIndex = Number(month) - 1;
    if (!MONTHS_ID[monthIndex]) return datePart;
    return `${Number(day)} ${MONTHS_ID[monthIndex]} ${year}`;
};

const formatAmount = (val) => {
    if (val === undefined || val === null) return "0";
    const num = typeof val === 'string' ? parseFloat(val.replace(/,/g, '')) : val;
    return new Intl.NumberFormat('id-ID').format(num || 0);
};

const normalizeCoaKey = (coa) => {
    return `${coa?.coa_id || coa?.id || ''}-${coa?.code || ''}-${coa?.name || ''}-${coa?.type || ''}`;
};

const coaRows = (txn) => {
    const list = Array.isArray(txn?.coas) ? txn.coas : [];
    const uniq = new Set();
    const rows = [];

    for (const coa of list) {
        const key = normalizeCoaKey(coa);
        if (!key || uniq.has(key)) continue;
        uniq.add(key);

        const code = coa?.code || '';
        const name = coa?.name || '';
        const label = code && name ? `${code} - ${name}` : (code || name || '-');
        rows.push({ key, label });
    }

    return rows;
};

const visibleCoas = (txn) => {
    return coaRows(txn).slice(0, 2);
};

const hiddenCoaCount = (txn) => {
    const total = coaRows(txn).length;
    return total > 2 ? total - 2 : 0;
};
</script>

<style scoped>
.history-refreshbar {
  height: 3px;
  width: 100%;
  background: var(--color-surface-muted);
  overflow: hidden;
}

.history-refreshbar__fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary), var(--color-primary-strong));
  transition: width 250ms ease-out;
}

.history-refresh-status {
  @apply inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-bold;
  background: rgba(15, 118, 110, 0.10);
  color: var(--color-primary);
}

.history-loading__status {
  @apply flex items-center gap-3 px-4 pb-2 pt-4;
}

.history-loading__percent {
  @apply w-10 shrink-0 text-right text-sm font-bold;
  color: var(--color-primary);
  font-variant-numeric: tabular-nums;
}

.history-loading__bar {
  @apply h-1.5 min-w-0 flex-1 overflow-hidden rounded-full;
  background: var(--color-surface-muted);
}

.history-loading__fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--color-primary), var(--color-primary-strong));
  transition: width 250ms ease-out;
}

.history-loading__meta {
  @apply shrink-0 text-[11px] font-medium;
  color: var(--color-text-muted);
}

.history-skeleton {
  @apply flex items-center gap-3 px-4 py-2.5;
}

.history-skeleton + .history-skeleton {
  border-top: 1px solid var(--color-border);
}

.history-skeleton__check {
  @apply h-4 w-4 shrink-0 rounded border;
  border-color: var(--color-border);
  background: var(--color-surface-muted);
}

.history-skeleton__lines {
  @apply flex min-w-0 flex-1 flex-col gap-1.5;
}

.history-skeleton__bar {
  @apply block h-2.5 rounded-full;
  background: linear-gradient(90deg, var(--color-surface-muted) 25%, var(--color-surface-raised) 45%, var(--color-surface-muted) 65%);
  background-size: 200% 100%;
  animation: history-skeleton-sweep 1.4s ease-in-out infinite;
}

.history-skeleton__bar--meta {
  height: 9px;
}

.history-skeleton__bar--end {
  @apply ml-auto shrink-0;
  height: 10px;
}

@keyframes history-skeleton-sweep {
  from { background-position: 200% 0; }
  to { background-position: -200% 0; }
}

@media (prefers-reduced-motion: reduce) {
  .history-skeleton__bar {
    animation: none;
  }
}

.history-empty {
  @apply px-4;
}

.history-head {
  background: var(--color-surface-muted);
  border-bottom: 1px solid var(--color-border);
}

.history-head__label {
  @apply text-[10px] font-semibold uppercase tracking-wider;
  color: var(--color-text-muted);
}

.history-sort {
  @apply inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium transition-colors;
  color: var(--color-text-muted);
}

.history-sort:hover {
  background: var(--color-surface-raised);
  color: var(--color-text);
}

.history-sort--active {
  background: rgba(15, 118, 110, 0.10);
  color: var(--color-primary);
}

.history-row {
  transition: background-color 160ms ease;
}

.history-row + .history-row {
  border-top: 1px solid var(--color-border);
}

.history-row:hover {
  background: rgba(15, 118, 110, 0.05);
}

.history-row--selected {
  background: rgba(15, 118, 110, 0.10);
}

.history-meta {
  color: var(--color-text-muted);
}

.history-meta__dot {
  @apply shrink-0;
  opacity: 0.55;
}

.history-meta__empty {
  @apply shrink-0;
  opacity: 0.75;
}

.history-coa-tag {
  background: rgba(15, 118, 110, 0.10);
  border: 1px solid rgba(15, 118, 110, 0.18);
  color: var(--color-primary);
}

.history-coa-more {
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
  color: var(--color-text-muted);
}

.history-chip {
  border: 1px solid transparent;
}

.history-chip--primary {
  color: var(--color-primary);
  background: rgba(15, 118, 110, 0.10);
  border-color: rgba(15, 118, 110, 0.18);
}

.history-chip--warning {
  color: var(--color-warning);
  background: rgba(180, 83, 9, 0.10);
  border-color: rgba(180, 83, 9, 0.18);
}

.history-chip--success {
  color: var(--color-success);
  background: rgba(22, 101, 52, 0.10);
  border-color: rgba(22, 101, 52, 0.18);
}

.history-chip--danger {
  color: var(--color-danger);
  background: rgba(185, 28, 28, 0.10);
  border-color: rgba(185, 28, 28, 0.18);
}

.history-totals {
  background: var(--color-surface-muted);
  border-top: 2px solid var(--color-border);
}

.history-totals__group {
  @apply text-[10px] font-bold uppercase tracking-wider;
  color: var(--color-text-muted);
  margin-right: 4px;
}

.history-totals__item {
  @apply inline-flex items-center gap-1;
  color: var(--color-text-muted);
}

.history-totals__item b {
  @apply text-xs font-bold;
  color: var(--color-text);
}

.history-totals__sep {
  @apply inline-block;
  width: 1px;
  height: 16px;
  background: var(--color-border-strong, var(--color-border));
  margin: 0 8px;
}

.history-pagination {
  background: var(--color-surface-muted);
  border-top: 1px solid var(--color-border);
}

.history-page-button {
  @apply min-w-[32px] h-8 rounded text-xs font-medium transition-all;
  border: 1px solid var(--color-border);
  background: var(--color-surface-raised);
  color: var(--color-text-muted);
}

.history-page-button:hover:not(:disabled) {
  border-color: var(--color-border-strong);
  color: var(--color-text);
}

.history-page-button:disabled {
  opacity: 0.3;
}

.history-page-button--active {
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-strong));
  border-color: transparent;
  color: #fff;
}
</style>
