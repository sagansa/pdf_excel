<template>
  <div class="space-y-5">
    <PageHeader
      eyebrow="Upload Checklist"
      icon="bi bi-check2-square"
      title="Yearly upload status per bank account"
      subtitle="Pantau kelengkapan upload file statement per bulan, per akun bank. BCA atau bank lain bisa dipisah menjadi beberapa rekening."
    >
      <template #actions>
        <div class="flex items-center gap-2">
          <!-- Year Selector -->
          <select
            v-model="selectedYear"
            @change="onYearChange"
            class="checklist-year-select"
            aria-label="Tahun checklist"
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
    <template v-if="store.isLoading && !checklist">
      <div class="skl skl-progress"></div>
      <div class="cl-main">
        <div class="flex flex-col gap-2.5">
          <div v-for="i in 3" :key="i" class="skl skl-bank"></div>
        </div>
        <div class="skl skl-grid"></div>
      </div>
    </template>

    <!-- Error -->
    <div v-else-if="store.error && !checklist" class="section-card cl-notice">
      <i class="bi bi-exclamation-triangle-fill text-2xl" style="color: var(--color-danger)"></i>
      <p class="cl-notice__text">Gagal memuat checklist. Periksa koneksi lalu coba muat ulang.</p>
      <button type="button" class="btn-primary" @click="refresh">
        <i class="bi bi-arrow-clockwise"></i> Muat ulang
      </button>
    </div>

    <template v-else-if="checklist">
      <!-- Empty: no bank columns at all -->
      <div v-if="checklistColumns.length === 0" class="section-card cl-notice">
        <i class="bi bi-inbox text-2xl" style="color: var(--color-text-muted)"></i>
        <p class="cl-notice__text">
          Belum ada data statement untuk {{ selectedYear }}. Upload statement lewat menu
          <strong>Converter</strong>, atau pisahkan rekening di Kelola Akun Bank di bawah.
        </p>
      </div>

      <template v-else>
        <!-- Year progress card -->
        <div class="cl-progress-card">
          <div class="cl-pct">
            <span class="cl-pct__value">{{ summary.pct }}%</span>
            <small class="cl-pct__caption">{{ summary.uploaded }}/{{ summary.total }} slot</small>
          </div>

          <div class="cl-slotzone">
            <div class="cl-slotbar" :key="selectedYear" aria-hidden="true">
              <div v-for="(group, gi) in slotGroups" :key="gi" class="cl-slotgrp">
                <span
                  v-for="seg in group"
                  :key="seg.key"
                  class="cl-seg"
                  :class="`seg-${seg.state}`"
                  :style="{ animationDelay: seg.delay + 'ms' }"
                ></span>
              </div>
            </div>
            <div class="cl-legend">
              <span><i class="lg-dot seg-up"></i>Terupload <b>{{ summary.uploaded }}</b></span>
              <span><i class="lg-dot seg-miss"></i>Bolong <b>{{ summary.missing }}</b></span>
              <span><i class="lg-dot seg-imb"></i>di antaranya selisih DB/CR <b>{{ summary.imbalanced }}</b></span>
              <span><i class="lg-dot seg-fut"></i>Belum jatuh tempo <b>{{ summary.future }}</b></span>
            </div>
          </div>

          <div class="cl-yeartotals">
            <span>Total Debit {{ selectedYear }} <b>{{ formatAmount(summary.totalDebit) }}</b></span>
            <span>Total Kredit {{ selectedYear }} <b>{{ formatAmount(summary.totalCredit) }}</b></span>
          </div>
        </div>

        <!-- Main: bank rail + month grid -->
        <div class="cl-main">
          <!-- Bank rail -->
          <aside class="cl-rail">
            <button
              v-for="bank in railBanks"
              :key="bank.key"
              type="button"
              class="cl-bankcard"
              :class="{
                'cl-bankcard-focus': activeBanks.has(bank.key),
                'cl-bankcard-dim': activeBanks.size > 0 && !activeBanks.has(bank.key),
              }"
              :aria-pressed="activeBanks.has(bank.key)"
              :title="`Klik untuk ${activeBanks.has(bank.key) ? 'menampilkan semua bank' : 'fokus pada ' + bank.name}`"
              @click="toggleBank(bank.key)"
            >
              <div class="bc-head">
                <span class="bc-name">{{ bank.name }}</span>
                <span class="bc-state" :class="bank.stateClass">{{ bank.stateLabel }}</span>
              </div>
              <div v-if="bank.accountNumber" class="bc-acct">····{{ bank.accountNumber }}</div>
              <div class="bc-strip" aria-hidden="true">
                <i
                  v-for="cell in bank.strip"
                  :key="cell.month"
                  :class="`seg-${cell.state}`"
                ></i>
              </div>
              <div class="bc-meta">
                <span class="bc-frac">{{ bank.uploadedCount }}/12</span>
                <span class="bc-nums" :title="`${bank.txnCount} txn · DB ${formatAmount(bank.totalDebit)} · CR ${formatAmount(bank.totalCredit)}`">{{ bank.txnCount }} txn · DB {{ formatCompact(bank.totalDebit) }} · CR {{ formatCompact(bank.totalCredit) }}</span>
              </div>
            </button>

            <button
              type="button"
              class="cl-defs-link"
              :aria-expanded="defsOpen"
              :title="defsOpen ? 'Tutup kelola akun bank' : 'Buka kelola akun bank'"
              @click="toggleBankDefs"
            >
              <span class="cl-defs-link__label">
                <i class="bi bi-gear"></i> Kelola Akun Bank
              </span>
              <span class="cl-defs-link__meta">
                <i class="bi bi-chevron-down" :class="{ 'cl-defs-link__chev--open': defsOpen }"></i>
              </span>
            </button>
          </aside>

          <!-- Month grid -->
          <SectionCard
            :title="`Checklist ${selectedYear}`"
            subtitle="Arahkan kursor ke sel untuk detail file dan periode upload · klik kartu bank untuk memfokuskan satu rekening."
            body-class="p-4 overflow-x-auto"
          >
            <div class="cl-monthgrid">
              <div
                v-for="monthRow in checklist.months"
                :key="monthRow.month"
                class="cl-mcol"
                :class="{
                  'cl-mcol-now': isCurrentMonth(monthRow.month),
                  'cl-mcol-future': isFutureMonth(monthRow.month) && !isCurrentMonth(monthRow.month),
                }"
              >
                <div class="cl-mhead">
                  <span class="mh-name">
                    {{ shortMonthName(monthRow.month) }}
                    <span v-if="isCurrentMonth(monthRow.month)" class="mh-now">now</span>
                  </span>
                  <span class="mh-num">{{ String(monthRow.month).padStart(2, '0') }}</span>
                </div>

                <div
                  v-for="column in checklistColumns"
                  :key="column.key"
                  class="cl-cell"
                  :class="[
                    cellState(monthRow, column),
                    { 'cl-cell-dim': activeBanks.size > 0 && !activeBanks.has(column.key) },
                  ]"
                  :title="cellTitle(monthRow, column)"
                >
                  <!-- Uploaded -->
                  <template v-if="monthRow.banks[column.key]?.uploaded">
                    <div class="cu-top">
                      <span class="cu-tag">{{ shortTag(column) }}</span>
                      <i
                        v-if="hasLargeImbalance(monthRow.banks[column.key])"
                        class="bi bi-exclamation-triangle-fill cu-flag"
                      ></i>
                    </div>
                    <div class="cu-txn">{{ monthRow.banks[column.key].transaction_count }} txn</div>
                    <div class="cu-amt">
                      <span class="amt-db">D {{ formatCompact(monthRow.banks[column.key].total_debit) }}</span>
                      <span class="amt-cr">C {{ formatCompact(monthRow.banks[column.key].total_credit) }}</span>
                    </div>
                  </template>

                  <!-- Missing -->
                  <template v-else-if="!isFutureMonth(monthRow.month)">
                    <div class="cm-mark"><i class="bi bi-exclamation-lg"></i></div>
                  </template>

                  <!-- Not yet due -->
                  <template v-else>
                    <div class="cf-mark"><i class="bi bi-dash"></i></div>
                  </template>
                </div>
              </div>
            </div>
          </SectionCard>
        </div>
      </template>
    </template>

    <BankAccountDefinitionsCard ref="defsCard" @changed="refresh" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import BankAccountDefinitionsCard from '../components/uploads/BankAccountDefinitionsCard.vue';
import PageHeader from '../components/ui/PageHeader.vue';
import SectionCard from '../components/ui/SectionCard.vue';
import { useHistoryStore } from '../stores/history';

const store = useHistoryStore();
const currentYear = new Date().getFullYear();

// Year options: from 2020 up to current year + 1
const availableYears = computed(() => {
  const years = [];
  for (let y = currentYear + 1; y >= 2020; y--) years.push(y);
  return years;
});

const selectedYear = ref(store.checklistYear || currentYear);
const activeBanks = ref(new Set()); // empty = show all

const defsCard = ref(null);

const checklist = computed(() => store.uploadChecklist);
const checklistColumns = computed(() => {
  if (!checklist.value) return [];

  if (Array.isArray(checklist.value.columns) && checklist.value.columns.length > 0) {
    return checklist.value.columns;
  }

  return (checklist.value.banks || []).map((bank) => ({
    key: bank,
    label: formatBankCode(bank),
    bank_code: bank,
    account_number: null,
    display_name: null,
  }));
});

const MONTH_SHORT = {
  1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'Mei', 6: 'Jun',
  7: 'Jul', 8: 'Ags', 9: 'Sep', 10: 'Okt', 11: 'Nov', 12: 'Des',
};

const shortMonthName = (month) => MONTH_SHORT[month] || String(month);

const isCurrentMonth = (month) => {
  const now = new Date();
  return now.getFullYear() === selectedYear.value && now.getMonth() + 1 === month;
};

// A slot is "belum jatuh tempo" when its month has not ended yet
const isFutureMonth = (month) => {
  const now = new Date();
  if (selectedYear.value > now.getFullYear()) return true;
  if (selectedYear.value < now.getFullYear()) return false;
  return month > now.getMonth() + 1;
};

const hasLargeImbalance = (cell) => {
  if (!cell || !cell.uploaded) return false;
  const max = Math.max(cell.total_debit, cell.total_credit);
  if (max === 0) return false;
  const delta = Math.abs(cell.total_debit - cell.total_credit);
  return delta / max > 0.3; // flag if >30% difference
};

const cellState = (monthRow, column) => {
  const cell = monthRow.banks[column.key];
  if (cell?.uploaded) return 'cs-up';
  return isFutureMonth(monthRow.month) ? 'cs-fut' : 'cs-miss';
};

const slotState = (monthRow, column) => {
  const cell = monthRow.banks[column.key];
  if (cell?.uploaded) return hasLargeImbalance(cell) ? 'imb' : 'up';
  return isFutureMonth(monthRow.month) ? 'fut' : 'miss';
};

// Segments of the year slot bar, grouped by month
const slotGroups = computed(() => {
  if (!checklist.value) return [];
  const months = checklist.value.months || [];
  const banks = checklistColumns.value;
  let idx = 0;
  return months.map((m) =>
    banks.map((column) => ({
      key: `${m.month}-${column.key}`,
      state: slotState(m, column),
      delay: Math.min(idx++ * 8, 800),
    }))
  );
});

// ---- Computed summaries ----
const summary = computed(() => {
  if (!checklist.value) return { uploaded: 0, missing: 0, future: 0, imbalanced: 0, total: 0, pct: 0, totalDebit: 0, totalCredit: 0 };
  let uploaded = 0, missing = 0, future = 0, imbalanced = 0, totalDebit = 0, totalCredit = 0;
  const banks = checklistColumns.value;
  const months = checklist.value.months || [];
  const totalSlots = months.length * banks.length;
  for (const m of months) {
    for (const bank of banks) {
      const cell = m.banks[bank.key];
      if (cell?.uploaded) {
        uploaded++;
        if (hasLargeImbalance(cell)) imbalanced++;
        totalDebit += cell.total_debit || 0;
        totalCredit += cell.total_credit || 0;
      } else if (isFutureMonth(m.month)) {
        future++;
      } else {
        missing++;
      }
    }
  }
  const pct = totalSlots > 0 ? Math.round((uploaded / totalSlots) * 100) : 0;
  return { uploaded, missing, future, imbalanced, total: totalSlots, pct, totalDebit, totalCredit };
});

const railBanks = computed(() => {
  if (!checklist.value) return [];
  const months = checklist.value.months || [];
  return checklistColumns.value.map((column) => {
    let uploadedCount = 0, missingCount = 0, futureCount = 0, txnCount = 0;
    let totalDebit = 0, totalCredit = 0;
    const strip = months.map((m) => {
      const state = slotState(m, column);
      const cell = m.banks[column.key];
      if (state === 'up' || state === 'imb') {
        uploadedCount++;
        txnCount += cell.transaction_count || 0;
        totalDebit += cell.total_debit || 0;
        totalCredit += cell.total_credit || 0;
      } else if (state === 'miss') {
        missingCount++;
      } else {
        futureCount++;
      }
      return { month: m.month, state };
    });

    let stateLabel = 'Lengkap';
    let stateClass = 'st-ok';
    if (missingCount > 0) {
      stateLabel = `Bolong ${missingCount}`;
      stateClass = 'st-miss';
    } else if (uploadedCount === 0 && futureCount > 0) {
      stateLabel = 'Belum mulai';
      stateClass = 'st-fut';
    }

    return {
      key: column.key,
      name: formatChecklistColumnLabel(column),
      accountNumber: column.account_number ? String(column.account_number).slice(-4) : null,
      strip,
      uploadedCount,
      missingCount,
      txnCount,
      totalDebit,
      totalCredit,
      stateLabel,
      stateClass,
    };
  });
});

// ---- Formatters ----
const formatAmount = (v) => new Intl.NumberFormat('id-ID').format(Math.round(v || 0));

const formatCompact = (v) => {
  const n = Math.round(v || 0);
  if (n >= 1_000_000_000) return (n / 1_000_000_000).toFixed(1) + 'M';
  if (n >= 10_000_000) return Math.round(n / 1_000_000) + 'jt';
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'jt';
  if (n >= 1_000) return Math.round(n / 1_000) + 'rb';
  return String(n);
};

const formatBankCode = (code) => {
  const val = (code || '').toString();
  return val.replace('_CC', ' CC');
};

const formatChecklistColumnLabel = (column) => {
  if (!column) return '';
  if (column.label) return column.label;

  const bankLabel = formatBankCode(column.bank_code || column.key);
  if (column.display_name) return `${bankLabel} · ${column.display_name}`;
  if (column.account_number) return `${bankLabel} · ${String(column.account_number).slice(-4)}`;
  return bankLabel;
};

// Short tag inside a grid cell; disambiguates when one bank has several accounts
const shortTag = (column) => {
  let tag = formatBankCode(column.bank_code || column.key);
  const sameBank = checklistColumns.value.filter((c) => (c.bank_code || c.key) === (column.bank_code || column.key));
  if (sameBank.length > 1) {
    tag += column.account_number ? `·${String(column.account_number).slice(-2)}` : '·U';
  }
  return tag;
};

const cellTitle = (monthRow, column) => {
  const cell = monthRow.banks[column.key];
  const period = `${monthRow.label} ${selectedYear.value}`;
  if (!cell?.uploaded) {
    if (isFutureMonth(monthRow.month)) {
      return `Belum jatuh tempo — ${period}`;
    }
    return `Belum ada upload — ${formatChecklistColumnLabel(column)} · ${period}`;
  }
  const lines = [
    `${formatChecklistColumnLabel(column)} · ${period}`,
    `${cell.transaction_count} txn · DB ${formatAmount(cell.total_debit)} · CR ${formatAmount(cell.total_credit)}`,
  ];
  if (cell.source_files?.length) {
    const more = cell.source_files.length > 1 ? ` (+${cell.source_files.length - 1} file lain)` : '';
    lines.push(`File: ${cell.source_files[0]}${more}`);
  }
  if (cell.last_upload) lines.push(`Terakhir upload: ${cell.last_upload}`);
  if (hasLargeImbalance(cell)) {
    lines.push(`⚠ Selisih DB/CR besar: Rp ${formatAmount(Math.abs(cell.total_debit - cell.total_credit))}`);
  }
  return lines.join('\n');
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
    next.add(bank);
  } else {
    next.add(bank);
  }
  activeBanks.value = next;
};

const defsOpen = computed(() => !!defsCard.value?.expanded);

const toggleBankDefs = () => defsCard.value?.toggleFromParent();

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

/* ── Skeleton loader ───────────────────────────── */
.skl {
  @apply animate-pulse rounded-2xl;
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
}
.skl-progress { @apply h-24; }
.skl-bank    { @apply h-24; }
.skl-grid    { @apply min-h-[26rem] flex-1; }

/* ── Notice (error / empty) ────────────────────── */
.cl-notice {
  @apply flex flex-col items-center justify-center gap-3 p-10 text-center;
}
.cl-notice__text {
  @apply max-w-md text-sm leading-relaxed;
  color: var(--color-text-muted);
}

/* ── Year progress card ────────────────────────── */
.cl-progress-card {
  @apply flex items-center gap-6 px-6 py-4;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
}
.cl-pct { @apply flex flex-col; }
.cl-pct__value {
  @apply font-mono font-semibold leading-none;
  font-size: 2.1rem;
  color: var(--color-primary);
}
.cl-pct__caption {
  @apply mt-1.5 text-[11px] font-bold uppercase tracking-widest;
  color: var(--color-text-muted);
}
.cl-slotzone { @apply flex min-w-0 flex-1 flex-col gap-2; }
.cl-slotbar { @apply flex gap-1.5; }
.cl-slotgrp { @apply flex min-w-0 flex-1 gap-px; }
.cl-seg {
  @apply min-w-0 flex-1;
  height: 14px;
  border-radius: 3px;
  transform-origin: left center;
  animation: seg-in 320ms cubic-bezier(0.22, 1, 0.36, 1) both;
}
.seg-up   { background: var(--color-primary); }
.seg-miss { background: color-mix(in srgb, var(--color-danger) 68%, var(--color-surface)); }
.seg-imb  { background: var(--color-accent); }
.seg-fut  { background: var(--color-border); opacity: 0.55; }
@keyframes seg-in {
  from { transform: scaleX(0); opacity: 0.3; }
  to   { transform: scaleX(1); opacity: 1; }
}
@media (prefers-reduced-motion: reduce) {
  .cl-seg { animation: none; }
}
.cl-legend {
  @apply flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px];
  color: var(--color-text-muted);
}
.cl-legend b {
  @apply font-mono font-semibold;
  color: var(--color-text);
}
.lg-dot {
  @apply mr-1.5 inline-block h-2 w-2 rounded-sm align-middle;
}
.cl-yeartotals {
  @apply flex shrink-0 flex-col gap-0.5 text-[11px] text-right;
  color: var(--color-text-muted);
}
.cl-yeartotals b {
  @apply ml-1 font-mono font-semibold;
  color: var(--color-text);
}

/* ── Main layout ───────────────────────────────── */
.cl-main {
  @apply grid items-start gap-4;
  grid-template-columns: 256px minmax(0, 1fr);
}

/* ── Bank rail ─────────────────────────────────── */
.cl-rail {
  @apply flex flex-col gap-2.5;
}
.cl-bankcard {
  @apply w-full cursor-pointer rounded-2xl border p-3.5 text-left transition-all;
  background: var(--color-surface);
  border-color: var(--color-border);
}
.cl-bankcard:hover { border-color: var(--color-primary); }
.cl-bankcard:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px var(--color-primary-ring);
  border-color: var(--color-primary);
}
.cl-bankcard-focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-ring);
}
.cl-bankcard-dim { opacity: 0.45; }
.bc-head { @apply flex items-start justify-between gap-2; }
.bc-name {
  @apply text-[13px] font-extrabold leading-snug;
  color: var(--color-text);
}
.bc-state { @apply shrink-0 text-[11px] font-extrabold; }
.st-ok   { color: var(--color-primary); }
.st-miss { color: var(--color-danger); }
.st-fut  { color: var(--color-text-muted); }
.bc-acct {
  @apply mt-0.5 font-mono text-[11px];
  color: var(--color-text-muted);
}
.bc-strip {
  @apply my-2 grid grid-cols-12 gap-px;
}
.bc-strip i { height: 8px; border-radius: 2px; }
.bc-meta { @apply flex items-baseline justify-between gap-2 text-[11px]; color: var(--color-text-muted); }
.bc-frac {
  @apply shrink-0 font-mono text-[11px] font-bold;
  color: var(--color-primary);
}
.bc-nums { @apply min-w-0 truncate font-mono text-[11px]; }

/* ── Rail link to definitions ──────────────────── */
.cl-defs-link {
  @apply flex w-full cursor-pointer items-center justify-between gap-2 rounded-2xl border border-dashed px-3.5 py-2.5 text-left transition-all;
  border-color: var(--color-border-strong);
  background: transparent;
  color: var(--color-text-muted);
}
.cl-defs-link:hover,
.cl-defs-link[aria-expanded='true'] { border-color: var(--color-primary); color: var(--color-primary); }
.cl-defs-link__label { @apply flex items-center gap-2 text-[12px] font-bold; }
.cl-defs-link__meta { @apply flex items-center gap-1.5 text-[11px]; }
.cl-defs-link__chev--open { transform: rotate(180deg); }

/* ── Month grid ────────────────────────────────── */
.cl-monthgrid {
  @apply grid gap-1.5;
  grid-template-columns: repeat(12, minmax(60px, 1fr));
  min-width: 790px;
}
.cl-mcol { @apply flex flex-col gap-1; }
.cl-mhead {
  @apply flex min-h-[52px] flex-col items-center justify-start border-b-2 pb-1.5 pt-1;
  border-color: var(--color-border);
}
.mh-name { @apply flex items-center gap-1 text-[11.5px] font-extrabold; color: var(--color-text-muted); }
.mh-num  { @apply font-mono text-[11px] opacity-70; color: var(--color-text-muted); }
.cl-mcol-now .cl-mhead { border-color: var(--color-primary); }
.cl-mcol-now .mh-name,
.cl-mcol-now .mh-num { color: var(--color-primary); opacity: 1; }
.cl-mcol-future { opacity: 0.55; }
.mh-now {
  @apply rounded-full px-1.5 py-px text-[11px] font-extrabold uppercase leading-none tracking-wider;
  background: var(--color-primary-ring);
  color: var(--color-primary);
}

/* ── Cells ─────────────────────────────────────── */
.cl-cell {
  @apply relative h-[76px] overflow-hidden rounded-[10px] p-1.5 text-left transition-opacity;
  font-size: 11px;
}
.cs-up {
  background: color-mix(in srgb, var(--color-primary) 7%, transparent);
  border: 1px solid color-mix(in srgb, var(--color-primary) 22%, transparent);
}
.cs-miss {
  background: color-mix(in srgb, var(--color-danger) 5%, transparent);
  border: 1.5px dashed color-mix(in srgb, var(--color-danger) 45%, transparent);
}
.cs-fut {
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
}
.cl-cell-dim { opacity: 0.25; }

.cu-top { @apply flex items-center; }
.cu-tag {
  @apply min-w-0 truncate text-[11px] font-extrabold uppercase tracking-tight;
  color: var(--color-text-muted);
}
.cu-flag {
  @apply absolute bottom-1.5 right-1.5 text-[11px];
  color: var(--color-accent);
}
.cu-txn {
  @apply mt-1 font-mono text-[11px] font-semibold;
  color: var(--color-text);
}
.cu-amt { @apply mt-0.5 flex flex-col font-mono text-[11px] leading-tight; }
.amt-db { color: var(--color-danger); }
.amt-cr { color: var(--color-success); }

.cm-mark {
  @apply flex h-full items-center justify-center;
  color: color-mix(in srgb, var(--color-danger) 60%, transparent);
  font-size: 14px;
}
.cf-mark {
  @apply flex h-full items-center justify-center;
  color: var(--color-text-muted);
  opacity: 0.5;
  font-size: 13px;
}

/* ── Responsive ────────────────────────────────── */
@media (max-width: 1180px) {
  .cl-main { grid-template-columns: minmax(0, 1fr); }
  .cl-rail {
    @apply static grid grid-cols-2 gap-2.5;
  }
  .cl-defs-link { @apply col-span-2; }
}
@media (max-width: 640px) {
  .cl-rail { grid-template-columns: 1fr; }
  .cl-defs-link { @apply col-span-1; }
  .cl-progress-card { @apply flex-col items-start gap-3; }
  .cl-yeartotals { @apply text-left; }
}

/* ── Dark theme lifts ──────────────────────────── */
.dark .cs-miss {
  background: color-mix(in srgb, var(--color-danger) 9%, transparent);
  border-color: color-mix(in srgb, var(--color-danger) 62%, transparent);
}
.dark .cm-mark {
  color: color-mix(in srgb, var(--color-danger) 78%, transparent);
}
.dark .cl-cell-dim { opacity: 0.3; }
</style>
