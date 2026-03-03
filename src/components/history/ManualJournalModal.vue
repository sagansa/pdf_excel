<template>
  <BaseModal :isOpen="isOpen" @close="$emit('close')">
    <div class="bg-white rounded-2xl p-5 md:p-6 w-full max-w-5xl shadow-xl border border-gray-100 animate-fade-in mx-auto mt-8">
      <div class="flex items-start justify-between mb-5">
        <div>
          <h2 class="text-xl font-bold text-gray-900">Manual Journal</h2>
          <p class="text-xs text-gray-500 mt-1">Create balanced multi-line entries directly from Transactions.</p>
        </div>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-700 transition-colors p-1">
          <i class="bi bi-x-lg"></i>
        </button>
      </div>

      <form @submit.prevent="handleSubmit" class="space-y-5">
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div class="lg:col-span-2 bg-white rounded-2xl border border-gray-200 p-4 md:p-5">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label class="block text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-1.5">Date</label>
                <input
                  type="date"
                  v-model="header.txn_date"
                  required
                  class="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all outline-none text-sm"
                />
              </div>

              <div>
                <label class="block text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-1.5">Company</label>
                <select
                  v-model="header.company_id"
                  class="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all outline-none text-sm"
                >
                  <option value="">-- No Company --</option>
                  <option v-for="c in companies" :key="c.id" :value="c.id">{{ c.short_name || c.name }}</option>
                </select>
              </div>

              <div class="md:col-span-2">
                <label class="block text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-1.5">Journal Memo</label>
                <input
                  type="text"
                  v-model="header.description"
                  placeholder="e.g. Reklasifikasi biaya operasional"
                  required
                  class="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all outline-none text-sm"
                />
              </div>
            </div>
          </div>

          <div class="bg-gray-900 rounded-2xl p-4 text-white">
            <div class="text-[10px] text-gray-400 uppercase font-bold tracking-widest mb-4">Balance Summary</div>
            <div class="space-y-3">
              <div class="flex items-center justify-between">
                <span class="text-xs text-gray-300">Total Debits</span>
                <span class="text-sm font-mono font-bold text-sky-300">Rp {{ formatCurrency(totalDebits) }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-xs text-gray-300">Total Credits</span>
                <span class="text-sm font-mono font-bold text-amber-300">Rp {{ formatCurrency(totalCredits) }}</span>
              </div>
              <div class="pt-3 border-t border-gray-700 flex items-center justify-between">
                <span class="text-xs text-gray-300">Difference</span>
                <span class="text-lg font-mono font-black" :class="difference === 0 ? 'text-emerald-300' : 'text-rose-300'">
                  Rp {{ formatCurrency(difference) }}
                </span>
              </div>
              <div class="text-[10px] text-gray-400">
                {{ lines.length }} lines • {{ hasDebitLine ? 'Debit OK' : 'No debit line' }} • {{ hasCreditLine ? 'Credit OK' : 'No credit line' }}
              </div>
            </div>
          </div>
        </div>

        <!-- Lines -->
        <div class="space-y-3 bg-white rounded-2xl border border-gray-200 p-4 md:p-5">
          <div class="flex items-center justify-between">
            <label class="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Journal Lines</label>
            <button
              type="button"
              @click="addLine"
              class="text-xs font-bold text-indigo-600 hover:text-indigo-700 flex items-center gap-1 px-2 py-1 rounded-lg hover:bg-indigo-50 transition-colors"
            >
              <i class="bi bi-plus-lg"></i> Add Line
            </button>
          </div>

          <div class="hidden md:grid grid-cols-[60px_130px_1fr_180px_1fr_44px] gap-2 text-[10px] font-bold uppercase tracking-wider text-gray-400 px-1">
            <div>Line</div>
            <div>Side</div>
            <div>COA</div>
            <div>Amount</div>
            <div>Line Memo</div>
            <div></div>
          </div>

          <div class="space-y-2 max-h-[340px] overflow-y-auto pr-1">
            <div v-for="(line, index) in lines" :key="index"
              class="grid grid-cols-1 md:grid-cols-[60px_130px_1fr_180px_1fr_44px] gap-2 items-start p-3 bg-gray-50 border border-gray-100 rounded-xl group hover:border-indigo-200 transition-all"
            >
              <div class="text-xs md:text-[11px] font-bold text-gray-500 py-1.5">#{{ index + 1 }}</div>

              <!-- Side -->
              <div>
                <select
                  v-model="line.side"
                  class="w-full px-2 py-1.5 bg-white border border-gray-200 rounded-lg focus:border-indigo-500 transition-all outline-none text-xs font-bold"
                  :class="line.side === 'DEBIT' ? 'text-sky-700' : 'text-amber-700'"
                >
                  <option value="DEBIT">DEBIT (Dr)</option>
                  <option value="CREDIT">CREDIT (Cr)</option>
                </select>
              </div>

              <!-- COA -->
              <div>
                <select
                  v-model="line.coa_id"
                  required
                  class="w-full px-2 py-1.5 bg-white border border-gray-200 rounded-lg focus:border-indigo-500 transition-all outline-none text-xs"
                >
                  <option value="">Select account...</option>
                  <optgroup v-for="group in coaOptionsGrouped" :key="group.category" :label="group.category">
                    <option v-for="coa in group.items" :key="coa.id" :value="coa.id">
                      {{ coa.code }} - {{ coa.name }}
                    </option>
                  </optgroup>
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
                  class="w-full pl-7 pr-2 py-1.5 bg-white border border-gray-200 rounded-lg focus:border-indigo-500 transition-all outline-none text-xs font-semibold text-right"
                />
              </div>

              <div>
                <input
                  type="text"
                  v-model="line.description"
                  placeholder="Optional line memo"
                  class="w-full px-2 py-1.5 bg-white border border-gray-200 rounded-lg focus:border-indigo-500 transition-all outline-none text-xs"
                />
              </div>

              <!-- Remove -->
              <button
                type="button"
                @click="removeLine(index)"
                :disabled="lines.length <= 2"
                class="mt-1.5 text-gray-300 hover:text-red-500 disabled:opacity-20 disabled:cursor-not-allowed transition-colors"
                title="Remove line"
              >
                <i class="bi bi-trash"></i>
              </button>
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
         lines.value.every(l => l.coa_id && l.amount > 0) &&
         hasDebitLine.value &&
         hasCreditLine.value;
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

const hasDebitLine = computed(() => lines.value.some(l => l.side === 'DEBIT' && Number(l.amount) > 0));
const hasCreditLine = computed(() => lines.value.some(l => l.side === 'CREDIT' && Number(l.amount) > 0));

const formatCurrency = (val) => {
  return new Intl.NumberFormat('id-ID').format(Math.abs(val));
};

const handleSubmit = async () => {
  if (!hasDebitLine.value || !hasCreditLine.value) {
    error.value = "Journal must contain at least one debit line and one credit line.";
    return;
  }

  if (difference.value !== 0) {
    error.value = "Journal must be balanced (Total Debits must equal Total Credits).";
    return;
  }

  isLoading.value = true;
  error.value = null;

  try {
    const payload = {
      ...header,
      lines: lines.value.map(line => ({
        ...line,
        description: (line.description || '').trim() || null
      }))
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
