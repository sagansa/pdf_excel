<template>
  <div class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
    <div class="bg-slate-50 border-b border-slate-200 px-6 py-4 flex items-center justify-between">
      <div>
        <h3 class="text-lg font-bold text-slate-800">Manual Inventory Adjustments</h3>
        <p class="text-xs text-slate-500 mt-0.5">Adjust beginning and ending inventory</p>
      </div>

      <div v-if="isSaving" class="flex items-center gap-2 text-indigo-600">
        <div class="animate-spin h-4 w-4 border-2 border-indigo-600 border-t-transparent rounded-full"></div>
        <span class="text-xs font-medium">Saving...</span>
      </div>
    </div>

    <div class="p-6">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
        <!-- Beginning Inventory -->
        <div class="space-y-4">
          <div class="flex items-center gap-2 pb-2 border-b border-slate-100">
            <i class="bi bi-box-arrow-in-right text-indigo-500"></i>
            <h4 class="font-bold text-slate-700 uppercase tracking-wider text-xs">Beginning Inventory (Awal)</h4>
          </div>
          
          <div class="space-y-3">
            <div>
              <label class="block text-xs font-semibold text-slate-500 mb-1">Valuation Amount (Rp)</label>
              <div class="relative">
                <span class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm font-medium">Rp</span>
                <input 
                  v-model.number="form.beginning_inventory_amount"
                  type="number" 
                  class="w-full pl-10 pr-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all text-sm"
                  placeholder="0"
                />
              </div>
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 mb-1">Quantity (Unit)</label>
              <input 
                v-model.number="form.beginning_inventory_qty"
                type="number" 
                class="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all text-sm"
                placeholder="0"
              />
            </div>
          </div>
        </div>

        <!-- Ending Inventory -->
        <div class="space-y-4">
          <div class="flex items-center gap-2 pb-2 border-b border-slate-100">
            <i class="bi bi-box-arrow-left text-orange-500"></i>
            <h4 class="font-bold text-slate-700 uppercase tracking-wider text-xs">Ending Inventory (Akhir)</h4>
          </div>
          
          <div class="space-y-3">
            <div>
              <label class="block text-xs font-semibold text-slate-500 mb-1">Valuation Amount (Rp)</label>
              <div class="relative">
                <span class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm font-medium">Rp</span>
                <input 
                  v-model.number="form.ending_inventory_amount"
                  type="number" 
                  class="w-full pl-10 pr-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-all text-sm"
                  placeholder="0"
                />
              </div>
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 mb-1">Quantity (Unit)</label>
              <input 
                v-model.number="form.ending_inventory_qty"
                type="number" 
                class="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-all text-sm"
                placeholder="0"
              />
            </div>
          </div>
        </div>
      </div>

      <div class="mt-8 flex items-center justify-between pt-6 border-t border-slate-100">
        <div class="flex items-center gap-2 text-slate-500 text-xs italic">
          <i class="bi bi-info-circle"></i>
          These values will be used to calculate HPP (COGS) in the Income Statement.
        </div>
        <button 
          @click="saveBalances"
          :disabled="isSaving || !companyId"
          class="bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white px-6 py-2 rounded-lg font-bold text-sm shadow-md transition-all flex items-center gap-2"
        >
          <i class="bi bi-check-lg text-lg"></i>
          Save Adjustments
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, computed } from 'vue';
import { useReportsStore } from '../../stores/reports';

const props = defineProps({
  companyId: {
    type: String,
    default: null
  },
  year: {
    type: [String, Number],
    default: new Date().getFullYear()
  }
});

const emit = defineEmits(['saved', 'update:year']);
const store = useReportsStore();
const isSaving = ref(false);

const availableYears = computed(() => {
  const currentYear = new Date().getFullYear();
  const years = [];
  for (let i = currentYear - 2; i <= currentYear + 1; i++) {
    years.push(i);
  }
  return years;
});

const form = ref({
  beginning_inventory_amount: 0,
  beginning_inventory_qty: 0,
  ending_inventory_amount: 0,
  ending_inventory_qty: 0,
  is_manual: true
});

const fetchBalances = async () => {
  if (!props.companyId || !props.year) return;
  
  const balance = await store.fetchInventoryBalances(props.year, props.companyId);
  if (balance && Object.keys(balance).length > 0) {
    form.value = {
      beginning_inventory_amount: balance.beginning_inventory_amount || 0,
      beginning_inventory_qty: balance.beginning_inventory_qty || 0,
      ending_inventory_amount: balance.ending_inventory_amount || 0,
      ending_inventory_qty: balance.ending_inventory_qty || 0,
      is_manual: balance.is_manual ?? true
    };
  } else {
    // Reset form if no balance found
    form.value = {
      beginning_inventory_amount: 0,
      beginning_inventory_qty: 0,
      ending_inventory_amount: 0,
      ending_inventory_qty: 0,
      is_manual: true
    };
  }
};

const saveBalances = async () => {
  if (!props.companyId || !props.year) return;
  
  isSaving.value = true;
  try {
    await store.saveInventoryBalances({
      ...form.value,
      company_id: props.companyId,
      year: parseInt(props.year)
    });
    emit('saved');
  } catch (err) {
    console.error("Save failed:", err);
  } finally {
    isSaving.value = false;
  }
};

watch(() => [props.companyId, props.year], () => {
  fetchBalances();
}, { deep: true });

onMounted(() => {
  fetchBalances();
});
</script>
