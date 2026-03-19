<template>
  <div class="space-y-6">
    <PageHeader
      eyebrow="General Ledger"
      icon="bi bi-journal-text"
      title="Ledger detail by account"
      subtitle="Telusuri pergerakan debit, kredit, dan saldo berjalan per akun untuk periode aktif."
    >
      <template #actions>
        <div class="flex items-center gap-2 relative">
          <Button
            v-if="ledgerData.coa_groups && ledgerData.coa_groups.length > 0"
            variant="secondary"
            @click="showExportMenu = !showExportMenu"
            class="gap-2"
          >
            <i class="bi bi-download"></i>
            <span>Export</span>
            <i class="bi bi-chevron-down text-xs transition-transform" :class="{ 'rotate-180': showExportMenu }"></i>
          </Button>
          
          <!-- Export Dropdown -->
          <div 
            v-if="showExportMenu" 
            class="ledger-menu absolute right-0 top-full mt-2 w-48 py-1 z-50 animate-in fade-in slide-in-from-top-2 duration-200"
          >
            <button
              @click="handleExport('excel')"
              class="ledger-menu__item"
            >
              <i class="bi bi-file-earmark-spreadsheet text-emerald-500"></i>
              Excel (.xlsx)
            </button>
            <button
              @click="handleExport('pdf')"
              class="ledger-menu__item"
            >
              <i class="bi bi-file-earmark-pdf text-rose-500"></i>
              PDF
            </button>
          </div>
        </div>
      </template>
    </PageHeader>

    <!-- Main Content -->
    <div class="space-y-6">
      <!-- Report Navigation Tabs -->
      <SectionCard body-class="p-3">
        <div class="reports-tab-wrap">
          <button
            v-for="tab in reportTabs"
            :key="tab.id"
            class="reports-tab"
            :class="{ 'reports-tab--active': tab.id === 'gl' }"
            @click="tab.id === 'gl' ? null : goToReports(tab.route)"
          >
            <i :class="[tab.icon, 'mr-2']"></i>
            {{ tab.label }}
          </button>
        </div>
      </SectionCard>

      <!-- Shared Filters -->
      <ReportFilters
        v-model="reportStore.filters"
        :available-years="reportStore.availableYears"
        :companies="companyStore.companies"
        :is-loading="loading"
      />

      <SectionCard body-class="p-4">
        <FormField label="COA Code (Opsional)" label-class="!text-xs" wrapper-class="md:w-80">
          <TextInput
            v-model="coaCode"
            type="text"
            placeholder="Contoh: 1101"
            prefix-icon="bi bi-search"
          />
        </FormField>
      </SectionCard>

      <!-- Summary Cards -->
      <div v-if="!loading && ledgerData.coa_groups?.length" class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard icon="bi bi-receipt" label="Total Transaksi" :value="ledgerData.total_transactions" variant="primary" />
        <StatCard icon="bi bi-arrow-up-circle" label="Total Debit" :value="formatCurrency(ledgerData.grand_total_debit)" variant="success" />
        <StatCard icon="bi bi-arrow-down-circle" label="Total Kredit" :value="formatCurrency(ledgerData.grand_total_credit)" variant="danger" />
      </div>

      <!-- Balance Alert -->
      <div v-if="!loading && ledgerData.coa_groups?.length" 
           :class="ledgerData.is_balanced 
             ? 'bg-success/5 border-success/20 text-success' 
             : 'bg-warning/5 border-warning/20 text-warning'" 
           class="rounded-2xl border p-4 flex items-start gap-4 shadow-sm">
        <div class="mt-0.5">
          <i :class="ledgerData.is_balanced ? 'bi bi-check-circle-fill' : 'bi bi-exclamation-triangle-fill'" class="text-lg"></i>
        </div>
        <div>
          <h4 class="font-bold text-sm">{{ ledgerData.is_balanced ? 'Balance!' : 'Unbalanced!' }}</h4>
          <p class="text-xs mt-1 opacity-90">
            <template v-if="!ledgerData.is_balanced">
              Selisih: <strong>{{ formatCurrency(Math.abs(ledgerData.grand_total_debit - ledgerData.grand_total_credit)) }}</strong> ditemukan di antara total debit dan kredit.
            </template>
            <template v-else>
              Total Debit dan Kredit seimbang secara akuntansi.
            </template>
          </p>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="flex flex-col items-center justify-center py-20 grayscale opacity-50">
        <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-primary"></div>
        <p class="mt-4 text-xs font-bold uppercase tracking-widest text-theme-muted">Memuat Data Ledger...</p>
      </div>

      <!-- No Data -->
      <div v-if="!loading && !ledgerData.coa_groups?.length" 
           class="flex flex-col items-center justify-center py-24 text-center">
        <div class="w-20 h-20 rounded-full bg-surface-muted flex items-center justify-center mb-6">
          <i class="bi bi-journal-x text-4xl text-theme-muted opacity-20"></i>
        </div>
        <h3 class="text-lg font-bold text-theme">Tidak Ada Data</h3>
        <p class="text-theme-muted text-sm mt-1 max-w-xs mx-auto">Belum ada transaksi untuk filter atau perusahaan yang dipilih dalam periode ini.</p>
      </div>

      <!-- Ledger Table -->
      <div v-if="!loading && ledgerData.coa_groups?.length" class="space-y-6">
        <div v-for="coaGroup in ledgerData.coa_groups" 
             :key="coaGroup.coa_code" 
             class="surface-card group/coa overflow-hidden rounded-2xl border border-border transition-all duration-300"
             :class="{ 'ring-1 ring-primary/20 shadow-lg': isExpanded(coaGroup.coa_code) }">
             
          <!-- COA Header (Sticky) -->
          <div class="ledger-group-header sticky top-0 z-30 flex items-center justify-between px-6 py-4 cursor-pointer hover:bg-surface-muted transition-colors"
               @click="toggleGroup(coaGroup.coa_code)">
            <div class="flex items-center gap-4">
              <div class="w-10 h-10 rounded-xl bg-primary/5 flex items-center justify-center text-primary transition-transform duration-300"
                   :class="{ 'rotate-90': isExpanded(coaGroup.coa_code) }">
                <i class="bi bi-chevron-right"></i>
              </div>
              <div>
                <h3 class="text-base font-bold text-theme flex items-center gap-2">
                  <span class="opacity-50 font-mono text-sm tracking-tighter">{{ coaGroup.coa_code }}</span>
                  {{ coaGroup.coa_name }}
                </h3>
                <p class="text-[10px] font-bold uppercase tracking-widest text-theme-muted opacity-60 mt-0.5">{{ coaGroup.coa_category }}</p>
              </div>
            </div>
            
            <div class="flex items-center gap-8">
              <div class="hidden md:flex items-center gap-8">
                <div class="text-right">
                  <p class="text-[9px] font-black uppercase text-theme-muted tracking-widest mb-1">Debit</p>
                  <p class="text-sm font-bold text-success">{{ formatCurrency(coaGroup.total_debit) }}</p>
                </div>
                <div class="text-right">
                  <p class="text-[9px] font-black uppercase text-theme-muted tracking-widest mb-1">Kredit</p>
                  <p class="text-sm font-bold text-danger">{{ formatCurrency(coaGroup.total_credit) }}</p>
                </div>
              </div>
              <div class="text-right min-w-[120px]">
                <p class="text-[9px] font-black uppercase text-theme-muted tracking-widest mb-1">Balance</p>
                <p class="text-base font-black" :class="coaGroup.ending_balance >= 0 ? 'text-primary' : 'text-danger'">
                  {{ formatCurrency(Math.abs(coaGroup.ending_balance)) }}
                </p>
              </div>
            </div>
          </div>
          
          <!-- Transactions Table (Collapsible) -->
          <div v-show="isExpanded(coaGroup.coa_code)" 
               class="overflow-x-auto border-t border-border animate-in slide-in-from-top-2 duration-300">
            <table class="min-w-full table-compact">
              <thead class="bg-surface-muted shadow-sm border-b border-border">
                <tr>
                  <th class="px-6 py-3 text-left w-[120px]">Tanggal</th>
                  <th class="px-6 py-3 text-left">Deskripsi</th>
                  <th class="px-6 py-3 text-left w-[150px]">Marking</th>
                  <th class="px-6 py-3 text-left w-[100px]">Akun</th>
                  <th class="px-6 py-3 text-right w-[140px]">Debit</th>
                  <th class="px-6 py-3 text-right w-[140px]">Kredit</th>
                  <th class="px-6 py-3 text-right w-[150px]">Saldo Berjalan</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-border">
                <template v-for="txn in coaGroup.transactions" :key="txn.transaction_id">
                  <tr v-for="(entry, idx) in txn.entries" 
                      :key="txn.transaction_id + '_' + idx"
                      class="ledger-row group/row transition-colors"
                      :class="{ 'bg-primary/5': idx === 0 }">
                    <td class="px-6 py-4 whitespace-nowrap text-xs font-medium text-theme opacity-80">
                      <div v-if="idx === 0">{{ formatDate(txn.txn_date) }}</div>
                    </td>
                    <td class="px-6 py-4 text-sm text-theme">
                      <div v-if="idx === 0" class="font-bold leading-snug">{{ txn.description }}</div>
                      <div v-else class="text-theme-muted text-[11px] font-medium flex items-center gap-2 mt-1 opacity-70">
                        <i class="bi bi-arrow-return-right text-primary/40"></i>
                        <span>Splits: {{ entry.coa_code }}</span>
                      </div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                      <div v-if="idx === 0 && txn.mark_name" 
                           class="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-black uppercase tracking-widest bg-surface-raised border border-border text-theme-muted">
                        {{ txn.mark_name }}
                      </div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-xs font-bold">
                       <span :class="idx === 0 ? 'text-primary' : 'text-theme-muted opacity-60'">
                        {{ entry.coa_code }}
                      </span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-right font-mono font-bold">
                      <span v-if="entry.debit > 0" class="text-success">
                        {{ formatAmount(entry.debit) }}
                      </span>
                      <span v-else class="text-theme-muted opacity-20">-</span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-right font-mono font-bold">
                      <span v-if="entry.credit > 0" class="text-danger">
                        {{ formatAmount(entry.credit) }}
                      </span>
                      <span v-else class="text-theme-muted opacity-20">-</span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-right font-mono">
                      <div v-if="idx === 0" 
                           class="font-black" 
                           :class="entry.current_entry?.running_balance >= 0 ? 'text-primary' : 'text-danger'">
                        {{ formatAmount(Math.abs(entry.current_entry?.running_balance || 0)) }}
                      </div>
                      <div v-else class="text-[10px] text-theme-muted opacity-30">...</div>
                    </td>
                  </tr>
                </template>
              </tbody>
            </table>
            
            <div class="px-6 py-4 bg-surface-muted/30 border-t border-border flex justify-between items-center text-[11px] font-bold text-theme-muted uppercase tracking-widest">
              <span>Account End Activity</span>
              <div class="flex gap-4">
                <span>Total Debit: <span class="text-success">{{ formatAmount(coaGroup.total_debit) }}</span></span>
                <span>Total Kredit: <span class="text-danger">{{ formatAmount(coaGroup.total_credit) }}</span></span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, onBeforeUnmount } from 'vue';
import { useRouter } from 'vue-router';
import ReportFilters from '../components/reports/ReportFilters.vue';
import FormField from '../components/ui/FormField.vue';
import PageHeader from '../components/ui/PageHeader.vue';
import SectionCard from '../components/ui/SectionCard.vue';
import StatCard from '../components/ui/StatCard.vue';
import TextInput from '../components/ui/TextInput.vue';
import Button from '../components/ui/Button.vue';
import { useReportsStore } from '../stores/reports';
import { useCompanyStore } from '../stores/companies';

const router = useRouter();
const reportStore = useReportsStore();
const companyStore = useCompanyStore();

// State
const loading = ref(false);
const showExportMenu = ref(false);
const coaCode = ref('');
const expandedGroups = ref(new Set());
const ledgerData = ref({
  company_id: '',
  start_date: '',
  end_date: '',
  coa_groups: [],
  total_accounts: 0,
  total_transactions: 0,
  grand_total_debit: 0,
  grand_total_credit: 0,
  is_balanced: true
});

let autoLoadTimer = null;
let filterWatchStop = null;
let companyWatchStop = null;

const reportTabs = [
  { id: 'income-statement', label: 'Income Statement', route: 'income-statement', icon: 'bi bi-file-earmark-bar-graph' },
  { id: 'monthly-revenue', label: 'Monthly Revenue', route: 'monthly-revenue', icon: 'bi bi-calendar3' },
  { id: 'balance-sheet', label: 'Balance Sheet', route: 'balance-sheet', icon: 'bi bi-file-earmark-spreadsheet' },
  { id: 'cash-flow', label: 'Cash Flow', route: 'cash-flow', icon: 'bi bi-cash-stack' },
  { id: 'gl', label: 'GL', route: 'gl', icon: 'bi bi-journal-text' },
  { id: 'payroll-summary', label: 'Payroll Summary', route: 'payroll-summary', icon: 'bi bi-people' },
  { id: 'marks-report', label: 'Marks Summary', route: 'marks-report', icon: 'bi bi-tags' }
];

// Methods
const goToReports = (tab) => {
  router.push({ name: 'reports', query: { tab } });
};

const formatAmount = (num) => {
  return new Intl.NumberFormat('id-ID').format(num || 0);
};

const formatCurrency = (amount) => {
  return `Rp ${formatAmount(amount)}`;
};

const formatDate = (dateStr) => {
  if (!dateStr) return '-';
  const date = new Date(dateStr);
  return date.toLocaleDateString('id-ID', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
};

const isExpanded = (code) => expandedGroups.value.has(code);

const toggleGroup = (code) => {
  if (expandedGroups.value.has(code)) {
    expandedGroups.value.delete(code);
  } else {
    expandedGroups.value.add(code);
  }
};

const loadGeneralLedger = async () => {
  loading.value = true;
  try {
    const params = new URLSearchParams({
      start_date: reportStore.filters.startDate,
      end_date: reportStore.filters.endDate,
      report_type: (reportStore.filters.reportType || 'real').toLowerCase()
    });

    if (reportStore.filters.companyId) {
      params.append('company_id', reportStore.filters.companyId);
    }
    if (coaCode.value?.trim()) {
      params.append('coa_code', coaCode.value.trim());
    }

    const response = await fetch(`/api/reports/general-ledger?${params}`);
    const data = await response.json();

    if (data.success) {
      ledgerData.value = data.data;
      // Auto-expand if only one account
      if (data.data.coa_groups?.length === 1) {
        expandedGroups.value.add(data.data.coa_groups[0].coa_code);
      }
    } else {
      ledgerData.value = { ...ledgerData.value, coa_groups: [] };
    }
  } catch (error) {
    console.error('Error loading general ledger:', error);
    ledgerData.value = { ...ledgerData.value, coa_groups: [] };
  } finally {
    loading.value = false;
  }
};

const scheduleAutoLoad = () => {
  if (!reportStore.filters.startDate || !reportStore.filters.endDate) return;
  if (autoLoadTimer) clearTimeout(autoLoadTimer);
  autoLoadTimer = setTimeout(loadGeneralLedger, 300);
};

const bootstrap = async () => {
  await companyStore.fetchCompanies();
  await reportStore.loadFilters();
  await reportStore.fetchAvailableYears(reportStore.filters.companyId || null);
  
  // Sync logic simplified: assume store state is mostly correct or managed by ReportFilters
  await loadGeneralLedger();

  filterWatchStop = watch(
    () => ({ ...reportStore.filters, coCode: coaCode.value }),
    async () => {
      await reportStore.saveFilters();
      scheduleAutoLoad();
    },
    { deep: true }
  );

  companyWatchStop = watch(
    () => reportStore.filters.companyId,
    async (companyId, oldId) => {
      if (companyId === oldId) return;
      await reportStore.fetchAvailableYears(companyId || null);
    }
  );
};

const handleExport = async (format) => {
  showExportMenu.value = false;
  try {
    const params = new URLSearchParams({
      start_date: reportStore.filters.startDate,
      end_date: reportStore.filters.endDate,
      report_type: (reportStore.filters.reportType || 'real').toLowerCase(),
      format
    });

    if (reportStore.filters.companyId) params.append('company_id', reportStore.filters.companyId);
    if (coaCode.value?.trim()) params.append('coa_code', coaCode.value.trim());

    const response = await fetch(`/api/reports/general-ledger/export?${params}`);
    if (response.ok) {
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      const companyLabel = reportStore.filters.companyId || 'all';
      a.href = url;
      a.download = `GL-${companyLabel}-${reportStore.filters.startDate}-${reportStore.filters.endDate}.${format === 'excel' ? 'xlsx' : 'pdf'}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    }
  } catch (error) {
    console.error('Export error:', error);
  }
};

onMounted(bootstrap);

onBeforeUnmount(() => {
  if (autoLoadTimer) clearTimeout(autoLoadTimer);
  if (filterWatchStop) filterWatchStop();
  if (companyWatchStop) companyWatchStop();
});
</script>

<style scoped>
.reports-tab-wrap {
  @apply flex gap-2 overflow-x-auto;
  -ms-overflow-style: none;
  scrollbar-width: none;
}

.reports-tab-wrap::-webkit-scrollbar {
  display: none;
}

.reports-tab {
  @apply inline-flex items-center whitespace-nowrap rounded-2xl px-4 py-2.5 text-sm font-medium transition-all;
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
  color: var(--color-text-muted);
}

.reports-tab:hover {
  border-color: var(--color-border-strong);
  color: var(--color-text);
}

.reports-tab--active {
  background: rgba(15, 118, 110, 0.12);
  border-color: rgba(15, 118, 110, 0.18);
  color: var(--color-primary);
  box-shadow: var(--shadow-soft);
}

.reports-menu {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 16px;
  box-shadow: var(--shadow-card);
  overflow: hidden;
}

.reports-menu__item {
  @apply flex w-full items-center gap-2 px-4 py-2 text-left text-sm transition-colors;
  color: var(--color-text);
}

.reports-menu__item:hover {
  background: var(--color-surface-muted);
}

.ledger-group-header {
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border-muted);
}

.surface-card:hover .ledger-group-header {
  background: var(--color-surface-muted);
}

.ledger-row:hover {
  background: var(--color-primary-light);
}

.ledger-group-header.sticky {
  box-shadow: 0 1px 0 0 var(--color-border);
}
</style>
