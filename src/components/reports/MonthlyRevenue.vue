<template>
  <div class="space-y-6">
    <!-- Header Summary (Simplified) -->
    <div class="bg-white p-4 rounded-xl shadow-sm border border-slate-200">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-lg font-semibold text-slate-800">Monthly Revenue Summary ({{ year }})</h3>
        <p class="text-xs text-slate-500">Historical comparison and growth</p>
      </div>
      
      <!-- Summary Cards -->
      <div v-if="isLoading" class="py-12 text-center">
        <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
        <p class="text-sm text-slate-500 mt-2">Loading data...</p>
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4">
        <div 
          v-for="item in processedMonthlyData" 
          :key="item.month"
          class="p-4 rounded-xl border transition-all hover:shadow-md"
          :class="item.revenue > 0 ? 'bg-white border-slate-200' : 'bg-slate-50/50 border-slate-100'"
        >
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-bold uppercase tracking-wider text-slate-400">{{ getMonthName(item.month) }}</span>
            <div v-if="item.revenue > 0" class="h-2 w-2 rounded-full bg-green-500"></div>
          </div>
          <div class="flex flex-col">
            <span class="text-2xl font-bold" :class="item.revenue > 0 ? 'text-slate-800' : 'text-slate-300'">
              {{ formatCurrency(item.revenue) }}
            </span>
            
            <!-- Comparison Info -->
            <div class="mt-2 flex items-center justify-between border-t border-slate-100 pt-2" v-if="item.revenue > 0 || item.prevRevenue > 0">
              <div class="flex flex-col">
                <span class="text-[9px] text-slate-400 uppercase font-semibold">Prev Year</span>
                <span class="text-xs font-medium text-slate-500">{{ formatCurrency(item.prevRevenue) }}</span>
              </div>
              <div 
                v-if="item.growth !== null"
                class="text-[10px] font-bold px-1.5 py-0.5 rounded flex items-center gap-0.5"
                :class="item.growth >= 0 ? 'bg-green-50 text-green-600' : 'bg-red-50 text-red-600'"
              >
                <i :class="item.growth >= 0 ? 'bi bi-arrow-up-short' : 'bi bi-arrow-down-short'"></i>
                {{ Math.abs(item.growth).toFixed(1) }}%
              </div>
            </div>
            <span v-else class="text-[10px] text-slate-300 mt-1">No revenue data</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Total Annual Summary -->
    <div v-if="!isLoading" class="bg-indigo-600 rounded-xl p-6 text-white shadow-lg overflow-hidden relative">
      <div class="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div class="flex-1">
          <h4 class="text-indigo-100 text-sm font-medium uppercase tracking-widest mb-1">Total Revenue {{ year }}</h4>
          <p class="text-4xl font-black">{{ formatCurrency(totalAnnualRevenue) }}</p>
        </div>
        <div v-if="annualGrowth !== null" class="bg-white/10 backdrop-blur-md rounded-xl p-4 border border-white/20">
          <div class="text-xs text-indigo-100 mb-1 uppercase tracking-wider font-bold">Annual Growth</div>
          <div class="flex items-end gap-2">
            <span class="text-2xl font-black">{{ annualGrowth >= 0 ? '+' : '' }}{{ annualGrowth.toFixed(1) }}%</span>
            <span class="text-[10px] text-indigo-200 mb-1">vs {{ parseInt(year) - 1 }}</span>
          </div>
        </div>
        <div class="text-right flex flex-col justify-end">
          <p class="text-indigo-200 text-xs italic">Data summary for Coretax purposes</p>
          <p class="text-indigo-300 text-[10px] mt-1">Prev Year: {{ formatCurrency(totalPrevAnnualRevenue) }}</p>
        </div>
      </div>
      <!-- Decorative background -->
      <div class="absolute -right-10 -top-10 h-40 w-40 bg-white/10 rounded-full blur-3xl"></div>
      <div class="absolute -left-10 -bottom-10 h-40 w-40 bg-indigo-400/20 rounded-full blur-3xl"></div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, watch, computed, ref } from 'vue';
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

const getMonthName = (monthNum) => {
  return new Intl.DateTimeFormat('en-US', { month: 'long' }).format(new Date(2000, monthNum - 1, 1));
};

const formatCurrency = (amount) => {
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    minimumFractionDigits: 0
  }).format(amount);
};

const monthlyData = computed(() => store.monthlyRevenue || []);
const monthlyPrevData = computed(() => store.monthlyRevenuePrevYear || []);

const processedMonthlyData = computed(() => {
  return monthlyData.value.map((item, index) => {
    const prevItem = monthlyPrevData.value[index] || { revenue: 0 };
    const revenue = item.revenue || 0;
    const prevRevenue = prevItem.revenue || 0;
    
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
  return monthlyData.value.reduce((sum, item) => sum + item.revenue, 0);
});

const totalPrevAnnualRevenue = computed(() => {
  return monthlyPrevData.value.reduce((sum, item) => sum + item.revenue, 0);
});

const annualGrowth = computed(() => {
  if (totalPrevAnnualRevenue.value === 0) return null;
  return ((totalAnnualRevenue.value - totalPrevAnnualRevenue.value) / totalPrevAnnualRevenue.value) * 100;
});

const fetchData = async () => {
  if (!props.year) return;
  isLoading.value = true;
  try {
    await store.fetchMonthlyRevenue(props.year, props.companyId);
  } catch (error) {
    console.error('Failed to fetch monthly revenue:', error);
  } finally {
    isLoading.value = false;
  }
};

watch(() => [props.companyId, props.year], () => {
  fetchData();
}, { deep: true });

onMounted(() => {
  fetchData();
});
</script>

<style scoped>
/* Any custom styles here */
</style>
