<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50/30">
    <!-- Header -->
    <div class="bg-white border-b border-gray-200 sticky top-0 z-10 shadow-sm">
      <div class="max-w-7xl mx-auto px-6 py-4">
        <div class="flex items-center justify-between">
          <div>
            <h1 class="text-2xl font-bold text-gray-900">General Ledger</h1>
            <p class="text-sm text-gray-500 mt-1">Laporan Buku Besar</p>
          </div>
          <div class="flex items-center gap-2">
            <button
              v-if="ledgerData.coa_groups && ledgerData.coa_groups.length > 0"
              @click="showExportMenu = !showExportMenu"
              class="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors flex items-center gap-2"
            >
              <i class="bi bi-download"></i>
              <span>Export</span>
              <i class="bi bi-chevron-down text-xs"></i>
            </button>
            
            <!-- Export Dropdown -->
            <div 
              v-if="showExportMenu" 
              class="absolute right-0 top-full mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-100 py-1 z-50"
            >
              <button
                @click="handleExport('excel')"
                class="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
              >
                <i class="bi bi-file-earmark-spreadsheet text-green-600"></i>
                Excel (.xlsx)
              </button>
              <button
                @click="handleExport('pdf')"
                class="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
              >
                <i class="bi bi-file-earmark-pdf text-red-600"></i>
                PDF
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="max-w-7xl mx-auto px-6 py-6">
      <!-- Report Navigation Tabs -->
      <div class="bg-white rounded-lg shadow-sm border border-gray-200 mb-6">
        <div class="border-b border-gray-200">
          <nav class="flex -mb-px overflow-x-auto">
            <button
              @click="goToReports('income-statement')"
              class="px-6 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            >
              <i class="bi bi-file-earmark-bar-graph mr-2"></i>
              Income Statement
            </button>
            <button
              @click="goToReports('monthly-revenue')"
              class="px-6 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            >
              <i class="bi bi-calendar3 mr-2"></i>
              Monthly Revenue
            </button>
            <button
              @click="goToReports('balance-sheet')"
              class="px-6 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            >
              <i class="bi bi-file-earmark-spreadsheet mr-2"></i>
              Balance Sheet
            </button>
            <button
              @click="goToReports('cash-flow')"
              class="px-6 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            >
              <i class="bi bi-cash-stack mr-2"></i>
              Cash Flow
            </button>
            <button
              class="px-6 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap border-indigo-600 text-indigo-600"
            >
              <i class="bi bi-journal-text mr-2"></i>
              GL
            </button>
            <button
              @click="goToReports('payroll-summary')"
              class="px-6 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            >
              <i class="bi bi-people mr-2"></i>
              Payroll Summary
            </button>
            <button
              @click="goToReports('marks-report')"
              class="px-6 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            >
              <i class="bi bi-tags mr-2"></i>
              Marks Summary
            </button>
          </nav>
        </div>
      </div>

      <!-- Shared Filters -->
      <ReportFilters
        v-model="reportStore.filters"
        :available-years="reportStore.availableYears"
        :companies="companyStore.companies"
        :is-loading="loading"
      />

      <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
        <label class="block text-xs font-medium text-gray-700 mb-1">COA Code (Opsional)</label>
        <input
          v-model="coaCode"
          type="text"
          placeholder="Contoh: 1101"
          class="w-full md:w-80 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
        />
      </div>

      <!-- Summary Cards -->
      <div v-if="!loading && ledgerData.coa_groups && ledgerData.coa_groups.length > 0" class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div class="flex items-center">
            <div class="flex-1">
              <p class="text-sm font-medium text-gray-600">Total Transaksi</p>
              <p class="text-2xl font-bold text-gray-900">{{ ledgerData.total_transactions }}</p>
            </div>
            <div class="flex-shrink-0">
              <i class="bi bi-receipt text-3xl text-indigo-600 opacity-20"></i>
            </div>
          </div>
        </div>
        
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div class="flex items-center">
            <div class="flex-1">
              <p class="text-sm font-medium text-gray-600">Total Debit</p>
              <p class="text-2xl font-bold text-green-600">Rp {{ formatNumber(ledgerData.grand_total_debit) }}</p>
            </div>
            <div class="flex-shrink-0">
              <i class="bi bi-arrow-up-circle text-3xl text-green-600 opacity-20"></i>
            </div>
          </div>
        </div>
        
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div class="flex items-center">
            <div class="flex-1">
              <p class="text-sm font-medium text-gray-600">Total Kredit</p>
              <p class="text-2xl font-bold text-red-600">Rp {{ formatNumber(ledgerData.grand_total_credit) }}</p>
            </div>
            <div class="flex-shrink-0">
              <i class="bi bi-arrow-down-circle text-3xl text-red-600 opacity-20"></i>
            </div>
          </div>
        </div>
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
        <p class="mt-4 text-gray-600">Memuat General Ledger...</p>
      </div>

      <!-- No Data -->
      <div v-if="!loading && (!ledgerData.coa_groups || ledgerData.coa_groups.length === 0)" 
           class="text-center py-12">
        <i class="bi bi-journal-x text-6xl text-gray-300"></i>
        <p class="text-gray-500 mt-4">Belum ada data untuk filter yang dipilih.</p>
      </div>

      <!-- Ledger Table -->
      <div v-if="!loading && ledgerData.coa_groups && ledgerData.coa_groups.length > 0" class="space-y-6">
        <div v-for="coaGroup in ledgerData.coa_groups" :key="coaGroup.coa_code" class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <!-- COA Header -->
          <div class="bg-gray-50 border-b border-gray-200 px-6 py-4">
            <div class="flex items-center justify-between">
              <div class="flex-1">
                <h3 class="text-lg font-semibold text-gray-900 flex items-center gap-2">
                  <i class="bi bi-folder2-open text-indigo-600"></i>
                  {{ coaGroup.coa_code }} - {{ coaGroup.coa_name }}
                </h3>
                <p class="text-sm text-gray-600 mt-1">{{ coaGroup.coa_category }}</p>
              </div>
              <div class="flex items-center gap-6">
                <div class="text-right">
                  <p class="text-xs text-gray-500 uppercase tracking-wide">Debit</p>
                  <p class="text-lg font-semibold text-green-600">Rp {{ formatNumber(coaGroup.total_debit) }}</p>
                </div>
                <div class="text-right">
                  <p class="text-xs text-gray-500 uppercase tracking-wide">Kredit</p>
                  <p class="text-lg font-semibold text-red-600">Rp {{ formatNumber(coaGroup.total_credit) }}</p>
                </div>
                <div class="text-right">
                  <p class="text-xs text-gray-500 uppercase tracking-wide">Saldo</p>
                  <p class="text-lg font-semibold" :class="coaGroup.ending_balance >= 0 ? 'text-indigo-600' : 'text-red-600'">
                    Rp {{ formatNumber(Math.abs(coaGroup.ending_balance)) }}
                  </p>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Transactions Table -->
          <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-200">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider" width="100">
                    Tanggal
                  </th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Deskripsi
                  </th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider" width="150">
                    Mark
                  </th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider" width="100">
                    COA
                  </th>
                  <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider" width="120">
                    Debit
                  </th>
                  <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider" width="120">
                    Kredit
                  </th>
                  <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider" width="130">
                    Saldo
                  </th>
                </tr>
              </thead>
              <tbody class="bg-white divide-y divide-gray-200">
                <template v-for="txn in coaGroup.transactions" :key="txn.transaction_id">
                  <!-- Show all entries for this transaction -->
                  <tr v-for="(entry, idx) in txn.entries" :key="txn.transaction_id + '_' + idx"
                      :class="{'bg-indigo-50': idx === 0, 'hover:bg-gray-50': true}">
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      <div v-if="idx === 0">{{ formatDate(txn.txn_date) }}</div>
                    </td>
                    <td class="px-6 py-4 text-sm text-gray-900">
                      <div v-if="idx === 0" class="font-medium">{{ txn.description }}</div>
                      <div v-else class="text-gray-500 text-xs flex items-center gap-1">
                        <i class="bi bi-arrow-return-right"></i>
                        {{ txn.entries[0].coa_code }} → {{ entry.coa_code }}
                      </div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      <span v-if="idx === 0" class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                        {{ txn.mark_name || '-' }}
                      </span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm">
                      <span :class="idx === 0 ? 'font-medium text-indigo-600' : 'text-gray-500'">
                        {{ entry.coa_code }}
                      </span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900">
                      <span v-if="entry.debit > 0" :class="idx === 0 ? 'font-semibold text-green-600' : 'text-green-600'">
                        {{ formatNumber(entry.debit) }}
                      </span>
                      <span v-else class="text-gray-400">-</span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900">
                      <span v-if="entry.credit > 0" :class="idx === 0 ? 'font-semibold text-red-600' : 'text-red-600'">
                        {{ formatNumber(entry.credit) }}
                      </span>
                      <span v-else class="text-gray-400">-</span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-right">
                      <span v-if="idx > 0" class="text-gray-400">...</span>
                      <strong v-else :class="entry.current_entry && entry.current_entry.running_balance >= 0 ? 'text-indigo-600' : 'text-red-600'">
                        {{ formatNumber(Math.abs(entry.current_entry ? entry.current_entry.running_balance : 0)) }}
                      </strong>
                    </td>
                  </tr>
                  <!-- Separator row between transactions -->
                  <tr v-if="txn !== coaGroup.transactions[coaGroup.transactions.length - 1]" class="bg-gray-100">
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
import { useReportsStore } from '../stores/reports';
import { useCompanyStore } from '../stores/companies';

export default {
  name: 'GeneralLedger',
  components: {
    ReportFilters
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
/* Additional custom styles if needed */
</style>
