<template>
  <BaseModal :isOpen="isOpen" @close="close" size="xl">
    <template #title>
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
          <i class="bi bi-receipt text-primary"></i>
        </div>
        <div v-if="localTxn">
          <p class="text-sm font-bold text-theme leading-tight">Transaction Details</p>
          <p class="text-[10px] font-mono text-muted leading-tight">{{ localTxn.bank_code }} · {{ formatDate(localTxn.txn_date) }}</p>
        </div>
      </div>
    </template>

    <div v-if="localTxn" class="flex flex-col">
      <!-- ─── Tab Bar ─────────────────────────────────────────── -->
      <div class="flex gap-1 px-5 pt-4 pb-0 border-b border-border">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="txn-tab"
          :class="{ 'txn-tab--active': activeTab === tab.id }"
          @click="activeTab = tab.id"
        >
          <i :class="[tab.icon, 'mr-1.5 text-xs']"></i>
          {{ tab.label }}
        </button>
      </div>

      <!-- ─── TAB: Transaction Info ──────────────────────────── -->
      <div v-show="activeTab === 'info'" class="p-5 grid grid-cols-1 lg:grid-cols-2 gap-5">

        <!-- LEFT COLUMN -->
        <div class="space-y-4">

          <!-- Amount Hero -->
          <div class="p-4 rounded-2xl bg-surface-muted border border-border flex items-center justify-between">
            <div>
              <p class="text-[10px] font-bold text-muted uppercase tracking-[0.2em]">Transaction Date</p>
              <p class="text-sm font-bold text-theme mt-0.5">{{ formatDate(localTxn.txn_date) }}</p>
              <div class="flex items-center gap-1.5 mt-1.5">
                <span class="px-2 py-0.5 rounded text-[9px] font-black uppercase tracking-widest border"
                  :class="localTxn.db_cr === 'DB'
                    ? 'bg-success/10 text-success border-success/20'
                    : 'bg-danger/10 text-danger border-danger/20'"
                >
                  <i :class="localTxn.db_cr === 'DB' ? 'bi-arrow-down-circle-fill' : 'bi-arrow-up-circle-fill'" class="bi mr-1 text-[9px]"></i>
                  {{ localTxn.db_cr === 'DB' ? 'Masuk' : 'Keluar' }}
                </span>
                <span class="text-[10px] text-muted font-mono">{{ localTxn.bank_code }}</span>
              </div>
            </div>
            <div class="text-right">
              <p class="text-[10px] font-bold text-muted uppercase tracking-[0.2em]">Amount</p>
              <p class="text-2xl font-black font-mono tracking-tight mt-0.5"
                :class="localTxn.db_cr === 'DB' ? 'text-success' : 'text-danger'">
                {{ localTxn.db_cr === 'DB' ? '+' : '-' }}{{ formatAmount(localTxn.amount) }}
              </p>
            </div>
          </div>

          <!-- Company -->
          <div class="space-y-1.5">
            <label class="label-base flex items-center gap-2">
              <i class="bi bi-building text-primary text-xs"></i>
              Entity / Company
            </label>
            <SelectInput
              :model-value="localTxn.company_id || ''"
              :options="store.companies.map(c => ({ value: c.id, label: `${c.name} (${c.short_name})` }))"
              placeholder="-- No Company Assigned --"
              @update:model-value="handleCompanyChange"
            />
          </div>

          <!-- Source Bank & File -->
          <div class="grid grid-cols-2 gap-3">
            <div class="space-y-1">
              <p class="text-[10px] font-bold text-muted uppercase tracking-[0.2em]">Source Bank</p>
              <div class="flex items-center gap-2 bg-surface-muted rounded-xl border border-border px-3 py-2">
                <i class="bi bi-bank text-muted text-xs"></i>
                <span class="text-xs font-semibold text-theme">{{ localTxn.bank_code }}</span>
              </div>
            </div>
            <div class="space-y-1">
              <p class="text-[10px] font-bold text-muted uppercase tracking-[0.2em]">Source File</p>
              <div class="flex items-center gap-2 bg-surface-muted rounded-xl border border-border px-3 py-2 overflow-hidden" :title="localTxn.source_file">
                <i class="bi bi-file-earmark-text text-muted text-xs flex-shrink-0"></i>
                <span class="text-xs text-muted truncate">{{ localTxn.source_file || '-' }}</span>
              </div>
            </div>
          </div>

          <!-- Notes -->
          <div class="space-y-1.5">
            <div class="flex justify-between items-center">
              <label class="label-base flex items-center gap-2">
                <i class="bi bi-sticky text-primary text-xs"></i>
                Internal Notes
              </label>
              <transition name="fade">
                <span v-if="notesSaved && showSavedMessage" class="text-[10px] text-success font-bold flex items-center gap-1">
                  <i class="bi bi-check-circle-fill"></i> Saved
                </span>
              </transition>
            </div>
            <div class="relative">
              <textarea
                v-model="notes"
                placeholder="Add private notes for this transaction..."
                class="w-full text-xs bg-surface-raised border border-border rounded-xl focus:ring-1 focus:ring-primary focus:border-primary min-h-[80px] p-3 transition-all font-sans resize-none"
                @blur="notes !== localTxn.notes && saveNotes()"
              ></textarea>
              <button
                v-if="notes !== localTxn.notes"
                @click="saveNotes"
                class="absolute bottom-2 right-2 text-[10px] font-black uppercase tracking-widest bg-primary text-white px-3 py-1 rounded-lg shadow-lg transition-all"
                :disabled="isSavingNotes"
              >
                {{ isSavingNotes ? 'Saving...' : 'Save' }}
              </button>
            </div>
          </div>
        </div>

        <!-- RIGHT COLUMN -->
        <div class="space-y-4">

          <!-- Description -->
          <div class="space-y-1.5">
            <p class="label-base">Description / Reference</p>
            <div class="bg-surface-muted p-3 rounded-xl border border-border min-h-[80px] max-h-[120px] overflow-y-auto">
              <p class="text-xs text-theme leading-relaxed font-mono whitespace-pre-wrap">{{ localTxn.description }}</p>
            </div>
          </div>

          <!-- Classification & COA -->
          <div class="p-4 rounded-2xl bg-primary/5 border border-primary/10 space-y-3">
            <div class="flex justify-between items-center">
              <div class="text-[10px] font-black text-primary uppercase tracking-[0.25em] flex items-center gap-2">
                <i class="bi bi-tag-fill"></i> Classification & COA
              </div>
              <button
                v-if="!localTxn.is_linked_to_manual"
                class="text-[10px] font-black text-primary hover:bg-primary/10 px-3 py-1.5 rounded-lg transition-all uppercase tracking-widest border border-primary/20"
                @click="openAssignMark"
              >
                {{ markDetails ? 'Edit' : 'Map Accounts' }}
              </button>
            </div>

            <div v-if="markDetails" class="space-y-3">
              <div
                v-if="localTxn.is_linked_to_manual"
                class="rounded-xl border border-primary/10 bg-primary/5 px-3 py-2 text-[10px] text-primary"
              >
                This transaction is already referenced by a manual journal. The classification and COA shown here follow that journal so the source transaction does not appear double-counted.
              </div>

              <!-- Report categories -->
              <div class="grid grid-cols-3 gap-2 pb-3 border-b border-primary/10">
                <div class="space-y-0.5">
                  <p class="text-[9px] text-primary/60 uppercase font-black tracking-widest">Internal</p>
                  <p class="text-[11px] font-bold text-theme">{{ markDetails.internal_report || '-' }}</p>
                </div>
                <div class="space-y-0.5">
                  <p class="text-[9px] text-primary/60 uppercase font-black tracking-widest">Personal</p>
                  <p class="text-[11px] font-bold text-theme">{{ markDetails.personal_use || '-' }}</p>
                </div>
                <div class="space-y-0.5">
                  <p class="text-[9px] text-primary/60 uppercase font-black tracking-widest">Taxation</p>
                  <p class="text-[11px] font-bold text-theme">{{ markDetails.tax_report || '-' }}</p>
                </div>
              </div>

              <!-- COA Mappings -->
              <div v-if="markDetails.mappings && markDetails.mappings.length > 0" class="space-y-1.5">
                <p class="text-[9px] text-primary/70 uppercase font-black flex items-center gap-1 tracking-widest">
                  <i class="bi bi-diagram-3-fill"></i> COA Mappings
                </p>
                <div
                  v-for="(map, idx) in markDetails.mappings"
                  :key="idx"
                  class="bg-surface p-2.5 rounded-xl border border-border flex items-center justify-between gap-2 hover:border-primary/50 transition-all"
                >
                  <div class="flex items-center gap-2 min-w-0">
                    <span class="font-mono font-bold text-[10px] text-primary bg-primary/5 px-1.5 py-0.5 rounded border border-primary/10 flex-shrink-0">{{ map.code }}</span>
                    <span class="text-xs font-bold text-theme truncate">{{ map.name }}</span>
                  </div>
                  <div class="flex items-center gap-1.5 flex-shrink-0">
                    <span class="text-[8px] font-black px-1.5 py-0.5 rounded uppercase tracking-widest border"
                      :class="map.type === 'DEBIT' ? 'bg-warning/10 text-warning border-warning/20' : 'bg-success/10 text-success border-success/20'"
                    >{{ map.type }}</span>
                    <FiscalCategoryBadge :category="map.fiscal_category" />
                    <select
                      :value="map.fiscal_category || 'DEDUCTIBLE'"
                      @change="e => updateCoaFiscal(map.coa_id, e.target.value)"
                      class="text-[9px] bg-surface-muted border border-border rounded px-1.5 py-1 focus:ring-1 focus:ring-primary outline-none font-bold uppercase tracking-tight"
                    >
                      <option value="DEDUCTIBLE">Deductible</option>
                      <option value="NON_DEDUCTIBLE_PERMANENT">Non-Ded (Perm)</option>
                      <option value="NON_DEDUCTIBLE_TEMPORARY">Non-Ded (Temp)</option>
                      <option value="NON_TAXABLE_INCOME">Non-Taxable</option>
                    </select>
                  </div>
                </div>
              </div>
              <p v-else class="text-[10px] text-muted italic text-center py-2">No COA mappings defined.</p>
            </div>

            <div v-else class="py-6 text-center border-2 border-dashed border-primary/10 rounded-2xl">
              <i class="bi bi-intersect text-2xl text-primary/20 mb-2 block"></i>
              <p class="text-xs text-muted font-medium">No classification assigned yet.</p>
              <p v-if="localTxn.is_linked_to_manual" class="mt-1 text-[10px] text-primary">
                This transaction is linked to a manual journal. Review the manual journal if the classification should be changed.
              </p>
            </div>
          </div>
        </div>
      </div>

      <!-- ─── TAB: COGS / HPP ────────────────────────────────── -->
      <div v-show="activeTab === 'cogs'" class="p-5">
        <HppDetailSection :transaction="localTxn" />
      </div>
    </div>

    <template #footer>
      <div class="flex items-center justify-between w-full">
        <div class="flex gap-2">
          <button
            v-if="localTxn?.bank_code === 'MANUAL'"
            @click="editManualJournal"
            class="btn-secondary !text-xs !py-2 h-[38px]"
          >
            <i class="bi bi-pencil-square me-2"></i> Edit Journal
          </button>
          <button
            @click="deleteTxn"
            class="btn-secondary !bg-danger/5 !text-danger hover:!bg-danger/10 !border-danger/10 !text-xs !py-2 h-[38px]"
          >
            <i class="bi bi-trash3 me-2"></i> Delete
          </button>
        </div>
        <button @click="close" class="btn-primary !py-2 !px-8 h-[38px] !text-xs">
          Close
        </button>
      </div>
    </template>
  </BaseModal>
</template>

<script setup>
import { ref, computed, watch, toRefs } from 'vue';
import BaseModal from '../ui/BaseModal.vue';
import SelectInput from '../ui/SelectInput.vue';
import { useHistoryStore } from '../../stores/history';
import { useCoaStore } from '../../stores/coa';
import HppDetailSection from './HppDetailSection.vue';
import FiscalCategoryBadge from '../ui/FiscalCategoryBadge.vue';

const props = defineProps({
  isOpen: Boolean,
  transaction: Object
});

const emit = defineEmits(['close', 'assign-mark', 'edit-journal']);
const store = useHistoryStore();
const { transaction: localTxn } = toRefs(props);

// Tab control
const activeTab = ref('info');
const tabs = [
  { id: 'info', label: 'Transaction Info', icon: 'bi bi-receipt' },
  { id: 'cogs', label: 'COGS / HPP', icon: 'bi bi-box-seam' },
];

// Notes Logic
const notes = ref('');
const isSavingNotes = ref(false);
const notesSaved = ref(false);
const showSavedMessage = ref(false);

const markDetails = computed(() => {
  if (!localTxn.value) return null;
  const effectiveMarkId = localTxn.value.mark_id || localTxn.value.manual_mark_id;
  if (!effectiveMarkId) return null;
  return store.marks.find(m => m.id === effectiveMarkId);
});

const close = () => {
  activeTab.value = 'info';
  emit('close');
};
const openAssignMark = () => emit('assign-mark', localTxn.value);
const editManualJournal = () => {
  const editId = localTxn.value.parent_id || localTxn.value.id;
  emit('edit-journal', editId);
};

const deleteTxn = async () => {
  if (!confirm('Are you sure you want to delete this transaction?')) return;
  try {
    await store.deleteTransaction(localTxn.value.id);
    close();
  } catch (e) {
    alert('Failed to delete: ' + e.message);
  }
};

const formatDate = (dateStr) => dateStr ? dateStr.split(' ')[0] : '-';
const formatAmount = (val) => new Intl.NumberFormat('id-ID').format(val);

watch(localTxn, (newVal) => {
  if (newVal) {
    notes.value = newVal.notes || '';
    activeTab.value = 'info';
  }
}, { immediate: true });

const saveNotes = async () => {
  if (!localTxn.value) return;
  isSavingNotes.value = true;
  try {
    await store.updateNotes(localTxn.value.id, notes.value);
    notesSaved.value = true;
    showSavedMessage.value = true;
    setTimeout(() => { showSavedMessage.value = false; }, 2000);
  } catch (e) {
    alert('Failed to save notes');
  } finally {
    isSavingNotes.value = false;
  }
};

const handleCompanyChange = async (companyId) => {
  if (!localTxn.value) return;
  try {
    await store.assignCompany(localTxn.value.id, companyId || null);
  } catch (e) {
    alert('Failed to update company');
  }
};

const coaStore = useCoaStore();
const updateCoaFiscal = async (coaId, fiscalCategory) => {
  try {
    await coaStore.updateCoa(coaId, { fiscal_category: fiscalCategory });
    await store.fetchMarks();
  } catch (e) {
    alert('Failed to update fiscal category: ' + e.message);
  }
};
</script>

<style scoped>
.txn-tab {
  @apply inline-flex items-center px-4 py-2.5 text-sm font-medium rounded-t-xl transition-all whitespace-nowrap border-b-2 -mb-px;
  border-bottom-color: transparent;
  color: var(--color-text-muted);
  background: transparent;
}

.txn-tab:hover {
  color: var(--color-text);
}

.txn-tab--active {
  border-bottom-color: var(--color-primary);
  color: var(--color-primary);
  font-weight: 700;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
