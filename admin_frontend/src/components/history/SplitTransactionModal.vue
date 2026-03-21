<template>
  <BaseModal :isOpen="isOpen" @close="onClose" size="2xl">
    <template #title>
      <div class="flex items-center justify-between w-full">
        <div class="flex items-center gap-2">
          <div class="p-1 rounded-md" style="background: rgba(15, 118, 110, 0.10);">
            <i class="bi bi-diagram-3 text-sm" style="color: var(--color-primary);"></i>
          </div>
          <span class="text-theme font-bold tracking-tight text-sm">Split Transaction</span>
        </div>
        <div v-if="transaction" class="flex items-center gap-2 text-[10px]">
           <span class="text-muted font-semibold uppercase tracking-widest text-[9px]">Total</span>
           <span class="font-bold text-sm font-mono" :class="transaction.db_cr === 'CR' ? 'text-success' : 'text-danger'">
             {{ formatAmount(transaction.amount) }}
           </span>
        </div>
      </div>
    </template>

    <div v-if="transaction" class="space-y-4 px-6 py-4">
      <!-- Minimal Info Header -->
      <div class="bg-surface-muted border border-border p-3 rounded-2xl flex items-center gap-4 text-xs">
        <div class="flex items-center gap-1.5 min-w-0">
          <i class="bi bi-calendar3 text-muted"></i>
          <span class="font-bold text-theme whitespace-nowrap">{{ formatDate(transaction.txn_date) }}</span>
        </div>
        <div class="w-px h-3 bg-border"></div>
        <div class="flex items-center gap-1.5 min-w-0 flex-1">
          <i class="bi bi-card-text text-muted"></i>
          <span class="font-bold text-theme truncate" :title="transaction.description">{{ transaction.description }}</span>
        </div>
      </div>

      <!-- Allocation Progress Bar -->
      <div class="space-y-1.5">
        <div class="flex justify-between text-[10px]">
          <span class="font-bold text-muted uppercase tracking-widest">Allocation</span>
          <span class="font-bold font-mono" :class="Math.abs(remainingAmount) <= 0.01 ? 'text-success' : 'text-primary'">
             {{ formatAmount(allocatedAmount) }} / {{ formatAmount(transactionAmount) }}
          </span>
        </div>
        <div class="relative h-1.5 w-full bg-surface-muted rounded-full overflow-hidden flex shadow-inner">
           <div
              class="h-full transition-all duration-300 ease-in-out"
              :class="allocatedPercent > 100 ? 'bg-danger' : 'bg-primary'"
              :style="{ width: `${Math.min(allocatedPercent, 100)}%` }"
            ></div>
            <div
              v-if="allocatedPercent > 100"
              class="h-full bg-danger"
              :style="{ width: `${Math.min(allocatedPercent - 100, 100)}%` }"
            ></div>
        </div>
        <div class="flex justify-between items-center text-[10px]">
          <span :class="allocatedPercent > 100 ? 'text-danger font-bold' : 'text-primary font-bold'">{{ allocatedPercent.toFixed(0) }}%</span>
           <span v-if="Math.abs(remainingAmount) > 0.01" :class="remainingAmount > 0 ? 'text-warning' : 'text-danger'">
             {{ remainingAmount > 0 ? 'Rem:' : 'Over:' }} {{ formatAmount(Math.abs(remainingAmount)) }}
           </span>
           <span v-else class="text-success font-bold flex items-center gap-1">
             <i class="bi bi-check-circle-fill text-[9px]"></i> OK
           </span>
        </div>
      </div>

      <div class="space-y-3">
        <div class="flex items-center justify-between">
          <span class="text-[10px] font-bold text-muted uppercase tracking-widest">Splits</span>
          <button
            @click="addSplit"
            class="btn-ghost px-3 py-1.5 text-[10px] font-bold"
            style="color: var(--color-primary);"
          >
            <i class="bi bi-plus-circle mr-1"></i> Add
          </button>
        </div>

        <div v-if="splits.length === 0" class="py-6 border-2 border-dashed border-border rounded-2xl text-center">
          <p class="text-[10px] text-muted">No splits added</p>
        </div>

        <div class="space-y-1.5 max-h-[300px] overflow-y-auto pr-1 custom-scrollbar">
          <transition-group enter-active-class="transition duration-200" enter-from-class="opacity-0 -translate-y-2" leave-active-class="transition duration-150" leave-to-class="opacity-0 -translate-y-2">
            <div
              v-for="(split, index) in splits"
              :key="index"
              class="group surface-card border border-border hover:border-primary rounded-2xl p-3 shadow-sm transition-all flex items-center gap-4"
            >
               <!-- Badge -->
               <div class="w-6 h-6 rounded-full bg-surface-muted text-xs font-bold text-muted flex items-center justify-center shrink-0">
                 {{ index + 1 }}
               </div>

               <!-- Content Row -->
               <div class="flex-1 grid grid-cols-12 gap-4 items-center">
                 <!-- Mark Selector (takes up most space) -->
                 <div class="col-span-5">
                   <SearchableSelect
                     v-model="split.mark_id"
                     :options="markOptions"
                     placeholder="Select mark..."
                   />
                 </div>

                 <!-- Optional Notes -->
                 <div class="col-span-4">
                   <input
                     v-model="split.notes"
                     placeholder="Notes..."
                     class="w-full text-sm border border-border rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none bg-surface-muted focus:bg-surface transition-colors placeholder:text-muted"
                   >
                 </div>

                 <!-- Amount Input -->
                 <div class="col-span-3 relative group/amount">
                    <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <span class="text-muted text-xs font-medium">Rp</span>
                    </div>
                    <input
                      type="number"
                      step="0.01"
                      v-model.number="split.amount"
                      class="w-full pl-8 pr-3 py-2 bg-surface-muted focus:bg-surface border border-border rounded-lg text-xs font-mono font-bold text-right focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-colors"
                      placeholder="0"
                    >
                    <button
                      v-if="index === splits.length - 1 && remainingAmount > 0"
                      @click="fillRemainder(index)"
                      class="absolute -top-2.5 -right-2 w-5 h-5 rounded-full flex items-center justify-center text-xs shadow-sm opacity-0 group-hover/amount:opacity-100 transition-opacity"
                      :style="{ background: 'rgba(15, 118, 110, 0.10)', color: 'var(--color-primary)' }"
                      title="Fill Remainder"
                    >
                      <i class="bi bi-arrow-down-short"></i>
                    </button>
                 </div>
               </div>

               <!-- Delete Button -->
               <button @click="removeSplit(index)" class="w-8 h-8 rounded-lg flex items-center justify-center text-muted hover:text-danger hover:bg-danger/10 transition-colors shrink-0">
                 <i class="bi bi-trash-fill text-sm"></i>
               </button>
            </div>
          </transition-group>
        </div>
      </div>

      <!-- Compact Error -->
      <div v-if="splits.length > 0 && hasValidationError" class="rounded-2xl px-3 py-2 border text-xs flex items-center gap-2" style="background: rgba(185, 28, 28, 0.08); border-color: rgba(185, 28, 28, 0.18);">
         <i class="bi bi-exclamation-circle-fill" style="color: var(--color-danger);"></i>
         <span class="font-medium" style="color: var(--color-danger);">{{ validationMessage }}</span>
      </div>
    </div>

    <template #footer>
      <div class="flex items-center justify-between w-full">
         <span class="text-[10px] text-muted">
           {{ splits.length }} split{{ splits.length !== 1 ? 's' : '' }}
         </span>
         <div class="flex gap-2">
            <button @click="onClose" class="btn-secondary px-4 py-2 text-xs font-medium">Cancel</button>
            <button
               @click="saveSplits"
               :disabled="hasValidationError"
               class="btn-primary px-4 py-2 text-xs font-bold transition-all flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
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
import { ref, computed, watch } from 'vue';
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
    return [];
  }

  return sortedMarks.value.map(m => ({
    id: m.id,
    label: m.internal_report || m.personal_use || 'Unnamed Mark'
  }));
});

const toNumeric = (val) => {
  if (val === undefined || val === null || val === '') return 0;
  if (typeof val === 'number') return val;
  // Handle Indonesian formatting: dots as thousands, commas as decimals if string
  // and generic string numbers.
  const cleaned = String(val).replace(/\./g, '').replace(/,/g, '.');
  const parsed = parseFloat(cleaned);
  return isNaN(parsed) ? 0 : parsed;
};

const transactionAmount = computed(() => {
  if (!props.transaction) return 0;
  // Use toNumeric for safety
  return toNumeric(props.transaction.amount);
});

const allocatedAmount = computed(() => {
  return splits.value.reduce((sum, split) => sum + toNumeric(split.amount), 0);
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

  const remainingError = Math.abs(remainingAmount.value) > 0.01;
  const amountError = splits.value.some(s => s.amount === null || s.amount === undefined || s.amount === '');
  const markError = splits.value.some(s => !s.mark_id || s.mark_id === '' || s.mark_id === null || s.mark_id === undefined);

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
  console.log('[SplitTransactionModal] Adding split. Transaction amount:', transactionAmount.value);
  const remaining = transactionAmount.value - allocatedAmount.value;
  const defaultAmount = remaining > 0 ? remaining : 0;
  
  splits.value.push({
    mark_id: '',
    amount: defaultAmount > 0 ? Number(defaultAmount.toFixed(2)) : 0,
    notes: ''
  });
  console.log('[SplitTransactionModal] Splits now:', splits.value);
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
      splits.value = existingSplits.map((s) => ({
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
