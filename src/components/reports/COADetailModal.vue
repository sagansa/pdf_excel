<template>
  <BaseModal :isOpen="isOpen" @close="$emit('close')" size="2xl">
    <div class="bg-white rounded-2xl p-6 w-full max-w-6xl max-h-[95vh] overflow-hidden flex flex-col shadow-2xl">
      <!-- Header -->
      <div class="flex items-center justify-between mb-4 pb-4 border-b border-gray-100">
        <div>
          <h2 class="text-xl font-bold text-gray-900">General Ledger</h2>
          <p class="text-sm text-gray-500 font-medium">{{ coaData.code }} - {{ coaData.name }}</p>
        </div>
      </div>

      <!-- Filters -->
      <div class="mb-6 p-4 bg-gray-50 border border-gray-200 rounded-xl">
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
          <!-- Month Filter -->
          <div>
            <label class="block text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-1.5">Month</label>
            <select
              v-model="filters.month"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm bg-white"
            >
              <option value="">All Months</option>
              <option v-for="month in availableMonths" :key="month.value" :value="month.value">
                {{ month.label }}
              </option>
            </select>
          </div>

          <!-- Type Filter -->
          <div>
            <label class="block text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-1.5">Type</label>
            <select
              v-model="filters.type"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm bg-white"
            >
              <option value="">All Types</option>
              <option v-for="type in availableTypes" :key="type" :value="type">
                {{ type === 'DB' ? 'Debit (DB)' : 'Credit (CR)' }}
              </option>
            </select>
          </div>

          <!-- Mark Filter -->
          <div>
            <label class="block text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-1.5">Marking</label>
            <select
              v-model="filters.markSearch"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm bg-white"
            >
              <option value="">All Markings</option>
              <option v-for="mark in availableMarkings" :key="mark" :value="mark">
                {{ mark }}
              </option>
            </select>
          </div>

          <!-- Actions -->
          <div class="flex gap-2">
            <button
              @click="clearFilters"
              class="flex-1 px-4 py-2 bg-white border border-gray-300 text-gray-700 font-semibold rounded-lg hover:bg-gray-50 transition-colors text-sm shadow-sm"
            >
              Clear All
            </button>
          </div>
        </div>
      </div>

      <!-- Stats Summary -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div class="bg-indigo-50 border border-indigo-100 rounded-xl p-4 flex items-center gap-4">
          <div class="w-10 h-10 rounded-full bg-indigo-100 flex items-center justify-center">
            <i class="bi bi-currency-dollar text-indigo-600"></i>
          </div>
          <div>
            <p class="text-[10px] font-bold text-indigo-400 uppercase tracking-wider">Net Balance</p>
            <p class="text-xl font-black text-indigo-900">{{ formatCurrency(totalBalance) }}</p>
          </div>
        </div>
        <div class="bg-gray-50 border border-gray-200 rounded-xl p-4 flex items-center gap-4">
          <div class="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center">
            <i class="bi bi-list-check text-gray-600"></i>
          </div>
          <div>
            <p class="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Transactions</p>
            <p class="text-xl font-black text-gray-900">{{ filteredTransactions.length }}</p>
          </div>
        </div>
        <div class="bg-gray-50 border border-gray-200 rounded-xl p-4 flex items-center gap-4">
          <div class="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center">
            <i class="bi bi-calendar3 text-gray-600"></i>
          </div>
          <div class="overflow-hidden">
            <p class="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Period</p>
            <p class="text-sm font-bold text-gray-700 truncate" :title="periodDisplay">{{ periodDisplay }}</p>
          </div>
        </div>
      </div>

      <!-- Main Content -->
      <div class="flex-1 overflow-hidden flex flex-col min-h-0">
        <div v-if="isLoading" class="flex-1 flex flex-col items-center justify-center py-20">
          <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-600"></div>
          <p class="mt-4 text-gray-500 text-sm font-medium">Fetching transactions...</p>
        </div>

        <div v-else-if="transactions.length === 0" class="flex-1 flex flex-col items-center justify-center py-20 bg-gray-50 rounded-2xl border-2 border-dashed border-gray-200 m-2">
          <div class="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center mb-4">
            <i class="bi bi-inbox text-3xl text-gray-300"></i>
          </div>
          <p class="text-gray-500 font-bold text-lg">No transactions found</p>
          <p class="text-gray-400 text-sm mt-1">There are no records for this COA in the selected period.</p>
        </div>

        <div v-else class="flex-1 overflow-auto rounded-xl border border-gray-200 shadow-inner bg-gray-50/20">
          <table class="w-full border-collapse">
            <thead class="bg-gray-50 sticky top-0 z-20 shadow-sm text-left">
              <tr>
                <th @click="sortBy('txn_date')" class="px-4 py-3 text-[10px] font-bold text-gray-400 uppercase tracking-widest cursor-pointer hover:bg-gray-100 transition-colors">
                  Date
                  <i v-if="sortConfig.key === 'txn_date'" :class="sortConfig.direction === 'asc' ? 'bi-caret-up-fill' : 'bi-caret-down-fill'" class="bi ms-1"></i>
                </th>
                <th @click="sortBy('description')" class="px-4 py-3 text-[10px] font-bold text-gray-400 uppercase tracking-widest cursor-pointer hover:bg-gray-100 transition-colors">
                  Description
                  <i v-if="sortConfig.key === 'description'" :class="sortConfig.direction === 'asc' ? 'bi-caret-up-fill' : 'bi-caret-down-fill'" class="bi ms-1"></i>
                </th>
                <th @click="sortBy('mark_name')" class="px-4 py-3 text-[10px] font-bold text-gray-400 uppercase tracking-widest cursor-pointer hover:bg-gray-100 transition-colors">
                  Marking
                  <i v-if="sortConfig.key === 'mark_name'" :class="sortConfig.direction === 'asc' ? 'bi-caret-up-fill' : 'bi-caret-down-fill'" class="bi ms-1"></i>
                </th>
                <th class="px-4 py-3 text-center text-[10px] font-bold text-gray-400 uppercase tracking-widest">Type</th>
                <th @click="sortBy('effective_amount')" class="px-4 py-3 text-right text-[10px] font-bold text-gray-400 uppercase tracking-widest cursor-pointer hover:bg-gray-100 transition-colors">
                  Amount
                  <i v-if="sortConfig.key === 'effective_amount'" :class="sortConfig.direction === 'asc' ? 'bi-caret-up-fill' : 'bi-caret-down-fill'" class="bi ms-1"></i>
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100 bg-white">
              <tr v-for="(txn, index) in filteredTransactions" :key="txn.id + '-' + index" class="hover:bg-indigo-50/30 transition-colors group">
                <td class="px-4 py-3 text-xs whitespace-nowrap text-gray-500 font-medium font-mono border-l-4 border-transparent group-hover:border-indigo-500">
                  {{ formatDate(txn.txn_date) }}
                </td>
                <td class="px-4 py-3 text-sm text-gray-900 font-medium max-w-[400px]">
                  {{ txn.description }}
                </td>
                <td class="px-4 py-3 text-sm">
                  <span v-if="txn.mark_name" class="inline-flex items-center px-2.5 py-1 rounded-md text-[11px] font-bold bg-gray-100 text-gray-600 border border-gray-200">
                    {{ txn.mark_name }}
                  </span>
                  <span v-else class="text-gray-300 italic text-xs">Unmarked</span>
                </td>
                <td class="px-4 py-3 text-center">
                  <div class="inline-flex items-center justify-center px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-tighter"
                    :class="txn.db_cr === 'CR' ? 'bg-green-100 text-green-700 border border-green-200' : 'bg-red-100 text-red-700 border border-red-200'">
                    {{ txn.db_cr }}
                  </div>
                </td>
                <td class="px-4 py-3 text-sm text-right font-mono font-black"
                  :class="txn.effective_amount >= 0 ? 'text-green-700' : 'text-red-600'">
                  {{ (txn.effective_amount >= 0 ? '' : '-') + formatAmount(Math.abs(txn.effective_amount)) }}
                </td>
              </tr>
            </tbody>
          </table>
          
          <div v-if="filteredTransactions.length === 0" class="p-20 text-center">
            <p class="text-gray-400 italic text-sm">No transactions match your search filters.</p>
            <button @click="clearFilters" class="mt-2 text-indigo-600 font-bold hover:underline text-xs">Clear all filters</button>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="mt-6 pt-4 border-t border-gray-100 flex justify-between items-center text-gray-400">
        <p class="text-[10px] font-medium uppercase tracking-widest flex items-center gap-2">
          <i class="bi bi-info-circle text-indigo-400"></i>
          General Ledger Report - Total {{ filteredTransactions.length }} Entries
        </p>
        <button @click="$emit('close')" class="px-3 py-1.5 text-gray-500 hover:text-gray-800 text-[11px] font-bold uppercase tracking-wider hover:bg-gray-50 rounded transition-colors flex items-center gap-2">
          <i class="bi bi-arrow-left"></i>
          Back to Reports
        </button>
      </div>
    </div>
  </BaseModal>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import BaseModal from '../ui/BaseModal.vue';
import { reportsApi } from '../../api';

const props = defineProps({
  isOpen: Boolean,
  coaData: {
    type: Object,
    required: true
  },
  filters: {
    type: Object,
    default: () => ({})
  }
});

const emit = defineEmits(['close']);

const isLoading = ref(false);
const transactions = ref([]);

// Sorting configuration
const sortConfig = ref({
  key: 'txn_date',
  direction: 'desc'
});

const sortBy = (key) => {
  if (sortConfig.value.key === key) {
    sortConfig.value.direction = sortConfig.value.direction === 'asc' ? 'desc' : 'asc';
  } else {
    sortConfig.value.key = key;
    sortConfig.value.direction = 'asc';
  }
};

const periodDisplay = computed(() => {
  if (props.filters.startDate && props.filters.endDate) {
    return `${formatDate(props.filters.startDate)} - ${formatDate(props.filters.endDate)}`;
  } else if (props.filters.asOfDate) {
    return `As of ${formatDate(props.filters.asOfDate)}`;
  }
  return 'All time';
});

const totalBalance = computed(() => {
  return filteredTransactions.value.reduce((sum, txn) => sum + (txn.effective_amount || 0), 0);
});

// Available months for filter
const availableMonths = computed(() => {
  const months = new Set();
  transactions.value.forEach(txn => {
    const date = new Date(txn.txn_date);
    const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
    months.add(monthKey);
  });

  return Array.from(months)
    .sort((a, b) => b.localeCompare(a))
    .map(m => {
      const [year, monthNum] = m.split('-');
      const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
      return {
        value: m,
        label: `${monthNames[parseInt(monthNum) - 1]} ${year}`
      };
    });
});

// Available types for filter (CR/DB)
const availableTypes = computed(() => {
  const types = new Set();
  transactions.value.forEach(txn => {
    if (txn.db_cr) types.add(txn.db_cr);
  });
  return Array.from(types).sort();
});

// Available markings for filter
const availableMarkings = computed(() => {
  const marks = new Set();
  transactions.value.forEach(txn => {
    if (txn.mark_name) marks.add(txn.mark_name);
  });
  return Array.from(marks).sort();
});

// Filters
const filters = ref({
  month: '',
  type: '',
  markSearch: ''
});

// Filtered and Sorted transactions
const filteredTransactions = computed(() => {
  let filtered = [...transactions.value];

  // Apply filters
  if (filters.value.month) {
    filtered = filtered.filter(txn => {
      const date = new Date(txn.txn_date);
      const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
      return monthKey === filters.value.month;
    });
  }

  if (filters.value.type) {
    filtered = filtered.filter(txn => txn.db_cr === filters.value.type);
  }

  if (filters.value.markSearch) {
    filtered = filtered.filter(txn => txn.mark_name === filters.value.markSearch);
  }

  // Apply sorting
  const { key, direction } = sortConfig.value;
  filtered.sort((a, b) => {
    let valA = a[key] || '';
    let valB = b[key] || '';

    if (key === 'txn_date') {
      valA = new Date(valA).getTime();
      valB = new Date(valB).getTime();
    } else if (key === 'effective_amount') {
      valA = parseFloat(valA);
      valB = parseFloat(valB);
    } else {
      valA = String(valA).toLowerCase();
      valB = String(valB).toLowerCase();
    }

    if (valA < valB) return direction === 'asc' ? -1 : 1;
    if (valA > valB) return direction === 'asc' ? 1 : -1;
    return 0;
  });

  return filtered;
});

// Clear all filters
const clearFilters = () => {
  filters.value = { month: '', type: '', markSearch: '' };
};

const formatDate = (dateStr) => {
  if (!dateStr) return '-';
  const date = new Date(dateStr);
  return date.toLocaleDateString('id-ID', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
};

const formatAmount = (amount) => {
  if (amount === null || amount === undefined) return '0';
  return new Intl.NumberFormat('id-ID', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(amount);
};

const formatCurrency = (amount) => {
  if (amount === null || amount === undefined) return 'Rp 0';
  return 'Rp ' + formatAmount(amount);
};

const fetchTransactions = async () => {
  if (!props.coaData?.id) return;

  isLoading.value = true;
  try {
    const params = { coa_id: props.coaData.id };

    // For balance sheet accounts, prioritize as_of_date logic
    const isBalanceSheetAccount = props.coaData.category && ['ASSET', 'LIABILITY', 'EQUITY'].includes(props.coaData.category);
    
    if (isBalanceSheetAccount && props.filters.asOfDate) {
      // For balance sheet accounts, use as_of_date logic
      params.as_of_date = props.filters.asOfDate;
    } else {
      // For income statement accounts or fallback, use date range logic
      if (props.filters.startDate && props.filters.endDate) {
        params.start_date = props.filters.startDate;
        params.end_date = props.filters.endDate;
      }
      if (props.filters.asOfDate) {
        params.as_of_date = props.filters.asOfDate;
      }
    }
    
    if (props.filters.companyId) {
      params.company_id = props.filters.companyId;
    }

    console.log('Fetching COA Detail with params:', params);
    const res = await reportsApi.getCoaDetail(params);
    console.log('Response:', res.data);
    console.log('Transactions count:', res.data.transactions?.length || 0);
    transactions.value = res.data.transactions || [];
  } catch (e) {
    console.error('Failed to fetch COA details:', e);
    transactions.value = [];
  } finally {
    isLoading.value = false;
  }
};

watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    fetchTransactions();
    // Reset sort when opening
    sortConfig.value = { key: 'txn_date', direction: 'desc' };
  } else {
    transactions.value = [];
    filters.value = { month: '', type: '', markSearch: '' };
  }
});
</script>
