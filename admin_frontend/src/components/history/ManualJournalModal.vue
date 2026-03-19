<template>
  <BaseModal :isOpen="isOpen" @close="$emit('close')" size="2xl">
    <template #title>
      <div class="flex items-center gap-2.5">
        <div class="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <i class="bi bi-journal-text text-lg"></i>
        </div>
        <div>
          <h3 class="text-base font-bold">{{ editId ? 'Edit Manual Journal' : 'Manual Journal' }}</h3>
          <p class="text-[10px] text-muted font-medium uppercase tracking-wider">
            {{ editId ? 'Modify existing journal entry' : 'Create balanced multi-line entries' }}
          </p>
        </div>
      </div>
    </template>

    <div class="p-5 space-y-5">
      <form @submit.prevent="handleSubmit" class="space-y-5">
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-5">
          <!-- Header Info -->
          <div class="lg:col-span-2 p-4 rounded-xl border border-border bg-surface-muted/30 space-y-4">
            <div class="flex items-center gap-2 mb-1">
              <span class="text-[10px] font-black text-primary uppercase tracking-tighter bg-primary/10 px-1.5 py-0.5 rounded">Journal Info</span>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div class="space-y-1.5">
                <label class="block text-[10px] font-bold text-muted uppercase tracking-wider ml-1">Transaction Date</label>
                <TextInput
                  v-model="header.txn_date"
                  type="date"
                  size="sm"
                  required
                />
              </div>

              <div class="space-y-1.5">
                <label class="block text-[10px] font-bold text-muted uppercase tracking-wider ml-1">Company</label>
                <SelectInput
                  v-model="header.company_id"
                  :options="companyOptions"
                  placeholder="-- No Company --"
                  size="sm"
                />
              </div>



              <div class="md:col-span-2 space-y-1.5">
                <label class="block text-[10px] font-bold text-muted uppercase tracking-wider ml-1">Journal Memo</label>
                <TextInput
                  v-model="header.description"
                  placeholder="e.g. Reklasifikasi biaya operasional"
                  size="sm"
                  required
                />
              </div>
            </div>
          </div>

          <!-- Summary Box -->
          <div class="rounded-xl p-4 bg-gray-900 text-white shadow-lg space-y-3">
            <div class="flex items-center gap-2 text-[10px] text-gray-400 uppercase font-bold tracking-widest">
              <i class="bi bi-lightning-charge-fill text-yellow-400"></i>
              Balance
            </div>
            
            <div class="space-y-2">
              <div class="flex items-center justify-between">
                <span class="text-[11px] text-gray-300">Debits</span>
                <span class="text-xs font-mono font-bold text-sky-300">Rp {{ formatCurrency(totalDebits) }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-[11px] text-gray-300">Credits</span>
                <span class="text-xs font-mono font-bold text-amber-300">Rp {{ formatCurrency(totalCredits) }}</span>
              </div>
              
              <div class="pt-2 border-t border-gray-700">
                <div class="flex items-center justify-between">
                  <span class="text-[11px] text-gray-300">Diff</span>
                  <span class="text-base font-mono font-black" :class="difference === 0 ? 'text-emerald-400' : 'text-rose-400'">
                    Rp {{ formatCurrency(difference) }}
                  </span>
                </div>
                <div class="text-[9px] font-bold uppercase tracking-tighter text-right" :class="difference === 0 ? 'text-emerald-400/70' : 'text-rose-400/70'">
                    {{ difference === 0 ? 'Balanced' : 'Out of Balance' }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Lines -->
        <div class="p-4 rounded-xl border border-border bg-surface overflow-hidden">
            <div class="flex items-center gap-4">
              <h4 class="text-[11px] font-bold text-theme uppercase tracking-wider flex items-center gap-2">
                <i class="bi bi-list-columns-reverse text-primary"></i>
                Journal Lines
              </h4>
              <SegmentedControl
                v-model="activeReportType"
                :options="reportTypeOptions"
                variant="primary"
                class="scale-90"
              />
            </div>
            <button
              type="button"
              @click="addLine"
              class="text-[11px] font-bold text-primary hover:bg-primary/10 px-2 py-1 rounded-lg transition-all flex items-center gap-1.5"
            >
              <i class="bi bi-plus-circle-fill"></i> Add Line
            </button>

          <!-- Header Labels -->
          <div class="hidden md:grid grid-cols-[30px_110px_1fr_150px_1fr_60px_36px] gap-2 text-[9px] font-bold uppercase tracking-wider text-muted px-2 mb-1">
            <div>#</div>
            <div>Side</div>
            <div>Account (COA)</div>
            <div class="text-right">Amount</div>
            <div>Line Memo</div>
            <div class="text-center">Link</div>
            <div></div>
          </div>

          <div class="space-y-1.5 max-h-[300px] overflow-y-auto pr-1 custom-scrollbar">
            <div v-for="(line, index) in lines" :key="index"
              class="grid grid-cols-1 md:grid-cols-[30px_110px_1fr_150px_1fr_60px_36px] gap-2 items-center p-2 rounded-lg border border-border bg-surface-muted/20 group hover:border-primary/20 transition-all shadow-sm shadow-black/5"
              :class="activeLineIndex === index ? 'ring-1 ring-primary border-primary bg-primary/5' : ''"
            >
              <div class="text-[10px] font-bold text-muted flex items-center justify-center md:justify-start">
                {{ index + 1 }}
              </div>

              <!-- Side -->
              <div class="relative">
                <select
                  v-model="line.side"
                  class="w-full px-2 py-1.5 bg-surface border border-border rounded-lg focus:ring-1 focus:ring-primary focus:border-primary transition-all outline-none text-[10px] font-bold appearance-none pr-6 cursor-pointer"
                  :class="line.side === 'DEBIT' ? 'text-sky-500' : 'text-amber-500'"
                >
                  <option value="DEBIT">DEBIT (Dr)</option>
                  <option value="CREDIT">CREDIT (Cr)</option>
                </select>
                <i class="bi bi-chevron-down absolute right-2 top-1/2 -translate-y-1/2 text-[9px] pointer-events-none text-muted"></i>
              </div>

              <div class="min-w-0">
                <SearchableSelect
                   :model-value="activeReportType === 'real' ? line.coa_id : line.coa_id_coretax"
                   :options="coaSelectOptions"
                   placeholder="Account..."
                   @update:modelValue="(val) => coaChanged(line, val)"
                />
              </div>

              <!-- Amount -->
              <div>
                <TextInput
                  v-model.number="line.amount"
                  placeholder="0"
                  type="number"
                  :leadingLabel="true"
                  size="sm"
                  class="text-right font-mono font-bold text-[11px]"
                >
                  <template #leading>
                    <span class="text-[9px] font-bold">Rp</span>
                  </template>
                </TextInput>
              </div>

              <div>
                <input
                  type="text"
                  v-model="line.description"
                  placeholder="Memo..."
                  class="w-full px-2 py-1.5 bg-surface border border-border rounded-lg focus:ring-1 focus:ring-primary/30 focus:border-primary transition-all outline-none text-[10px] text-theme placeholder:text-muted/50"
                />
              </div>

              <!-- Link Button -->
              <div class="flex justify-center">
                <button
                  type="button"
                  @click="toggleLineLink(index)"
                  class="relative w-8 h-8 flex items-center justify-center rounded-lg transition-all"
                  :class="line.linked_transactions?.length > 0 
                    ? 'text-primary bg-primary/10 hover:bg-primary/20' 
                    : 'text-muted hover:text-primary hover:bg-primary/10'"
                  :title="line.linked_transactions?.length > 0 ? `${line.linked_transactions.length} linked` : 'Link transactions'"
                >
                  <i class="bi bi-link-45deg text-lg"></i>
                  <span v-if="line.linked_transactions?.length > 0" 
                    class="absolute -top-1 -right-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-1 text-[8px] font-black text-white shadow-sm ring-1 ring-surface"
                  >
                    {{ line.linked_transactions.length }}
                  </span>
                </button>
              </div>

              <!-- Remove -->
              <div class="flex justify-center">
                <button
                  type="button"
                  @click="removeLine(index)"
                  :disabled="lines.length <= 2"
                  class="w-8 h-8 flex items-center justify-center rounded-lg text-muted hover:text-red-500 hover:bg-red-500/10 disabled:opacity-20 disabled:cursor-not-allowed transition-all"
                  title="Remove line"
                >
                  <i class="bi bi-trash-fill text-xs"></i>
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Link to Existing Transactions -->
        <div v-if="showLinkPanel" class="p-4 rounded-xl border border-primary/20 bg-surface shadow-lg ring-1 ring-primary/5">
          <div class="flex items-center justify-between mb-3 pb-2 border-b border-border/50">
            <h4 class="text-[11px] font-bold text-theme uppercase tracking-wider flex items-center gap-2">
              <i class="bi bi-link-45deg text-primary text-base"></i>
              Linking for Line #{{ activeLineIndex + 1 }}
              <span v-if="lines[activeLineIndex]?.linked_transactions?.length > 0" class="bg-primary/10 text-primary text-[9px] font-black px-1.5 py-0.5 rounded-full">
                {{ lines[activeLineIndex].linked_transactions.length }} linked
              </span>
            </h4>
            <button
              type="button"
              @click="showLinkPanel = false; activeLineIndex = null"
              class="text-muted hover:text-theme transition-colors p-1"
            >
              <i class="bi bi-x-lg text-xs"></i>
            </button>
          </div>

          <!-- Linked chips -->
          <div v-if="lines[activeLineIndex]?.linked_transactions?.length > 0" class="flex flex-wrap gap-1.5 mb-4 p-2 rounded-lg bg-surface-muted/30 border border-border/50">
            <div
              v-for="txn in lines[activeLineIndex].linked_transactions"
              :key="txn.id"
              class="flex items-center gap-1.5 bg-primary/10 border border-primary/20 text-primary text-[10px] font-semibold px-2 py-1 rounded-lg"
            >
              <i class="bi bi-paperclip text-[9px]"></i>
              <span class="max-w-[200px] truncate" :title="txn.description">
                {{ formatDate(txn.txn_date) }} — {{ txn.description || '(no desc)' }}
              </span>
              <span class="font-mono text-[9px] text-primary/70">Rp {{ formatCurrency(txn.amount) }}</span>
              <button
                type="button"
                @click="unlinkTransaction(txn.id, activeLineIndex)"
                class="ml-1 text-primary/60 hover:text-red-500 transition-colors"
              >
                <i class="bi bi-x text-xs"></i>
              </button>
            </div>
          </div>
          <p v-else class="text-[10px] text-muted italic mb-4 px-2">
            No transactions linked to this line yet. Search and add below.
          </p>

          <!-- Search panel -->
          <transition
            enter-active-class="transition duration-200 ease-out"
            enter-from-class="opacity-0 -translate-y-2"
            enter-to-class="opacity-100 translate-y-0"
          >
            <div v-if="showLinkPanel" class="space-y-3 mt-2 pt-3 border-t border-border/50">
              <div class="grid grid-cols-1 md:grid-cols-3 gap-2">
                <input
                  type="text"
                  v-model="linkSearch.query"
                  @input="debouncedSearch"
                  placeholder="Search description..."
                  class="px-2.5 py-1.5 bg-surface border border-border rounded-lg text-[10px] text-theme focus:ring-1 focus:ring-primary/30 focus:border-primary outline-none placeholder:text-muted/50"
                />
                <input
                  type="date"
                  v-model="linkSearch.start_date"
                  @change="searchLinkable"
                  class="px-2.5 py-1.5 bg-surface border border-border rounded-lg text-[10px] text-theme focus:ring-1 focus:ring-primary/30 focus:border-primary outline-none"
                />
                <input
                  type="date"
                  v-model="linkSearch.end_date"
                  @change="searchLinkable"
                  class="px-2.5 py-1.5 bg-surface border border-border rounded-lg text-[10px] text-theme focus:ring-1 focus:ring-primary/30 focus:border-primary outline-none"
                />
              </div>

              <!-- Results -->
              <div v-if="linkResults.length > 0" class="space-y-1 max-h-[200px] overflow-y-auto pr-1 custom-scrollbar">
                <div
                  v-for="txn in linkResults"
                  :key="txn.id"
                  class="grid grid-cols-[1fr_auto_auto] gap-2 items-center px-3 py-2 rounded-lg border border-border hover:border-primary/30 hover:bg-primary/5 cursor-pointer transition-all group"
                  @click="linkTransaction(txn)"
                >
                  <div class="min-w-0">
                    <p class="text-[10px] font-semibold text-theme truncate">{{ txn.description || '(no desc)' }}</p>
                    <p class="text-[9px] text-muted">
                      {{ formatDate(txn.txn_date) }}
                      <span v-if="txn.company_name" class="ml-1">· {{ txn.company_name }}</span>
                      <span v-if="txn.bank_code" class="ml-1 font-bold">· {{ txn.bank_code }}</span>
                    </p>
                  </div>
                  <span class="text-[10px] font-mono font-bold" :class="txn.db_cr === 'DB' ? 'text-sky-500' : 'text-amber-500'">
                    {{ txn.db_cr === 'DB' ? 'Dr' : 'Cr' }} {{ formatCurrency(txn.amount) }}
                  </span>
                  <span class="text-[9px] font-bold text-primary opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1">
                    <i class="bi bi-plus-circle"></i> Link
                  </span>
                </div>
              </div>
              <p v-else-if="isSearching" class="text-[10px] text-muted text-center py-4">
                <i class="bi bi-arrow-repeat animate-spin mr-1"></i> Searching...
              </p>
              <p v-else-if="linkSearchDone" class="text-[10px] text-muted text-center py-3">
                No transactions found.
              </p>
              <p v-else class="text-[10px] text-muted text-center py-3">
                Enter a keyword or date range to search.
              </p>
            </div>
          </transition>
        </div>

        <!-- Errors -->
        <transition enter-active-class="transition duration-200 ease-out" enter-from-class="opacity-0 -translate-y-2" enter-to-class="opacity-100 translate-y-0">
          <div v-if="error" class="p-4 rounded-xl border border-red-500/20 bg-red-500/5 text-red-500 text-xs font-medium flex items-center gap-3">
            <div class="w-6 h-6 rounded-lg bg-red-500/10 flex items-center justify-center flex-shrink-0">
              <i class="bi bi-exclamation-triangle-fill"></i>
            </div>
            {{ error }}
          </div>
        </transition>

        <!-- Actions -->
        <div class="flex gap-4 pt-4 border-t border-border/50">
          <button
            type="button"
            @click="$emit('close')"
            class="flex-1 btn-secondary py-3 text-base"
            :disabled="isLoading"
          >
            Discard Changes
          </button>
          <button
            type="submit"
            :disabled="isLoading || difference !== 0 || !isFormValid"
            class="flex-1 btn-primary py-3 text-base shadow-lg shadow-primary/20"
          >
            <div class="flex items-center justify-center gap-2">
              <span v-if="isLoading" class="spinner-border w-5 h-5"></span>
              <template v-else>
                <i class="bi bi-cloud-check-fill text-lg"></i>
                <span>{{ editId ? 'Update Journal Entry' : 'Post Journal Entry' }}</span>
              </template>
            </div>
          </button>
        </div>
      </form>
    </div>
  </BaseModal>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue';
import BaseModal from '../ui/BaseModal.vue';
import TextInput from '../ui/TextInput.vue';
import SelectInput from '../ui/SelectInput.vue';
import SearchableSelect from '../ui/SearchableSelect.vue';
import SegmentedControl from '../ui/SegmentedControl.vue';
import { historyApi } from '../../api';

const props = defineProps({
  isOpen: Boolean,
  editId: {
    type: String,
    default: null
  },
  companies: {
    type: Array,
    default: () => []
  },
  coaList: {
    type: Array,
    default: () => []
  }
});

const emit = defineEmits(['close', 'saved']);

const isLoading = ref(false);
const error = ref(null);
const activeReportType = ref('real');
const reportTypeOptions = [
  { label: 'Real', value: 'real' },
  { label: 'Coretax', value: 'coretax' }
];

const header = reactive({
  txn_date: new Date().toISOString().split('T')[0],
  description: '',
  company_id: '',
});

const lines = ref([
  { coa_id: '', coa_id_coretax: '', side: 'DEBIT', amount: null, description: '' },
  { coa_id: '', coa_id_coretax: '', side: 'CREDIT', amount: null, description: '' }
]);

const coaChanged = (line, val) => {
  if (activeReportType.value === 'real') {
    line.coa_id = val;
    if (!line.coa_id_coretax || line.coa_id_coretax === '') {
      line.coa_id_coretax = val;
    }
  } else {
    line.coa_id_coretax = val;
    if (!line.coa_id || line.coa_id === '') {
      line.coa_id = val;
    }
  }
};

// --- Link feature state ---
const showLinkPanel = ref(false);
const activeLineIndex = ref(null); // NEW: Track which line we are linking for
const linkResults = ref([]);
const isSearching = ref(false);
const linkSearchDone = ref(false);
const linkSearch = reactive({
  query: '',
  start_date: '',
  end_date: ''
});

let searchTimer = null;
const debouncedSearch = () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(searchLinkable, 400);
};

const searchLinkable = async () => {
  if (!linkSearch.query && !linkSearch.start_date && !linkSearch.end_date) {
    linkResults.value = [];
    linkSearchDone.value = false;
    return;
  }

  isSearching.value = true;
  linkSearchDone.value = false;
  
  // Exclude IDs already linked to ANY line to avoid duplicates in search (optional)
  const linkedIds = new Set();
  lines.value.forEach(l => {
    (l.linked_transactions || []).forEach(lt => linkedIds.add(lt.id));
  });

  try {
    const params = {};
    if (header.company_id) params.company_id = header.company_id;
    if (linkSearch.query) params.search = linkSearch.query;
    if (linkSearch.start_date) params.start_date = linkSearch.start_date;
    if (linkSearch.end_date) params.end_date = linkSearch.end_date;

    const res = await historyApi.getLinkableTransactions(params);
    linkResults.value = (res.data.transactions || []).filter(t => !linkedIds.has(t.id));
  } catch (e) {
    console.error('Failed to search linkable transactions', e);
    linkResults.value = [];
  } finally {
    isSearching.value = false;
    linkSearchDone.value = true;
  }
};

const linkTransaction = (txn) => {
  if (activeLineIndex.value === null) return;
  const line = lines.value[activeLineIndex.value];
  if (!line.linked_transactions) line.linked_transactions = [];
  
  if (!line.linked_transactions.find(t => t.id === txn.id)) {
    line.linked_transactions.push(txn);
    // Remove from results
    linkResults.value = linkResults.value.filter(t => t.id !== txn.id);
  }
};

const unlinkTransaction = (txnId, lineIndex) => {
  const targetIndex = lineIndex !== undefined ? lineIndex : activeLineIndex.value;
  if (targetIndex === null) return;
  
  const line = lines.value[targetIndex];
  if (line && line.linked_transactions) {
    line.linked_transactions = line.linked_transactions.filter(t => t.id !== txnId);
  }
};

const toggleLineLink = (index) => {
  if (activeLineIndex.value === index) {
      activeLineIndex.value = null;
      showLinkPanel.value = false;
  } else {
      activeLineIndex.value = index;
      showLinkPanel.value = true;
      // Maybe trigger search if query exists
      if (linkSearch.query || linkSearch.start_date || linkSearch.end_date) {
          searchLinkable();
      }
  }
};
// --- End link feature ---

const companyOptions = computed(() => {
  return props.companies.map(c => ({
    id: c.id,
    label: c.name
  }));
});

const coaSelectOptions = computed(() => {
  if (!props.coaList) return [];
  const categories = ['ASSET', 'LIABILITY', 'EQUITY', 'REVENUE', 'EXPENSE'];
  const options = [];
  
  categories.forEach(cat => {
    const items = props.coaList.filter(c => c.category === cat);
    if (items.length > 0) {
      options.push({ label: cat, type: 'separator' });
      items.forEach(coa => {
        options.push({
          id: coa.id,
          label: `${coa.code} - ${coa.name}`
        });
      });
    }
  });
  
  return options;
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
    coa_id_coretax: '',
    side: lastLine.side === 'DEBIT' ? 'CREDIT' : 'DEBIT',
    amount: null,
    description: '',
    linked_transactions: [] // NEW
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

const formatDate = (d) => {
  if (!d) return '';
  return new Date(d).toLocaleDateString('id-ID', { day: '2-digit', month: 'short', year: 'numeric' });
};

const fetchJournalData = async (id) => {
  isLoading.value = true;
  error.value = null;
  try {
    const res = await historyApi.getManualJournal(id);
    const data = res.data;
    
    // Fill Header
    header.txn_date = data.header.txn_date ? data.header.txn_date.substring(0, 10) : '';
    header.description = data.header.description;
    header.company_id = data.header.company_id || '';
    
    // Fill Lines
    lines.value = data.lines.map(l => ({
      coa_id: l.coa_id || '',
      coa_id_coretax: l.coa_id_coretax || '',
      side: l.side,
      amount: l.amount,
      description: l.description || '',
      linked_transactions: l.linked_transactions || [] // NEW: Populate per-line links
    }));
    
    // Fill Links (Legacy support for journal-level links if any)
    // linkedTransactions.value = data.linked_transactions || [];
    
  } catch (e) {
    error.value = "Failed to load journal data for editing.";
    console.error(e);
  } finally {
    isLoading.value = false;
  }
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
        description: (line.description || '').trim() || null,
        linked_transaction_ids: (line.linked_transactions || []).map(lt => lt.id) // NEW: Send per-line IDs
      })),
      linked_transaction_ids: [] // Clear header-level links on save if redirecting to lines
    };
    
    if (props.editId) {
      await historyApi.updateManualTransaction(props.editId, payload);
    } else {
      await historyApi.createManualTransaction(payload);
    }
    
    emit('saved');
    emit('close');
  } catch (e) {
    error.value = e.response?.data?.error || `Failed to ${props.editId ? 'update' : 'create'} manual transaction`;
    console.error(e);
  } finally {
    isLoading.value = false;
  }
};

const resetForm = () => {
  header.description = '';
  header.company_id = '';
  header.txn_date = new Date().toISOString().split('T')[0];
  activeReportType.value = 'real';
  lines.value = [
    { coa_id: '', coa_id_coretax: '', side: 'DEBIT', amount: null, description: '', linked_transactions: [] },
    { coa_id: '', coa_id_coretax: '', side: 'CREDIT', amount: null, description: '', linked_transactions: [] }
  ];
  activeLineIndex.value = null; // NEW
  linkResults.value = [];
  linkSearch.query = '';
  linkSearch.start_date = '';
  linkSearch.end_date = '';
  showLinkPanel.value = false;
  linkSearchDone.value = false;
  error.value = null;
};

watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    resetForm();
    if (props.editId) {
      fetchJournalData(props.editId);
    }
  }
});

watch(() => props.editId, (newVal) => {
  if (props.isOpen && newVal) {
    fetchJournalData(newVal);
  }
});
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: var(--color-border);
  border-radius: 9999px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: var(--color-border-strong);
}

input::-webkit-outer-spin-button,
input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
</style>
