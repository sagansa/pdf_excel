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
              @click="activeTab = 'inventory'"
              class="px-6 py-3 text-sm font-medium border-b-2 transition-colors"
              :class="activeTab === 'inventory'
                ? 'border-indigo-600 text-indigo-600' 
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'"
            >
              <i class="bi bi-box-seam mr-2"></i>
              Inventory Adjustments
            </button>
            <button
              @click="activeTab = 'balance-sheet'"
              disabled
              class="px-6 py-3 text-sm font-medium border-b-2 border-transparent text-gray-400 cursor-not-allowed"
            >
              <i class="bi bi-file-earmark-spreadsheet mr-2"></i>
              Balance Sheet
              <span class="ml-2 text-xs bg-gray-100 px-2 py-0.5 rounded">Coming Soon</span>
            </button>
            <button
              @click="activeTab = 'cash-flow'"
              disabled
              class="px-6 py-3 text-sm font-medium border-b-2 border-transparent text-gray-400 cursor-not-allowed"
            >
              <i class="bi bi-cash-stack mr-2"></i>
              Cash Flow
              <span class="ml-2 text-xs bg-gray-100 px-2 py-0.5 rounded">Coming Soon</span>
            </button>
          </nav>
        </div>
      </div>

      <!-- Filters -->
      <ReportFilters
        v-if="activeTab === 'income-statement'"
        v-model="store.filters"
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
        <div v-if="store.isLoading && activeTab === 'income-statement'" class="absolute inset-0 bg-white/50 backdrop-blur-sm z-20 flex flex-col items-center justify-center rounded-lg border border-gray-200">
          <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
          <p class="text-sm text-gray-500 mt-4">Generating report...</p>
        </div>

        <!-- Report Content -->
        <div :class="{ 'opacity-50 pointer-events-none': store.isLoading && activeTab === 'income-statement' }">
          <IncomeStatement
            v-if="activeTab === 'income-statement'"
            :data="store.incomeStatement"
          />
          <MonthlyRevenue
            v-if="activeTab === 'monthly-revenue'"
            :company-id="store.filters.companyId"
          />
          <InventoryAdjustments
            v-if="activeTab === 'inventory'"
            :company-id="store.filters.companyId"
            :year="store.filters.year"
            @saved="generateReport"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import { useReportsStore } from '../stores/reports';
import { useCompanyStore } from '../stores/companies';
import ReportFilters from '../components/reports/ReportFilters.vue';
import IncomeStatement from '../components/reports/IncomeStatement.vue';
import MonthlyRevenue from '../components/reports/MonthlyRevenue.vue';
import InventoryAdjustments from '../components/reports/InventoryAdjustments.vue';

const store = useReportsStore();
const companyStore = useCompanyStore();

const activeTab = ref('income-statement');

// Add watcher for persistence
watch(() => store.filters, () => {
  store.saveFilters();
}, { deep: true });

const companies = ref([]);

const generateReport = async () => {
  if (!store.filters.startDate || !store.filters.endDate) {
    alert('Please select start and end dates');
    return;
  }

  try {
    if (activeTab.value === 'income-statement') {
      await store.fetchIncomeStatement(
        store.filters.startDate,
        store.filters.endDate,
        store.filters.companyId
      );
    }
  } catch (error) {
    console.error('Failed to generate report:', error);
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
        company_id: store.filters.companyId
      }
    );
  } catch (error) {
    console.error('Failed to export:', error);
    alert('Failed to export report');
  }
};

onMounted(async () => {
  // Load companies first
  await companyStore.fetchCompanies();
  companies.value = companyStore.companies;

  // Load persistence filters
  await store.loadFilters();
  
  // Set default dates if empty
  if (!store.filters.startDate) {
      const date = new Date();
      date.setDate(1);
      store.filters.startDate = date.toISOString().split('T')[0];
  }
  if (!store.filters.endDate) {
      store.filters.endDate = new Date().toISOString().split('T')[0];
  }
  
  // Auto-generate report with filters
  await generateReport();
});
</script>
