<template>
  <div class="space-y-6">
    <!-- Loading State -->
    <div v-if="isLoading" class="flex justify-center py-12">
      <div class="spinner-border w-8 h-8 text-indigo-600 border-2"></div>
    </div>

    <!-- Empty State -->
    <div v-else-if="!marks.length" class="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
      <div class="w-16 h-16 bg-indigo-50 text-indigo-600 rounded-full flex items-center justify-center mx-auto mb-4">
        <i class="bi bi-tags text-3xl"></i>
      </div>
      <h3 class="text-lg font-bold text-gray-900">No Data Found</h3>
      <p class="text-gray-500 text-sm mt-1">Try changing the date range or company filter</p>
    </div>

    <!-- Report Content -->
    <div v-else class="space-y-6">
      <!-- Summary Cards -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p class="text-xs font-medium text-blue-600 uppercase mb-1">Total Debit</p>
          <p class="text-xl font-bold text-blue-900">{{ formatCurrency(summary.total_debit) }}</p>
        </div>
        <div class="bg-green-50 border border-green-200 rounded-lg p-4">
          <p class="text-xs font-medium text-green-600 uppercase mb-1">Total Credit</p>
          <p class="text-xl font-bold text-green-900">{{ formatCurrency(summary.total_credit) }}</p>
        </div>
        <div class="bg-purple-50 border border-purple-200 rounded-lg p-4">
          <p class="text-xs font-medium text-purple-600 uppercase mb-1">Net Difference</p>
          <p class="text-xl font-bold text-purple-900" :class="summary.net_difference >= 0 ? '' : 'text-red-600'">{{ formatCurrency(summary.net_difference) }}</p>
        </div>
        <div class="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <p class="text-xs font-medium text-gray-600 uppercase mb-1">Total Marks</p>
          <p class="text-xl font-bold text-gray-900">{{ summary.total_marks }}</p>
        </div>
      </div>

      <!-- Table -->
      <div class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th 
                  class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100 select-none"
                  @click="setSort('mark_name')"
                >
                  Mark 
                  <i class="bi ml-1" :class="getSortIcon('mark_name')"></i>
                </th>
                <th 
                  class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100 select-none"
                  @click="setSort('total_debit')"
                >
                  Debit 
                  <i class="bi ml-1" :class="getSortIcon('total_debit')"></i>
                </th>
                <th 
                  class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100 select-none"
                  @click="setSort('total_credit')"
                >
                  Credit 
                  <i class="bi ml-1" :class="getSortIcon('total_credit')"></i>
                </th>
                <th 
                  class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100 select-none"
                  @click="setSort('net_amount')"
                >
                  Net 
                  <i class="bi ml-1" :class="getSortIcon('net_amount')"></i>
                </th>
                <th 
                  class="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100 select-none"
                  @click="setSort('transaction_count')"
                >
                  Transactions 
                  <i class="bi ml-1" :class="getSortIcon('transaction_count')"></i>
                </th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr v-for="mark in sortedMarks" :key="mark.mark_id" class="hover:bg-gray-50">
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="text-sm font-bold text-gray-900">{{ mark.mark_name }}</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-right">
                  <div class="text-sm font-bold text-green-600">{{ formatCurrency(mark.total_debit) }}</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-right">
                  <div class="text-sm font-bold text-red-600">{{ formatCurrency(mark.total_credit) }}</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-right">
                  <div class="text-sm font-bold" :class="mark.net_amount >= 0 ? 'text-green-600' : 'text-red-600'">
                    {{ formatCurrency(mark.net_amount) }}
                  </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-center">
                  <span class="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-700 rounded">
                    {{ mark.transaction_count }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed } from 'vue';
import { useReportsStore } from '../../stores/reports';
import { reportsApi } from '../../api';

const props = defineProps({
  filters: Object
});

const marks = ref([]);
const summary = ref({});
const isLoading = ref(false);
const sortBy = ref('mark_name'); // 'mark_name', 'total_debit', 'total_credit', 'net_amount', 'transaction_count'
const sortDesc = ref(false);

const store = useReportsStore();

const sortedMarks = computed(() => {
  const sorted = [...marks.value];
  sorted.sort((a, b) => {
    let aVal = a[sortBy.value];
    let bVal = b[sortBy.value];
    
    // Handle string comparison for mark_name
    if (typeof aVal === 'string') {
      aVal = aVal.toLowerCase();
      bVal = bVal.toLowerCase();
    }
    
    if (sortDesc.value) {
      return aVal < bVal ? 1 : aVal > bVal ? -1 : 0;
    } else {
      return aVal > bVal ? 1 : aVal < bVal ? -1 : 0;
    }
  });
  return sorted;
});

const setSort = (field) => {
  if (sortBy.value === field) {
    sortDesc.value = !sortDesc.value;
  } else {
    sortBy.value = field;
    sortDesc.value = false;
  }
};

const getSortIcon = (field) => {
  if (sortBy.value !== field) return 'bi-arrow-down-up text-gray-300';
  return sortDesc.value ? 'bi-sort-down text-indigo-600' : 'bi-sort-up text-indigo-600';
};

const loadData = async () => {
  if (!store.filters.startDate || !store.filters.endDate) return;
  
  isLoading.value = true;
  try {
    const response = await reportsApi.getMarksSummary(
      store.filters.startDate,
      store.filters.endDate,
      store.filters.companyId,
      store.filters.reportType
    );
    marks.value = response.data.marks || [];
    summary.value = response.data.summary || {};
  } catch (err) {
    console.error('Failed to load marks summary:', err);
  } finally {
    isLoading.value = false;
  }
};

const formatCurrency = (amount) => {
  if (!amount) return 'Rp 0';
  
  const numericValue = Number(amount);
  const isNegative = numericValue < 0;
  const absValue = Math.abs(numericValue);
  
  const formatted = new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(absValue);
  
  // Accounting format: use parentheses for negative numbers
  return isNegative ? `(${formatted})` : formatted;
};

// Watch filters changes
watch(() => [store.filters.startDate, store.filters.endDate, store.filters.companyId], () => {
  loadData();
}, { deep: true });

onMounted(() => {
  loadData();
});
</script>
