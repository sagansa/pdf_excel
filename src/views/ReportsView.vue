<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50/30">
    <!-- Header -->
    <div class="bg-white border-b border-gray-200 sticky top-0 z-10 shadow-sm">
      <div class="max-w-7xl mx-auto px-6 py-4">
        <div class="flex items-center justify-between">
          <div>
            <h1 class="text-2xl font-bold text-gray-900">Financial Reports</h1>
            <p class="text-sm text-gray-500 mt-1">Laporan Keuangan Berdasarkan CoreTax 2025</p>
          </div>
          <div class="flex items-center gap-2 relative">
            <button
              v-if="store.hasIncomeStatement"
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
                @click="handleExport('xml')"
                class="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
              >
                <i class="bi bi-file-earmark-code text-orange-600"></i>
                CoreTax XML
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="max-w-7xl mx-auto px-6 py-6">
      <!-- Report Type Tabs -->
      <div class="bg-white rounded-lg shadow-sm border border-gray-200 mb-6">
        <div class="border-b border-gray-200">
          <nav class="flex -mb-px">
            <button
              @click="activeTab = 'income-statement'"
              class="px-6 py-3 text-sm font-medium border-b-2 transition-colors"
              :class="activeTab === 'income-statement' 
                ? 'border-indigo-600 text-indigo-600' 
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'"
            >
              <i class="bi bi-file-earmark-bar-graph mr-2"></i>
              Income Statement
            </button>
            <button
              @click="activeTab = 'monthly-revenue'"
              class="px-6 py-3 text-sm font-medium border-b-2 transition-colors"
              :class="activeTab === 'monthly-revenue' 
                ? 'border-indigo-600 text-indigo-600' 
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'"
            >
              <i class="bi bi-calendar3 mr-2"></i>
              Monthly Revenue
            </button>
            <button
              @click="activeTab = 'balance-sheet'"
              class="px-6 py-3 text-sm font-medium border-b-2 transition-colors"
              :class="activeTab === 'balance-sheet'
                ? 'border-indigo-600 text-indigo-600' 
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'"
            >
              <i class="bi bi-file-earmark-spreadsheet mr-2"></i>
              Balance Sheet
            </button>
            <button
              @click="activeTab = 'cash-flow'"
              class="px-6 py-3 text-sm font-medium border-b-2 transition-colors"
              :class="activeTab === 'cash-flow'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'"
            >
              <i class="bi bi-cash-stack mr-2"></i>
              Cash Flow
            </button>
            <button
              @click="navigateToGeneralLedger()"
              class="px-6 py-3 text-sm font-medium border-b-2 transition-colors"
              :class="'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'"
            >
              <i class="bi bi-journal-text mr-2"></i>
              General Ledger
            </button>
            <button
              @click="activeTab = 'payroll-summary'"
              class="px-6 py-3 text-sm font-medium border-b-2 transition-colors"
              :class="activeTab === 'payroll-summary'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'"
            >
              <i class="bi bi-people mr-2"></i>
              Payroll Summary
            </button>
            <button
              @click="activeTab = 'marks-report'"
              class="px-6 py-3 text-sm font-medium border-b-2 transition-colors"
              :class="activeTab === 'marks-report'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'"
            >
              <i class="bi bi-tags mr-2"></i>
              Marks Summary
            </button>
          </nav>
        </div>
      </div>

      <!-- Filters -->
      <ReportFilters
        v-model="store.filters"
        :available-years="store.availableYears"
        :companies="companies"
        :is-loading="store.isLoading"
        @generate="generateReport"
      />

      <!-- Error Message -->
      <div v-if="store.error" class="mt-6 bg-red-50 border border-red-200 rounded-lg p-4">
        <div class="flex items-center gap-2">
          <i class="bi bi-exclamation-triangle-fill text-red-600"></i>
          <p class="text-sm text-red-800">{{ store.error }}</p>
        </div>
      </div>

      <!-- Loading and Content Area -->
      <div class="mt-6 relative min-h-[400px]">
        <!-- Global Loading Overlay (Subtle) -->
        <div v-if="store.isLoading" class="absolute inset-0 bg-white/50 backdrop-blur-sm z-20 flex flex-col items-center justify-center rounded-lg border border-gray-200">
          <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
          <p class="text-sm text-gray-500 mt-4">Generating all reports...</p>
        </div>

        <!-- Report Content -->
        <div :class="{ 'opacity-50 pointer-events-none': store.isLoading }">
          <IncomeStatementComparative
            v-if="activeTab === 'income-statement'"
            :key="`is-${refreshKey}`"
            :data="store.incomeStatement"
            @view-coa="openCoaDetail"
          />
          <MonthlyRevenue
            v-if="activeTab === 'monthly-revenue'"
            :key="`mr-${refreshKey}`"
            :company-id="store.filters.companyId"
          />
          <BalanceSheet
            v-if="activeTab === 'balance-sheet'"
            :key="`bs-${refreshKey}`"
            :data="store.balanceSheet"
            @view-coa="openCoaDetail"
          />
          <CashFlow
            v-if="activeTab === 'cash-flow'"
            :key="`cf-${refreshKey}`"
            :data="store.cashFlow"
          />
          <PayrollSalarySummary
            v-if="activeTab === 'payroll-summary'"
            :key="`ps-${refreshKey}`"
            :data="store.payrollSalarySummary"
          />
          <MarksReport
            v-if="activeTab === 'marks-report'"
            :key="`mr-${refreshKey}`"
          />
        </div>
      </div>
    </div>

    <!-- COA Detail Modal -->
    <COADetailModal
      :isOpen="showCoaModal"
      :coaData="selectedCoa"
      :filters="store.filters"
      @close="showCoaModal = false"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import { useReportsStore } from '../stores/reports';
import { useCompanyStore } from '../stores/companies';
import { useCoaStore } from '../stores/coa';
import ReportFilters from '../components/reports/ReportFilters.vue';
import IncomeStatementComparative from '../components/reports/IncomeStatementComparative.vue';
import MonthlyRevenue from '../components/reports/MonthlyRevenue.vue';
import BalanceSheet from '../components/reports/BalanceSheet.vue';
import CashFlow from '../components/reports/CashFlow.vue';
import PayrollSalarySummary from '../components/reports/PayrollSalarySummary.vue';
import MarksReport from '../components/reports/MarksReport.vue';
import COADetailModal from '../components/reports/COADetailModal.vue';

const store = useReportsStore();
const companyStore = useCompanyStore();
const coaStore = useCoaStore();

const activeTab = ref('income-statement');
const refreshKey = ref(0);
const showCoaModal = ref(false);
const selectedCoa = ref(null);

  const openCoaDetail = async (coaItem) => {
    if (!coaItem || !coaItem.code) return;

    try {
      await coaStore.fetchCoa();
      const coaList = coaStore.coaList || [];
      const coaRecord = coaList.find(c => c.code === coaItem.code);

      if (coaRecord) {
        selectedCoa.value = { ...coaItem, id: coaRecord.id };
        showCoaModal.value = true;
      } else {
        console.warn(`COA with code ${coaItem.code} not found in COA list`);
        selectedCoa.value = { ...coaItem };
        showCoaModal.value = true;
      }
    } catch (error) {
      console.error('Failed to fetch COA details:', error);
      selectedCoa.value = { ...coaItem };
      showCoaModal.value = true;
    }
  };

// Add watcher for persistence
watch(() => store.filters, (newFilters) => {
  console.log('ReportsView: Filters changed:', newFilters);
  store.saveFilters();
}, { deep: true });

// Also watch specific year changes
watch(() => store.filters.year, (newYear) => {
  console.log('ReportsView: Year changed to:', newYear);
}, { immediate: true });

const companies = ref([]);

const getCurrentYear = () => new Date().getFullYear();

const getYearDateRange = (year) => {
  const normalizedYear = String(year);
  return {
    year: normalizedYear,
    startDate: `${normalizedYear}-01-01`,
    endDate: `${normalizedYear}-12-31`,
    asOfDate: `${normalizedYear}-12-31`
  };
};

const syncFiltersWithAvailableYears = () => {
  const availableYears = (store.availableYears || [])
    .map((year) => parseInt(year, 10))
    .filter((year) => !Number.isNaN(year))
    .sort((a, b) => b - a);

  const fallbackYear = availableYears.length > 0 ? availableYears[0] : getCurrentYear();
  const selectedYear = parseInt(store.filters.year, 10);
  const shouldResetYear = Number.isNaN(selectedYear) || !availableYears.includes(selectedYear);
  const targetYear = shouldResetYear ? fallbackYear : selectedYear;
  const yearRange = getYearDateRange(targetYear);

  console.log('syncFiltersWithAvailableYears:', {
    availableYears,
    selectedYear,
    shouldResetYear,
    targetYear,
    currentFilters: store.filters,
    yearRange
  });

  store.filters = {
    ...store.filters,
    year: yearRange.year,
    startDate: shouldResetYear || !store.filters.startDate ? yearRange.startDate : store.filters.startDate,
    endDate: shouldResetYear || !store.filters.endDate ? yearRange.endDate : store.filters.endDate,
    asOfDate: shouldResetYear || !store.filters.asOfDate ? yearRange.asOfDate : store.filters.asOfDate,
    reportType: store.filters.reportType || 'real'
  };
  
  console.log('After sync:', store.filters);
};

const generateReport = async () => {
  // Global validation
  if (!store.filters.startDate || !store.filters.endDate || !store.filters.asOfDate) {
    alert('Please ensure all required filter dates are selected (Period Range and As Of Date)');
    return;
  }

  console.log('ReportsView: generateReport called with filters:', {
    year: store.filters.year,
    startDate: store.filters.startDate,
    endDate: store.filters.endDate,
    asOfDate: store.filters.asOfDate
  });

  try {
    // Generate all reports at once
    await store.fetchAllReports();
    // Increment refreshKey to force-refresh components
    refreshKey.value++;
  } catch (error) {
    console.error('Failed to generate all reports:', error);
  }
};

const showExportMenu = ref(false);

const handleExport = async (format) => {
  showExportMenu.value = false;
  try {
    await store.exportReport(
      activeTab.value, 
      format,
      {
        start_date: store.filters.startDate,
        end_date: store.filters.endDate,
        company_id: store.filters.companyId,
        report_type: store.filters.reportType
      }
    );
  } catch (error) {
    console.error('Failed to export:', error);
    alert('Failed to export report');
  }
};

const navigateToGeneralLedger = () => {
  // Navigate to General Ledger page
  window.location.href = '/general-ledger';
};

onMounted(async () => {
  console.log('ReportsView: onMounted started');
  
  // Load companies first
  await companyStore.fetchCompanies();
  companies.value = companyStore.companies;

  // Load persistence filters
  await store.loadFilters();
  console.log('ReportsView: After loadFilters, current filters:', store.filters);

  await store.fetchAvailableYears(store.filters.companyId || null);
  syncFiltersWithAvailableYears();

  console.log('ReportsView: Final filters before generate:', store.filters);
  
  // Auto-generate report with filters
  await generateReport();
});

watch(
  () => store.filters.companyId,
  async (companyId, oldCompanyId) => {
    if (companyId === oldCompanyId) return;
    await store.fetchAvailableYears(companyId || null);
    syncFiltersWithAvailableYears();
  }
);
</script>
