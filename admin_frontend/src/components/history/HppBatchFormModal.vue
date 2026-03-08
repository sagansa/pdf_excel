<template>
  <div v-if="isOpen" class="fixed inset-0 z-[100] flex items-center justify-center overflow-y-auto overflow-x-hidden bg-black/50 backdrop-blur-sm p-4">
    <div class="relative w-full max-w-5xl bg-white rounded-2xl shadow-2xl flex flex-col max-h-[90vh]">
      
      <!-- Header -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100 bg-gray-50/80 rounded-t-2xl shrink-0">
        <div>
          <h3 class="text-xl font-bold text-gray-900">{{ batchId ? 'Edit COGS Batch' : 'Create COGS Batch' }}</h3>
          <p class="text-xs text-gray-500 mt-0.5">Define transactions and assign product costs</p>
        </div>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 bg-white hover:bg-gray-100 rounded-full p-2 transition-colors shadow-sm border border-gray-200">
          <i class="bi bi-x-lg text-lg"></i>
        </button>
      </div>

      <!-- Scrollable Content -->
      <div class="p-6 overflow-y-auto flex-1 space-y-8">
        <!-- Error Alert -->
        <div v-if="error" class="bg-red-50 text-red-700 p-4 rounded-xl border border-red-100 flex items-start gap-3">
            <i class="bi bi-exclamation-triangle-fill mt-0.5"></i>
            <div>
                <h4 class="font-bold text-sm">{{ batchId ? 'Error loading/saving batch' : 'Error creating batch' }}</h4>
                <p class="text-xs">{{ error }}</p>
            </div>
        </div>

        <!-- No Company Warning -->
        <div v-if="!companyId" class="bg-yellow-50 text-yellow-800 p-4 rounded-xl border border-yellow-100 flex items-start gap-3">
            <i class="bi bi-exclamation-circle mt-0.5"></i>
            <div>
                <h4 class="font-bold text-sm">No Company Selected</h4>
                <p class="text-xs">Please select a company from the filter above first.</p>
            </div>
        </div>

        <!-- 1. General Info -->
        <div>
          <label class="block text-sm font-bold text-gray-700 mb-2">Batch Memo / Description</label>
          <input 
            v-model="form.memo" 
            type="text" 
            class="w-full px-4 py-2 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
            placeholder="e.g. Import Shipment INV-001, China"
          />
          <!-- Batch Date Display (read-only, auto-calculated) -->
          <div v-if="form.transactions.length > 0" class="mt-2 flex items-center gap-2 text-xs">
            <span class="bg-indigo-50 text-indigo-700 px-2 py-1 rounded font-semibold">
              <i class="bi bi-calendar-event"></i> Batch Date: {{ getBatchDateDisplay() }}
            </span>
            <span class="text-gray-400">(from earliest transaction)</span>
          </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
          
          <!-- 2. Transaction Selection -->
          <div class="space-y-4">
            <div class="flex justify-between items-center bg-indigo-50 px-4 py-2 rounded-lg border border-indigo-100">
              <h4 class="font-bold text-indigo-900 flex items-center gap-2">
                <i class="bi bi-pass bg-white text-indigo-600 p-1.5 rounded-md shadow-sm"></i>
                1. Select Transactions
              </h4>
              <div class="text-right">
                <span class="text-[10px] text-gray-500 font-bold uppercase tracking-wider block">IDR Total</span>
                <span class="font-bold text-indigo-700">Rp {{ formatNumber(totalTxnAmount) }}</span>
              </div>
            </div>

            <!-- Transaction Linker with Search -->
            <div class="border border-gray-200 rounded-xl overflow-hidden bg-white">
              <div class="bg-gray-50 px-3 py-2 border-b border-gray-200 flex gap-2">
                <input type="month" v-model="filterMonth" class="text-xs border-gray-200 rounded px-2 py-1 flex-1" />
                <select v-model="searchMark" class="text-xs border-gray-200 rounded px-2 py-1 flex-1 max-w-[150px]">
                  <option value="">All Marks</option>
                  <option v-for="m in uniqueMarks" :key="m" :value="m">{{ m }}</option>
                </select>
                <input 
                  v-model="searchQuery" 
                  type="text" 
                  placeholder="Search transactions..." 
                  class="text-xs border-gray-200 rounded px-2 py-1 flex-[2]"
                />
                <button @click="loadTransactions" class="bg-white border border-gray-200 rounded px-3 py-1 text-xs hover:bg-gray-50" title="Reload transactions from server (clears selections)">
                  <i class="bi bi-arrow-clockwise"></i>
                </button>
              </div>
              <div class="bg-yellow-50 px-3 py-2 text-[10px] text-yellow-800 border-b border-yellow-100" v-if="filterMonth && !/^\d{4}-\d{2}$/.test(filterMonth)">
                ⚠️ Invalid month format: {{ filterMonth }} - Please select a valid month
              </div>
              
              <div class="max-h-64 overflow-y-auto relative">
                <div v-if="isLoadingTxns" class="absolute inset-0 bg-white/50 flex items-center justify-center">
                  <div class="spinner-border w-6 h-6 text-indigo-600 border-2"></div>
                </div>
                
                <div v-else-if="!filterMonth" class="absolute inset-0 bg-white/90 flex items-center justify-center p-8">
                  <div class="text-center text-gray-400">
                    <i class="bi bi-calendar-event text-4xl mb-2 block"></i>
                    <p class="text-sm font-medium">Select a month to load transactions</p>
                    <p class="text-xs mt-1">Or use the search box to find transactions by description</p>
                  </div>
                </div>
                
                <table class="w-full text-xs" v-else>
                  <thead class="bg-white sticky top-0 shadow-sm">
                    <tr>
                      <th class="px-3 py-2 text-left cursor-pointer hover:bg-gray-100 select-none group transition-colors" @click="toggleSort('date')">
                        Date <i class="bi ml-1 group-hover:text-indigo-400" :class="sortBy === 'date' ? (sortDesc ? 'bi-sort-down text-indigo-600' : 'bi-sort-up text-indigo-600') : 'bi-arrow-down-up text-gray-300'"></i>
                      </th>
                      <th class="px-3 py-2 text-left cursor-pointer hover:bg-gray-100 select-none group transition-colors" @click="toggleSort('mark')">
                        Mark / Desc <i class="bi ml-1 group-hover:text-indigo-400" :class="sortBy === 'mark' ? (sortDesc ? 'bi-sort-down text-indigo-600' : 'bi-sort-up text-indigo-600') : 'bi-arrow-down-up text-gray-300'"></i>
                      </th>
                      <th class="px-3 py-2 text-right cursor-pointer hover:bg-gray-100 select-none group transition-colors" @click="toggleSort('amount')">
                        Amount <i class="bi ml-1 group-hover:text-indigo-400" :class="sortBy === 'amount' ? (sortDesc ? 'bi-sort-down text-indigo-600' : 'bi-sort-up text-indigo-600') : 'bi-arrow-down-up text-gray-300'"></i>
                      </th>
                      <th class="px-3 py-2 text-center w-12">Add</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-gray-100">
                    <tr v-if="filteredTransactions.length === 0">
                      <td colspan="4" class="text-center py-4 text-gray-500">
                        <span v-if="searchQuery">No transactions match your search.</span>
                        <span v-else>No unlinked transactions found for this month.</span>
                      </td>
                    </tr>
                    <tr 
                      v-for="txn in filteredTransactions" 
                      :key="txn.id"
                      class="hover:bg-gray-50 transition-colors"
                      :class="{'bg-indigo-50/50': isTransactionSelected(txn.id)}"
                    >
                      <td class="px-3 py-2 whitespace-nowrap">{{ txn.txn_date }}</td>
                      <td class="px-3 py-2 max-w-[200px] truncate" :title="txn.description">
                        <span v-if="txn.mark" class="font-bold text-indigo-700 bg-indigo-50 px-1.5 py-0.5 rounded mr-1 text-[10px] border border-indigo-100">{{ txn.mark }}</span>
                        <span :class="txn.mark ? 'text-gray-500' : 'text-gray-900'">{{ txn.description }}</span>
                      </td>
                      <td class="px-3 py-2 text-right font-medium" :class="txn.amount < 0 ? 'text-red-600' : 'text-green-600'">
                        {{ formatNumber(Math.abs(txn.amount)) }}
                      </td>
                      <td class="px-3 py-2 text-center">
                        <button 
                          v-if="!isTransactionSelected(txn.id)"
                          @click="addTransaction(txn)"
                          class="p-1 text-indigo-600 hover:bg-indigo-100 rounded"
                        >
                          <i class="bi bi-plus-circle-fill"></i>
                        </button>
                        <button 
                          v-else
                          @click="removeTransaction(txn.id)"
                          class="p-1 text-red-500 hover:bg-red-50 rounded"
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
            <div v-if="form.transactions.length > 0" class="bg-gray-50 rounded-xl p-3 border border-gray-200">
              <h5 class="text-xs font-bold text-gray-700 mb-2 uppercase tracking-wide">Selected ({{ form.transactions.length }})</h5>
              <div class="space-y-1 mt-2">
                <div v-for="t in form.transactions" :key="t.id" class="flex justify-between items-center text-xs bg-white p-2 rounded border border-gray-100 shadow-sm gap-2">
                  <div class="truncate min-w-0" :title="t.description">
                    <span class="text-gray-500 whitespace-nowrap">{{ t.txn_date }}</span> <span class="text-gray-300">|</span> 
                    <span v-if="t.mark" class="font-bold text-indigo-700 text-[10px] bg-indigo-50 px-1 py-0.5 rounded mr-1 border border-indigo-100">{{ t.mark }}</span>
                    <span :class="t.mark ? 'text-gray-500' : 'text-gray-900'">{{ t.description }}</span>
                  </div>
                  <div class="flex items-center gap-3">
                    <span class="font-medium text-gray-900">{{ formatNumber(Math.abs(t.amount)) }}</span>
                    <button @click="removeTransaction(t.id)" class="text-gray-400 hover:text-red-500"><i class="bi bi-x"></i></button>
                  </div>
                </div>
              </div>
            </div>

          </div>

          <!-- 3. Product Mapping -->
          <div class="space-y-4">
            <div class="flex justify-between items-center bg-green-50 px-4 py-2 rounded-lg border border-green-100">
              <h4 class="font-bold text-green-900 flex items-center gap-2">
                <i class="bi bi-box-seam bg-white text-green-600 p-1.5 rounded-md shadow-sm"></i>
                2. Map Products
              </h4>
              <div class="text-right">
                <span class="text-[10px] text-gray-500 font-bold uppercase tracking-wider block">Foreign Total</span>
                <span class="font-bold text-green-700">{{ formatNumber(totalForeignValue) }}</span>
              </div>
            </div>

            <div class="border border-gray-200 rounded-xl overflow-hidden bg-white">
              <table class="w-full text-xs">
                <thead class="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th class="px-3 py-3 text-left font-semibold text-gray-600">Product</th>
                    <th class="px-3 py-3 text-center font-semibold text-gray-600 w-24">Cur</th>
                    <th class="px-3 py-3 text-right font-semibold text-gray-600 w-24">Qty</th>
                    <th class="px-3 py-3 text-right font-semibold text-gray-600 w-32">Price/u</th>
                    <th class="px-3 py-3 text-center w-12"></th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-100">
                  <tr v-for="(item, index) in form.products" :key="index" class="group hover:bg-gray-50/50 transition-colors">
                    <td class="p-2">
                      <select v-model="item.product_id" @change="onProductSelect(item)" class="w-full bg-white border border-gray-200 rounded px-2 py-1.5 text-xs focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500">
                        <option value="">-- Select Product --</option>
                        <option v-for="p in availableProducts" :key="p.id" :value="p.id">
                          {{ p.code }} - {{ p.name }}
                        </option>
                      </select>
                    </td>
                    <td class="p-2">
                      <input v-model="item.foreign_currency" type="text" class="w-full bg-white border border-gray-200 rounded px-2 py-1.5 text-xs text-center focus:ring-1 focus:ring-indigo-500" placeholder="USD">
                    </td>
                    <td class="p-2">
                      <input v-model.number="item.quantity" type="number" step="0.01" class="w-full bg-white border border-gray-200 rounded px-2 py-1.5 text-xs text-right focus:ring-1 focus:ring-indigo-500">
                    </td>
                    <td class="p-2">
                      <input v-model.number="item.foreign_price" type="number" step="0.01" class="w-full bg-white border border-gray-200 rounded px-2 py-1.5 text-xs text-right focus:ring-1 focus:ring-indigo-500">
                    </td>
                    <td class="p-2 text-center">
                      <button @click="removeProductRow(index)" class="text-gray-400 hover:text-red-500 p-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <i class="bi bi-trash"></i>
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
              <div class="px-3 py-2 bg-gray-50 border-t border-gray-200">
                <button @click="addProductRow" class="text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1">
                  <i class="bi bi-plus-circle"></i> Add Row
                </button>
              </div>
            </div>

            <!-- Proportional Preview -->
            <div v-if="form.products.length > 0 && totalTxnAmount > 0" class="bg-slate-50 rounded-xl p-4 border border-slate-200">
                <h5 class="text-xs font-bold text-slate-700 mb-3 uppercase tracking-wide flex items-center gap-2">
                    <i class="bi bi-calculator"></i> COGS Unit Price Preview (IDR)
                </h5>
                <div class="space-y-2">
                    <div v-for="(item, index) in form.products" :key="index" class="flex justify-between items-center text-xs pb-2 border-b border-slate-200/60 last:border-0 last:pb-0">
                        <div class="flex flex-col">
                            <span class="font-medium text-slate-900">{{ getProductName(item.product_id) }}</span>
                            <span class="text-[10px] text-slate-500">{{ item.quantity || 0 }} units • {{ ((calculateRowIdr(item) / totalTxnAmount) * 100 || 0).toFixed(1) }}% of total</span>
                        </div>
                        <div class="text-right">
                            <div class="font-bold text-indigo-700">Unit Cost: Rp {{ formatNumber(calculateUnitIdr(item)) }}</div>
                            <div class="text-[10px] text-slate-500">Total: Rp {{ formatNumber(calculateRowIdr(item)) }}</div>
                        </div>
                    </div>
                </div>
            </div>

          </div>
        </div>

      </div>

      <!-- Footer CTA -->
      <div class="px-6 py-4 border-t border-gray-100 bg-gray-50/80 rounded-b-2xl shrink-0 flex items-center justify-between">
        <div class="flex items-center gap-2 text-xs">
           <span v-if="syncStatus === 'synced'" class="text-green-600 flex items-center gap-1 font-medium"><i class="bi bi-check-circle-fill"></i> Balanced (100%)</span>
           <span v-else-if="syncStatus === 'empty'" class="text-gray-500 flex items-center gap-1"><i class="bi bi-dash-circle"></i> Incomplete Mapping</span>
           <span v-else class="text-yellow-600 flex items-center gap-1"><i class="bi bi-exclamation-triangle-fill"></i> Need Txn & Products</span>
        </div>
        <div class="flex gap-3">
          <button @click="$emit('close')" class="px-5 py-2.5 text-sm font-bold text-gray-600 hover:bg-gray-100 rounded-xl transition-colors">
            Cancel
          </button>
          <button @click="saveBatch" :disabled="isSaving || syncStatus === 'empty'" class="px-6 py-2.5 bg-indigo-600 text-white text-sm font-bold rounded-xl hover:bg-indigo-700 active:bg-indigo-800 transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2">
            <span v-if="isSaving" class="spinner-border w-4 h-4 text-white border-2"></span>
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
import { useProductStore } from '../../stores/products';
import { hppApi } from '../../api';

const props = defineProps({
  isOpen: Boolean,
  batchId: String,
  companyId: String
});

const emit = defineEmits(['close', 'saved']);

const batchStore = useHppBatchStore();
const productStore = useProductStore();

const form = ref({
    memo: '',
    transactions: [],
    products: []
});

const availableProducts = computed(() => productStore.products);

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
    return form.value.products.reduce((sum, p) => sum + ((p.quantity || 0) * (p.foreign_price || 0)), 0);
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
    if (form.value.transactions.length > 0 && form.value.products.length > 0 && totalForeignValue.value > 0) return 'synced';
    return 'empty';
});

// Initialization
const init = async () => {
    error.value = '';
    form.value = { memo: '', transactions: [], products: [] };
    
    console.log('=== Init COGS Batch Modal ===', { 
        batchId: props.batchId, 
        companyId: props.companyId,
        isOpen: props.isOpen 
    });
    
    if (!props.companyId) {
        error.value = 'Company ID is required. Please select a company first.';
        console.error('No companyId provided!');
        return;
    }
    
    // Load products list if empty
    if (availableProducts.value.length === 0) {
        console.log('Loading products for company:', props.companyId);
        await productStore.fetchProducts(props.companyId);
        console.log('Products loaded:', availableProducts.value.length);
    }
    
    if (props.batchId) {
        // Load existing batch
        try {
            const data = await batchStore.fetchBatchDetails(props.batchId);
            console.log('Loaded batch details:', data);
            
            form.value.memo = data.batch.memo;
            form.value.transactions = data.transactions;
            form.value.products = data.products.map(p => ({
                product_id: p.product_id,
                foreign_currency: p.foreign_currency,
                quantity: p.quantity,
                foreign_price: p.foreign_price
            }));
            
            // Set filter month to the batch date for editing (ensure YYYY-MM format)
            if (data.batch.batch_date) {
                const batchDateStr = String(data.batch.batch_date);
                // Extract YYYY-MM from date string (could be YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
                filterMonth.value = batchDateStr.slice(0, 7);
                console.log('Set filterMonth from batch_date:', filterMonth.value);
            }
        } catch (e) {
            console.error('Error loading batch details:', e);
            error.value = "Failed to load batch details: " + (e.response?.data?.error || e.message || 'Unknown error');
        }
    } else {
        // Init with 1 empty row for new batch
        console.log('Creating new batch, adding initial product row');
        addProductRow();
    }
    
    // Don't auto-load transactions - user must select month or search first
    console.log('Select a month or use search to find transactions');
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
        console.warn('No companyId provided, cannot load transactions');
        linkableTransactions.value = [];
        return;
    }
    
    // Only load if month is selected and in valid format (YYYY-MM)
    if (!filterMonth.value || !/^\d{4}-\d{2}$/.test(filterMonth.value)) {
        console.log('No valid month selected, not loading transactions');
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
            console.error('Invalid year or month:', { year, month });
            error.value = 'Invalid month selected';
            linkableTransactions.value = [];
            return;
        }
        
        const lastDay = new Date(yearNum, monthNum, 0).getDate();
        const start = `${yearNum}-${String(monthNum).padStart(2, '0')}-01`;
        const end = `${yearNum}-${String(monthNum).padStart(2, '0')}-${lastDay}`;
        
        console.log('Loading transactions for:', { companyId: props.companyId, start, end });
        
        const res = await hppApi.getLinkableTransactions(props.companyId, start, end);
        console.log('API Response:', res.data);
        
        // Exclude ones that are already linked to *other* batches
        linkableTransactions.value = res.data.transactions.filter(t => {
            return !t.is_linked || form.value.transactions.some(ft => ft.id === t.id);
        });
        console.log('Filtered transactions count:', linkableTransactions.value.length);
    } catch (e) {
        console.error('Error loading transactions:', e);
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
const addProductRow = () => {
    form.value.products.push({
        product_id: '',
        foreign_currency: 'USD',
        quantity: 1,
        foreign_price: 0
    });
};

const removeProductRow = (index) => {
    form.value.products.splice(index, 1);
};

const onProductSelect = (item) => {
    const product = availableProducts.value.find(p => p.id === item.product_id);
    if (product) {
        item.foreign_currency = product.default_currency || 'USD';
        item.foreign_price = product.default_price || 0;
    }
};

const getProductName = (id) => {
    const p = availableProducts.value.find(x => x.id === id);
    return p ? p.name : 'Unknown Product';
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
    
    const validProducts = form.value.products.filter(p => p.product_id && p.quantity > 0);
    if (validProducts.length === 0) {
        error.value = 'At least one product with quantity > 0 must be added';
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
    
    console.log('Calculated batch_date from transactions:', earliestDate, 'from', form.value.transactions.map(t => t.txn_date));
    
    const payload = {
        id: props.batchId, // Will be null for new
        company_id: props.companyId,
        memo: form.value.memo,
        batch_date: earliestDate,
        transaction_ids: form.value.transactions.map(t => t.id),
        products: validProducts
    };
    
    console.log('Saving COGS batch with payload:', payload);
    
    try {
        await batchStore.saveBatch(payload);
        emit('saved');
    } catch (e) {
        console.error('Error saving batch:', e);
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
