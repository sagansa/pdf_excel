<template>
  <div class="space-y-6">
    <PageHeader
      eyebrow="Reporting Studio"
      icon="bi bi-file-earmark-bar-graph-fill"
      title="Financial reports with a cleaner analysis shell"
      subtitle="Income statement, balance sheet, revenue, cash flow, and payroll summary in one reporting workspace."
    >
      <template #actions>
      <div class="flex items-center gap-2 relative">
            <button
              v-if="store.hasIncomeStatement"
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
import { ref, onMounted, onBeforeUnmount, watch } from 'vue';
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
