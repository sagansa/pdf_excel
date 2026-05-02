<template>
  <div class="space-y-6">
    <!-- Header Summary (Simplified) -->
    <div class="bg-surface p-4 rounded-xl shadow-sm border border-border">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-lg font-semibold text-theme">Monthly Revenue Summary ({{ selectedYear }})</h3>
        <p class="text-xs text-muted">Historical comparison and growth</p>
      </div>

      <!-- Summary Cards -->
      <div v-if="isLoading" class="py-12 text-center">
        <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
        <p class="text-sm text-muted mt-2">Loading data...</p>
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4">
        <div
          v-for="item in processedMonthlyData"
          :key="item.month"
          class="p-4 rounded-xl border transition-all hover:shadow-md"
          :class="monthCardClass(item)"
        >
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-bold uppercase tracking-wider text-muted">{{ getMonthName(item.month) }}</span>
            <div v-if="item.revenue > 0" class="h-2 w-2 rounded-full bg-green-500"></div>
          </div>
          <div class="flex flex-col">
            <span class="text-2xl font-bold" :class="item.revenue > 0 ? 'text-theme' : 'text-muted'">
              {{ formatCurrency(item.revenue) }}
            </span>

            <!-- Comparison Info -->
            <div class="mt-2 flex items-center justify-between border-t border-border pt-2" v-if="item.revenue > 0 || item.prevRevenue > 0">
              <div class="flex flex-col">
                <span class="text-[9px] text-muted uppercase font-semibold">Prev Year</span>
                <span class="text-xs font-medium text-muted">{{ formatCurrency(item.prevRevenue) }}</span>
              </div>
              <div
                v-if="item.growth !== null"
                class="text-[10px] font-bold px-1.5 py-0.5 rounded flex items-center gap-0.5"
                :class="item.growth >= 0 ? 'bg-green-500/10 text-success' : 'bg-red-500/10 text-danger'"
              >
                <i :class="item.growth >= 0 ? 'bi bi-arrow-up-short' : 'bi bi-arrow-down-short'"></i>
                {{ Math.abs(item.growth).toFixed(1) }}%
              </div>
            </div>
            <span v-else class="text-[10px] text-muted mt-1">No revenue data</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Total Annual Summary -->
    <div v-if="!isLoading" class="bg-surface-raised rounded-xl p-6 text-theme shadow-lg border border-border overflow-hidden relative">
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div class="flex-1">
          <h4 class="text-muted text-sm font-medium uppercase tracking-widest mb-1">Total Revenue {{ selectedYear }}</h4>
          <p class="text-4xl font-black">{{ formatCurrency(totalAnnualRevenue) }}</p>
        </div>
        <div v-if="annualGrowth !== null" class="bg-surface border border-border rounded-xl p-4">
          <div class="text-xs text-muted mb-1 uppercase tracking-wider font-bold">Annual Growth</div>
          <div class="flex items-end gap-2">
            <span class="text-2xl font-black">{{ annualGrowth >= 0 ? '+' : '' }}{{ annualGrowth.toFixed(1) }}%</span>
            <span class="text-[10px] text-muted mb-1">vs {{ parseInt(selectedYear) - 1 }}</span>
          </div>
        </div>
        <div class="text-right flex flex-col justify-end">
          <p class="text-muted text-xs italic">Data summary for Coretax purposes</p>
          <p class="text-muted text-[10px] mt-1">Prev Year: {{ formatCurrency(totalPrevAnnualRevenue) }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { watch, computed, ref } from 'vue';
import { useReportsStore } from '../../stores/reports';

const store = useReportsStore();

const props = defineProps({
  companyId: {
    type: [String, Number],
    default: null
  },
  year: {
    type: [String, Number],
    default: new Date().getFullYear()
  }
});

const isLoading = ref(false);

const selectedYear = computed(() => store.filters.year || props.year);

const getMonthName = (monthNum) => {
  return new Intl.DateTimeFormat('en-US', { month: 'long' }).format(new Date(2000, monthNum - 1, 1));
};

const normalizeRevenue = (amount) => Math.abs(Number(amount || 0));

const formatCurrency = (amount) => {
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(amount);
};

const monthlyData = computed(() => {
  return store.monthlyRevenue || [];
});
const monthlyPrevData = computed(() => {
  return store.monthlyRevenuePrevYear || [];
});

const processedMonthlyData = computed(() => {
  return monthlyData.value.map((item, index) => {
    const prevItem = monthlyPrevData.value[index] || { revenue: 0 };
    const revenue = normalizeRevenue(item.revenue);
    const prevRevenue = normalizeRevenue(prevItem.revenue);

    let growth = null;
    if (prevRevenue > 0) {
      growth = ((revenue - prevRevenue) / prevRevenue) * 100;
    }

    return {
      ...item,
      prevRevenue,
      growth
    };
  });
});

const totalAnnualRevenue = computed(() => {
  const total = monthlyData.value.reduce((sum, item) => sum + normalizeRevenue(item.revenue), 0);
  return total;
});

const totalPrevAnnualRevenue = computed(() => {
  return monthlyPrevData.value.reduce((sum, item) => sum + normalizeRevenue(item.revenue), 0);
});

const annualGrowth = computed(() => {
  if (totalPrevAnnualRevenue.value === 0) return null;
  return ((totalAnnualRevenue.value - totalPrevAnnualRevenue.value) / totalPrevAnnualRevenue.value) * 100;
});

const fetchData = async () => {
  // Use store.filters.year instead of props.year to ensure synchronization
  const yearToFetch = selectedYear.value;

  if (!yearToFetch) return;
  isLoading.value = true;
  try {
    await store.fetchMonthlyRevenue(yearToFetch, props.companyId, store.filters.reportType || 'real');
  } catch (error) {
    console.error('Failed to fetch monthly revenue:', error);
  } finally {
    isLoading.value = false;
  }
};

const monthCardClass = (item) => {
  if (item.revenue > 0) {
    return 'bg-surface-raised border-border hover:border-primary/50';
  }
  return 'bg-surface-muted/70 border-border text-muted';
};

watch(() => [props.companyId, selectedYear.value, store.filters.reportType], () => {
  fetchData();
}, { deep: true, immediate: true });

</script>

<style scoped>
/* Any custom styles here */
</style>
