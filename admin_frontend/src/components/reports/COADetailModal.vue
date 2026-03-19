<template>
  <BaseModal :isOpen="isOpen" @close="$emit('close')" size="2xl">
    <template #title>
      <div class="flex flex-col">
        <span class="text-xs font-bold uppercase tracking-widest text-primary opacity-70 mb-0.5">General Ledger Detail</span>
        <span class="text-theme">{{ coaData.code }} - {{ coaData.name }}</span>
      </div>
    </template>

    <div class="space-y-6 p-6">
      <!-- Filters -->
      <SectionCard body-class="p-4 bg-surface-muted/30">
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
          <FormField label="Month" label-class="!text-[10px] !font-black uppercase tracking-wider">
            <SelectInput
              v-model="filters.month"
              :options="[
                { value: '', label: 'All Months' },
                ...availableMonths
              ]"
              size="sm"
            />
          </FormField>

          <FormField label="Type" label-class="!text-[10px] !font-black uppercase tracking-wider">
            <SelectInput
              v-model="filters.type"
              :options="[
                { value: '', label: 'All Types' },
                ...availableTypes.map(t => ({ value: t, label: t === 'DB' ? 'Debit (DB)' : 'Credit (CR)' }))
              ]"
              size="sm"
            />
          </FormField>

          <FormField label="Marking" label-class="!text-[10px] !font-black uppercase tracking-wider">
            <SelectInput
              v-model="filters.markSearch"
              :options="[
                { value: '', label: 'All Markings' },
                ...availableMarkings.map(m => ({ value: m, label: m }))
              ]"
              size="sm"
            />
          </FormField>

          <div class="flex gap-2">
            <Button
              variant="secondary"
              @click="clearFilters"
              size="sm"
              full-width
              class="h-[38px]"
            >
              Clear All
            </Button>
          </div>
        </div>
      </SectionCard>

      <!-- Stats Summary -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard 
          icon="bi bi-currency-dollar" 
          label="Net Balance" 
          :value="formatCurrency(totalBalance)" 
          variant="primary"
        />
        <StatCard 
          icon="bi bi-list-check" 
          label="Transactions" 
          :value="filteredTransactions.length" 
          variant="default"
        />
        <StatCard 
          icon="bi bi-calendar3" 
          label="Period" 
          :value="periodDisplay" 
          variant="default"
          class="overflow-hidden"
        />
      </div>

      <!-- Main Content -->
      <div class="flex-1 overflow-hidden flex flex-col min-h-[400px]">
        <div v-if="isLoading" class="flex-1 flex flex-col items-center justify-center py-20 grayscale opacity-50">
          <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-primary"></div>
          <p class="mt-4 text-xs font-bold uppercase tracking-widest text-theme-muted">Fetching transactions...</p>
        </div>

        <div v-else-if="transactions.length === 0" 
             class="flex-1 flex flex-col items-center justify-center py-20 bg-surface-muted rounded-2xl border-2 border-dashed border-border m-2">
          <div class="w-16 h-16 rounded-full bg-surface-raised flex items-center justify-center mb-4 text-theme-muted opacity-20">
            <i class="bi bi-inbox text-3xl"></i>
          </div>
          <p class="text-theme font-bold text-lg">No transactions found</p>
          <p class="text-theme-muted text-sm mt-1">There are no records for this COA in the selected period.</p>
        </div>

        <div v-else class="flex-1 overflow-auto rounded-xl border border-border bg-surface-muted/10">
          <table class="w-full border-collapse table-compact">
            <thead class="bg-surface-muted sticky top-0 z-20 shadow-sm text-left">
              <tr>
                <th @click="sortBy('txn_date')" class="px-4 py-3 text-[10px] font-black text-theme-muted uppercase tracking-widest cursor-pointer hover:bg-surface-raised transition-colors">
                  Date
                  <i v-if="sortConfig.key === 'txn_date'" :class="sortConfig.direction === 'asc' ? 'bi-caret-up-fill' : 'bi-caret-down-fill'" class="bi ms-1"></i>
                </th>
                <th @click="sortBy('description')" class="px-4 py-3 text-[10px] font-black text-theme-muted uppercase tracking-widest cursor-pointer hover:bg-surface-raised transition-colors">
                  Description
                  <i v-if="sortConfig.key === 'description'" :class="sortConfig.direction === 'asc' ? 'bi-caret-up-fill' : 'bi-caret-down-fill'" class="bi ms-1"></i>
                </th>
                <th @click="sortBy('mark_name')" class="px-4 py-3 text-[10px] font-black text-theme-muted uppercase tracking-widest cursor-pointer hover:bg-surface-raised transition-colors">
                  Marking
                  <i v-if="sortConfig.key === 'mark_name'" :class="sortConfig.direction === 'asc' ? 'bi-caret-up-fill' : 'bi-caret-down-fill'" class="bi ms-1"></i>
                </th>
                <th class="px-4 py-3 text-center text-[10px] font-black text-theme-muted uppercase tracking-widest">Type</th>
                <th @click="sortBy('effective_amount')" class="px-4 py-3 text-right text-[10px] font-black text-theme-muted uppercase tracking-widest cursor-pointer hover:bg-surface-raised transition-colors">
                  Amount
                  <i v-if="sortConfig.key === 'effective_amount'" :class="sortConfig.direction === 'asc' ? 'bi-caret-up-fill' : 'bi-caret-down-fill'" class="bi ms-1"></i>
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-border bg-surface">
              <tr v-for="(txn, index) in filteredTransactions" :key="txn.id + '-' + index" class="hover:bg-primary/5 transition-colors group">
                <td class="px-4 py-3 text-xs whitespace-nowrap text-theme-muted font-bold font-mono">
                  {{ formatDate(txn.txn_date) }}
                </td>
                <td class="px-4 py-3 text-sm text-theme font-bold max-w-[400px]">
                  {{ txn.description }}
                </td>
                <td class="px-4 py-3 text-sm">
                  <span v-if="txn.mark_name" class="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-black uppercase tracking-widest bg-surface-raised text-theme-muted border border-border">
                    {{ txn.mark_name }}
                  </span>
                  <span v-else class="text-theme-muted/40 italic text-[10px] font-bold uppercase tracking-widest">Unmarked</span>
                </td>
                <td class="px-4 py-3 text-center">
                  <div class="inline-flex items-center justify-center px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-tighter shadow-sm"
                    :class="txn.db_cr === 'CR' ? 'bg-success/10 text-success border border-success/20' : 'bg-danger/10 text-danger border border-danger/20'">
                    {{ txn.db_cr }}
                  </div>
                </td>
                <td class="px-4 py-3 text-sm text-right font-mono font-black"
                  :class="txn.effective_amount >= 0 ? 'text-success' : 'text-danger'">
                  {{ (txn.effective_amount >= 0 ? '' : '-') + formatAmount(Math.abs(txn.effective_amount)) }}
                </td>
              </tr>
            </tbody>
          </table>
          
          <div v-if="filteredTransactions.length === 0" class="p-20 text-center">
            <p class="text-theme-muted italic text-sm">No transactions match your search filters.</p>
            <Button variant="ghost" size="sm" @click="clearFilters" class="mt-2 text-primary font-bold">Clear all filters</Button>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="flex-1 flex items-center gap-2">
        <i class="bi bi-info-circle text-primary opacity-50"></i>
        <span class="text-[10px] font-bold uppercase tracking-widest text-theme-muted">
          Showing {{ filteredTransactions.length }} Entries
        </span>
      </div>
      <Button variant="secondary" @click="$emit('close')" class="gap-2">
        <i class="bi bi-arrow-left"></i>
        Back to Reports
      </Button>
    </template>
  </BaseModal>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import BaseModal from '../ui/BaseModal.vue';
import SectionCard from '../ui/SectionCard.vue';
import FormField from '../ui/FormField.vue';
import SelectInput from '../ui/SelectInput.vue';
import StatCard from '../ui/StatCard.vue';
import Button from '../ui/Button.vue';
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
      params.as_of_date = props.filters.asOfDate;
    } else {
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

    const res = await reportsApi.getCoaDetail(params);
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
