<template>
  <BaseModal :isOpen="isOpen" @close="close" size="lg">
    <template #title>
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
          <i class="bi bi-receipt text-primary"></i>
        </div>
        <span>Transaction Details</span>
      </div>
    </template>
    
    <div v-if="localTxn" class="p-6 space-y-6">
      <!-- Main Status Card -->
      <div class="p-5 rounded-2xl bg-surface-muted border border-border shadow-soft">
        <div class="flex justify-between items-start">
          <div class="space-y-1">
            <p class="text-[10px] font-bold text-muted uppercase tracking-[0.2em]">Transaction Date</p>
            <p class="text-sm font-bold text-theme">{{ formatDate(localTxn.txn_date) }}</p>
          </div>
          <div class="text-right space-y-1">
            <p class="text-[10px] font-bold text-muted uppercase tracking-[0.2em]">Amount</p>
            <p class="text-2xl font-black font-mono tracking-tight" 
               :class="localTxn.db_cr === 'CR' ? 'text-success' : 'text-danger'">
              {{ localTxn.db_cr === 'CR' ? '+' : '-' }}{{ formatAmount(localTxn.amount) }}
            </p>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- Company Assignment -->
        <div class="col-span-1 md:col-span-2 space-y-2">
          <label class="text-[10px] font-bold text-muted uppercase tracking-[0.2em] ml-1">Entity / Company</label>
          <SelectInput
            :model-value="localTxn.company_id || ''"
            :options="store.companies.map(c => ({ value: c.id, label: `${c.name} (${c.short_name})` }))"
            placeholder="-- No Company Assigned --"
            @update:model-value="handleCompanyChange"
            class="!py-2.5"
          />
        </div>

        <!-- Metadata Grid -->
        <div class="space-y-4">
          <div class="space-y-1">
            <p class="text-[10px] font-bold text-muted uppercase tracking-[0.2em]">Source Bank</p>
            <div class="flex items-center gap-2 text-sm font-semibold text-theme">
              <div class="w-5 h-5 rounded bg-surface border border-border flex items-center justify-center text-[10px]">
                <i class="bi bi-bank"></i>
              </div>
              {{ localTxn.bank_code }}
            </div>
          </div>
          
          <div class="space-y-1">
            <p class="text-[10px] font-bold text-muted uppercase tracking-[0.2em]">Import Source</p>
            <p class="text-xs text-muted truncate max-w-full" :title="localTxn.source_file">
              <i class="bi bi-file-earmark-text me-1"></i> {{ localTxn.source_file }}
            </p>
          </div>
        </div>

        <!-- Description Box -->
        <div class="space-y-2">
          <p class="text-[10px] font-bold text-muted uppercase tracking-[0.2em]">Description / Reference</p>
          <div class="bg-surface-muted p-3 rounded-xl border border-border min-h-[4.5rem]">
            <p class="text-xs text-theme leading-relaxed font-mono whitespace-pre-wrap">{{ localTxn.description }}</p>
          </div>
        </div>
      </div>
      
      <!-- Notes & Classification Group -->
      <div class="grid grid-cols-1 gap-6 pt-2">
        <!-- Notes Section -->
        <div class="space-y-3">
          <div class="flex justify-between items-center">
            <p class="text-[10px] font-bold text-muted uppercase tracking-[0.2em] ml-1">Internal Notes</p>
            <transition name="fade">
              <span v-if="notesSaved && showSavedMessage" class="text-[10px] text-success font-bold flex items-center gap-1">
                <i class="bi bi-check-circle-fill"></i> Saved Successfully
              </span>
            </transition>
          </div>
          <div class="relative group">
            <textarea 
                v-model="notes"
                placeholder="Add private notes for this transaction..." 
                class="w-full text-xs bg-surface-raised border-border rounded-xl focus:ring-primary focus:border-primary min-h-[80px] p-3 transition-all font-sans"
                @blur="notes !== localTxn.notes && saveNotes()"
            ></textarea>
            <button 
                v-if="notes !== localTxn.notes"
                @click="saveNotes" 
                class="absolute bottom-3 right-3 text-[10px] font-black uppercase tracking-widest bg-primary text-white px-3 py-1.5 rounded-lg shadow-lg hover:shadow-primary/20 transition-all"
                :disabled="isSavingNotes"
            >
              {{ isSavingNotes ? 'Saving...' : 'Save Changes' }}
            </button>
          </div>
        </div>

        <!-- Classification & COA Grid -->
        <div class="p-5 rounded-2xl bg-primary/5 border border-primary/10 space-y-4">
          <div class="flex justify-between items-center">
            <div class="text-[10px] font-black text-primary uppercase tracking-[0.25em] flex items-center gap-2">
              <i class="bi bi-tag-fill"></i> Classification & COA
            </div>
            <button 
              class="text-[10px] font-black text-primary hover:bg-primary/10 px-3 py-1.5 rounded-lg transition-all uppercase tracking-widest border border-primary/20" 
              @click="openAssignMark"
            >
              {{ markDetails ? 'Edit Mapping' : 'Map Accounts' }}
            </button>
          </div>
          
          <div v-if="markDetails" class="space-y-4">
            <div class="grid grid-cols-3 gap-4 pb-4 border-b border-primary/10">
              <div class="space-y-1">
                <p class="text-[9px] text-primary/60 uppercase font-black tracking-widest">Internal</p>
                <p class="text-[11px] font-bold text-theme">{{ markDetails.internal_report || '-' }}</p>
              </div>
              <div class="space-y-1">
                <p class="text-[9px] text-primary/60 uppercase font-black tracking-widest">Personal</p>
                <p class="text-[11px] font-bold text-theme">{{ markDetails.personal_use || '-' }}</p>
              </div>
              <div class="space-y-1">
                <p class="text-[9px] text-primary/60 uppercase font-black tracking-widest">Taxation</p>
                <p class="text-[11px] font-bold text-theme">{{ markDetails.tax_report || '-' }}</p>
              </div>
            </div>
            
            <div v-if="markDetails.mappings && markDetails.mappings.length > 0">
              <p class="text-[9px] text-primary/70 uppercase font-black mb-3 flex items-center gap-1 tracking-widest">
                <i class="bi bi-diagram-3-fill"></i> COA Mappings
              </p>
              <div class="grid grid-cols-1 gap-2">
                <div v-for="(map, idx) in markDetails.mappings" :key="idx" 
                    class="bg-surface p-2.5 rounded-xl border border-border flex items-center justify-between group hover:border-primary/50 transition-all shadow-sm"
                >
                  <div class="flex items-center gap-3">
                    <span class="font-mono font-bold text-[10px] text-primary bg-primary/5 px-2 py-1 rounded border border-primary/10">
                      {{ map.code }}
                    </span>
                    <span class="text-xs font-bold text-theme">{{ map.name }}</span>
                  </div>
                  <span class="text-[8px] font-black px-2 py-1 rounded-md uppercase tracking-widest border" 
                      :class="map.type === 'DEBIT' 
                        ? 'bg-warning/10 text-warning border-warning/20' 
                        : 'bg-success/10 text-success border-success/20'">
                    {{ map.type }}
                  </span>
                </div>
              </div>
            </div>
            <div v-else class="text-[10px] text-muted italic py-2 text-center">
              No specific COA mappings defined for this mark.
            </div>
          </div>
          <div v-else class="py-6 text-center border-2 border-dashed border-primary/10 rounded-2xl bg-surface/50">
            <i class="bi bi-intersect text-2xl text-primary/20 mb-2 block"></i>
            <p class="text-xs text-muted font-medium">No classification assigned yet.</p>
          </div>
        </div>
      </div>
          
      <!-- HPP Section -->
      <div class="pt-2">
        <HppDetailSection :transaction="localTxn" />
      </div>
    </div>

    <template #footer>
      <div class="flex items-center justify-between w-full">
        <div class="flex gap-2">
          <button 
            v-if="localTxn.bank_code === 'MANUAL'"
            @click="editManualJournal"
            class="btn-secondary !text-xs !py-2 h-[38px]"
          >
            <i class="bi bi-pencil-square me-2"></i> Edit Journal
          </button>
          
          <button 
            @click="deleteTxn" 
            class="btn-secondary !bg-danger/5 !text-danger hover:!bg-danger/10 !border-danger/10 transition-all !text-xs !py-2 h-[38px]"
          >
            <i class="bi bi-trash3 me-2"></i> Delete
          </button>
        </div>
        
        <button @click="close" class="btn-primary !py-2 !px-8 h-[38px] !text-xs">
          Close View
        </button>
      </div>
    </template>
  </BaseModal>
</template>

<script setup>
import { ref, computed, watch, toRefs } from 'vue';
import BaseModal from '../ui/BaseModal.vue';
import { useHistoryStore } from '../../stores/history';
import HppDetailSection from './HppDetailSection.vue';

const props = defineProps({
  isOpen: Boolean,
  transaction: Object
});

const emit = defineEmits(['close', 'assign-mark', 'edit-journal']);
const store = useHistoryStore();
const { transaction: localTxn } = toRefs(props);

// Notes Logic
const notes = ref('');
const isSavingNotes = ref(false);
const notesSaved = ref(false);
const showSavedMessage = ref(false);

const markDetails = computed(() => {
    if (!localTxn.value || !localTxn.value.mark_id) return null;
    return store.marks.find(m => m.id === localTxn.value.mark_id);
});

const close = () => emit('close');
const openAssignMark = () => emit('assign-mark', localTxn.value);
const editManualJournal = () => {
    // If it's a child, we want the parent_id, otherwise it's the id itself
    const editId = localTxn.value.parent_id || localTxn.value.id;
    emit('edit-journal', editId);
};

const deleteTxn = async () => {
    if(!confirm("Are you sure you want to delete this transaction?")) return;
    try {
        await store.deleteTransaction(localTxn.value.id);
        close();
    } catch (e) {
        alert("Failed to delete: " + e.message);
    }
};

const formatDate = (dateStr) => dateStr ? dateStr.split(" ")[0] : '-';
const formatAmount = (val) => new Intl.NumberFormat('id-ID').format(val);

watch(localTxn, (newVal) => {
    if (newVal) {
        notes.value = newVal.notes || '';
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
</script>
