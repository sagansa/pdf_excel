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
            <button
              v-if="ledgerData.coa_groups && ledgerData.coa_groups.length > 0"
              @click="showExportMenu = !showExportMenu"
              class="btn-secondary gap-2"
            >
              <i class="bi bi-download"></i>
              <span>Export</span>
              <i class="bi bi-chevron-down text-xs"></i>
            </button>
            
            <!-- Export Dropdown -->
            <div 
              v-if="showExportMenu" 
              class="ledger-menu absolute right-0 top-full mt-2 w-48 py-1 z-50"
            >
              <button
                @click="handleExport('excel')"
                class="ledger-menu__item"
              >
                <i class="bi bi-file-earmark-spreadsheet text-green-600"></i>
                Excel (.xlsx)
              </button>
              <button
                @click="handleExport('pdf')"
                class="ledger-menu__item"
              >
                <i class="bi bi-file-earmark-pdf text-red-600"></i>
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
        <div class="ledger-tabs">
            <button
              @click="goToReports('income-statement')"
              class="ledger-tab"
            >
              <i class="bi bi-file-earmark-bar-graph mr-2"></i>
              Income Statement
            </button>
            <button
              @click="goToReports('monthly-revenue')"
              class="ledger-tab"
            >
              <i class="bi bi-calendar3 mr-2"></i>
              Monthly Revenue
            </button>
            <button
              @click="goToReports('balance-sheet')"
              class="ledger-tab"
            >
              <i class="bi bi-file-earmark-spreadsheet mr-2"></i>
              Balance Sheet
            </button>
            <button
              @click="goToReports('cash-flow')"
              class="ledger-tab"
            >
              <i class="bi bi-cash-stack mr-2"></i>
              Cash Flow
            </button>
            <button
              class="ledger-tab ledger-tab--active"
            >
              <i class="bi bi-journal-text mr-2"></i>
              GL
            </button>
            <button
              @click="goToReports('payroll-summary')"
              class="ledger-tab"
            >
              <i class="bi bi-people mr-2"></i>
              Payroll Summary
            </button>
            <button
              @click="goToReports('marks-report')"
              class="ledger-tab"
            >
              <i class="bi bi-tags mr-2"></i>
              Marks Summary
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

      <SectionCard content-class="mb-6" body-class="p-4">
        <FormField label="COA Code (Opsional)" label-class="!text-xs" wrapper-class="md:w-80">
          <TextInput
            v-model="coaCode"
            type="text"
            placeholder="Contoh: 1101"
          />
        </FormField>
      </SectionCard>

      <!-- Summary Cards -->
      <div v-if="!loading && ledgerData.coa_groups && ledgerData.coa_groups.length > 0" class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <StatCard icon="bi bi-receipt" label="Total Transaksi" :value="ledgerData.total_transactions" tone="info" />
        <StatCard icon="bi bi-arrow-up-circle" label="Total Debit" :value="`Rp ${formatNumber(ledgerData.grand_total_debit)}`" tone="success" />
        <StatCard icon="bi bi-arrow-down-circle" label="Total Kredit" :value="`Rp ${formatNumber(ledgerData.grand_total_credit)}`" tone="danger" />
      </div>

      <!-- Balance Alert -->
      <div v-if="!loading && ledgerData.coa_groups && ledgerData.coa_groups.length > 0" 
           :class="ledgerData.is_balanced ? 'bg-green-50 border-green-200 text-green-800' : 'bg-yellow-50 border-yellow-200 text-yellow-800'" 
           class="rounded-lg border p-4 mb-6">
        <div class="flex items-center">
          <i :class="ledgerData.is_balanced ? 'bi bi-check-circle-fill text-green-600' : 'bi bi-exclamation-triangle-fill text-yellow-600'" class="mr-3"></i>
          <div>
            <strong>{{ ledgerData.is_balanced ? 'Balance!' : 'Unbalanced!' }}</strong>
            <span v-if="!ledgerData.is_balanced" class="ml-2">
              Selisih: Rp {{ formatNumber(Math.abs(ledgerData.grand_total_debit - ledgerData.grand_total_credit)) }}
            </span>
            <span v-else> Total Debit dan Kredit seimbang.</span>
          </div>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="flex flex-col items-center justify-center py-12">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
        <p class="mt-4 text-muted">Memuat General Ledger...</p>
      </div>

      <!-- No Data -->
      <div v-if="!loading && (!ledgerData.coa_groups || ledgerData.coa_groups.length === 0)" 
           class="text-center py-12">
        <i class="bi bi-journal-x text-6xl text-muted"></i>
        <p class="text-muted mt-4">Belum ada data untuk filter yang dipilih.</p>
      </div>

      <!-- Ledger Table -->
      <div v-if="!loading && ledgerData.coa_groups && ledgerData.coa_groups.length > 0" class="space-y-6">
        <div v-for="coaGroup in ledgerData.coa_groups" :key="coaGroup.coa_code" class="surface-card overflow-hidden">
          <!-- COA Header -->
          <div class="ledger-group-header px-6 py-4">
            <div class="flex items-center justify-between">
              <div class="flex-1">
                <h3 class="text-lg font-semibold text-theme flex items-center gap-2">
                  <i class="bi bi-folder2-open" style="color: var(--color-primary)"></i>
                  {{ coaGroup.coa_code }} - {{ coaGroup.coa_name }}
                </h3>
                <p class="text-sm text-muted mt-1">{{ coaGroup.coa_category }}</p>
              </div>
              <div class="flex items-center gap-6">
                <div class="text-right">
                  <p class="text-xs text-muted uppercase tracking-wide">Debit</p>
                  <p class="text-lg font-semibold text-green-600">Rp {{ formatNumber(coaGroup.total_debit) }}</p>
                </div>
                <div class="text-right">
                  <p class="text-xs text-muted uppercase tracking-wide">Kredit</p>
                  <p class="text-lg font-semibold text-red-600">Rp {{ formatNumber(coaGroup.total_credit) }}</p>
                </div>
                <div class="text-right">
                  <p class="text-xs text-muted uppercase tracking-wide">Saldo</p>
                  <p class="text-lg font-semibold" :class="coaGroup.ending_balance >= 0 ? 'text-indigo-600' : 'text-red-600'">
                    Rp {{ formatNumber(Math.abs(coaGroup.ending_balance)) }}
                  </p>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Transactions Table -->
          <div class="overflow-x-auto">
            <table class="min-w-full table-compact">
              <thead>
                <tr>
                  <th class="px-6 py-3 text-left" width="100">
                    Tanggal
                  </th>
                  <th class="px-6 py-3 text-left">
                    Deskripsi
                  </th>
                  <th class="px-6 py-3 text-left" width="150">
                    Mark
                  </th>
                  <th class="px-6 py-3 text-left" width="100">
                    COA
                  </th>
                  <th class="px-6 py-3 text-right" width="120">
                    Debit
                  </th>
                  <th class="px-6 py-3 text-right" width="120">
                    Kredit
                  </th>
                  <th class="px-6 py-3 text-right" width="130">
                    Saldo
                  </th>
                </tr>
              </thead>
              <tbody class="divide-y" style="border-color: var(--color-border)">
                <template v-for="txn in coaGroup.transactions" :key="txn.transaction_id">
                  <!-- Show all entries for this transaction -->
                  <tr v-for="(entry, idx) in txn.entries" :key="txn.transaction_id + '_' + idx"
                      :class="{'bg-indigo-50/20': idx === 0, 'ledger-row': true}">
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-theme">
                      <div v-if="idx === 0">{{ formatDate(txn.txn_date) }}</div>
                    </td>
                    <td class="px-6 py-4 text-sm text-theme">
                      <div v-if="idx === 0" class="font-medium">{{ txn.description }}</div>
                      <div v-else class="text-muted text-xs flex items-center gap-1">
                        <i class="bi bi-arrow-return-right"></i>
                        {{ txn.entries[0].coa_code }} → {{ entry.coa_code }}
                      </div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-theme">
                      <span v-if="idx === 0" class="ledger-mark-chip">
                        {{ txn.mark_name || '-' }}
                      </span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm">
                      <span :class="idx === 0 ? 'font-medium text-indigo-600' : 'text-muted'">
                        {{ entry.coa_code }}
                      </span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-right text-theme mono">
                      <span v-if="entry.debit > 0" :class="idx === 0 ? 'font-semibold text-green-600' : 'text-green-600'">
                        {{ formatNumber(entry.debit) }}
                      </span>
                      <span v-else class="text-muted">-</span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-right text-theme mono">
                      <span v-if="entry.credit > 0" :class="idx === 0 ? 'font-semibold text-red-600' : 'text-red-600'">
                        {{ formatNumber(entry.credit) }}
                      </span>
                      <span v-else class="text-muted">-</span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-right">
                      <span v-if="idx > 0" class="text-muted">...</span>
                      <strong v-else :class="entry.current_entry && entry.current_entry.running_balance >= 0 ? 'text-indigo-600' : 'text-red-600'">
                        {{ formatNumber(Math.abs(entry.current_entry ? entry.current_entry.running_balance : 0)) }}
                      </strong>
                    </td>
                  </tr>
                  <!-- Separator row between transactions -->
                  <tr v-if="txn !== coaGroup.transactions[coaGroup.transactions.length - 1]" class="ledger-separator">
                    <td colspan="7" class="px-6 py-1"></td>
                  </tr>
                </template>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import ReportFilters from '../components/reports/ReportFilters.vue';
import FormField from '../components/ui/FormField.vue';
import PageHeader from '../components/ui/PageHeader.vue';
import SectionCard from '../components/ui/SectionCard.vue';
import StatCard from '../components/ui/StatCard.vue';
import TextInput from '../components/ui/TextInput.vue';
import { useReportsStore } from '../stores/reports';
import { useCompanyStore } from '../stores/companies';

export default {
  name: 'GeneralLedger',
  components: {
    FormField,
    PageHeader,
    ReportFilters,
    SectionCard,
    StatCard,
    TextInput
  },
  setup() {
    const reportStore = useReportsStore();
    const companyStore = useCompanyStore();
    return { reportStore, companyStore };
  },
  data() {
    return {
      loading: false,
      showExportMenu: false,
      coaCode: '',
      autoLoadTimer: null,
      filterWatchStop: null,
      companyWatchStop: null,
      ledgerData: {
        company_id: '',
        start_date: '',
        end_date: '',
        coa_groups: [],
        total_accounts: 0,
        total_transactions: 0,
        grand_total_debit: 0,
        grand_total_credit: 0,
        is_balanced: true
      }
    };
  },
  async mounted() {
    await this.bootstrap();
  },
  beforeUnmount() {
    if (this.autoLoadTimer) {
      clearTimeout(this.autoLoadTimer);
    }
    if (this.filterWatchStop) {
      this.filterWatchStop();
    }
    if (this.companyWatchStop) {
      this.companyWatchStop();
    }
  },
  methods: {
    goToReports(tab) {
      this.$router.push({
        name: 'reports',
        query: { tab }
      });
    },
    getCurrentYear() {
      return new Date().getFullYear();
    },
    getYearDateRange(year) {
      const normalizedYear = String(year);
      return {
        year: normalizedYear,
        startDate: `${normalizedYear}-01-01`,
        endDate: `${normalizedYear}-12-31`,
        asOfDate: `${normalizedYear}-12-31`
      };
    },
    syncFiltersWithAvailableYears() {
      const availableYears = (this.reportStore.availableYears || [])
        .map((year) => parseInt(year, 10))
        .filter((year) => !Number.isNaN(year))
        .sort((a, b) => b - a);

      const fallbackYear = availableYears.length > 0 ? availableYears[0] : this.getCurrentYear();
      const selectedYear = parseInt(this.reportStore.filters.year, 10);
      const shouldResetYear = Number.isNaN(selectedYear) || !availableYears.includes(selectedYear);
      const targetYear = shouldResetYear ? fallbackYear : selectedYear;
      const yearRange = this.getYearDateRange(targetYear);

      this.reportStore.filters = {
        ...this.reportStore.filters,
        year: yearRange.year,
        startDate: shouldResetYear || !this.reportStore.filters.startDate ? yearRange.startDate : this.reportStore.filters.startDate,
        endDate: shouldResetYear || !this.reportStore.filters.endDate ? yearRange.endDate : this.reportStore.filters.endDate,
        asOfDate: shouldResetYear || !this.reportStore.filters.asOfDate ? yearRange.asOfDate : this.reportStore.filters.asOfDate,
        reportType: (this.reportStore.filters.reportType || 'real').toLowerCase()
      };
    },
    scheduleAutoLoad() {
      if (!this.reportStore.filters.startDate || !this.reportStore.filters.endDate) {
        return;
      }
      if (this.autoLoadTimer) {
        clearTimeout(this.autoLoadTimer);
      }
      this.autoLoadTimer = setTimeout(() => {
        this.loadGeneralLedger();
      }, 300);
    },
    async bootstrap() {
      await this.companyStore.fetchCompanies();
      await this.reportStore.loadFilters();
      await this.reportStore.fetchAvailableYears(this.reportStore.filters.companyId || null);
      this.syncFiltersWithAvailableYears();
      await this.loadGeneralLedger();

      this.filterWatchStop = this.$watch(
        () => ({ ...this.reportStore.filters, coaCode: this.coaCode }),
        async () => {
          await this.reportStore.saveFilters();
          this.scheduleAutoLoad();
        },
        { deep: true }
      );

      this.companyWatchStop = this.$watch(
        () => this.reportStore.filters.companyId,
        async (companyId, oldCompanyId) => {
          if (companyId === oldCompanyId) return;
          await this.reportStore.fetchAvailableYears(companyId || null);
          this.syncFiltersWithAvailableYears();
        }
      );
    },
    async loadGeneralLedger() {
      this.loading = true;
      try {
        const params = new URLSearchParams({
          start_date: this.reportStore.filters.startDate,
          end_date: this.reportStore.filters.endDate,
          report_type: (this.reportStore.filters.reportType || 'real').toLowerCase()
        });

        if (this.reportStore.filters.companyId) {
          params.append('company_id', this.reportStore.filters.companyId);
        }
        if (this.coaCode && this.coaCode.trim()) {
          params.append('coa_code', this.coaCode.trim());
        }

        const response = await fetch(`/api/reports/general-ledger?${params}`);
        const data = await response.json();

        if (data.success) {
          this.ledgerData = data.data;
        } else {
          this.ledgerData = { ...this.ledgerData, coa_groups: [] };
          console.error('Failed to load General Ledger:', data.error || 'Unknown error');
        }
      } catch (error) {
        console.error('Error loading general ledger:', error);
        this.ledgerData = { ...this.ledgerData, coa_groups: [] };
      } finally {
        this.loading = false;
      }
    },
    formatNumber(num) {
      return new Intl.NumberFormat('id-ID').format(num || 0);
    },
    formatDate(dateStr) {
      if (!dateStr) return '-';
      const date = new Date(dateStr);
      return date.toLocaleDateString('id-ID', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
    },
    async handleExport(format) {
      this.showExportMenu = false;
      try {
        const params = new URLSearchParams({
          start_date: this.reportStore.filters.startDate,
          end_date: this.reportStore.filters.endDate,
          report_type: (this.reportStore.filters.reportType || 'real').toLowerCase(),
          format
        });

        if (this.reportStore.filters.companyId) {
          params.append('company_id', this.reportStore.filters.companyId);
        }
        if (this.coaCode && this.coaCode.trim()) {
          params.append('coa_code', this.coaCode.trim());
        }

        const response = await fetch(`/api/reports/general-ledger/export?${params}`);

        if (response.ok) {
          const blob = await response.blob();
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          const companyLabel = this.reportStore.filters.companyId || 'all-companies';
          a.href = url;
          a.download = `general-ledger-${companyLabel}-${this.reportStore.filters.startDate}-to-${this.reportStore.filters.endDate}.${format === 'excel' ? 'xlsx' : 'pdf'}`;
          document.body.appendChild(a);
          a.click();
          window.URL.revokeObjectURL(url);
          document.body.removeChild(a);
        } else {
          const errorData = await response.json();
          alert('Export failed: ' + (errorData.error || 'Unknown error'));
        }
      } catch (error) {
        console.error('Export error:', error);
        alert('Export failed. Please try again.');
      }
    }
  }
};
</script>

<style scoped>
.ledger-tabs {
  @apply flex gap-2 overflow-x-auto;
}

.ledger-tab {
  @apply inline-flex items-center whitespace-nowrap rounded-2xl px-4 py-2.5 text-sm font-medium transition-all;
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
  color: var(--color-text-muted);
}

.ledger-tab:hover {
  border-color: var(--color-border-strong);
  color: var(--color-text);
}

.ledger-tab--active {
  background: rgba(15, 118, 110, 0.12);
  border-color: rgba(15, 118, 110, 0.18);
  color: var(--color-primary);
  box-shadow: var(--shadow-soft);
}

.ledger-menu {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 16px;
  box-shadow: var(--shadow-card);
  overflow: hidden;
}

.ledger-menu__item {
  @apply flex w-full items-center gap-2 px-4 py-2 text-left text-sm transition-colors;
  color: var(--color-text);
}

.ledger-menu__item:hover {
  background: var(--color-surface-muted);
}

.ledger-group-header {
  background: var(--color-surface-muted);
  border-bottom: 1px solid var(--color-border);
}

.ledger-row:hover {
  background: rgba(15, 118, 110, 0.05);
}

.ledger-mark-chip {
  @apply inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium;
  background: var(--color-surface-muted);
  color: var(--color-text);
}

.ledger-separator {
  background: var(--color-surface-muted);
}
</style>

<style scoped>
/* Additional custom styles if needed */
</style>
