<template>
  <div class="bg-gradient-to-br from-white to-gray-50 rounded-2xl shadow-sm border border-gray-200 p-6 relative overflow-hidden">
    <div class="flex items-center justify-between mb-6 relative z-10">
      <div>
        <h3 class="text-lg font-bold text-gray-900">Financial Overview</h3>
        <p class="text-xs text-gray-500">{{ currentPeriod }}</p>
      </div>
      <router-link 
        to="/reports" 
        class="text-xs font-medium text-indigo-600 hover:text-indigo-700 bg-indigo-50 px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1"
      >
        <span>View Full Report</span>
        <i class="bi bi-arrow-right"></i>
      </router-link>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="grid grid-cols-1 md:grid-cols-3 gap-4 animate-pulse">
      <div v-for="i in 3" :key="i" class="h-24 bg-gray-100 rounded-xl"></div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="bg-red-50 text-red-600 p-4 rounded-xl text-sm flex items-center gap-2">
      <i class="bi bi-exclamation-circle"></i>
      <span>Failed to load financial data</span>
    </div>

    <!-- Data Display -->
    <div v-else class="grid grid-cols-1 md:grid-cols-3 gap-6 relative z-10">
      <!-- Revenue -->
      <div class="bg-white p-4 rounded-xl shadow-sm border border-gray-100">
        <div class="flex items-center gap-3 mb-2">
          <div class="w-8 h-8 rounded-lg bg-green-100 text-green-600 flex items-center justify-center">
            <i class="bi bi-arrow-up-right text-sm"></i>
          </div>
          <span class="text-xs font-semibold text-gray-500 uppercase tracking-wide">Revenue</span>
        </div>
        <p class="text-xl font-bold text-gray-900">{{ formatCurrency(revenue) }}</p>
      </div>

      <!-- Expenses -->
      <div class="bg-white p-4 rounded-xl shadow-sm border border-gray-100">
        <div class="flex items-center gap-3 mb-2">
          <div class="w-8 h-8 rounded-lg bg-red-100 text-red-600 flex items-center justify-center">
            <i class="bi bi-arrow-down-right text-sm"></i>
          </div>
          <span class="text-xs font-semibold text-gray-500 uppercase tracking-wide">Expenses</span>
        </div>
        <p class="text-xl font-bold text-gray-900">{{ formatCurrency(expenses) }}</p>
      </div>

      <!-- Net Income -->
      <div class="bg-gradient-to-br from-indigo-600 to-indigo-700 p-4 rounded-xl shadow-lg text-white">
        <div class="flex items-center gap-3 mb-2">
          <div class="w-8 h-8 rounded-lg bg-white/20 flex items-center justify-center">
            <i class="bi bi-wallet2 text-sm text-white"></i>
          </div>
          <span class="text-xs font-semibold text-indigo-100 uppercase tracking-wide">Net Income</span>
        </div>
        <p class="text-xl font-bold text-white">{{ formatCurrency(netIncome) }}</p>
      </div>
    </div>

    <!-- Decorative Elements -->
    <div class="absolute top-0 right-0 w-64 h-64 bg-indigo-50/50 rounded-full blur-3xl -mr-32 -mt-32 pointer-events-none"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useReportsStore } from '../../stores/reports';

const store = useReportsStore();
const isLoading = ref(true);
const revenue = ref(0);
const expenses = ref(0);
const netIncome = ref(0);
const error = ref(null);

const currentPeriod = computed(() => {
  const date = new Date();
  return date.toLocaleDateString('id-ID', { month: 'long', year: 'numeric' });
});

const formatCurrency = (amount) => {
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    maximumFractionDigits: 0
  }).format(amount);
};

onMounted(async () => {
  try {
    const today = new Date();
    // Start of month
    const startDate = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().split('T')[0];
    // Today
    const endDate = today.toISOString().split('T')[0];

    await store.fetchIncomeStatement(startDate, endDate);
    
    revenue.value = store.totalRevenue;
    expenses.value = store.totalExpenses;
    netIncome.value = store.netIncome;
  } catch (err) {
    error.value = err.message;
  } finally {
    isLoading.value = false;
  }
});
</script>
