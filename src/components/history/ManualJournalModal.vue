<template>
  <BaseModal :isOpen="isOpen" @close="$emit('close')">
    <div class="bg-white rounded-2xl p-6 w-full max-w-2xl shadow-xl border border-gray-100 animate-fade-in mx-auto mt-10">
      <div class="flex items-center justify-between mb-6">
        <div>
          <h2 class="text-xl font-bold text-gray-900">Manual Journal Entry</h2>
          <p class="text-sm text-gray-500 mt-1">Multi-line double-entry accounting</p>
        </div>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 transition-colors">
          <i class="bi bi-x-lg"></i>
        </button>
      </div>

      <form @submit.prevent="handleSubmit" class="space-y-6">
        <div class="grid grid-cols-2 gap-4 bg-gray-50/50 p-4 rounded-2xl border border-gray-100">
          <!-- Date -->
          <div>
            <label class="block text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-1.5">Date</label>
            <input
              type="date"
              v-model="header.txn_date"
              required
              class="w-full px-3 py-2 bg-white border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all outline-none text-sm"
            />
          </div>

          <!-- Company -->
          <div>
            <label class="block text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-1.5">Company</label>
            <select
              v-model="header.company_id"
              class="w-full px-3 py-2 bg-white border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all outline-none text-sm"
            >
              <option value="">-- No Company --</option>
              <option v-for="c in companies" :key="c.id" :value="c.id">{{ c.short_name || c.name }}</option>
            </select>
          </div>

          <!-- Description (Header) -->
          <div class="col-span-2">
            <label class="block text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-1.5">Journal Memo</label>
            <input
              type="text"
              v-model="header.description"
              placeholder="e.g. Accrue PPh Badan 2024"
              required
              class="w-full px-3 py-2 bg-white border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all outline-none text-sm"
            />
          </div>
        </div>

        <!-- Lines -->
        <div class="space-y-3">
          <div class="flex items-center justify-between">
            <label class="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Journal Lines</label>
            <button
              type="button"
              @click="addLine"
              class="text-xs font-bold text-indigo-600 hover:text-indigo-700 flex items-center gap-1"
            >
              <i class="bi bi-plus-lg"></i> Add Line
            </button>
          </div>

          <div class="space-y-2">
            <div v-for="(line, index) in lines" :key="index"
              class="grid grid-cols-[1fr_120px_160px_auto] gap-2 items-start p-3 bg-white border border-gray-100 rounded-xl shadow-sm group hover:border-indigo-200 transition-all"
            >
              <!-- COA -->
              <div>
                <select
                  v-model="line.coa_id"
                  required
                  class="w-full px-2 py-1.5 bg-gray-50 border border-transparent rounded-lg focus:bg-white focus:border-indigo-500 transition-all outline-none text-xs"
                >
                  <option value="">Select account...</option>
                  <optgroup v-for="group in coaOptionsGrouped" :key="group.category" :label="group.category">
                    <option v-for="coa in group.items" :key="coa.id" :value="coa.id">
                      {{ coa.code }} - {{ coa.name }}
                    </option>
                  </optgroup>
                </select>
              </div>

              <!-- Side -->
              <div>
                <select
                  v-model="line.side"
                  class="w-full px-2 py-1.5 bg-gray-50 border border-transparent rounded-lg focus:bg-white focus:border-indigo-500 transition-all outline-none text-xs font-bold"
                  :class="line.side === 'DEBIT' ? 'text-blue-600' : 'text-orange-600'"
                >
                  <option value="DEBIT">DEBIT (Dr)</option>
                  <option value="CREDIT">CREDIT (Cr)</option>
                </select>
              </div>

              <!-- Amount -->
              <div class="relative">
                <span class="absolute left-2 top-1/2 -translate-y-1/2 text-[10px] text-gray-400 font-bold">Rp</span>
                <input
                  type="number"
                  v-model.number="line.amount"
                  placeholder="0"
                  required
                  class="w-full pl-7 pr-2 py-1.5 bg-gray-50 border border-transparent rounded-lg focus:bg-white focus:border-indigo-500 transition-all outline-none text-xs font-semibold text-right"
                />
              </div>

              <!-- Remove -->
              <button
                type="button"
                @click="removeLine(index)"
                :disabled="lines.length <= 2"
                class="mt-1.5 text-gray-300 hover:text-red-500 disabled:opacity-0 transition-colors"
                title="Remove line"
              >
                <i class="bi bi-trash"></i>
              </button>
            </div>
          </div>
        </div>

        <!-- Summary -->
        <div class="bg-gray-900 rounded-2xl p-4 text-white flex items-center justify-between shadow-inner">
          <div class="flex gap-6">
            <div>
              <div class="text-[10px] text-gray-400 uppercase font-bold tracking-widest mb-1">Total Debits</div>
              <div class="text-sm font-mono font-bold text-blue-400">Rp {{ formatCurrency(totalDebits) }}</div>
            </div>
            <div>
              <div class="text-[10px] text-gray-400 uppercase font-bold tracking-widest mb-1">Total Credits</div>
              <div class="text-sm font-mono font-bold text-orange-400">Rp {{ formatCurrency(totalCredits) }}</div>
            </div>
          </div>
          <div class="text-right">
            <div class="text-[10px] text-gray-400 uppercase font-bold tracking-widest mb-1">Difference</div>
            <div
              class="text-lg font-mono font-black"
              :class="difference === 0 ? 'text-green-400' : 'text-red-400'"
            >
              Rp {{ formatCurrency(difference) }}
            </div>
          </div>
        </div>

        <!-- Errors -->
        <div v-if="error" class="p-3 bg-red-50 border border-red-100 rounded-xl text-red-600 text-xs flex items-center gap-2">
          <i class="bi bi-exclamation-circle-fill"></i>
          {{ error }}
        </div>

        <!-- Actions -->
        <div class="flex gap-3 pt-2">
          <button
            type="button"
            @click="$emit('close')"
            class="flex-1 px-4 py-3 border border-gray-200 rounded-xl text-sm font-semibold text-gray-600 hover:bg-gray-50 transition-colors"
            :disabled="isLoading"
          >
            Cancel
          </button>
          <button
            type="submit"
            :disabled="isLoading || difference !== 0 || !isFormValid"
            class="flex-1 px-4 py-3 bg-indigo-600 text-white rounded-xl text-sm font-bold shadow-lg shadow-indigo-200 hover:bg-indigo-700 hover:shadow-indigo-300 transition-all disabled:opacity-50 disabled:grayscale flex items-center justify-center gap-2"
          >
            <span v-if="isLoading" class="spinner-border spinner-border-sm"></span>
            <i v-else class="bi bi-journal-plus"></i>
            {{ isLoading ? 'Posting...' : 'Post Journal' }}
          </button>
        </div>
      </form>
    </div>
  </BaseModal>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue';
import BaseModal from '../ui/BaseModal.vue';
import { historyApi } from '../../api';

const props = defineProps({
  isOpen: Boolean,
  companies: Array,
  coaList: Array
});

const emit = defineEmits(['close', 'saved']);

const isLoading = ref(false);
const error = ref(null);

const header = reactive({
  txn_date: new Date().toISOString().split('T')[0],
  description: '',
  company_id: ''
});

const lines = ref([
  { coa_id: '', side: 'DEBIT', amount: null, description: '' },
  { coa_id: '', side: 'CREDIT', amount: null, description: '' }
]);

const coaOptionsGrouped = computed(() => {
  if (!props.coaList) return [];
  const categories = ['ASSET', 'LIABILITY', 'EQUITY', 'REVENUE', 'EXPENSE'];
  return categories.map(cat => ({
    category: cat,
    items: props.coaList.filter(c => c.category === cat)
  })).filter(g => g.items.length > 0);
});

const isFormValid = computed(() => {
  return header.description && 
         header.txn_date && 
         lines.value.length >= 2 && 
         lines.value.every(l => l.coa_id && l.amount > 0);
});

const addLine = () => {
  const lastLine = lines.value[lines.value.length - 1];
  lines.value.push({
    coa_id: '',
    side: lastLine.side === 'DEBIT' ? 'CREDIT' : 'DEBIT',
    amount: null,
    description: ''
  });
};

const removeLine = (index) => {
  if (lines.value.length > 2) {
    lines.value.splice(index, 1);
  }
};

const totalDebits = computed(() => {
  return lines.value
    .filter(l => l.side === 'DEBIT')
    .reduce((sum, l) => sum + (Number(l.amount) || 0), 0);
});

const totalCredits = computed(() => {
  return lines.value
    .filter(l => l.side === 'CREDIT')
    .reduce((sum, l) => sum + (Number(l.amount) || 0), 0);
});

const difference = computed(() => {
  const diff = totalDebits.value - totalCredits.value;
  return Math.round(diff * 100) / 100;
});

const formatCurrency = (val) => {
  return new Intl.NumberFormat('id-ID').format(Math.abs(val));
};

const handleSubmit = async () => {
  if (difference.value !== 0) {
    error.value = "Journal must be balanced (Total Debits must equal Total Credits).";
    return;
  }

  isLoading.value = true;
  error.value = null;

  try {
    const payload = {
      ...header,
      lines: lines.value
    };
    await historyApi.createManualTransaction(payload);
    emit('saved');
    emit('close');
  } catch (e) {
    error.value = e.response?.data?.error || "Failed to create manual transaction";
    console.error(e);
  } finally {
    isLoading.value = false;
  }
};

watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    // Reset form
    header.description = '';
    header.company_id = '';
    header.txn_date = new Date().toISOString().split('T')[0];
    lines.value = [
      { coa_id: '', side: 'DEBIT', amount: null, description: '' },
      { coa_id: '', side: 'CREDIT', amount: null, description: '' }
    ];
    error.value = null;
  }
});
</script>

<style scoped>
.animate-fade-in { animation: fadeIn 0.3s ease-out forwards; }
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

input::-webkit-outer-spin-button,
input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
</style>
