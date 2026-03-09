<template>
  <div v-if="isOpen" class="fixed inset-0 z-[100] flex items-center justify-center overflow-y-auto overflow-x-hidden bg-black/50 backdrop-blur-sm p-4">
    <div class="hpp-batch-modal relative flex max-h-[94vh] w-full max-w-[1480px] flex-col overflow-hidden">
      
      <!-- Header -->
      <div class="hpp-batch-modal__header shrink-0">
        <div>
          <h3 class="text-xl font-bold text-theme">{{ batchId ? 'Edit COGS Batch' : 'Create COGS Batch' }}</h3>
          <p class="mt-0.5 text-xs text-muted">Bangun relasi transaksi pembelian ke item monitoring dan turunkan harga pokok per unit.</p>
        </div>
        <button @click="$emit('close')" class="hpp-batch-modal__close">
          <i class="bi bi-x-lg text-lg"></i>
        </button>
      </div>

      <!-- Scrollable Content -->
      <div class="p-8 overflow-y-auto flex-1 space-y-8">
        <!-- Error Alert -->
        <div v-if="error" class="hpp-batch-alert hpp-batch-alert--danger">
            <i class="bi bi-exclamation-triangle-fill mt-0.5"></i>
            <div>
                <h4 class="font-bold text-sm">{{ batchId ? 'Error loading/saving batch' : 'Error creating batch' }}</h4>
                <p class="text-xs">{{ error }}</p>
            </div>
        </div>

        <!-- No Company Warning -->
        <div v-if="!companyId" class="hpp-batch-alert hpp-batch-alert--warning">
            <i class="bi bi-exclamation-circle mt-0.5"></i>
            <div>
                <h4 class="font-bold text-sm">No Company Selected</h4>
                <p class="text-xs">Please select a company from the filter above first.</p>
            </div>
        </div>

        <!-- 1. General Info -->
        <div>
          <label class="label-base">Batch Memo / Description</label>
          <input 
            v-model="form.memo" 
            type="text" 
            class="input-base min-h-[42px]"
            placeholder="e.g. Import Shipment INV-001, China"
          />
          <!-- Batch Date Display (read-only, auto-calculated) -->
          <div v-if="form.transactions.length > 0" class="mt-2 flex items-center gap-2 text-xs">
            <span class="stat-pill !px-2.5 !py-1">
              <i class="bi bi-calendar-event"></i> Batch Date: {{ getBatchDateDisplay() }}
            </span>
            <span class="text-muted">(from earliest transaction)</span>
          </div>
        </div>

        <div class="grid grid-cols-1 gap-8 xl:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
          
          <!-- 2. Transaction Selection -->
          <div class="space-y-4">
            <div class="hpp-batch-panel hpp-batch-panel--teal">
              <h4 class="flex items-center gap-2 font-bold text-theme">
                <i class="bi bi-pass hpp-batch-panel__icon"></i>
                1. Select Transactions
              </h4>
              <div class="text-right">
                <span class="block text-[10px] font-bold uppercase tracking-wider text-muted">IDR Total</span>
                <span class="font-bold text-theme mono">Rp {{ formatNumber(totalTxnAmount) }}</span>
              </div>
            </div>

            <!-- Transaction Linker with Search -->
            <div class="hpp-batch-shell">
              <div class="hpp-batch-toolbar">
                <input type="month" v-model="filterMonth" class="input-base min-h-[34px] flex-1 !px-2 !py-1 text-xs" />
                <select v-model="searchMark" class="input-base min-h-[34px] max-w-[150px] flex-1 !px-2 !py-1 text-xs">
                  <option value="">All Marks</option>
                  <option v-for="m in uniqueMarks" :key="m" :value="m">{{ m }}</option>
                </select>
                <input 
                  v-model="searchQuery" 
                  type="text" 
                  placeholder="Search transactions..." 
                  class="input-base min-h-[34px] flex-[2] !px-2 !py-1 text-xs"
                />
                <button @click="loadTransactions" class="btn-secondary !min-h-[34px] !px-3 !py-1 text-xs" title="Reload transactions from server (clears selections)">
                  <i class="bi bi-arrow-clockwise"></i>
                </button>
              </div>
              <div class="hpp-batch-inline-alert" v-if="filterMonth && !/^\d{4}-\d{2}$/.test(filterMonth)">
                ⚠️ Invalid month format: {{ filterMonth }} - Please select a valid month
              </div>
              
              <div class="max-h-64 overflow-y-auto relative">
                <div v-if="isLoadingTxns" class="absolute inset-0 flex items-center justify-center bg-black/10 backdrop-blur-[1px]">
                  <div class="hpp-batches__spinner !h-6 !w-6 !border-2"></div>
                </div>
                
                <div v-else-if="!filterMonth" class="absolute inset-0 flex items-center justify-center p-8">
                  <div class="text-center text-muted">
                    <i class="bi bi-calendar-event text-4xl mb-2 block"></i>
                    <p class="text-sm font-medium text-theme">Select a month to load transactions</p>
                    <p class="text-xs mt-1">Or use the search box to find transactions by description</p>
                  </div>
                </div>
                
                <table class="table-compact w-full text-xs" v-else>
                  <thead class="sticky top-0 shadow-sm">
                    <tr>
                      <th class="cursor-pointer select-none transition-colors hover:bg-white/5" @click="toggleSort('date')">
                        Date <i class="bi ml-1" :class="sortBy === 'date' ? (sortDesc ? 'bi-sort-down text-[color:var(--color-primary)]' : 'bi-sort-up text-[color:var(--color-primary)]') : 'bi-arrow-down-up opacity-50'"></i>
                      </th>
                      <th class="cursor-pointer select-none transition-colors hover:bg-white/5" @click="toggleSort('mark')">
                        Mark / Desc <i class="bi ml-1" :class="sortBy === 'mark' ? (sortDesc ? 'bi-sort-down text-[color:var(--color-primary)]' : 'bi-sort-up text-[color:var(--color-primary)]') : 'bi-arrow-down-up opacity-50'"></i>
                      </th>
                      <th class="cursor-pointer select-none text-right transition-colors hover:bg-white/5" @click="toggleSort('amount')">
                        Amount <i class="bi ml-1" :class="sortBy === 'amount' ? (sortDesc ? 'bi-sort-down text-[color:var(--color-primary)]' : 'bi-sort-up text-[color:var(--color-primary)]') : 'bi-arrow-down-up opacity-50'"></i>
                      </th>
                      <th class="text-center w-12">Add</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-if="filteredTransactions.length === 0">
                      <td colspan="4" class="py-5 text-center text-muted">
                        <span v-if="searchQuery">No transactions match your search.</span>
                        <span v-else>No unlinked transactions found for this month.</span>
                      </td>
                    </tr>
                    <tr 
                      v-for="txn in filteredTransactions" 
                      :key="txn.id"
                      class="transition-colors hover:bg-white/5"
                      :class="{'!bg-[rgba(15,118,110,0.08)]': isTransactionSelected(txn.id)}"
                    >
                      <td class="whitespace-nowrap">{{ txn.txn_date }}</td>
                      <td class="max-w-[200px] truncate" :title="txn.description">
                        <span v-if="txn.mark" class="stat-pill !mr-1 !rounded-lg !px-2 !py-0.5 !text-[10px]">{{ txn.mark }}</span>
                        <span :class="txn.mark ? 'text-muted' : 'text-theme'">{{ txn.description }}</span>
                      </td>
                      <td class="text-right font-medium" :class="txn.amount < 0 ? 'text-red-400' : 'text-emerald-400'">
                        {{ formatNumber(Math.abs(txn.amount)) }}
                      </td>
                      <td class="text-center">
                        <button 
                          v-if="!isTransactionSelected(txn.id)"
                          @click="addTransaction(txn)"
                          class="rounded p-1 text-[color:var(--color-primary)] hover:bg-[rgba(15,118,110,0.12)]"
                        >
                          <i class="bi bi-plus-circle-fill"></i>
                        </button>
                        <button 
                          v-else
                          @click="removeTransaction(txn.id)"
                          class="rounded p-1 text-red-400 hover:bg-red-500/10"
                        >
                          <i class="bi bi-x-circle-fill"></i>
                        </button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <!-- Selected Txns List -->
            <div v-if="form.transactions.length > 0" class="surface-card-muted rounded-xl p-3">
              <h5 class="mb-2 text-xs font-bold uppercase tracking-wide text-theme">Selected ({{ form.transactions.length }})</h5>
              <div class="space-y-1 mt-2">
                <div v-for="t in form.transactions" :key="t.id" class="hpp-batch-selected-row">
                  <div class="truncate min-w-0" :title="t.description">
                    <span class="whitespace-nowrap text-muted">{{ t.txn_date }}</span> <span class="text-muted/50">|</span> 
                    <span v-if="t.mark" class="stat-pill !mr-1 !rounded-lg !px-2 !py-0.5 !text-[10px]">{{ t.mark }}</span>
                    <span :class="t.mark ? 'text-muted' : 'text-theme'">{{ t.description }}</span>
                  </div>
                  <div class="flex items-center gap-3">
                    <span class="font-medium text-theme mono">{{ formatNumber(Math.abs(t.amount)) }}</span>
                    <button @click="removeTransaction(t.id)" class="btn-ghost rounded-lg p-1 hover:!text-red-400"><i class="bi bi-x"></i></button>
                  </div>
                </div>
              </div>
            </div>

          </div>

          <!-- 3. Monitoring Mapping -->
          <div class="space-y-4">
            <div class="hpp-batch-panel hpp-batch-panel--amber">
              <h4 class="flex items-center gap-2 font-bold text-theme">
                <i class="bi bi-box-seam hpp-batch-panel__icon"></i>
                2. Map Monitoring Items
              </h4>
              <div class="text-right">
                <span class="block text-[10px] font-bold uppercase tracking-wider text-muted">Foreign Total</span>
                <span class="font-bold text-theme mono">{{ formatNumber(totalForeignValue) }}</span>
              </div>
            </div>

            <div class="hpp-batch-shell">
              <div class="overflow-x-auto">
                <table class="table-compact w-full text-xs">
                  <thead>
                    <tr>
                      <th class="w-[35%] min-w-[280px]">Monitoring Item</th>
                      <th class="w-[14%] min-w-[72px] text-center">Cur</th>
                      <th class="w-[14%] min-w-[100px] text-right">Qty</th>
                      <th class="w-[14%] min-w-[100px] text-right">Price / Unit</th>
                      <th class="w-[16%] min-w-[100px] text-right">Total</th>
                      <th class="w-[2%] min-w-[44px] text-center"></th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(item, index) in form.items" :key="index" class="group align-top transition-colors hover:bg-white/5">
                      <td class="p-2">
                        <select v-model="item.stock_monitoring_id" @change="onProductSelect(item)" class="input-base min-h-[36px] !px-2 !py-1.5 text-xs">
                          <option value="">-- Select Monitoring --</option>
                          <option v-for="p in availableItems" :key="p.id" :value="p.id">
                            {{ p.name }}{{ p.unit_name ? ` (${p.unit_name})` : '' }}
                          </option>
                        </select>
                      </td>
                      <td class="p-2">
                        <input
                          v-model="item.foreign_currency"
                          type="text"
                          class="input-base min-h-[36px] !px-2 !py-1.5 text-center text-xs mono"
                          placeholder="USD"
                        >
                      </td>
                      <td class="p-2">
                        <input
                          v-model.number="item.quantity"
                          type="number"
                          step="1"
                          class="input-base min-h-[36px] !px-2 !py-1.5 text-right text-xs mono"
                        >
                      </td>
                      <td class="p-2">
                        <input
                          v-model.number="item.foreign_price"
                          type="number"
                          step="0.01"
                          class="input-base min-h-[36px] !px-2 !py-1.5 text-right text-xs mono"
                        >
                      </td>
                      <td class="p-2">
                        <div class="input-base flex min-h-[36px] items-center justify-end !px-2 text-xs mono text-theme">
                          {{ formatNumber((item.quantity || 0) * (item.foreign_price || 0)) }}
                        </div>
                      </td>
                      <td class="p-2 text-center">
                        <button @click="removeItemRow(index)" class="btn-ghost rounded-lg p-2 opacity-0 transition-opacity group-hover:opacity-100 hover:!text-red-400">
                          <i class="bi bi-trash"></i>
                        </button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div class="hpp-batch-toolbar border-t">
                <button @click="addItemRow" class="btn-ghost flex items-center gap-1 text-xs font-semibold text-[color:var(--color-primary)] hover:!text-[color:var(--color-primary-strong)]">
                  <i class="bi bi-plus-circle"></i> Add Monitoring Row
                </button>
              </div>
            </div>

            <!-- Proportional Preview -->
            <div v-if="form.items.length > 0 && totalTxnAmount > 0" class="surface-card-muted rounded-xl p-4">
                <h5 class="mb-3 flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-theme">
                    <i class="bi bi-calculator"></i> COGS Unit Price Preview (IDR)
                </h5>
                <div class="space-y-2">
                    <div v-for="(item, index) in form.items" :key="index" class="flex items-center justify-between border-b border-[color:var(--color-border)] pb-2 text-xs last:border-0 last:pb-0">
                        <div class="flex flex-col">
                            <span class="font-medium text-theme">{{ getItemName(item.stock_monitoring_id, item.item_name) }}</span>
                            <span class="text-[10px] text-muted">
                              {{ item.quantity || 0 }} units • {{ ((calculateRowIdr(item) / totalTxnAmount) * 100 || 0).toFixed(1) }}% of total
                            </span>
                        </div>
                        <div class="text-right">
                            <div class="font-bold text-theme mono">Unit Cost: Rp {{ formatNumber(calculateUnitIdr(item)) }}</div>
                            <div class="text-[10px] text-muted">Total: Rp {{ formatNumber(calculateRowIdr(item)) }}</div>
                        </div>
                    </div>
                </div>
            </div>

          </div>
        </div>

      </div>

      <!-- Footer CTA -->
      <div class="hpp-batch-modal__footer shrink-0">
        <div class="flex items-center gap-2 text-xs">
           <span v-if="syncStatus === 'synced'" class="flex items-center gap-1 font-medium text-emerald-400"><i class="bi bi-check-circle-fill"></i> Balanced (100%)</span>
           <span v-else-if="syncStatus === 'empty'" class="flex items-center gap-1 text-muted"><i class="bi bi-dash-circle"></i> Incomplete Mapping</span>
           <span v-else class="flex items-center gap-1 text-amber-400"><i class="bi bi-exclamation-triangle-fill"></i> Need Txn & Products</span>
        </div>
        <div class="flex gap-3">
          <button @click="$emit('close')" class="btn-secondary !px-5 !py-2.5 text-sm">
            Cancel
          </button>
          <button @click="saveBatch" :disabled="isSaving || syncStatus === 'empty'" class="btn-primary !px-6 !py-2.5 gap-2 text-sm">
            <span v-if="isSaving" class="hpp-batches__spinner !h-4 !w-4 !border-2 !border-white/25 !border-t-white"></span>
            <i v-else class="bi bi-check2-circle"></i>
            {{ isSaving ? 'Saving...' : 'Save COGS Batch' }}
          </button>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { useHppBatchStore } from '../../stores/hppBatch';
import { hppApi } from '../../api';

const props = defineProps({
  isOpen: Boolean,
  batchId: String,
  companyId: String
});

const emit = defineEmits(['close', 'saved']);

const batchStore = useHppBatchStore();

const form = ref({
    memo: '',
    transactions: [],
    items: []
});

const availableItems = ref([]);

// Transaction UI State
const filterMonth = ref(''); // Empty by default - only load when user selects month or searches
const searchQuery = ref('');
const linkableTransactions = ref([]);
const isLoadingTxns = ref(false);

const isSaving = ref(false);
const error = ref('');

// Sorting and Filtering State
const searchMark = ref('');
const sortBy = ref('date');
const sortDesc = ref(true);

const toggleSort = (field) => {
    if (sortBy.value === field) {
        sortDesc.value = !sortDesc.value;
    } else {
        sortBy.value = field;
        sortDesc.value = field === 'date'; // Default date descending, others ascending
    }
};

const uniqueMarks = computed(() => {
    const marks = new Set();
    linkableTransactions.value.forEach(txn => {
        if (txn.mark) marks.add(txn.mark);
    });
    return Array.from(marks).sort();
});

// Filtered and sorted transactions
const filteredTransactions = computed(() => {
    let result = linkableTransactions.value;
    
    // 1. Filter by specific mark dropdown
    if (searchMark.value) {
        result = result.filter(txn => txn.mark === searchMark.value);
    }
    
    // 2. Filter by text query
    if (searchQuery.value) {
        const query = searchQuery.value.toLowerCase();
        result = result.filter(txn => 
            (txn.description || '').toLowerCase().includes(query) ||
            (txn.mark || '').toLowerCase().includes(query) ||
            (txn.txn_date || '').includes(query) ||
            String(Math.abs(txn.amount || 0)).includes(query)
        );
    }
    
    // 3. Sort
    result = [...result].sort((a, b) => {
        let modifier = sortDesc.value ? -1 : 1;
        if (sortBy.value === 'date') {
            return a.txn_date < b.txn_date ? -1 * modifier : (a.txn_date > b.txn_date ? 1 * modifier : 0);
        } else if (sortBy.value === 'mark') {
            const markA = (a.mark || '').toLowerCase();
            const markB = (b.mark || '').toLowerCase();
            return markA < markB ? -1 * modifier : (markA > markB ? 1 * modifier : 0);
        } else if (sortBy.value === 'amount') {
            const amtA = Math.abs(a.amount || 0);
            const amtB = Math.abs(b.amount || 0);
            return amtA < amtB ? -1 * modifier : (amtA > amtB ? 1 * modifier : 0);
        }
        return 0;
    });
    
    return result;
});

// Watch filterMonth to reload transactions
watch(filterMonth, () => {
    searchQuery.value = ''; // Reset search when month changes
    loadTransactions();
});

// Computed Math
const totalTxnAmount = computed(() => {
    return form.value.transactions.reduce((sum, t) => sum + Math.abs(t.amount), 0);
});

const totalForeignValue = computed(() => {
    return form.value.items.reduce((sum, p) => sum + ((p.quantity || 0) * (p.foreign_price || 0)), 0);
});

const calculateRowIdr = (item) => {
    if (totalForeignValue.value <= 0) return 0;
    const itemValue = (item.quantity || 0) * (item.foreign_price || 0);
    return totalTxnAmount.value * (itemValue / totalForeignValue.value);
};

const calculateUnitIdr = (item) => {
    const qty = item.quantity || 0;
    if (qty <= 0) return 0;
    return calculateRowIdr(item) / qty;
};

const syncStatus = computed(() => {
    if (form.value.transactions.length > 0 && form.value.items.length > 0 && totalForeignValue.value > 0) return 'synced';
    return 'empty';
});

// Initialization
const init = async () => {
    error.value = '';
    form.value = { memo: '', transactions: [], items: [] };

    if (!props.companyId) {
        error.value = 'Company ID is required. Please select a company first.';
        return;
    }
    
    // Load monitoring items list if empty
    if (availableItems.value.length === 0) {
        const response = await hppApi.getItems('storage');
        availableItems.value = response.data.items || [];
    }
    
    if (props.batchId) {
        // Load existing batch
        try {
            const data = await batchStore.fetchBatchDetails(props.batchId);
            
            form.value.memo = data.batch.memo;
            form.value.transactions = data.transactions;
            const batchItems = data.items || data.products || [];
            form.value.items = batchItems.map(p => ({
                stock_monitoring_id: p.stock_monitoring_id || p.product_id,
                item_name: p.item_name || p.product_name,
                details_summary: p.details_summary || '',
                foreign_currency: p.foreign_currency,
                quantity: p.quantity,
                foreign_price: p.foreign_price
            }));
            
            // Set filter month to the batch date for editing (ensure YYYY-MM format)
            if (data.batch.batch_date) {
                const batchDateStr = String(data.batch.batch_date);
                // Extract YYYY-MM from date string (could be YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
                filterMonth.value = batchDateStr.slice(0, 7);
            }
        } catch (e) {
            error.value = "Failed to load batch details: " + (e.response?.data?.error || e.message || 'Unknown error');
        }
    } else {
        // Init with 1 empty row for new batch
        addItemRow();
    }
};

onMounted(() => {
    if (props.isOpen) init();
});

watch(() => props.isOpen, (newVal) => {
    if (newVal) init();
});

// Transaction Logic
const loadTransactions = async () => {
    if (!props.companyId) {
        linkableTransactions.value = [];
        return;
    }
    
    // Only load if month is selected and in valid format (YYYY-MM)
    if (!filterMonth.value || !/^\d{4}-\d{2}$/.test(filterMonth.value)) {
        linkableTransactions.value = [];
        return;
    }
    
    isLoadingTxns.value = true;
    error.value = '';
    try {
        const [year, month] = filterMonth.value.split('-');
        const yearNum = parseInt(year);
        const monthNum = parseInt(month);
        
        // Validate year and month
        if (isNaN(yearNum) || isNaN(monthNum) || yearNum < 2000 || monthNum < 1 || monthNum > 12) {
            error.value = 'Invalid month selected';
            linkableTransactions.value = [];
            return;
        }
        
        const lastDay = new Date(yearNum, monthNum, 0).getDate();
        const start = `${yearNum}-${String(monthNum).padStart(2, '0')}-01`;
        const end = `${yearNum}-${String(monthNum).padStart(2, '0')}-${lastDay}`;

        const res = await hppApi.getLinkableTransactions(props.companyId, start, end);

        // Exclude ones that are already linked to *other* batches
        linkableTransactions.value = res.data.transactions.filter(t => {
            return !t.is_linked || form.value.transactions.some(ft => ft.id === t.id);
        });
    } catch (e) {
        error.value = "Failed to load transactions: " + (e.response?.data?.error || e.message || 'Unknown error');
        linkableTransactions.value = [];
    } finally {
        isLoadingTxns.value = false;
    }
};

const isTransactionSelected = (id) => {
    return form.value.transactions.some(t => t.id === id);
};

const addTransaction = (txn) => {
    if (!isTransactionSelected(txn.id)) {
        form.value.transactions.push(txn);
    }
};

const removeTransaction = (id) => {
    form.value.transactions = form.value.transactions.filter(t => t.id !== id);
};

// Product Row Logic
const addItemRow = () => {
    form.value.items.push({
        stock_monitoring_id: '',
        details_summary: '',
        foreign_currency: 'USD',
        quantity: 1,
        foreign_price: 0
    });
};

const removeItemRow = (index) => {
    form.value.items.splice(index, 1);
};

const onProductSelect = (item) => {
    const product = availableItems.value.find(p => p.id === item.stock_monitoring_id);
    if (product) {
        item.item_name = product.name;
        item.details_summary = product.details_summary || '';
        item.foreign_currency = product.default_currency || 'USD';
        item.foreign_price = product.default_price || 0;
    }
};

const getItemName = (id, fallbackName = '') => {
    const p = availableItems.value.find(x => x.id === id);
    return p ? p.name : (fallbackName || 'Unknown Item');
};

const getItemDetailsSummary = (id, fallbackSummary = '') => {
    const item = availableItems.value.find(x => x.id === id);
    return item?.details_summary || fallbackSummary || '';
};

const getBatchDateDisplay = () => {
    if (form.value.transactions.length === 0) return '-';
    // Get earliest date from selected transactions
    const earliest = form.value.transactions.reduce((min, txn) => {
        const txnDate = String(txn.txn_date).slice(0, 10);
        return txnDate < min ? txnDate : min;
    }, String(form.value.transactions[0].txn_date).slice(0, 10));
    return earliest;
};

// Save Logic
const saveBatch = async () => {
    isSaving.value = true;
    error.value = '';
    
    // Validate before save
    if (!form.value.memo) {
        error.value = 'Batch memo/description is required';
        isSaving.value = false;
        return;
    }
    
    if (form.value.transactions.length === 0) {
        error.value = 'At least one transaction must be selected';
        isSaving.value = false;
        return;
    }
    
    const validItems = form.value.items.filter((p) => p.stock_monitoring_id && p.quantity > 0);
    if (validItems.length === 0) {
        error.value = 'At least one monitoring item with quantity > 0 must be added';
        isSaving.value = false;
        return;
    }
    
    // Calculate batch_date from earliest transaction
    const earliestDate = form.value.transactions.reduce((earliest, txn) => {
        // Ensure we're comparing date strings in YYYY-MM-DD format
        const txnDate = String(txn.txn_date).slice(0, 10);
        const earliestDateStr = String(earliest).slice(0, 10);
        return txnDate < earliestDateStr ? txnDate : earliestDateStr;
    }, String(form.value.transactions[0].txn_date).slice(0, 10));
    
    const payload = {
        id: props.batchId, // Will be null for new
        company_id: props.companyId,
        memo: form.value.memo,
        batch_date: earliestDate,
        transaction_ids: form.value.transactions.map(t => t.id),
        items: validItems.map((item) => ({
            stock_monitoring_id: item.stock_monitoring_id,
            quantity: item.quantity,
            foreign_currency: item.foreign_currency,
            foreign_price: item.foreign_price,
        }))
    };
    try {
        await batchStore.saveBatch(payload);
        emit('saved');
    } catch (e) {
        error.value = e.response?.data?.error || e.message || 'Unknown error occurred while saving';
    } finally {
        isSaving.value = false;
    }
};

// Utils
const formatNumber = (val) => {
    return Number(val || 0).toLocaleString('id-ID', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
};
</script>

<style scoped>
.hpp-batch-modal {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card-hover);
  color: var(--color-text);
}

.hpp-batch-modal__header,
.hpp-batch-modal__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1.5rem;
  background: var(--color-surface-muted);
  border-bottom: 1px solid var(--color-border);
}

.hpp-batch-modal__footer {
  border-bottom: 0;
  border-top: 1px solid var(--color-border);
}

.hpp-batch-modal__close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.55rem;
  border-radius: 9999px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  color: var(--color-text-muted);
  transition: color 180ms ease, border-color 180ms ease, background 180ms ease;
}

.hpp-batch-modal__close:hover {
  color: var(--color-text);
  border-color: var(--color-border-strong);
  background: var(--color-surface-raised);
}

.hpp-batch-alert {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 1rem;
  border-radius: 1rem;
  border: 1px solid transparent;
}

.hpp-batch-alert--danger {
  background: rgba(185, 28, 28, 0.1);
  border-color: rgba(185, 28, 28, 0.18);
  color: #fca5a5;
}

.hpp-batch-alert--warning,
.hpp-batch-inline-alert {
  background: rgba(180, 83, 9, 0.12);
  border-color: rgba(180, 83, 9, 0.2);
  color: #fbbf24;
}

.hpp-batch-inline-alert {
  padding: 0.7rem 0.85rem;
  border-top: 1px solid rgba(180, 83, 9, 0.2);
  font-size: 10px;
}

.hpp-batch-panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.85rem 1rem;
  border-radius: 1rem;
  border: 1px solid var(--color-border);
}

.hpp-batch-panel--teal {
  background: linear-gradient(135deg, rgba(15, 118, 110, 0.12), rgba(15, 118, 110, 0.04));
}

.hpp-batch-panel--amber {
  background: linear-gradient(135deg, rgba(180, 83, 9, 0.12), rgba(180, 83, 9, 0.04));
}

.hpp-batch-panel__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border-radius: 0.75rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  color: var(--color-primary);
}

.hpp-batch-shell {
  overflow: hidden;
  border-radius: 1rem;
  border: 1px solid var(--color-border);
  background: var(--color-surface);
}

.hpp-batch-toolbar {
  display: flex;
  gap: 0.5rem;
  padding: 0.75rem;
  background: var(--color-surface-muted);
  border-bottom: 1px solid var(--color-border);
}

.hpp-batch-selected-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.55rem 0.7rem;
  font-size: 12px;
  border-radius: 0.85rem;
  border: 1px solid var(--color-border);
  background: var(--color-surface);
}

@media (max-width: 960px) {
  .hpp-batch-modal__header,
  .hpp-batch-modal__footer,
  .hpp-batch-panel,
  .hpp-batch-toolbar,
  .hpp-batch-selected-row {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
