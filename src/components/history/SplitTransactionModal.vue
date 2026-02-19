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
                       <div class="space-y-2">
  <!-- Standard Select for Testing -->
  <select 
    v-model="split.mark_id" 
    class="w-full text-xs border border-gray-200 rounded px-2 py-1.5 focus:ring-1 focus:ring-indigo-500 outline-none"
  >
    <option value="">Select mark...</option>
    <option 
      v-for="opt in markOptions" 
      :key="opt.id" 
      :value="opt.id"
    >
      {{ opt.label }}
    </option>
   </select>
</div>
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
  if (!sortedMarks.value || sortedMarks.value.length === 0) {
    console.log('SplitTransactionModal: No marks available yet');
    return [];
  }
  
  console.log('SplitTransactionModal: markOptions computed, sortedMarks count:', sortedMarks.value.length);
  const options = sortedMarks.value.map(m => ({
    id: m.id,
    label: m.internal_report || m.personal_use || 'Unnamed Mark'
  }));
  
  // Check if any split mark is missing from options
  const splitMarkIds = new Set(splits.value.filter(s => s.mark_id).map(s => s.mark_id));
  const availableMarkIds = new Set(sortedMarks.value.map(m => m.id));
  const missingMarkIds = [...splitMarkIds].filter(id => !availableMarkIds.has(id));
  
  if (missingMarkIds.length > 0) {
    console.warn('SplitTransactionModal: Some split marks not found in marks:', missingMarkIds);
  }
  
  return options;
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
  
  // Debug validation
  console.log('SplitTransactionModal: hasValidationError check:');
  console.log('  remainingAmount:', remainingAmount.value);
  console.log('  Math.abs(remainingAmount) > 0.01:', Math.abs(remainingAmount.value) > 0.01);
  
  const amountErrors = splits.value.map(s => !s.amount || s.amount === null || s.amount === undefined);
  console.log('  amount errors:', amountErrors);
  console.log('  some amount errors:', splits.value.some(s => !s.amount || s.amount === null || s.amount === undefined));
  
  const markErrors = splits.value.map(s => !s.mark_id);
  console.log('  mark errors:', markErrors);
  console.log('  some mark errors:', splits.value.some(s => !s.mark_id));
  
  console.log('  splits:', splits.value.map(s => ({mark_id: s.mark_id, amount: s.amount})));
  
  const remainingError = Math.abs(remainingAmount.value) > 0.01;
  const amountError = splits.value.some(s => s.amount === null || s.amount === undefined || s.amount === '');
  const markError = splits.value.some(s => !s.mark_id || s.mark_id === '' || s.mark_id === null || s.mark_id === undefined);
  
  console.log('  Final validation:', {remainingError, amountError, markError});
  
  return remainingError || amountError || markError;
});

const validationMessage = computed(() => {
  const remainingError = Math.abs(remainingAmount.value) > 0.01;
  const amountError = splits.value.some(s => s.amount === null || s.amount === undefined || s.amount === '');
  const markError = splits.value.some(s => !s.mark_id || s.mark_id === '' || s.mark_id === null || s.mark_id === undefined);
  
  if (remainingError) {
    return `Remaining: ${formatAmount(Math.abs(remainingAmount.value))} must be allocated`;
  } else if (remainingAmount.value < -0.01) {
    return `Over-allocated by: ${formatAmount(Math.abs(remainingAmount.value))}`;
  } else if (markError) {
    return 'All splits must have a mark selected';
  } else if (amountError) {
    return 'All splits must have an amount';
  }
  return '';
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
  
  console.log('SplitTransactionModal: Loading splits for transaction:', props.transaction.id);
  
  try {
    const existingSplits = await store.fetchSplits(props.transaction.id);
    console.log('SplitTransactionModal: Loaded splits:', existingSplits);
    
    if (existingSplits.length > 0) {
      splits.value = existingSplits.map((s, index) => {
        const mapped = {
          mark_id: s.mark_id,
          amount: s.amount,
          notes: s.notes || ''
        };
        console.log(`SplitTransactionModal: Mapped split ${index}:`, mapped, 'from:', s);
        return mapped;
      });
      console.log('SplitTransactionModal: Final mapped splits:', splits.value);
    } else {
      splits.value = [];
      console.log('SplitTransactionModal: No existing splits found');
    }
  } catch (e) {
    console.error('SplitTransactionModal: Failed to load splits:', e);
  }
};

watch(() => props.isOpen, (isOpen) => {
  if (isOpen && props.transaction) {
    // Ensure marks are loaded before loading splits
    console.log('SplitTransactionModal: Modal opening, marks count:', sortedMarks.value.length);
    
    if (sortedMarks.value.length === 0) {
      console.warn('SplitTransactionModal: No marks loaded yet, this might cause mark display issues');
    }
    
    console.log('SplitTransactionModal: Before loadExistingSplits');
    loadExistingSplits();
    
    // Check validation state after loading
    setTimeout(() => {
      console.log('SplitTransactionModal: After loadExistingSplits - hasValidationError:', hasValidationError.value);
      console.log('SplitTransactionModal: After loadExistingSplits - validationMessage:', validationMessage.value);
    }, 100);
  } else if (!isOpen) {
    splits.value = [];
  }
});

watch(() => splits.value, (newSplits) => {
  console.log('SplitTransactionModal: splits changed:', newSplits);
  console.log('SplitTransactionModal: split mark_ids:', newSplits.map(s => s.mark_id));
  console.log('SplitTransactionModal: markOptions count:', markOptions.value.length);
}, { deep: true });

watch(() => markOptions.value, (newOptions) => {
  console.log('SplitTransactionModal: markOptions changed, count:', newOptions.length);
  if (splits.value.length > 0) {
    console.log('SplitTransactionModal: checking split marks against new options:');
    splits.value.forEach((split, i) => {
      const found = newOptions.find(m => m.id === split.mark_id);
      console.log(`  Split ${i+1}: mark_id=${split.mark_id}, found=${Boolean(found)}, label=${found ? found.label : 'NOT FOUND'}`);
    });
  }
}, { deep: true, immediate: true });

// Additional debug for mark options
watch(() => markOptions.value, (newOptions) => {
  console.log('SplitTransactionModal: markOptions changed:', newOptions);
  if (newOptions.length > 0) {
    console.log('SplitTransactionModal: Sample markOptions:', newOptions.slice(0, 3));
  }
}, { immediate: true });

// Debug for specific mark search
watch(() => sortedMarks.value, (newMarks) => {
  console.log('SplitTransactionModal: sortedMarks changed, count:', newMarks.length);
  
  // Look for Laptop mark specifically
  const laptopMark = newMarks.find(m => m.id === '670f93c5-b940-4a06-a556-7c0f92a5cb86');
  if (laptopMark) {
    console.log('SplitTransactionModal: Found Laptop mark:', laptopMark);
  } else {
    console.warn('SplitTransactionModal: Laptop mark NOT found in sortedMarks');
  }
}, { immediate: true });
</script>
