<template>
  <BaseModal :isOpen="isOpen" @close="$emit('close')" size="2xl">
    <template #title>
      <div class="flex items-center gap-2.5">
        <div class="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <i class="bi bi-journal-text text-lg"></i>
        </div>
        <div>
          <h3 class="text-base font-bold">{{ editId ? 'Edit Manual Journal' : 'Manual Journal' }}</h3>
          <p class="text-[10px] font-medium uppercase tracking-wider text-muted">
            {{ editId ? 'Update journal and references' : 'Create journal with reference links' }}
          </p>
        </div>
      </div>
    </template>

    <div class="space-y-5 p-5">
      <form class="space-y-5" @submit.prevent="handleSubmit">
        <div class="grid grid-cols-1 gap-5 lg:grid-cols-3">
          <div class="space-y-4 rounded-xl border border-border bg-surface-muted/30 p-4 lg:col-span-2">
            <div class="flex items-center gap-2">
              <span class="rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-black uppercase tracking-tighter text-primary">Journal Info</span>
            </div>

            <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div class="space-y-1.5">
                <label class="ml-1 block text-[10px] font-bold uppercase tracking-wider text-muted">Transaction Date</label>
                <TextInput
                  v-model="header.txn_date"
                  type="date"
                  size="sm"
                  required
                />
              </div>

              <div class="space-y-1.5">
                <label class="ml-1 block text-[10px] font-bold uppercase tracking-wider text-muted">Company</label>
                <SelectInput
                  v-model="header.company_id"
                  :options="companyOptions"
                  placeholder="-- No Company --"
                  size="sm"
                />
              </div>

              <div class="space-y-1.5">
                <label class="ml-1 block text-[10px] font-bold uppercase tracking-wider text-muted">Mark</label>
                <SearchableSelect
                  :model-value="header.mark_id"
                  :options="markOptions"
                  placeholder="Select mark..."
                  @update:modelValue="val => header.mark_id = val || ''"
                />
              </div>

              <div class="space-y-1.5">
                <label class="ml-1 block text-[10px] font-bold uppercase tracking-wider text-muted">Journal Total</label>
                <TextInput
                  v-model.number="header.amount"
                  type="number"
                  min="0"
                  placeholder="0"
                  size="sm"
                  :leadingLabel="true"
                >
                  <template #leading>
                    <span class="text-[9px] font-bold">Rp</span>
                  </template>
                </TextInput>
              </div>

              <div class="space-y-1.5 md:col-span-2">
                <label class="ml-1 block text-[10px] font-bold uppercase tracking-wider text-muted">Journal Memo</label>
                <TextInput
                  v-model="header.description"
                  placeholder="e.g. Pelunasan dan reklasifikasi pajak"
                  size="sm"
                  required
                />
              </div>
            </div>
          </div>

          <div class="space-y-4 rounded-xl bg-gray-900 p-4 text-white shadow-lg">
            <div class="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-gray-400">
              <i class="bi bi-diagram-3-fill text-cyan-400"></i>
              Preview Summary
            </div>

            <div class="space-y-2">
              <div class="flex items-center justify-between gap-3">
                <span class="text-[11px] text-gray-300">Selected Mark</span>
                <span class="max-w-[170px] truncate text-right text-[11px] font-semibold text-white/90" :title="selectedMarkLabel">
                  {{ selectedMarkLabel || '-' }}
                </span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-[11px] text-gray-300">Transaction Dir</span>
                <span class="text-[11px] font-mono font-bold" :class="naturalDbCr === 'DB' ? 'text-emerald-300' : naturalDbCr === 'CR' ? 'text-amber-300' : 'text-slate-300'">
                  {{ naturalDbCr === 'DB' ? 'DB · Masuk' : naturalDbCr === 'CR' ? 'CR · Keluar' : '-' }}
                </span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-[11px] text-gray-300">Generated Debit</span>
                <span class="text-[11px] font-bold text-sky-300">{{ debitPreviewCount }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-[11px] text-gray-300">Generated Credit</span>
                <span class="text-[11px] font-bold text-amber-300">{{ creditPreviewCount }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-[11px] text-gray-300">References</span>
                <span class="text-[11px] font-bold text-cyan-300">{{ linkedTransactions.length }}</span>
              </div>
              <div class="space-y-1.5 border-t border-gray-700 pt-2">
                <div class="flex items-center justify-between">
                  <span class="text-[11px] text-gray-300">Debit Total</span>
                  <span class="text-[11px] font-mono font-bold text-sky-300">Rp {{ formatCurrency(resolvedDebitTotal) }}</span>
                </div>
                <div class="flex items-center justify-between">
                  <span class="text-[11px] text-gray-300">Credit Total</span>
                  <span class="text-[11px] font-mono font-bold text-amber-300">Rp {{ formatCurrency(resolvedCreditTotal) }}</span>
                </div>
                <div class="flex items-center justify-between">
                  <span class="text-[11px] text-gray-300">Diff</span>
                  <span class="text-base font-mono font-black" :class="difference === 0 ? 'text-emerald-300' : 'text-rose-300'">
                    Rp {{ formatCurrency(difference) }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="space-y-4 rounded-xl border border-border bg-surface p-4">
          <div class="flex items-center justify-between gap-3">
            <div class="flex items-center gap-4">
              <h4 class="flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-theme">
                <i class="bi bi-list-columns-reverse text-primary"></i>
                Generated Entries
              </h4>
              <SegmentedControl
                v-model="activeReportType"
                :options="reportTypeOptions"
                variant="primary"
                class="scale-90"
              />
            </div>
            <span class="text-[10px] font-semibold uppercase tracking-wider text-muted">
              Reference links are separate from COA lines
            </span>
          </div>

          <div v-if="generatedEntries.length > 0" class="space-y-2">
            <div class="hidden grid-cols-[110px_1fr_170px_110px] gap-2 px-2 text-[9px] font-bold uppercase tracking-wider text-muted md:grid">
              <div>Side</div>
              <div>Account (COA)</div>
              <div class="text-right">Amount</div>
              <div>Source</div>
            </div>

            <div
              v-for="entry in generatedEntries"
              :key="entry.key"
              class="grid grid-cols-1 items-center gap-2 rounded-lg border border-border bg-surface-muted/20 p-3 md:grid-cols-[110px_1fr_170px_110px]"
            >
              <div class="flex items-center">
                <span
                  class="inline-flex items-center rounded-lg px-2.5 py-1 text-[10px] font-bold uppercase"
                  :class="entry.side === 'DEBIT' ? 'bg-sky-500/10 text-sky-500' : 'bg-amber-500/10 text-amber-500'"
                >
                  {{ entry.side }}
                </span>
              </div>

              <div class="min-w-0">
                <p class="truncate text-[11px] font-semibold text-theme" :title="entry.label">{{ entry.label }}</p>
                <p class="text-[9px] uppercase tracking-wider" :class="entry.isActiveReportMissing ? 'text-amber-500' : 'text-muted'">
                  {{ activeReportType }}
                  <span v-if="entry.isActiveReportMissing" class="ml-1">mapping missing</span>
                </p>
              </div>

              <div class="space-y-1">
                <div class="relative">
                  <span class="absolute left-2 top-1/2 -translate-y-1/2 text-[9px] font-bold text-muted">Rp</span>
                  <input
                    :value="entry.manual_amount ?? ''"
                    type="number"
                    min="0"
                    placeholder="Auto / input"
                    class="w-full rounded-lg border border-border bg-surface py-1.5 pl-8 pr-2 text-right text-[11px] font-mono font-bold text-theme outline-none transition-all focus:border-primary focus:ring-1 focus:ring-primary/20"
                    @input="updateLineAmount(entry.key, $event.target.value)"
                  />
                </div>
                <p class="text-right text-[9px]" :class="entry.amount_mode === 'auto' ? 'text-emerald-500' : entry.amount_mode === 'pending' ? 'text-amber-500' : 'text-muted'">
                  <template v-if="entry.amount_mode === 'auto'">Auto remainder: Rp {{ formatCurrency(entry.resolved_amount) }}</template>
                  <template v-else-if="entry.amount_mode === 'pending'">Need manual amount</template>
                  <template v-else>Manual input</template>
                </p>
              </div>

              <div>
                <span
                  class="inline-flex items-center rounded-lg px-2 py-1 text-[9px] font-bold uppercase tracking-wider"
                  :class="entry.amount_mode === 'auto'
                    ? 'bg-emerald-500/10 text-emerald-500'
                    : entry.amount_mode === 'pending'
                      ? 'bg-amber-500/10 text-amber-500'
                      : 'bg-surface-muted/60 text-muted'"
                >
                  {{ entry.amount_mode_label }}
                </span>
              </div>
            </div>
          </div>

          <div v-else class="rounded-xl border border-dashed border-border p-6 text-center">
            <p class="text-[11px] text-muted">{{ generatedEntriesEmptyMessage }}</p>
          </div>
        </div>

        <div class="space-y-4 rounded-xl border border-border bg-surface p-4">
          <div class="flex items-center justify-between gap-3">
            <h4 class="flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-theme">
              <i class="bi bi-link-45deg text-primary"></i>
              Related Transactions
            </h4>
            <button
              type="button"
              @click="showReferencePanel = !showReferencePanel"
              class="rounded-lg px-2 py-1 text-[11px] font-bold text-primary transition-all hover:bg-primary/10"
            >
              {{ showReferencePanel ? 'Hide Search' : 'Add Reference' }}
            </button>
          </div>

          <div v-if="linkedTransactions.length > 0" class="flex flex-wrap gap-1.5 rounded-lg border border-border/50 bg-surface-muted/30 p-2">
            <div
              v-for="txn in linkedTransactions"
              :key="txn.id"
              class="flex items-center gap-1.5 rounded-lg border border-primary/20 bg-primary/10 px-2 py-1 text-[10px] font-semibold text-primary"
            >
              <i class="bi bi-paperclip text-[9px]"></i>
              <span class="max-w-[220px] truncate" :title="txn.description">
                {{ formatDate(txn.txn_date) }} — {{ txn.description || '(no desc)' }}
              </span>
              <span class="font-mono text-[9px] text-primary/70">Rp {{ formatCurrency(txn.amount) }}</span>
              <button
                type="button"
                @click="unlinkTransaction(txn.id)"
                class="ml-1 text-primary/60 transition-colors hover:text-red-500"
              >
                <i class="bi bi-x text-xs"></i>
              </button>
            </div>
          </div>
          <p v-else class="text-[10px] italic text-muted">
            No related transactions linked yet. Gunakan ini sebagai referensi tracking lintas tanggal, tidak terikat ke COA tertentu.
          </p>

          <div v-if="showReferencePanel" class="space-y-3 border-t border-border/50 pt-3">
            <div class="grid grid-cols-1 gap-2 md:grid-cols-3">
              <input
                v-model="linkSearch.query"
                type="text"
                placeholder="Search description..."
                class="rounded-lg border border-border bg-surface px-2.5 py-1.5 text-[10px] text-theme outline-none placeholder:text-muted/50 focus:border-primary focus:ring-1 focus:ring-primary/30"
                @input="debouncedSearch"
              />
              <input
                v-model="linkSearch.start_date"
                type="date"
                class="rounded-lg border border-border bg-surface px-2.5 py-1.5 text-[10px] text-theme outline-none focus:border-primary focus:ring-1 focus:ring-primary/30"
                @change="searchLinkable"
              />
              <input
                v-model="linkSearch.end_date"
                type="date"
                class="rounded-lg border border-border bg-surface px-2.5 py-1.5 text-[10px] text-theme outline-none focus:border-primary focus:ring-1 focus:ring-primary/30"
                @change="searchLinkable"
              />
            </div>

            <div v-if="linkResults.length > 0" class="max-h-[220px] space-y-1 overflow-y-auto pr-1 custom-scrollbar">
              <div
                v-for="txn in linkResults"
                :key="txn.id"
                class="grid cursor-pointer grid-cols-[1fr_auto_auto] items-center gap-2 rounded-lg border border-border px-3 py-2 transition-all hover:border-primary/30 hover:bg-primary/5 group"
                @click="linkTransaction(txn)"
              >
                <div class="min-w-0">
                  <div class="flex min-w-0 items-center gap-1.5">
                    <p class="truncate text-[10px] font-semibold text-theme">{{ txn.description || '(no desc)' }}</p>
                    <span
                      v-if="txn.is_split_child"
                      class="inline-flex items-center rounded-md bg-amber-500/10 px-1.5 py-0.5 text-[8px] font-bold uppercase tracking-wider text-amber-500"
                    >
                      Split item
                    </span>
                  </div>
                  <p class="text-[9px] text-muted">
                    {{ formatDate(txn.txn_date) }}
                    <span v-if="txn.company_name" class="ml-1">· {{ txn.company_name }}</span>
                    <span v-if="txn.bank_code" class="ml-1 font-bold">· {{ txn.bank_code }}</span>
                    <span v-if="txn.parent_description" class="ml-1">· parent: {{ txn.parent_description }}</span>
                  </p>
                </div>
                <div class="flex flex-col items-end gap-0.5">
                  <span class="text-[10px] font-mono font-bold" :class="txn.db_cr === 'DB' ? 'text-success' : 'text-danger'">
                    {{ txn.db_cr === 'DB' ? 'Masuk' : 'Keluar' }} {{ formatCurrency(txn.amount) }}
                  </span>
                </div>
                <span class="flex items-center gap-1 text-[9px] font-bold text-primary opacity-0 transition-opacity group-hover:opacity-100">
                  <i class="bi bi-plus-circle"></i> Link
                </span>
              </div>
            </div>
            <p v-else-if="isSearching" class="py-4 text-center text-[10px] text-muted">
              <i class="bi bi-arrow-repeat mr-1 animate-spin"></i> Searching...
            </p>
            <p v-else-if="linkSearchDone" class="py-3 text-center text-[10px] text-muted">
              No transactions found.
            </p>
            <p v-else class="py-3 text-center text-[10px] text-muted">
              Enter a keyword or date range to search.
            </p>
          </div>
        </div>

        <transition enter-active-class="transition duration-200 ease-out" enter-from-class="opacity-0 -translate-y-2" enter-to-class="opacity-100 translate-y-0">
          <div v-if="legacyMultiLine" class="flex items-center gap-3 rounded-xl border border-cyan-500/20 bg-cyan-500/5 p-4 text-xs font-medium text-cyan-600">
            <div class="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-lg bg-cyan-500/10">
              <i class="bi bi-arrow-repeat"></i>
            </div>
            Jurnal lama ini memakai format multi-line legacy. Data dasar sudah dipanggil; pilih 1 mark pengganti lalu simpan ulang untuk memakai format baru.
          </div>
        </transition>

        <transition enter-active-class="transition duration-200 ease-out" enter-from-class="opacity-0 -translate-y-2" enter-to-class="opacity-100 translate-y-0">
          <div v-if="hasNegativeAmount" class="flex items-center gap-3 rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 text-xs font-medium text-amber-500">
            <div class="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-lg bg-amber-500/10">
              <i class="bi bi-info-circle-fill"></i>
            </div>
            Nominal jurnal harus selalu positif.
          </div>
        </transition>

        <transition enter-active-class="transition duration-200 ease-out" enter-from-class="opacity-0 -translate-y-2" enter-to-class="opacity-100 translate-y-0">
          <div v-if="hasIncompleteMappings" class="flex items-center gap-3 rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 text-xs font-medium text-amber-500">
            <div class="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-lg bg-amber-500/10">
              <i class="bi bi-diagram-3-fill"></i>
            </div>
            Mark terpilih belum punya pasangan debit dan credit lengkap.
          </div>
        </transition>

        <transition enter-active-class="transition duration-200 ease-out" enter-from-class="opacity-0 -translate-y-2" enter-to-class="opacity-100 translate-y-0">
          <div v-if="allocationIssueMessage" class="flex items-center gap-3 rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 text-xs font-medium text-amber-500">
            <div class="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-lg bg-amber-500/10">
              <i class="bi bi-calculator"></i>
            </div>
            {{ allocationIssueMessage }}
          </div>
        </transition>

        <transition enter-active-class="transition duration-200 ease-out" enter-from-class="opacity-0 -translate-y-2" enter-to-class="opacity-100 translate-y-0">
          <div v-if="error" class="mt-2 flex items-center gap-3 rounded-xl border border-red-500/20 bg-red-500/5 p-4 text-xs font-medium text-red-500">
            <div class="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-lg bg-red-500/10">
              <i class="bi bi-exclamation-triangle-fill"></i>
            </div>
            {{ error }}
          </div>
        </transition>

        <div class="flex gap-4 border-t border-border/50 pt-4">
          <button
            type="button"
            class="btn-secondary flex-1 py-3 text-base"
            :disabled="isLoading"
            @click="$emit('close')"
          >
            Discard Changes
          </button>
          <button
            type="submit"
            class="btn-primary flex-1 py-3 text-base shadow-lg shadow-primary/20"
            :disabled="isLoading || !isFormValid"
          >
            <div class="flex items-center justify-center gap-2">
              <span v-if="isLoading" class="spinner-border h-5 w-5"></span>
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
import { computed, reactive, ref, watch } from 'vue';
import BaseModal from '../ui/BaseModal.vue';
import TextInput from '../ui/TextInput.vue';
import SelectInput from '../ui/SelectInput.vue';
import SearchableSelect from '../ui/SearchableSelect.vue';
import SegmentedControl from '../ui/SegmentedControl.vue';
import { historyApi, marksApi } from '../../api';

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
  marks: {
    type: Array,
    default: () => []
  }
});

const emit = defineEmits(['close', 'saved']);

const isLoading = ref(false);
const error = ref(null);
const legacyMultiLine = ref(false);
const activeReportType = ref('real');
const reportTypeOptions = [
  { label: 'Real', value: 'real' },
  { label: 'Coretax', value: 'coretax' }
];

const header = reactive({
  txn_date: new Date().toISOString().split('T')[0],
  description: '',
  company_id: '',
  mark_id: '',
  amount: null
});

const fallbackMarks = ref([]);
const lineStates = ref([]);
const linkedTransactions = ref([]);
const showReferencePanel = ref(false);
const linkResults = ref([]);
const isSearching = ref(false);
const linkSearchDone = ref(false);
const isHydrating = ref(false);
const pendingFetchedLines = ref([]);
const linkSearch = reactive({
  query: '',
  start_date: '',
  end_date: ''
});

const normalizeMappingType = (value) => (
  String(value || '').trim().toUpperCase() === 'CREDIT' ? 'CREDIT' : 'DEBIT'
);

const normalizeDbCr = (value) => {
  const normalized = String(value || '').trim().toUpperCase();
  if (normalized === 'CR') return 'CR';
  if (normalized === 'DB') return 'DB';
  return '';
};

const getMarkLabel = (mark) => {
  if (!mark) return '';
  return [mark.internal_report, mark.personal_use, mark.tax_report]
    .map(value => String(value || '').trim())
    .find(Boolean) || '';
};

const getMappingLabel = (mapping) => (
  [mapping?.code, mapping?.name].filter(Boolean).join(' - ')
);

const companyOptions = computed(() => (
  props.companies.map(company => ({
    id: company.id,
    label: company.name
  }))
));

const availableMarks = computed(() => (
  (props.marks && props.marks.length > 0) ? props.marks : fallbackMarks.value
));

const marksById = computed(() => new Map(
  (availableMarks.value || [])
    .filter(mark => mark?.id)
    .map(mark => [String(mark.id), mark])
));

const markOptions = computed(() => (
  [...(availableMarks.value || [])]
    .sort((a, b) => getMarkLabel(a).localeCompare(getMarkLabel(b), 'id'))
    .map(mark => ({
      id: mark.id,
      label: getMarkLabel(mark) || `Mark ${String(mark.id).slice(0, 8)}`
    }))
));

const selectedMark = computed(() => marksById.value.get(String(header.mark_id || '').trim()) || null);
const selectedMarkLabel = computed(() => getMarkLabel(selectedMark.value));
const naturalDbCr = computed(() => selectedMark.value ? normalizeDbCr(selectedMark.value.natural_direction) : '');

const sortMappings = (mappings = []) => (
  [...mappings].sort((a, b) => getMappingLabel(a).localeCompare(getMappingLabel(b), 'id'))
);

const buildSideTemplates = (realMappings = [], coretaxMappings = [], side) => {
  const count = Math.max(realMappings.length, coretaxMappings.length);
  const rows = [];
  for (let index = 0; index < count; index += 1) {
    const real = realMappings[index] || null;
    const coretax = coretaxMappings[index] || null;
    rows.push({
      key: `${side}-${index + 1}`,
      side,
      coa_id: real?.coa_id || real?.id || '',
      coa_id_coretax: coretax?.coa_id || coretax?.id || '',
      label_real: getMappingLabel(real),
      label_coretax: getMappingLabel(coretax),
    });
  }
  return rows;
};

const buildLineTemplates = (mark) => {
  if (!mark) return [];
  const realMappings = Array.isArray(mark.mappings_real) ? mark.mappings_real : [];
  const coretaxMappings = Array.isArray(mark.mappings_coretax) ? mark.mappings_coretax : [];

  const debitReal = sortMappings(realMappings.filter(mapping => normalizeMappingType(mapping.type || mapping.mapping_type) === 'DEBIT'));
  const creditReal = sortMappings(realMappings.filter(mapping => normalizeMappingType(mapping.type || mapping.mapping_type) === 'CREDIT'));
  const debitCoretax = sortMappings(coretaxMappings.filter(mapping => normalizeMappingType(mapping.type || mapping.mapping_type) === 'DEBIT'));
  const creditCoretax = sortMappings(coretaxMappings.filter(mapping => normalizeMappingType(mapping.type || mapping.mapping_type) === 'CREDIT'));

  return [
    ...buildSideTemplates(debitReal, debitCoretax, 'DEBIT'),
    ...buildSideTemplates(creditReal, creditCoretax, 'CREDIT')
  ];
};

const toNullableNumber = (value) => {
  if (value === null || value === undefined || value === '') return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const getLineResolvedLabel = (line) => {
  if (activeReportType.value === 'coretax' && line.label_coretax) return line.label_coretax;
  if (activeReportType.value === 'real' && line.label_real) return line.label_real;
  return line.label_real || line.label_coretax || 'Unmapped COA';
};

const isActiveReportMissing = (line) => (
  activeReportType.value === 'coretax'
    ? !line.coa_id_coretax
    : !line.coa_id
);

const resetLineStates = () => {
  lineStates.value = buildLineTemplates(selectedMark.value).map(line => ({
    ...line,
    manual_amount: null
  }));
};

const findMatchingLineIndex = (templates, savedLine) => templates.findIndex(template => {
  const sameSide = template.side === savedLine.side;
  if (!sameSide) return false;
  if (template.coa_id && savedLine.coa_id && template.coa_id === savedLine.coa_id) return true;
  if (template.coa_id_coretax && savedLine.coa_id_coretax && template.coa_id_coretax === savedLine.coa_id_coretax) return true;
  return false;
});

const applyFetchedLines = (savedLines = []) => {
  lineStates.value = buildLineTemplates(selectedMark.value).map(line => ({
    ...line,
    manual_amount: null
  }));

  for (const savedLine of (savedLines || [])) {
    const side = String(savedLine.side || '').toUpperCase() === 'CREDIT' ? 'CREDIT' : 'DEBIT';
    const index = findMatchingLineIndex(lineStates.value, { ...savedLine, side });
    if (index < 0) continue;
    lineStates.value[index].manual_amount = Number(savedLine.amount) || null;
  }
};

const debitPreviewCount = computed(() => lineStates.value.filter(line => line.side === 'DEBIT').length);
const creditPreviewCount = computed(() => lineStates.value.filter(line => line.side === 'CREDIT').length);
const hasIncompleteMappings = computed(() => Boolean(header.mark_id) && (!debitPreviewCount.value || !creditPreviewCount.value));

const resolveSideEntries = (entries, journalAmount) => {
  const total = Number(journalAmount) || 0;
  let fixedSum = 0;
  const blankEntries = [];
  const resolved = entries.map(entry => {
    const manualAmount = toNullableNumber(entry.manual_amount);
    if (manualAmount !== null) {
      fixedSum += manualAmount;
      return {
        ...entry,
        label: getLineResolvedLabel(entry),
        isActiveReportMissing: isActiveReportMissing(entry),
        resolved_amount: manualAmount,
        amount_mode: 'manual',
        amount_mode_label: 'Manual'
      };
    }

    blankEntries.push(entry.key);
    return {
      ...entry,
      label: getLineResolvedLabel(entry),
      isActiveReportMissing: isActiveReportMissing(entry),
      resolved_amount: null,
      amount_mode: 'pending',
      amount_mode_label: 'Pending'
    };
  });

  let issue = '';
  if (blankEntries.length === 1) {
    const remainder = total - fixedSum;
    const targetKey = blankEntries[0];
    for (const entry of resolved) {
      if (entry.key === targetKey) {
        entry.resolved_amount = remainder;
        entry.amount_mode = 'auto';
        entry.amount_mode_label = 'Auto';
      }
    }
    if (remainder <= 0) {
      issue = `${entries[0]?.side || 'Side'} remainder must be greater than 0`;
    }
  } else if (blankEntries.length > 1) {
    issue = `${entries[0]?.side || 'Side'} still has ${blankEntries.length} empty lines`;
  } else if (Math.abs(total - fixedSum) > 0.01) {
    issue = `${entries[0]?.side || 'Side'} total must equal journal total`;
  }

  return { entries: resolved, issue };
};

const sideResolution = computed(() => {
  const journalAmount = Number(header.amount) || 0;
  return {
    debit: resolveSideEntries(lineStates.value.filter(line => line.side === 'DEBIT'), journalAmount),
    credit: resolveSideEntries(lineStates.value.filter(line => line.side === 'CREDIT'), journalAmount)
  };
});

const generatedEntries = computed(() => ([
  ...sideResolution.value.debit.entries,
  ...sideResolution.value.credit.entries
]));

const allocationIssues = computed(() => {
  const issues = [];
  if (sideResolution.value.debit.issue) issues.push(sideResolution.value.debit.issue);
  if (sideResolution.value.credit.issue) issues.push(sideResolution.value.credit.issue);
  for (const entry of generatedEntries.value) {
    if (entry.resolved_amount !== null && entry.resolved_amount < 0) {
      issues.push(`${entry.label} results in a negative amount`);
      break;
    }
  }
  return issues;
});

const allocationIssueMessage = computed(() => allocationIssues.value[0] || '');
const resolvedDebitTotal = computed(() => (
  generatedEntries.value
    .filter(entry => entry.side === 'DEBIT')
    .reduce((sum, entry) => sum + (Number(entry.resolved_amount) || 0), 0)
));
const resolvedCreditTotal = computed(() => (
  generatedEntries.value
    .filter(entry => entry.side === 'CREDIT')
    .reduce((sum, entry) => sum + (Number(entry.resolved_amount) || 0), 0)
));
const difference = computed(() => Math.round((resolvedDebitTotal.value - resolvedCreditTotal.value) * 100) / 100);
const generatedEntriesEmptyMessage = computed(() => (
  !header.mark_id ? 'Select a mark first.' : 'This mark does not have any generated journal lines yet.'
));
const hasNegativeAmount = computed(() => (
  Number(header.amount) < 0 ||
  lineStates.value.some(line => toNullableNumber(line.manual_amount) !== null && Number(line.manual_amount) < 0)
));

const isFormValid = computed(() => (
  String(header.description || '').trim() &&
  header.txn_date &&
  header.mark_id &&
  Number(header.amount) > 0 &&
  !hasNegativeAmount.value &&
  !hasIncompleteMappings.value &&
  allocationIssues.value.length === 0 &&
  difference.value === 0 &&
  generatedEntries.value.length >= 2 &&
  generatedEntries.value.every(entry => Number(entry.resolved_amount) > 0)
));

const updateLineAmount = (key, rawValue) => {
  const target = lineStates.value.find(line => line.key === key);
  if (!target) return;
  target.manual_amount = rawValue === '' ? null : Number(rawValue);
};

let searchTimer = null;
const debouncedSearch = () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(searchLinkable, 400);
};

const getLinkedIds = () => new Set(linkedTransactions.value.map(txn => txn.id));

const searchLinkable = async () => {
  if (!linkSearch.query && !linkSearch.start_date && !linkSearch.end_date) {
    linkResults.value = [];
    linkSearchDone.value = false;
    return;
  }

  isSearching.value = true;
  linkSearchDone.value = false;
  const linkedIds = getLinkedIds();

  try {
    const params = {};
    if (props.editId) params.exclude_manual_txn_id = props.editId;
    if (header.company_id) params.company_id = header.company_id;
    if (linkSearch.query) params.search = linkSearch.query;
    if (linkSearch.start_date) params.start_date = linkSearch.start_date;
    if (linkSearch.end_date) params.end_date = linkSearch.end_date;

    const res = await historyApi.getLinkableTransactions(params);
    linkResults.value = (res.data.transactions || []).filter(txn => !linkedIds.has(txn.id));
  } catch (err) {
    console.error('Failed to search linkable transactions', err);
    linkResults.value = [];
  } finally {
    isSearching.value = false;
    linkSearchDone.value = true;
  }
};

const linkTransaction = (txn) => {
  if (linkedTransactions.value.find(item => item.id === txn.id)) return;
  linkedTransactions.value.push(txn);
  linkResults.value = linkResults.value.filter(item => item.id !== txn.id);
};

const unlinkTransaction = (txnId) => {
  linkedTransactions.value = linkedTransactions.value.filter(item => item.id !== txnId);
};

const formatCurrency = (value) => (
  new Intl.NumberFormat('id-ID').format(Math.abs(Number(value) || 0))
);

const formatDate = (value) => {
  if (!value) return '';
  return new Date(value).toLocaleDateString('id-ID', {
    day: '2-digit',
    month: 'short',
    year: 'numeric'
  });
};

const fetchJournalData = async (id) => {
  isLoading.value = true;
  error.value = null;
  isHydrating.value = true;

  try {
    const res = await historyApi.getManualJournal(id);
    const data = res.data || {};
    const journal = data.header || {};

    legacyMultiLine.value = Boolean(journal.legacy_multi_line);
    header.txn_date = journal.txn_date ? String(journal.txn_date).substring(0, 10) : '';
    header.description = journal.description || '';
    header.company_id = journal.company_id || '';
    header.mark_id = journal.mark_id || '';
    header.amount = Number(journal.amount) || null;
    linkedTransactions.value = [...(data.linked_transactions || [])];
    pendingFetchedLines.value = [...(data.lines || [])];

    if (header.mark_id && selectedMark.value) {
      applyFetchedLines(pendingFetchedLines.value);
      pendingFetchedLines.value = [];
    } else {
      lineStates.value = [];
    }
  } catch (err) {
    error.value = err.response?.data?.error || err.message || 'Failed to load journal data for editing.';
    console.error(err);
  } finally {
    isHydrating.value = false;
    isLoading.value = false;
  }
};

const handleSubmit = async () => {
  isLoading.value = true;
  error.value = null;

  try {
    const payload = {
      txn_date: header.txn_date,
      description: String(header.description || '').trim(),
      company_id: header.company_id || null,
      mark_id: String(header.mark_id || '').trim() || null,
      amount: Number(header.amount) || 0,
      lines: generatedEntries.value.map(entry => ({
        side: entry.side,
        amount: Number(entry.resolved_amount) || 0,
        description: String(header.description || '').trim(),
        label: entry.label,
        coa_id: entry.coa_id || null,
        coa_id_coretax: entry.coa_id_coretax || null
      })),
      linked_transaction_ids: linkedTransactions.value.map(txn => txn.id)
    };

    if (props.editId) {
      await historyApi.updateManualTransaction(props.editId, payload);
    } else {
      await historyApi.createManualTransaction(payload);
    }

    emit('saved');
    emit('close');
  } catch (err) {
    error.value = err.response?.data?.error || `Failed to ${props.editId ? 'update' : 'create'} manual journal`;
    console.error(err);
  } finally {
    isLoading.value = false;
  }
};

const resetForm = () => {
  header.txn_date = new Date().toISOString().split('T')[0];
  header.description = '';
  header.company_id = '';
  header.mark_id = '';
  header.amount = null;
  lineStates.value = [];
  linkedTransactions.value = [];
  legacyMultiLine.value = false;
  error.value = null;
  activeReportType.value = 'real';
  showReferencePanel.value = false;
  linkResults.value = [];
  linkSearch.query = '';
  linkSearch.start_date = '';
  linkSearch.end_date = '';
  linkSearchDone.value = false;
  isHydrating.value = false;
  pendingFetchedLines.value = [];
};

const ensureMarksLoaded = async () => {
  if ((props.marks && props.marks.length > 0) || fallbackMarks.value.length > 0) return;
  try {
    const response = await marksApi.getMarks();
    fallbackMarks.value = response.data?.marks || [];
  } catch (err) {
    console.error('Failed to fetch marks for manual journal modal', err);
  }
};

watch([() => header.mark_id, availableMarks], () => {
  if (isHydrating.value) return;
  if (!header.mark_id) {
    lineStates.value = [];
    pendingFetchedLines.value = [];
    return;
  }
  if (pendingFetchedLines.value.length > 0 && selectedMark.value) {
    applyFetchedLines(pendingFetchedLines.value);
    pendingFetchedLines.value = [];
    return;
  }
  resetLineStates();
});

watch(() => props.isOpen, async (isOpen) => {
  if (!isOpen) return;
  resetForm();
  await ensureMarksLoaded();
  if (props.editId) {
    await fetchJournalData(props.editId);
  }
});

watch(() => props.editId, async (nextEditId) => {
  if (props.isOpen && nextEditId) {
    await ensureMarksLoaded();
    await fetchJournalData(nextEditId);
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
