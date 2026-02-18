<template>
  <BaseModal :isOpen="isOpen" @close="onClose" size="lg">
    <template #title>
      <div class="flex items-center justify-between w-full">
        <div class="flex items-center gap-2">
          <div class="p-1 bg-indigo-50 rounded-md">
            <i class="bi bi-diagram-3 text-indigo-600 text-sm"></i>
          </div>
          <span class="text-gray-900 font-bold tracking-tight text-sm">Split Transaction</span>
        </div>
        <div v-if="transaction" class="flex items-center gap-2 text-[10px]">
           <span class="text-gray-400 font-semibold uppercase tracking-widest text-[9px]">Total</span>
           <span class="font-bold text-sm" :class="transaction.db_cr === 'CR' ? 'text-green-600' : 'text-red-500'">
             {{ formatAmount(transaction.amount) }}
           </span>
        </div>
      </div>
    </template>

    <div v-if="transaction" class="space-y-4 px-4 pb-4">
      <!-- Minimal Info Header -->
      <div class="bg-gray-50/50 border border-gray-100 p-2 rounded-lg flex items-center gap-4 text-xs">
        <div class="flex items-center gap-1.5 min-w-0">
          <i class="bi bi-calendar3 text-gray-400"></i>
          <span class="font-bold text-gray-700 whitespace-nowrap">{{ formatDate(transaction.txn_date) }}</span>
        </div>
        <div class="w-px h-3 bg-gray-200"></div>
        <div class="flex items-center gap-1.5 min-w-0 flex-1">
          <i class="bi bi-card-text text-gray-400"></i>
          <span class="font-bold text-gray-700 truncate" :title="transaction.description">{{ transaction.description }}</span>
        </div>
      </div>

      <!-- Allocation Progress Bar -->
      <div class="space-y-1.5">
        <div class="flex justify-between text-[10px]">
          <span class="font-bold text-gray-500 uppercase tracking-widest">Allocation</span>
          <span class="font-bold" :class="Math.abs(remainingAmount) <= 0.01 ? 'text-green-600' : 'text-indigo-600'">
             {{ formatAmount(allocatedAmount) }} / {{ formatAmount(transactionAmount) }}
          </span>
        </div>
        <div class="relative h-1.5 w-full bg-gray-100 rounded-full overflow-hidden flex shadow-inner">
           <div
              class="h-full transition-all duration-300 ease-in-out bg-indigo-500"
              :class="allocatedPercent > 100 ? 'bg-red-500' : ''"
              :style="{ width: `${Math.min(allocatedPercent, 100)}%` }"
            ></div>
            <div
              v-if="allocatedPercent > 100"
              class="h-full bg-red-600"
              :style="{ width: `${Math.min(allocatedPercent - 100, 100)}%` }"
            ></div>
        </div>
        <div class="flex justify-between items-center text-[10px]">
          <span :class="allocatedPercent > 100 ? 'text-red-500 font-bold' : 'text-indigo-600 font-bold'">{{ allocatedPercent.toFixed(0) }}%</span>
           <span v-if="Math.abs(remainingAmount) > 0.01" :class="remainingAmount > 0 ? 'text-amber-600' : 'text-red-600'">
             {{ remainingAmount > 0 ? 'Rem:' : 'Over:' }} {{ formatAmount(Math.abs(remainingAmount)) }}
           </span>
           <span v-else class="text-green-600 font-bold flex items-center gap-1">
             <i class="bi bi-check-circle-fill text-[9px]"></i> OK
           </span>
        </div>
      </div>

      <div class="space-y-3">
        <div class="flex items-center justify-between">
          <span class="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Splits</span>
          <button
            @click="addSplit"
            class="px-2 py-1 bg-indigo-50 text-indigo-600 hover:bg-indigo-100 rounded text-[10px] font-bold transition-colors border border-indigo-100"
          >
            + Add
          </button>
        </div>

        <div v-if="splits.length === 0" class="py-6 border-2 border-dashed border-gray-100 rounded-lg text-center">
          <p class="text-[10px] text-gray-400">No splits added</p>
        </div>

        <div class="space-y-1.5 max-h-[300px] overflow-y-auto pr-1 custom-scrollbar">
          <transition-group enter-active-class="transition duration-200" enter-from-class="opacity-0 -translate-y-2" leave-active-class="transition duration-150" leave-to-class="opacity-0 -translate-y-2">
            <div
              v-for="(split, index) in splits"
              :key="index"
              class="group bg-white border border-gray-200 hover:border-indigo-300 rounded-md p-2 shadow-sm transition-all grid grid-cols-[auto_1fr_auto] gap-2 items-start"
            >
               <!-- Badge -->
               <div class="mt-1.5 w-4 h-4 rounded-full bg-gray-100 text-[9px] font-bold text-gray-500 flex items-center justify-center">
                 {{ index + 1 }}
               </div>

               <!-- Content -->
               <div class="space-y-1.5">
                 <!-- Main Row: Mark + Amount -->
                 <div class="flex items-center gap-2">
                    <div class="flex-1 min-w-0">
                       <SearchableSelect
                         v-model="split.mark_id"
                         :options="markOptions"
                         placeholder="Select mark..."
                         class="text-xs"
                       />
                    </div>
                    <div class="w-28 relative">
                       <input
                          type="number"
                          step="0.01"
                          v-model.number="split.amount"
                          class="w-full bg-gray-50 border border-gray-200 rounded px-2 py-1 text-xs font-mono font-bold text-right focus:ring-1 focus:ring-indigo-500 outline-none"
                          placeholder="0.00"
                        >
                        <button
                          v-if="index === splits.length - 1 && remainingAmount > 0"
                          @click="fillRemainder(index)"
                          class="absolute -top-1.5 -right-1 w-3 h-3 bg-indigo-100 text-indigo-600 rounded-full flex items-center justify-center text-[8px] hover:bg-indigo-200"
                          title="Fill Remainder"
                        >
                          <i class="bi bi-arrow-down-short"></i>
                        </button>
                    </div>
                 </div>
                 <!-- Optional Notes -->
                 <input
                    v-model="split.notes"
                    placeholder="Optional notes..."
                    class="w-full bg-transparent text-[10px] text-gray-500 focus:text-gray-800 outline-none placeholder:text-gray-300 border-none p-0 h-auto"
                  >
               </div>

               <!-- Delete -->
               <button @click="removeSplit(index)" class="mt-1.5 text-gray-300 hover:text-red-500 transition-colors">
                 <i class="bi bi-x-circle-fill text-xs"></i>
               </button>
            </div>
          </transition-group>
        </div>
      </div>

      <!-- Compact Error -->
      <div v-if="splits.length > 0 && hasValidationError" class="bg-red-50 border border-red-100 px-3 py-1.5 rounded text-[10px] text-red-600 flex items-center gap-2">
         <i class="bi bi-exclamation-circle-fill"></i>
         <span class="font-medium">{{ validationMessage }}</span>
      </div>
    </div>

    <template #footer>
      <div class="flex items-center justify-between w-full">
         <span class="text-[10px] text-gray-400">
           {{ splits.length }} split{{ splits.length !== 1 ? 's' : '' }}
         </span>
         <div class="flex gap-2">
            <button @click="onClose" class="text-xs font-medium text-gray-500 hover:text-gray-900 px-3 py-1.5">Cancel</button>
            <button
               @click="saveSplits"
               :disabled="hasValidationError"
               class="px-4 py-1.5 bg-indigo-600 text-white text-xs font-bold rounded shadow-sm hover:bg-indigo-700 disabled:opacity-50 disabled:shadow-none transition-all flex items-center gap-1.5"
            >
               <i v-if="store.isLoading" class="bi bi-arrow-repeat animate-spin"></i>
               Save
            </button>
         </div>
      </div>
    </template>
  </BaseModal>
</template>
<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { useHistoryStore } from '../../stores/history';
import BaseModal from '../ui/BaseModal.vue';
import SearchableSelect from '../ui/SearchableSelect.vue';

const props = defineProps({
  isOpen: {
    type: Boolean,
    required: true
  },
  transaction: {
    type: Object,
    default: null
  }
});

const emit = defineEmits(['close', 'saved']);

const store = useHistoryStore();
const splits = ref([]);
const sortedMarks = computed(() => store.sortedMarks);

const markOptions = computed(() => {
  return sortedMarks.value.map(m => ({
    id: m.id,
    label: m.internal_report || m.personal_use || 'Unnamed Mark'
  }));
});

const transactionAmount = computed(() => {
  if (!props.transaction) return 0;
  return parseFloat(props.transaction.amount) || 0;
});

const allocatedAmount = computed(() => {
  return splits.value.reduce((sum, split) => sum + (parseFloat(split.amount) || 0), 0);
});

const allocatedPercent = computed(() => {
  if (transactionAmount.value === 0) return 0;
  return (allocatedAmount.value / transactionAmount.value) * 100;
});

const remainingAmount = computed(() => {
  return transactionAmount.value - allocatedAmount.value;
});

const hasValidationError = computed(() => {
  if (splits.value.length === 0) return false;
  return Math.abs(remainingAmount.value) > 0.01 || splits.value.some(s => !s.mark_id || s.amount === null || s.amount === undefined);
});

const validationMessage = computed(() => {
  if (remainingAmount.value > 0.01 && splits.value.length > 0) {
    return `Remaining: ${formatAmount(Math.abs(remainingAmount.value))} must be allocated`;
  } else if (remainingAmount.value < -0.01) {
    return `Over-allocated by: ${formatAmount(Math.abs(remainingAmount.value))}`;
  } else {
    const missingMark = splits.value.find(s => !s.mark_id);
    if (missingMark) return 'All splits must have a mark selected';
    const missingAmount = splits.value.find(s => s.amount === null || s.amount === undefined);
    if (missingAmount) return 'All splits must have an amount';
    return '';
  }
});

const formatDate = (dateStr) => {
  if (!dateStr || typeof dateStr !== 'string') return "-";
  try {
    return dateStr.split(" ")[0];
  } catch (e) { return dateStr; }
};

const formatAmount = (val) => {
  if (val === undefined || val === null) return "0";
  const num = typeof val === 'string' ? parseFloat(val.replace(/,/g, '')) : val;
  return new Intl.NumberFormat('id-ID').format(num || 0);
};

const addSplit = () => {
  const remaining = transactionAmount.value - allocatedAmount.value;
  const defaultAmount = remaining > 0 ? remaining : 0;
  
  splits.value.push({
    mark_id: '',
    amount: defaultAmount > 0 ? Math.min(defaultAmount, transactionAmount.value) : null,
    notes: ''
  });
};

const removeSplit = (index) => {
  splits.value.splice(index, 1);
};

const fillRemainder = (index) => {
  const currentSplit = splits.value[index];
  if (!currentSplit) return;
  const currentAmount = parseFloat(currentSplit.amount) || 0;
  currentSplit.amount = currentAmount + remainingAmount.value;
};

const saveSplits = async () => {
  if (hasValidationError.value) return;
  
  try {
    const validSplits = splits.value.filter(s => s.mark_id && s.amount !== null && s.amount !== undefined);
    await store.saveSplits(props.transaction.id, validSplits);
    emit('saved');
  } catch (e) {
    console.error('Failed to save splits:', e);
    alert('Failed to save splits: ' + (e.response?.data?.error || e.message));
  }
};

const onClose = () => {
  emit('close');
};

const loadExistingSplits = async () => {
  if (!props.transaction) return;
  
  try {
    const existingSplits = await store.fetchSplits(props.transaction.id);
    if (existingSplits.length > 0) {
      splits.value = existingSplits.map(s => ({
        mark_id: s.mark_id,
        amount: s.amount,
        notes: s.notes || ''
      }));
    } else {
      splits.value = [];
    }
  } catch (e) {
    console.error('Failed to load splits:', e);
  }
};

watch(() => props.isOpen, (isOpen) => {
  if (isOpen && props.transaction) {
    loadExistingSplits();
  } else if (!isOpen) {
    splits.value = [];
  }
});
</script>
