<template>
  <div class="px-5 py-6 rounded-2xl bg-surface-muted border border-border mt-6 space-y-5">
    <!-- Header -->
    <div class="flex justify-between items-center bg-surface/50 p-3 rounded-xl border border-border/50">
        <div class="text-[10px] font-black text-theme uppercase tracking-[0.2em] flex items-center gap-2">
            <div class="w-6 h-6 rounded bg-primary/10 flex items-center justify-center">
              <i class="bi bi-box-seam text-primary"></i>
            </div>
            Product COGS Allocation
        </div>
        <div class="text-[11px] font-bold text-muted uppercase tracking-widest">
            TXN Total: <span class="text-primary ml-1">IDR {{ formatNumber(transactionTotal) }}</span>
        </div>
    </div>
    
    <!-- Items Table -->
    <div class="grid grid-cols-1 gap-4">
        <div v-for="(item, index) in items" :key="index" 
             class="bg-surface p-4 rounded-xl border border-border shadow-sm relative group hover:border-primary/30 transition-all"
        >
            <button @click="removeItem(index)" 
                    class="absolute -top-2 -right-2 bg-danger text-white rounded-full w-6 h-6 flex items-center justify-center text-[10px] shadow-lg opacity-0 group-hover:opacity-100 transition-all hover:scale-110 active:scale-90"
            >
                <i class="bi bi-x-lg"></i>
            </button>
            <div class="grid grid-cols-12 gap-4 items-end">
                <div class="col-span-12 md:col-span-5">
                    <label class="block text-[9px] font-black text-muted uppercase tracking-widest mb-1.5 ml-1">Product / Item</label>
                    <select v-model="item.product_id" @change="onProductSelect(item)" 
                            class="input-base text-xs h-9 px-3 w-full"
                    >
                        <option value="">Select Product...</option>
                        <option v-for="p in products" :key="p.id" :value="p.id">{{ p.name }} ({{ p.code || 'No Code' }})</option>
                    </select>
                </div>
                <div class="col-span-4 md:col-span-2">
                    <label class="block text-[9px] font-black text-muted uppercase tracking-widest mb-1.5 ml-1">Quantity</label>
                    <input type="number" v-model.number="item.quantity" min="0.01" step="0.01" 
                           class="input-base text-xs h-9 px-3 text-right" 
                    />
                </div>
                <div class="col-span-8 md:col-span-5">
                    <div class="grid grid-cols-2 gap-3">
                      <div>
                        <label class="block text-[9px] font-black text-muted uppercase tracking-widest mb-1.5 ml-1">Price (Foreign)</label>
                        <div class="flex">
                            <select v-model="item.foreign_currency" 
                                    class="input-base text-[10px] h-9 px-2 w-16 rounded-r-none border-r-0 font-bold bg-surface-muted"
                            >
                                <option value="USD">USD</option>
                                <option value="CNY">CNY</option>
                                <option value="IDR">IDR</option>
                                <option value="EUR">EUR</option>
                                <option value="SGD">SGD</option>
                            </select>
                            <input type="number" v-model.number="item.foreign_price" step="0.01" 
                                   class="input-base rounded-l-none text-xs h-9 px-3 w-full text-right" 
                            />
                        </div>
                      </div>
                      <div class="text-right">
                        <label class="block text-[9px] font-black text-muted uppercase tracking-widest mb-1.5 mr-1">IDR Allocation</label>
                        <div class="h-9 flex items-center justify-end px-3 text-sm font-black text-theme bg-surface-muted rounded-xl border border-border/50 font-mono italic">
                            {{ formatNumber(calculateRowIdr(item)) }}
                        </div>
                      </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Empty State -->
    <div v-if="items.length === 0" 
         class="py-10 text-center border-2 border-dashed border-border rounded-xl bg-surface/50"
    >
      <i class="bi bi-box-fill text-3xl text-muted/30 mb-2 block"></i>
      <p class="text-[11px] font-bold text-muted uppercase tracking-widest">No products allocated</p>
    </div>

    <!-- Add Item Button & Summary -->
    <div class="pt-2 flex flex-col md:flex-row justify-between items-center gap-4">
        <button @click="addItem" 
                class="text-[10px] font-black text-primary hover:bg-primary/10 px-4 py-2 rounded-xl transition-all uppercase tracking-widest border border-primary/20 flex items-center gap-2"
        >
            <i class="bi bi-plus-circle-fill"></i> Add Product Row
        </button>

        <div class="flex items-center gap-6 bg-surface p-3 pr-4 rounded-2xl border border-border shadow-soft w-full md:w-auto justify-between">
            <div class="text-right pl-2">
                <p class="text-[9px] text-muted font-black uppercase tracking-widest mb-0.5">Assigned Total</p>
                <p class="text-sm font-black font-mono" :class="isMatched ? 'text-success' : 'text-warning'">
                    IDR {{ formatNumber(sumIdrHpp) }}
                </p>
            </div>
            <button 
                @click="saveHpp" 
                class="btn-primary !h-10 !px-6 !text-xs"
                :disabled="isSaving"
            >
                <i v-if="isSaving" class="bi bi-arrow-repeat animate-spin me-2"></i>
                <i v-else class="bi bi-cloud-check me-2"></i>
                Save Details
            </button>
        </div>
    </div>
    
    <!-- Status Messages -->
    <div class="h-4">
      <transition name="fade">
        <div v-if="error" class="text-[10px] font-bold text-danger bg-danger/5 px-3 py-1.5 rounded-lg border border-danger/10 flex items-center gap-2">
            <i class="bi bi-exclamation-triangle-fill"></i> {{ error }}
        </div>
      </transition>
      <transition name="fade">
        <div v-if="successMsg" class="text-[10px] font-bold text-success bg-success/5 px-3 py-1.5 rounded-lg border border-success/10 flex items-center gap-2">
            <i class="bi bi-check-circle-fill"></i> {{ successMsg }}
        </div>
      </transition>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
// import { useProductStore } from '../../stores/products';
import { hppApi } from '../../api';

const props = defineProps({
  transaction: {
      type: Object,
      required: true
  }
});

const products = ref([]);

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
    // Fetch products locally
    try {
        const response = await hppApi.getItems('storage');
        products.value = response.data.items || [];
    } catch (err) {
        console.error("Failed to fetch products:", err);
    }
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
