<template>
  <div class="reports-surface space-y-6">
    <PageHeader
      eyebrow="Reporting Studio"
      icon="bi bi-file-earmark-bar-graph-fill"
      title="Financial reports with a cleaner analysis shell"
      subtitle="Income statement, balance sheet, revenue, cash flow, and payroll summary in one reporting workspace."
    >
      <template #actions>
      <div class="flex items-center gap-2 relative">
            <button
              v-if="canExportCurrentTab"
              @click="showExportMenu = !showExportMenu"
              class="btn-secondary gap-2 text-sm"
            >
              <i class="bi bi-download"></i>
              <span>Export</span>
              <i class="bi bi-chevron-down text-xs"></i>
            </button>
            
            <!-- Export Dropdown -->
            <div 
              v-if="showExportMenu" 
              class="reports-menu absolute right-0 top-full mt-2 w-48 py-1 z-50"
            >
              <button
                @click="handleExport('excel')"
                class="reports-menu__item"
              >
                <i class="bi bi-file-earmark-spreadsheet text-green-600"></i>
                Excel (.xlsx)
              </button>
              <button
                v-if="supportsPdfExport"
                @click="handleExport('pdf')"
                class="reports-menu__item"
              >
                <i class="bi bi-file-earmark-pdf text-red-600"></i>
                {{ pdfExportLabel }}
              </button>
              <button
                @click="handleExport('xml')"
                class="reports-menu__item"
              >
                <i class="bi bi-file-earmark-code text-orange-600"></i>
                CoreTax XML
              </button>
            </div>
      </div>
      </template>
    </PageHeader>

    <!-- Main Content -->
    <div class="space-y-6">
      <!-- Report Type Tabs -->
      <SectionCard body-class="p-3">
        <div class="reports-tab-wrap">
            <button
              @click="handleTabClick('income-statement')"
              class="reports-tab"
              :class="{ 'reports-tab--active': activeTab === 'income-statement' }"
            >
              <i class="bi bi-file-earmark-bar-graph mr-2"></i>
              Income Statement
            </button>
            <button
              @click="handleTabClick('monthly-revenue')"
              class="reports-tab"
              :class="{ 'reports-tab--active': activeTab === 'monthly-revenue' }"
            >
              <i class="bi bi-calendar3 mr-2"></i>
              Monthly Revenue
            </button>
            <button
              @click="handleTabClick('balance-sheet')"
              class="reports-tab"
              :class="{ 'reports-tab--active': activeTab === 'balance-sheet' }"
            >
              <i class="bi bi-file-earmark-spreadsheet mr-2"></i>
              Balance Sheet
            </button>
            <button
              @click="handleTabClick('cash-flow')"
              class="reports-tab"
              :class="{ 'reports-tab--active': activeTab === 'cash-flow' }"
            >
              <i class="bi bi-cash-stack mr-2"></i>
              Cash Flow
            </button>
            <button
              @click="navigateToGeneralLedger()"
              class="reports-tab"
            >
              <i class="bi bi-journal-text mr-2"></i>
              GL
            </button>
            <button
              @click="handleTabClick('payroll-summary')"
              class="reports-tab"
              :class="{ 'reports-tab--active': activeTab === 'payroll-summary' }"
            >
              <i class="bi bi-people mr-2"></i>
              Payroll Summary
            </button>
            <button
              @click="handleTabClick('marks-report')"
              class="reports-tab"
              :class="{ 'reports-tab--active': activeTab === 'marks-report' }"
            >
              <i class="bi bi-tags mr-2"></i>
              Marks Summary
            </button>
        </div>
      </SectionCard>

      <!-- Filters -->
      <ReportFilters
        v-model="store.filters"
        :available-years="store.availableYears"
        :companies="companies"
        :is-loading="store.isLoading"
      />

      <!-- Error Message -->
      <div v-if="store.error" class="mt-6 reports-error rounded-2xl p-4">
        <div class="flex items-center gap-2">
          <i class="bi bi-exclamation-triangle-fill" style="color: var(--color-danger)"></i>
          <p class="text-sm" style="color: var(--color-danger)">{{ store.error }}</p>
        </div>
      </div>

      <!-- Loading and Content Area -->
      <div class="mt-6 relative min-h-[400px]">
        <!-- Global Loading Overlay (Subtle) -->
        <div v-if="store.isLoading" class="absolute inset-0 reports-loading z-20 flex flex-col items-center justify-center rounded-2xl">
          <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2" style="border-color: var(--color-primary)"></div>
          <p class="text-sm text-muted mt-4">Generating all reports...</p>
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
import { computed, ref, onMounted, onBeforeUnmount, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
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
import PageHeader from '../components/ui/PageHeader.vue';
import SectionCard from '../components/ui/SectionCard.vue';

const store = useReportsStore();
const companyStore = useCompanyStore();
const coaStore = useCoaStore();
const route = useRoute();
const router = useRouter();

const activeTab = ref('income-statement');
const refreshKey = ref(0);
const showCoaModal = ref(false);
const selectedCoa = ref(null);
const isHydratingFilters = ref(true);
const autoGenerateTimer = ref(null);
const reportTabs = new Set([
  'income-statement',
  'monthly-revenue',
  'balance-sheet',
  'cash-flow',
  'payroll-summary',
  'marks-report'
]);

const normalizeTab = (tab) => {
  const tabValue = String(tab || '').trim();
  return reportTabs.has(tabValue) ? tabValue : 'income-statement';
};

const canExportCurrentTab = computed(() => {
  if (activeTab.value === 'income-statement') {
    return Boolean(store.incomeStatement);
  }
  if (activeTab.value === 'balance-sheet') {
    return Boolean(store.balanceSheet);
  }
  return false;
});

const supportsPdfExport = computed(() => {
  return activeTab.value === 'income-statement' || activeTab.value === 'balance-sheet';
});

const pdfExportLabel = computed(() => {
  return (store.filters.reportType || 'real').toLowerCase() === 'coretax'
    ? 'CoreTax PDF (Combined)'
    : 'Formal PDF';
});

const handleTabClick = async (tab) => {
  const nextTab = normalizeTab(tab);
  activeTab.value = nextTab;
  try {
    await router.replace({
      query: {
        ...route.query,
        tab: nextTab
      }
    });
  } catch (error) {
    console.error('Failed to update report tab query:', error);
  }
};

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

const scheduleGenerateReport = () => {
  if (autoGenerateTimer.value) {
    clearTimeout(autoGenerateTimer.value);
  }
  autoGenerateTimer.value = setTimeout(() => {
    generateReport();
  }, 300);
};

// Add watcher for persistence + auto refresh
watch(() => store.filters, (newFilters) => {
  console.log('ReportsView: Filters changed:', newFilters);
  store.saveFilters();
  if (isHydratingFilters.value) return;
  if (!newFilters.startDate || !newFilters.endDate || !newFilters.asOfDate) return;
  scheduleGenerateReport();
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
    reportType: (store.filters.reportType || 'real').toLowerCase()
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
    asOfDate: store.filters.asOfDate,
    reportType: store.filters.reportType
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
        as_of_date: store.filters.asOfDate,
        company_id: store.filters.companyId,
        report_type: store.filters.reportType
      }
    );
  } catch (error) {
    console.error('Failed to export:', error);
    alert(error?.message || 'Failed to export report');
  }
};

const navigateToGeneralLedger = () => {
  router.push({ name: 'general-ledger' });
};

watch(
  () => route.query.tab,
  (tabFromQuery) => {
    activeTab.value = normalizeTab(tabFromQuery);
  },
  { immediate: true }
);

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
  isHydratingFilters.value = false;
});

watch(
  () => store.filters.companyId,
  async (companyId, oldCompanyId) => {
    if (companyId === oldCompanyId) return;
    await store.fetchAvailableYears(companyId || null);
    syncFiltersWithAvailableYears();
  }
);

onBeforeUnmount(() => {
  if (autoGenerateTimer.value) {
    clearTimeout(autoGenerateTimer.value);
  }
});
</script>

<style scoped>
.reports-tab-wrap {
  @apply flex gap-2 overflow-x-auto;
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

.reports-error {
  background: rgba(185, 28, 28, 0.08);
  border: 1px solid rgba(185, 28, 28, 0.18);
}

.reports-loading {
  background: rgba(255, 253, 248, 0.72);
  border: 1px solid var(--color-border);
  backdrop-filter: blur(10px);
}

:global(html.dark) .reports-loading {
  background: rgba(15, 21, 28, 0.72);
}
</style>

<style>
html.dark .reports-surface .bg-white {
  background: var(--color-surface);
  border-color: var(--color-border);
}

html.dark .reports-surface .bg-gray-50,
html.dark .reports-surface .bg-gray-100,
html.dark .reports-surface .bg-gray-200,
html.dark .reports-surface .bg-slate-50,
html.dark .reports-surface .bg-slate-100,
html.dark .reports-surface .bg-slate-200,
html.dark .reports-surface .bg-blue-50,
html.dark .reports-surface .bg-blue-100,
html.dark .reports-surface .bg-indigo-50,
html.dark .reports-surface .bg-indigo-100,
html.dark .reports-surface .bg-green-50,
html.dark .reports-surface .bg-green-100,
html.dark .reports-surface .bg-red-50,
html.dark .reports-surface .bg-red-100,
html.dark .reports-surface .bg-yellow-50,
html.dark .reports-surface .bg-yellow-100,
html.dark .reports-surface .bg-amber-50,
html.dark .reports-surface .bg-amber-100,
html.dark .reports-surface .bg-orange-50,
html.dark .reports-surface .bg-orange-100,
html.dark .reports-surface .bg-emerald-50,
html.dark .reports-surface .bg-emerald-100,
html.dark .reports-surface .bg-sky-50,
html.dark .reports-surface .bg-sky-100,
html.dark .reports-surface .bg-purple-50 {
  background: var(--color-surface-muted);
}

html.dark .reports-surface .border-gray-100,
html.dark .reports-surface .border-gray-200,
html.dark .reports-surface .border-gray-300,
html.dark .reports-surface .border-slate-100,
html.dark .reports-surface .border-slate-200,
html.dark .reports-surface .border-slate-300,
html.dark .reports-surface .border-blue-100,
html.dark .reports-surface .border-blue-200,
html.dark .reports-surface .border-green-100,
html.dark .reports-surface .border-green-200,
html.dark .reports-surface .border-red-100,
html.dark .reports-surface .border-red-200,
html.dark .reports-surface .border-yellow-200,
html.dark .reports-surface .border-amber-100,
html.dark .reports-surface .border-amber-200,
html.dark .reports-surface .border-orange-100,
html.dark .reports-surface .border-emerald-200,
html.dark .reports-surface .border-indigo-100,
html.dark .reports-surface .border-indigo-200,
html.dark .reports-surface .border-purple-200 {
  border-color: var(--color-border);
}

html.dark .reports-surface .divide-gray-100,
html.dark .reports-surface .divide-gray-200,
html.dark .reports-surface .divide-slate-100,
html.dark .reports-surface .divide-slate-200 {
  border-color: var(--color-border);
}

html.dark .reports-surface .text-gray-900,
html.dark .reports-surface .text-gray-800,
html.dark .reports-surface .text-gray-700,
html.dark .reports-surface .text-slate-800,
html.dark .reports-surface .text-slate-700 {
  color: var(--color-text);
}

html.dark .reports-surface .text-gray-600,
html.dark .reports-surface .text-gray-500,
html.dark .reports-surface .text-gray-400,
html.dark .reports-surface .text-gray-300,
html.dark .reports-surface .text-slate-600,
html.dark .reports-surface .text-slate-500,
html.dark .reports-surface .text-slate-400,
html.dark .reports-surface .text-slate-300 {
  color: var(--color-text-muted);
}

html.dark .reports-surface .text-green-900,
html.dark .reports-surface .text-green-800,
html.dark .reports-surface .text-green-700,
html.dark .reports-surface .text-green-600,
html.dark .reports-surface .text-emerald-700,
html.dark .reports-surface .text-emerald-600 {
  color: #86efac;
}

html.dark .reports-surface .text-red-900,
html.dark .reports-surface .text-red-800,
html.dark .reports-surface .text-red-700,
html.dark .reports-surface .text-red-600 {
  color: #fca5a5;
}

html.dark .reports-surface .text-blue-900,
html.dark .reports-surface .text-blue-800,
html.dark .reports-surface .text-blue-700,
html.dark .reports-surface .text-blue-600 {
  color: #93c5fd;
}

html.dark .reports-surface .text-indigo-900,
html.dark .reports-surface .text-indigo-800,
html.dark .reports-surface .text-indigo-700,
html.dark .reports-surface .text-indigo-600 {
  color: #a5b4fc;
}

html.dark .reports-surface .text-orange-900,
html.dark .reports-surface .text-orange-800,
html.dark .reports-surface .text-orange-700,
html.dark .reports-surface .text-orange-600 {
  color: #fdba74;
}

html.dark .reports-surface .text-amber-800,
html.dark .reports-surface .text-amber-700,
html.dark .reports-surface .text-amber-600 {
  color: #fcd34d;
}

html.dark .reports-surface .text-purple-900,
html.dark .reports-surface .text-purple-800,
html.dark .reports-surface .text-purple-700,
html.dark .reports-surface .text-purple-600 {
  color: #d8b4fe;
}

html.dark .reports-surface .text-sky-900,
html.dark .reports-surface .text-sky-800,
html.dark .reports-surface .text-sky-700,
html.dark .reports-surface .text-sky-600 {
  color: #7dd3fc;
}
</style>
