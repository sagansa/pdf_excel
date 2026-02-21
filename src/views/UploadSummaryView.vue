<template>
  <div class="space-y-6">
    <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
      <div>
        <h3 class="text-xl font-bold text-gray-900">Upload History Summary</h3>
        <p class="text-xs text-gray-500">Overview of all files uploaded to the system</p>
      </div>
      
      <div class="flex items-center gap-3">
        <!-- Filters -->
        <div class="flex items-center gap-2 bg-white px-3 py-1.5 rounded-xl border border-gray-200 shadow-sm">
          <i class="bi bi-funnel text-gray-400 text-xs"></i>
          
          <select v-model="filterBank" class="text-xs border-0 focus:ring-0 bg-transparent py-0 pr-8">
            <option value="">All Banks</option>
            <option v-for="bank in availableBanks" :key="bank" :value="bank">{{ formatBankCode(bank) }}</option>
          </select>
          
          <div class="h-4 w-px bg-gray-200 mx-1"></div>
          
          <select v-model="filterYear" class="text-xs border-0 focus:ring-0 bg-transparent py-0 pr-8">
            <option value="">All Years</option>
            <option v-for="year in availableYears" :key="year" :value="year">{{ year }}</option>
          </select>
        </div>

        <button 
          @click="store.fetchUploadSummary()" 
          class="btn-secondary flex items-center gap-2 py-2"
          :disabled="store.isLoading"
        >
          <i class="bi bi-arrow-clockwise" :class="{ 'animate-spin': store.isLoading }"></i>
          <span>Refresh</span>
        </button>
      </div>
    </div>

    <!-- Summary Table -->
    <div class="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th 
                @click="toggleSort('source_file')"
                class="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors group"
              >
                <div class="flex items-center gap-2">
                  Source File
                  <i v-if="sortBy === 'source_file'" class="bi" :class="sortDir === 'asc' ? 'bi-sort-alpha-down' : 'bi-sort-alpha-up-alt'"></i>
                  <i v-else class="bi bi-hash text-gray-300 opacity-0 group-hover:opacity-100"></i>
                </div>
              </th>
              <th class="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Bank</th>
              <th class="px-6 py-3 text-center text-xs font-bold text-gray-500 uppercase tracking-wider">Txns</th>
              <th class="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Period</th>
              <th class="px-6 py-3 text-right text-xs font-bold text-gray-500 uppercase tracking-wider">Totals</th>
              <th 
                @click="toggleSort('last_upload')"
                class="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors group"
              >
                <div class="flex items-center gap-2">
                  Last Upload
                  <i v-if="sortBy === 'last_upload'" class="bi" :class="sortDir === 'asc' ? 'bi-sort-numeric-down' : 'bi-sort-numeric-up-alt'"></i>
                  <i v-else class="bi bi-clock text-gray-300 opacity-0 group-hover:opacity-100"></i>
                </div>
              </th>
              <th class="px-6 py-3 text-center text-xs font-bold text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-100">
            <tr v-if="store.isLoading && store.uploadSummary.length === 0">
              <td colspan="7" class="text-center py-12">
                <span class="spinner-border text-indigo-500 w-8 h-8" role="status"></span>
              </td>
            </tr>
            <tr v-else-if="filteredAndSortedSummary.length === 0">
              <td colspan="7" class="text-center py-12 text-gray-400 italic">
                {{ store.uploadSummary.length === 0 ? 'No upload history found' : 'No matches found for active filters' }}
              </td>
            </tr>
            <tr v-for="item in filteredAndSortedSummary" :key="item.source_file + item.bank_code" class="hover:bg-gray-50 transition-colors">
              <td class="px-6 py-4">
                <div class="flex items-center gap-2">
                  <i class="bi bi-file-earmark-pdf text-red-500 text-lg"></i>
                  <span class="text-sm font-semibold text-gray-900 truncate max-w-xs" :title="item.source_file">
                    {{ item.source_file }}
                  </span>
                </div>
              </td>
              <td class="px-6 py-4 text-xs font-medium uppercase">
                <div class="flex flex-col gap-1">
                  <span class="text-gray-900 border-b border-gray-100 pb-0.5">{{ formatBankCode(item.bank_code) }}</span>
                </div>
              </td>
              <td class="px-6 py-4 text-center">
                <span class="bg-indigo-50 text-indigo-700 px-2.5 py-1 rounded-lg text-xs font-bold border border-indigo-100">
                  {{ item.transaction_count }}
                </span>
              </td>
              <td class="px-6 py-4 text-xs text-gray-500 font-mono">
                <div class="flex flex-col">
                  <span>{{ formatDate(item.start_date) }}</span>
                  <span class="text-[10px] text-gray-400 text-center">to</span>
                  <span>{{ formatDate(item.end_date) }}</span>
                </div>
              </td>
              <td class="px-6 py-4 text-right font-mono whitespace-nowrap">
                <div class="flex flex-col gap-0.5">
                  <div class="text-red-500 text-[10px]">DB: {{ formatAmount(item.total_debit) }}</div>
                  <div class="text-green-600 text-[10px]">CR: {{ formatAmount(item.total_credit) }}</div>
                </div>
              </td>
              <td class="px-6 py-4 text-[10px] text-gray-400">
                {{ formatDateTime(item.last_upload) }}
              </td>
              <td class="px-6 py-4 text-center">
                <button 
                  @click="openDeleteModal(item)"
                  class="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors border border-transparent hover:border-red-100"
                  :title="'Delete transactions from ' + item.source_file"
                  :disabled="store.isLoading"
                >
                  <i class="bi bi-trash"></i>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Delete Modal -->
    <DeleteSummaryModal 
      :show="showDeleteModal"
      :item="itemToDelete"
      :is-loading="store.isLoading"
      @close="closeDeleteModal"
      @confirm="confirmDelete"
    />
  </div>
</template>

<script setup>
import { onMounted, ref, computed } from 'vue';
import { useHistoryStore } from '../stores/history';
import DeleteSummaryModal from '../components/history/DeleteSummaryModal.vue';

const store = useHistoryStore();

// Filter State
const filterBank = ref('');
const filterYear = ref('');

// Sort State
const sortBy = ref('last_upload');
const sortDir = ref('desc');

// Delete Logic State
const showDeleteModal = ref(false);
const itemToDelete = ref(null);

onMounted(() => {
  store.fetchUploadSummary();
});

// Available filter options
const availableBanks = computed(() => {
  const banks = new Set(
    store.uploadSummary
      .map(item => item.bank_code)
      .filter(bank => bank !== null && bank !== undefined && String(bank).trim() !== '')
  );
  return Array.from(banks).sort();
});

const availableYears = computed(() => {
  const years = new Set();
  store.uploadSummary.forEach(item => {
    if (item.start_date) years.add(item.start_date.split('-')[0]);
    if (item.end_date) years.add(item.end_date.split('-')[0]);
  });
  return Array.from(years).sort().reverse();
});

// Filtering and Sorting Computed
const filteredAndSortedSummary = computed(() => {
  let result = [...store.uploadSummary];

  // Apply Filtering
  if (filterBank.value) {
    result = result.filter(item => item.bank_code === filterBank.value);
  }
  if (filterYear.value) {
    result = result.filter(item => {
      const startYear = item.start_date ? item.start_date.split('-')[0] : '';
      const endYear = item.end_date ? item.end_date.split('-')[0] : '';
      return startYear === filterYear.value || endYear === filterYear.value;
    });
  }

  // Apply Sorting
  result.sort((a, b) => {
    const dir = sortDir.value === 'asc' ? 1 : -1;
    let valA = a[sortBy.value];
    let valB = b[sortBy.value];

    // Handle alpha vs chrono
    if (sortBy.value === 'source_file') {
      valA = (valA || '').toLowerCase();
      valB = (valB || '').toLowerCase();
    }
    
    if (valA < valB) return -1 * dir;
    if (valA > valB) return 1 * dir;
    return 0;
  });

  return result;
});

const toggleSort = (key) => {
  if (sortBy.value === key) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc';
  } else {
    sortBy.value = key;
    sortDir.value = 'asc';
  }
};

const openDeleteModal = (item) => {
  itemToDelete.value = item;
  showDeleteModal.value = true;
};

const closeDeleteModal = () => {
  showDeleteModal.value = false;
  itemToDelete.value = null;
};

const confirmDelete = async () => {
  if (!itemToDelete.value) return;
  
  try {
    const item = itemToDelete.value;
    await store.deleteBySourceFile(item.source_file, item.bank_code);
    closeDeleteModal();
  } catch (err) {
    alert('Failed to delete transactions: ' + (err.response?.data?.error || err.message));
  }
};

const formatDate = (dateStr) => {
  if (!dateStr) return '-';
  return dateStr.split(' ')[0];
};

const formatDateTime = (dateTimeStr) => {
  if (!dateTimeStr) return '-';
  const parts = dateTimeStr.split(' ');
  return `${parts[0]} ${parts[1]}`;
};

const formatAmount = (amount) => {
  return new Intl.NumberFormat('id-ID').format(amount);
};

const formatBankCode = (bankCode) => {
  const value = (bankCode || '').toString();
  if (!value) return 'Unknown Bank';
  return value.replace('_CC', ' Credit Card');
};
</script>
