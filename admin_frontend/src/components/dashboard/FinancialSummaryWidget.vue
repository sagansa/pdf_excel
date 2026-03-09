<template>
  <div class="surface-card relative overflow-hidden p-6">
    <div class="flex items-center justify-between mb-6 relative z-10">
      <div>
        <h3 class="text-lg font-bold text-theme">Financial Overview</h3>
        <p class="text-xs text-muted">{{ currentPeriod }}</p>
      </div>
      <router-link 
        to="/reports" 
        class="btn-secondary !px-3 !py-1.5 !text-xs gap-1"
      >
        <span>View Full Report</span>
        <i class="bi bi-arrow-right"></i>
      </router-link>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="grid grid-cols-1 md:grid-cols-3 gap-4 animate-pulse">
      <div v-for="i in 3" :key="i" class="h-24 rounded-2xl summary-skeleton"></div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="summary-error p-4 rounded-2xl text-sm flex items-center gap-2">
      <i class="bi bi-exclamation-circle"></i>
      <span>Failed to load financial data</span>
    </div>

    <!-- Data Display -->
    <div v-else class="grid grid-cols-1 md:grid-cols-3 gap-6 relative z-10">
      <!-- Revenue -->
      <div class="summary-card">
        <div class="flex items-center gap-3 mb-2">
          <div class="summary-icon summary-icon--success">
            <i class="bi bi-arrow-up-right text-sm"></i>
          </div>
          <span class="text-xs font-semibold text-muted uppercase tracking-wide">Revenue</span>
        </div>
        <p class="text-xl font-bold text-theme mono">{{ formatCurrency(revenue) }}</p>
      </div>

      <!-- Expenses -->
      <div class="summary-card">
        <div class="flex items-center gap-3 mb-2">
          <div class="summary-icon summary-icon--danger">
            <i class="bi bi-arrow-down-right text-sm"></i>
          </div>
          <span class="text-xs font-semibold text-muted uppercase tracking-wide">Expenses</span>
        </div>
        <p class="text-xl font-bold text-theme mono">{{ formatCurrency(expenses) }}</p>
      </div>

      <!-- Net Income -->
      <div class="summary-card summary-card--highlight text-white">
        <div class="flex items-center gap-3 mb-2">
          <div class="summary-icon summary-icon--inverse">
            <i class="bi bi-wallet2 text-sm text-white"></i>
          </div>
          <span class="text-xs font-semibold text-white/70 uppercase tracking-wide">Net Income</span>
        </div>
        <p class="text-xl font-bold text-white mono">{{ formatCurrency(netIncome) }}</p>
      </div>
    </div>

    <!-- Decorative Elements -->
    <div class="absolute top-0 right-0 w-64 h-64 widget-glow rounded-full blur-3xl -mr-32 -mt-32 pointer-events-none"></div>
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

<style scoped>
.summary-card {
  @apply rounded-2xl p-4;
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border);
}

.summary-card--highlight {
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-strong));
  border-color: transparent;
  box-shadow: 0 18px 32px rgba(15, 118, 110, 0.22);
}

.summary-icon {
  @apply flex h-9 w-9 items-center justify-center rounded-xl;
}

.summary-icon--success {
  background: rgba(22, 101, 52, 0.12);
  color: var(--color-success);
}

.summary-icon--danger {
  background: rgba(185, 28, 28, 0.12);
  color: var(--color-danger);
}

.summary-icon--inverse {
  background: rgba(255, 255, 255, 0.18);
}

.summary-error {
  background: rgba(185, 28, 28, 0.08);
  border: 1px solid rgba(185, 28, 28, 0.18);
  color: var(--color-danger);
}

.summary-skeleton {
  background: var(--color-surface-muted);
}

.widget-glow {
  background: rgba(15, 118, 110, 0.10);
}
</style>
