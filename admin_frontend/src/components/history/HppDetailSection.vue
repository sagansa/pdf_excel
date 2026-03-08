<template>
  <div class="bg-blue-50/50 p-4 rounded-xl border border-blue-100 mt-4">
    <div class="flex justify-between items-center mb-3">
        <div class="text-[10px] font-extrabold text-blue-500 uppercase tracking-widest flex items-center gap-1">
            <i class="bi bi-box-seam"></i> Product COGS Details
        </div>
        <div class="text-xs font-bold text-gray-700">
            Transaction Total: <span class="text-blue-600 ml-1">IDR {{ formatNumber(transactionTotal) }}</span>
        </div>
    </div>
    
    <!-- Items Table -->
    <div class="space-y-3">
        <div v-for="(item, index) in items" :key="index" class="bg-white p-3 rounded-lg border border-blue-100 shadow-sm relative group">
            <button @click="removeItem(index)" class="absolute -top-2 -right-2 bg-red-100 text-red-600 rounded-full w-5 h-5 flex items-center justify-center text-[10px] hover:bg-red-200 opacity-0 group-hover:opacity-100 transition-opacity">
                <i class="bi bi-x-lg"></i>
            </button>
            <div class="grid grid-cols-12 gap-3 items-end">
                <div class="col-span-4">
                    <label class="block text-[9px] font-bold text-gray-400 uppercase tracking-wider mb-1">Product</label>
                    <select v-model="item.product_id" @change="onProductSelect(item)" class="input-base text-xs py-1.5 px-2">
                        <option value="">Select Product...</option>
                        <option v-for="p in products" :key="p.id" :value="p.id">{{ p.name }} ({{ p.code || 'No Code' }})</option>
                    </select>
                </div>
                <div class="col-span-2">
                    <label class="block text-[9px] font-bold text-gray-400 uppercase tracking-wider mb-1">Qty</label>
                    <input type="number" v-model.number="item.quantity" min="0.01" step="0.01" class="input-base text-xs py-1.5 px-2 text-right" />
                </div>
                <div class="col-span-3">
                    <label class="block text-[9px] font-bold text-gray-400 uppercase tracking-wider mb-1">Foreign Price</label>
                    <div class="flex">
                        <select v-model="item.foreign_currency" class="input-base text-xs py-1.5 px-1 w-16 rounded-r-none border-r-0">
                            <option value="USD">USD</option>
                            <option value="CNY">CNY</option>
                            <option value="IDR">IDR</option>
                            <option value="EUR">EUR</option>
                            <option value="SGD">SGD</option>
                        </select>
                        <input type="number" v-model.number="item.foreign_price" step="0.01" class="input-base rounded-l-none text-xs py-1.5 px-2 w-full text-right" />
                    </div>
                </div>
                <!-- Calculated Result -->
                <div class="col-span-3 text-right">
                    <label class="block text-[9px] font-bold text-gray-400 uppercase tracking-wider mb-1">IDR COGS</label>
                    <div class="text-sm font-bold text-gray-800 bg-gray-50 py-1.5 px-2 rounded border border-gray-100">
                        {{ formatNumber(calculateRowIdr(item)) }}
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Add Item Button & Summary -->
    <div class="mt-4 flex justify-between items-center">
        <button @click="addItem" class="text-xs font-bold text-blue-600 hover:text-blue-800 flex items-center gap-1">
            <i class="bi bi-plus-circle-fill"></i> Add Product
        </button>

        <div class="flex items-center gap-4">
            <div class="text-right">
                <p class="text-[10px] text-gray-500 font-bold uppercase">Assigned Total</p>
                <p class="text-sm font-bold" :class="isMatched ? 'text-green-600' : 'text-amber-600'">
                    IDR {{ formatNumber(sumIdrHpp) }}
                </p>
            </div>
            <button 
                @click="saveHpp" 
                class="btn-primary !bg-blue-600 hover:!bg-blue-700 !py-1.5 !px-3 !text-xs shadow-md shadow-blue-200"
                :disabled="isSaving"
            >
                <span v-if="isSaving" class="spinner-border w-3 h-3 me-1 border-2"></span>
                Save Details
            </button>
        </div>
    </div>
    
    <div v-if="error" class="mt-3 text-xs text-red-600 bg-red-50 p-2 rounded">
        {{ error }}
    </div>
    <div v-if="successMsg" class="mt-3 text-xs text-green-600 bg-green-50 p-2 rounded transition-opacity duration-1000">
        {{ successMsg }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { useProductStore } from '../../stores/products';
import { hppApi } from '../../api';

const props = defineProps({
  transaction: {
      type: Object,
      required: true
  }
});

const store = useProductStore();
const products = computed(() => store.products);

const items = ref([]);
const isSaving = ref(false);
const error = ref(null);
const successMsg = ref(null);

const transactionTotal = computed(() => {
    return Math.abs(parseFloat(props.transaction.amount) || 0);
});

// Calculate total foreign value across all items to find the proportions
const totalForeignValue = computed(() => {
    return items.value.reduce((sum, item) => {
        const qty = parseFloat(item.quantity) || 0;
        const price = parseFloat(item.foreign_price) || 0;
        return sum + (qty * price);
    }, 0);
});

const calculateRowIdr = (item) => {
    const totalTxn = transactionTotal.value;
    const foreignTotal = totalForeignValue.value;
    
    if (foreignTotal <= 0) return 0;
    
    const qty = parseFloat(item.quantity) || 0;
    const price = parseFloat(item.foreign_price) || 0;
    const itemForeignValue = qty * price;
    
    return totalTxn * (itemForeignValue / foreignTotal);
};

const sumIdrHpp = computed(() => {
    return items.value.reduce((sum, item) => sum + calculateRowIdr(item), 0);
});

const isMatched = computed(() => {
    const diff = Math.abs(sumIdrHpp.value - transactionTotal.value);
    return diff < 0.01 && items.value.length > 0;
});

const formatNumber = (num) => {
    return Number(num || 0).toLocaleString('id-ID', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
};

const loadHppData = async () => {
    if (!props.transaction || !props.transaction.id) return;
    try {
        const res = await hppApi.getTransactionHpp(props.transaction.id);
        if (res.data.items && res.data.items.length > 0) {
            items.value = res.data.items.map(i => ({
                product_id: i.product_id,
                quantity: parseFloat(i.quantity),
                foreign_currency: i.foreign_currency,
                foreign_price: parseFloat(i.foreign_price),
                calculated_idr_hpp: parseFloat(i.calculated_idr_hpp)
            }));
        } else {
            items.value = [];
        }
    } catch (err) {
        console.error("Failed to load HPP:", err);
    }
};

onMounted(async () => {
    // If store is empty, fetch. Actually we should always ensure products are loaded
    await store.fetchProducts();
    await loadHppData();
});

watch(() => props.transaction, async (newVal) => {
    if (newVal) {
        await loadHppData();
    }
}, { deep: true });

const addItem = () => {
    items.value.push({
        product_id: '',
        quantity: 1,
        foreign_currency: 'USD',
        foreign_price: 0
    });
};

const removeItem = (index) => {
    items.value.splice(index, 1);
};

const onProductSelect = (item) => {
    const prod = products.value.find(p => p.id === item.product_id);
    if (prod) {
        item.foreign_currency = prod.default_currency || 'USD';
        item.foreign_price = prod.default_price || 0;
    }
};

const saveHpp = async () => {
    error.value = null;
    successMsg.value = null;
    
    // Validation
    if (items.value.some(i => !i.product_id)) {
        error.value = "All items must have a product selected.";
        return;
    }
    
    isSaving.value = true;
    try {
        await hppApi.saveTransactionHpp(props.transaction.id, items.value);
        successMsg.value = "HPP Details saved successfully!";
        setTimeout(() => successMsg.value = null, 3000);
        // Reload to get calculated values fresh from DB
        await loadHppData();
    } catch (err) {
        error.value = err.response?.data?.error || err.message;
    } finally {
        isSaving.value = false;
    }
};
</script>
