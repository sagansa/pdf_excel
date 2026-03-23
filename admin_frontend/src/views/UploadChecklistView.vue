<template>
  <div class="space-y-6">
    <PageHeader
      eyebrow="Upload Checklist"
      icon="bi bi-check2-square"
      title="Yearly upload status per bank"
      subtitle="Pantau kelengkapan upload file statement per bulan, per bank. Cek nilai DB dan CR apakah sudah sesuai."
    >
      <template #actions>
        <div class="flex items-center gap-2">
          <!-- Year Selector -->
          <select
            v-model="selectedYear"
            @change="onYearChange"
            class="checklist-year-select"
          >
            <option v-for="y in availableYears" :key="y" :value="y">{{ y }}</option>
          </select>

          <button
            @click="refresh"
            class="btn-secondary flex items-center gap-2 py-2"
            :disabled="store.isLoading"
          >
            <i class="bi bi-arrow-clockwise" :class="{ 'animate-spin': store.isLoading }"></i>
            <span>Refresh</span>
          </button>
        </div>
      </template>
    </PageHeader>

    <!-- Loading skeleton -->
    <div v-if="store.isLoading && !checklist" class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div v-for="i in 4" :key="i" class="skeleton-card"></div>
    </div>

    <!-- Error -->
    <div v-else-if="store.error && !checklist" class="section-card p-6 text-center text-red-500">
      <i class="bi bi-exclamation-triangle-fill text-2xl mb-2"></i>
      <p>Gagal memuat data. Coba refresh.</p>
    </div>

    <template v-else-if="checklist">
      <!-- Summary Stat Cards -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Sudah Upload"
          :value="String(summaryStats.uploaded)"
          icon="bi bi-check-circle-fill"
          wrapperClass="stat-uploaded"
          labelClass="text-emerald-600"
          valueClass="text-emerald-500"
          iconWrapperClass="bg-emerald-500/10"
          iconClass="text-emerald-500"
          :subtext="`dari ${summaryStats.total} slot`"
          subtextClass="text-muted"
        />
        <StatCard
          label="Belum Upload"
          :value="String(summaryStats.missing)"
          icon="bi bi-x-circle-fill"
          wrapperClass="stat-missing"
          labelClass="text-red-500"
          valueClass="text-red-500"
          iconWrapperClass="bg-red-500/10"
          iconClass="text-red-500"
          :subtext="`${summaryStats.pct}% lengkap`"
          subtextClass="text-muted"
        />
        <StatCard
          label="Total Debit"
          :value="formatAmount(summaryStats.totalDebit)"
          icon="bi bi-arrow-down-circle-fill"
          wrapperClass="stat-debit"
          labelClass="text-red-400"
          valueClass="text-red-400"
          iconWrapperClass="bg-red-500/10"
          iconClass="text-red-400 text-sm"
        />
        <StatCard
          label="Total Credit"
          :value="formatAmount(summaryStats.totalCredit)"
          icon="bi bi-arrow-up-circle-fill"
          wrapperClass="stat-credit"
          labelClass="text-emerald-600"
          valueClass="text-emerald-500"
          iconWrapperClass="bg-emerald-500/10"
          iconClass="text-emerald-500 text-sm"
        />
      </div>

      <!-- Grid Table -->
      <SectionCard
        :title="`Checklist ${selectedYear}`"
        subtitle="✓ = file terupload · — = belum ada · ⚠ = selisih DB/CR besar"
        body-class="p-0 overflow-x-auto"
      >
        <table class="checklist-table min-w-full">
          <thead>
            <tr>
              <th class="cl-th cl-th-month">Bulan</th>
              <th
                v-for="bank in checklist.banks"
                :key="bank"
                class="cl-th cl-th-bank"
                :class="{ 'bank-hidden': activeBanks.size > 0 && !activeBanks.has(bank) }"
              >
                <span class="bank-name-label">{{ formatBankCode(bank) }}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="monthRow in checklist.months"
              :key="monthRow.month"
              class="cl-row"
              :class="{ 'cl-row-current': isCurrentMonth(monthRow.month) }"
            >
              <!-- Month label -->
              <td class="cl-td-month">
                <div class="flex items-center gap-1.5">
                  <span class="month-num">{{ String(monthRow.month).padStart(2, '0') }}</span>
                  <span class="month-name">{{ monthRow.label }}</span>
                  <span v-if="isCurrentMonth(monthRow.month)" class="current-badge">Now</span>
                </div>
              </td>

              <!-- Bank cells -->
              <td
                v-for="bank in checklist.banks"
                :key="bank"
                class="cl-td-cell"
                :class="{
                  'bank-hidden': activeBanks.size > 0 && !activeBanks.has(bank),
                  'cell-uploaded': monthRow.banks[bank]?.uploaded,
                  'cell-missing': !monthRow.banks[bank]?.uploaded,
                }"
              >
                <!-- Uploaded -->
                <template v-if="monthRow.banks[bank]?.uploaded">
                  <div class="cell-content-uploaded">
                    <div class="cell-check-row">
                      <i class="bi bi-check-circle-fill text-emerald-500 text-xs"></i>
                      <span class="cell-txn-count">{{ monthRow.banks[bank].transaction_count }} txn</span>
                      <i
                        v-if="hasLargeImbalance(monthRow.banks[bank])"
                        class="bi bi-exclamation-triangle-fill text-amber-400 text-xs"
                        :title="`Selisih DB/CR besar: ${formatAmount(Math.abs(monthRow.banks[bank].total_debit - monthRow.banks[bank].total_credit))}`"
                      ></i>
                    </div>
                    <div class="cell-amounts">
                      <div class="amount-db">DB {{ formatCompact(monthRow.banks[bank].total_debit) }}</div>
                      <div class="amount-cr">CR {{ formatCompact(monthRow.banks[bank].total_credit) }}</div>
                    </div>
                    <div v-if="monthRow.banks[bank].source_files?.length" class="cell-filename" :title="monthRow.banks[bank].source_files.join('\n')">
                      {{ monthRow.banks[bank].source_files[0] }}
                      <span v-if="monthRow.banks[bank].source_files.length > 1" class="more-files">
                        +{{ monthRow.banks[bank].source_files.length - 1 }}
                      </span>
                    </div>
                  </div>
                </template>

                <!-- Not uploaded -->
                <template v-else>
                  <div class="cell-content-missing">
                    <i class="bi bi-dash text-muted text-sm"></i>
                  </div>
                </template>
              </td>
            </tr>

            <!-- Totals footer row -->
            <tr class="cl-totals-row">
              <td class="cl-td-month">
                <span class="font-semibold text-xs uppercase tracking-wide text-muted">Total {{ selectedYear }}</span>
              </td>
              <td
                v-for="bank in checklist.banks"
                :key="bank"
                class="cl-td-cell cl-td-totals"
                :class="{ 'bank-hidden': activeBanks.size > 0 && !activeBanks.has(bank) }"
              >
                <div v-if="bankTotals[bank]?.uploaded > 0" class="totals-cell">
                  <div class="totals-uploaded">{{ bankTotals[bank].uploaded }}/12</div>
                  <div class="amount-db">DB {{ formatCompact(bankTotals[bank].totalDebit) }}</div>
                  <div class="amount-cr">CR {{ formatCompact(bankTotals[bank].totalCredit) }}</div>
                </div>
                <span v-else class="text-muted text-xs">—</span>
              </td>
            </tr>
          </tbody>
        </table>

        <template #footer>
          <div class="flex items-center justify-between px-6 py-3 text-xs text-muted">
            <span>Tahun {{ selectedYear }} · {{ checklist.banks.length }} bank</span>
            <!-- Bank filter chips -->
            <div v-if="checklist.banks.length > 1" class="flex items-center gap-1.5 flex-wrap justify-end">
              <span class="text-muted mr-1">Filter bank:</span>
              <button
                v-for="bank in checklist.banks"
                :key="bank"
                @click="toggleBank(bank)"
                class="bank-chip"
                :class="{ 'bank-chip-active': activeBanks.size === 0 || activeBanks.has(bank) }"
              >
                {{ formatBankCode(bank) }}
              </button>
            </div>
          </div>
        </template>
      </SectionCard>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import PageHeader from '../components/ui/PageHeader.vue';
import SectionCard from '../components/ui/SectionCard.vue';
import StatCard from '../components/ui/StatCard.vue';
import { useHistoryStore } from '../stores/history';

const store = useHistoryStore();
const currentYear = new Date().getFullYear();

// Year options: from 2022 up to current year + 1
const availableYears = computed(() => {
  const years = [];
  for (let y = currentYear + 1; y >= 2020; y--) years.push(y);
  return years;
});

const selectedYear = ref(store.checklistYear || currentYear);
const activeBanks = ref(new Set()); // empty = show all

const checklist = computed(() => store.uploadChecklist);

const isCurrentMonth = (month) => {
  const now = new Date();
  return now.getFullYear() === selectedYear.value && now.getMonth() + 1 === month;
};

const hasLargeImbalance = (cell) => {
  if (!cell || !cell.uploaded) return false;
  const max = Math.max(cell.total_debit, cell.total_credit);
  if (max === 0) return false;
  const delta = Math.abs(cell.total_debit - cell.total_credit);
  return delta / max > 0.3; // flag if >30% difference
};

// ---- Computed summaries ----
const summaryStats = computed(() => {
  if (!checklist.value) return { uploaded: 0, missing: 0, total: 0, pct: 0, totalDebit: 0, totalCredit: 0 };
  let uploaded = 0, missing = 0, totalDebit = 0, totalCredit = 0;
  const banks = checklist.value.banks || [];
  const months = checklist.value.months || [];
  const totalSlots = months.length * banks.length;
  for (const m of months) {
    for (const bank of banks) {
      const cell = m.banks[bank];
      if (cell?.uploaded) {
        uploaded++;
        totalDebit += cell.total_debit || 0;
        totalCredit += cell.total_credit || 0;
      } else {
        missing++;
      }
    }
  }
  const pct = totalSlots > 0 ? Math.round((uploaded / totalSlots) * 100) : 0;
  return { uploaded, missing, total: totalSlots, pct, totalDebit, totalCredit };
});

const bankTotals = computed(() => {
  if (!checklist.value) return {};
  const result = {};
  const banks = checklist.value.banks || [];
  const months = checklist.value.months || [];
  for (const bank of banks) {
    let up = 0, db = 0, cr = 0;
    for (const m of months) {
      const cell = m.banks[bank];
      if (cell?.uploaded) {
        up++;
        db += cell.total_debit || 0;
        cr += cell.total_credit || 0;
      }
    }
    result[bank] = { uploaded: up, totalDebit: db, totalCredit: cr };
  }
  return result;
});

// ---- Formatters ----
const formatAmount = (v) => new Intl.NumberFormat('id-ID').format(Math.round(v || 0));

const formatCompact = (v) => {
  const n = Math.round(v || 0);
  if (n >= 1_000_000_000) return (n / 1_000_000_000).toFixed(1) + 'M';
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'jt';
  if (n >= 1_000) return (n / 1_000).toFixed(0) + 'rb';
  return String(n);
};

const formatBankCode = (code) => {
  const val = (code || '').toString();
  return val.replace('_CC', ' CC');
};

// ---- Actions ----
const refresh = () => store.fetchUploadChecklist(selectedYear.value);

const onYearChange = () => {
  activeBanks.value = new Set();
  store.fetchUploadChecklist(selectedYear.value);
};

const toggleBank = (bank) => {
  const next = new Set(activeBanks.value);
  if (next.has(bank) && next.size === 1) {
    // last active — show all
    next.clear();
  } else if (next.has(bank)) {
    next.delete(bank);
  } else if (next.size === 0) {
    // currently showing all, click isolates this bank
    const allBanks = checklist.value?.banks || [];
    allBanks.filter(b => b !== bank).forEach(b => next.add(b));
    // Actually filter to ONLY show clicked bank:
    next.clear();
    next.add(bank);
  } else {
    next.add(bank);
  }
  activeBanks.value = next;
};

onMounted(() => {
  store.fetchUploadChecklist(selectedYear.value);
});

watch(() => store.checklistYear, (y) => {
  if (y && y !== selectedYear.value) selectedYear.value = y;
});
</script>

<style scoped>
/* ── Year selector ─────────────────────────────── */
.checklist-year-select {
  @apply rounded-xl border px-3 py-2 text-sm font-semibold cursor-pointer;
  background: var(--color-surface);
  border-color: var(--color-border);
  color: var(--color-text);
  outline: none;
  transition: border-color 160ms;
}
.checklist-year-select:hover,
.checklist-year-select:focus {
  border-color: var(--color-primary);
}

/* ── Stat cards ────────────────────────────────── */
.stat-uploaded, .stat-missing, .stat-debit, .stat-credit {
  border-color: var(--color-border);
  background: var(--color-surface);
}

/* ── Skeleton loader ───────────────────────────── */
.skeleton-card {
  @apply rounded-2xl h-24 animate-pulse;
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
}

/* ── Table shell ───────────────────────────────── */
.checklist-table {
  border-collapse: separate;
  border-spacing: 0;
  width: 100%;
}

/* ── Header ────────────────────────────────────── */
.cl-th {
  @apply px-3 py-3 text-left text-[10px] font-bold uppercase tracking-widest;
  background: var(--color-surface-muted);
  color: var(--color-text-muted);
  border-bottom: 1px solid var(--color-border);
  white-space: nowrap;
}
.cl-th-month { @apply pl-5; min-width: 10rem; }
.cl-th-bank  { @apply text-center; min-width: 9rem; }

/* ── Rows ──────────────────────────────────────── */
.cl-row {
  transition: background 140ms;
  border-bottom: 1px solid var(--color-border);
}
.cl-row:hover { background: var(--color-surface-muted); }
.cl-row-current { background: rgba(15, 118, 110, 0.04); }

/* ── Month cell ────────────────────────────────── */
.cl-td-month {
  @apply pl-5 pr-4 py-3;
  border-right: 1px solid var(--color-border);
  white-space: nowrap;
}
.month-num {
  @apply text-xs font-bold font-mono;
  color: var(--color-text-muted);
}
.month-name {
  @apply text-sm font-medium;
  color: var(--color-text);
}
.current-badge {
  @apply text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-full;
  background: rgba(15, 118, 110, 0.15);
  color: var(--color-primary);
}

/* ── Bank data cell ────────────────────────────── */
.cl-td-cell {
  @apply px-3 py-2.5 text-center align-middle;
  border-right: 1px solid var(--color-border);
  transition: background 140ms;
}
.cell-uploaded { background: rgba(16, 185, 129, 0.03); }
.cell-missing  {}
.bank-hidden   { display: none; }

/* ── Cell — uploaded content ───────────────────── */
.cell-content-uploaded { @apply flex flex-col gap-0.5 items-start text-left; }
.cell-check-row        { @apply flex items-center gap-1.5; }
.cell-txn-count        { @apply text-[10px] font-semibold; color: var(--color-text-muted); }
.cell-amounts          { @apply flex flex-col gap-px mt-0.5; }
.amount-db  { @apply text-[10px] font-mono; color: #f87171; }
.amount-cr  { @apply text-[10px] font-mono; color: #34d399; }
.cell-filename {
  @apply text-[9px] truncate max-w-[8rem] mt-0.5;
  color: var(--color-text-muted);
}
.more-files {
  @apply ml-0.5 font-semibold;
  color: var(--color-primary);
}

/* ── Cell — missing ────────────────────────────── */
.cell-content-missing  { @apply flex items-center justify-center h-full py-1; }

/* ── Totals row ────────────────────────────────── */
.cl-totals-row {
  background: var(--color-surface-muted);
  border-top: 2px solid var(--color-border);
}
.cl-td-totals { @apply text-left; }
.totals-cell  { @apply flex flex-col gap-px; }
.totals-uploaded {
  @apply text-[10px] font-bold;
  color: var(--color-primary);
}

/* ── Bank filter chips ─────────────────────────── */
.bank-chip {
  @apply px-2 py-0.5 text-[10px] font-semibold rounded-full border transition-all;
  background: var(--color-surface);
  border-color: var(--color-border);
  color: var(--color-text-muted);
}
.bank-chip:hover        { border-color: var(--color-primary); color: var(--color-primary); }
.bank-chip-active       { background: rgba(15,118,110,0.10); border-color: rgba(15,118,110,0.25); color: var(--color-primary); }

/* ── Bank header name ──────────────────────────── */
.bank-name-label { @apply block text-center; }
</style>
