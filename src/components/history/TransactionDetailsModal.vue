<template>
  <BaseModal :isOpen="isOpen" @close="close">
    <template #title>Transaction Details</template>
    
    <div v-if="localTxn" class="p-6 space-y-5">
        <div class="grid grid-cols-2 gap-y-5 gap-x-6">
            <!-- Row 1: Date & Amount -->
            <div class="space-y-1">
                <p class="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Date</p>
                <p class="text-sm font-semibold text-gray-900">{{ formatDate(localTxn.txn_date) }}</p>
            </div>
            <div class="space-y-1 text-right">
                <p class="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Amount</p>
                <p class="text-lg font-bold font-mono" :class="localTxn.db_cr === 'CR' ? 'text-green-600' : 'text-red-600'">
                    {{ localTxn.db_cr === 'CR' ? '+' : '-' }}{{ formatAmount(localTxn.amount) }}
                </p>
            </div>

            <!-- Row 2: Company (Full Width) -->
            <div class="col-span-2 space-y-1">
                <p class="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Company</p>
                <select 
                    class="text-sm font-semibold text-gray-900 border-gray-200 bg-gray-50/50 hover:bg-gray-50 rounded-lg p-2.5 w-full focus:ring-indigo-500 focus:border-indigo-500 transition-all"
                    :value="localTxn.company_id || ''"
                    @change="handleCompanyChange($event.target.value)"
                >
                    <option value="">-- No Company --</option>
                    <option v-for="c in store.companies" :key="c.id" :value="c.id">
                        {{ c.name }} ({{ c.short_name }})
                    </option>
                </select>
            </div>

            <!-- Row 3: Bank & Source -->
            <div class="space-y-1">
                <p class="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Bank</p>
                <p class="text-sm text-gray-700 font-medium">{{ localTxn.bank_code }}</p>
            </div>
            <div class="space-y-1 text-right">
                <p class="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Source File</p>
                <p class="text-xs text-gray-500 truncate max-w-[200px] ml-auto" :title="localTxn.source_file">{{ localTxn.source_file }}</p>
            </div>

            <!-- Row 4: Description -->
            <div class="col-span-2 space-y-1">
                <p class="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Description</p>
                <div class="bg-gray-50 p-3 rounded-lg border border-gray-100">
                    <p class="text-sm text-gray-700 leading-relaxed font-mono whitespace-pre-wrap">{{ localTxn.description }}</p>
                </div>
            </div>
            
            <!-- Notes Section -->
            <div class="col-span-2 space-y-1 pt-2 border-t border-gray-100 mt-2">
                <div class="flex justify-between items-center">
                    <p class="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Notes</p>
                    <button 
                        v-if="notes !== localTxn.notes"
                        @click="saveNotes" 
                        class="text-[10px] uppercase font-bold text-indigo-600 hover:text-indigo-800"
                        :disabled="isSavingNotes"
                    >
                        {{ isSavingNotes ? 'Saving...' : 'Save Note' }}
                    </button>
                    <span v-else-if="notesSaved" class="text-[10px] text-green-600 font-bold transition-opacity duration-1000" :class="{'opacity-0': !showSavedMessage}">Saved!</span>
                </div>
                <textarea 
                    v-model="notes"
                    placeholder="Add notes for this transaction..." 
                    class="w-full text-sm border-gray-200 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 min-h-[80px]"
                ></textarea>
            </div>
        </div>

            <!-- Marks/COA Section -->
            <div class="col-span-2 bg-indigo-50/50 p-4 rounded-xl border border-indigo-100 mt-2">
                <div class="flex justify-between items-center mb-3">
                    <div class="text-[10px] font-extrabold text-indigo-500 uppercase tracking-widest">Classification & COA</div>
                    <button class="text-[10px] font-bold text-indigo-600 hover:text-indigo-800 flex items-center gap-1" @click="openAssignMark">
                        <i class="bi bi-tag-fill"></i> {{ markDetails ? 'Change Mark' : 'Assign Mark' }}
                    </button>
                </div>
                
                <div v-if="markDetails" class="space-y-4">
                    <div class="grid grid-cols-3 gap-2 pb-3 border-b border-indigo-100/50">
                        <div>
                            <p class="text-[9px] text-indigo-400 uppercase font-bold mb-0.5">Internal</p>
                            <p class="text-xs font-semibold text-gray-800">{{ markDetails.internal_report || '-' }}</p>
                        </div>
                        <div>
                            <p class="text-[9px] text-indigo-400 uppercase font-bold mb-0.5">Personal</p>
                            <p class="text-xs font-semibold text-gray-800">{{ markDetails.personal_use || '-' }}</p>
                        </div>
                        <div>
                            <p class="text-[9px] text-indigo-400 uppercase font-bold mb-0.5">Tax</p>
                            <p class="text-xs font-semibold text-gray-800">{{ markDetails.tax_report || '-' }}</p>
                        </div>
                    </div>
                    
                    <!-- CoreTax Mappings Display -->
                    <div v-if="markDetails.mappings && markDetails.mappings.length > 0">
                        <p class="text-[9px] text-indigo-500 uppercase font-black mb-2 flex items-center gap-1">
                            <i class="bi bi-diagram-3-fill"></i> Mapped CoreTax Accounts (COA)
                        </p>
                        <div class="space-y-2">
                            <div v-for="(map, idx) in markDetails.mappings" :key="idx" 
                                class="bg-white p-2 rounded-lg border border-indigo-100 shadow-sm flex items-center justify-between group hover:border-indigo-300 transition-colors"
                            >
                                <div class="flex items-center gap-3">
                                    <span class="font-mono font-bold text-xs text-indigo-700 bg-indigo-50 px-2 py-1 rounded-md border border-indigo-200">
                                        {{ map.code }}
                                    </span>
                                    <span class="text-xs font-medium text-gray-700">{{ map.name }}</span>
                                </div>
                                <span class="text-[9px] font-black px-2 py-0.5 rounded-full uppercase tracking-tighter" 
                                    :class="map.type === 'DEBIT' ? 'bg-amber-100 text-amber-700 border border-amber-200' : 'bg-emerald-100 text-emerald-700 border border-emerald-200'">
                                    {{ map.type }}
                                </span>
                            </div>
                        </div>
                    </div>
                    <div v-else class="text-[10px] text-gray-500 italic py-2">
                        This mark has no COA mappings defined.
                    </div>
                </div>
                <p v-else class="text-sm text-gray-500 italic py-4 text-center bg-white/50 rounded-lg border border-dashed border-indigo-200">
                    No marks or COA assigned to this transaction.
                </p>
            </div>
            
            <!-- HPP Section -->
            <div class="col-span-2">
                <HppDetailSection :transaction="localTxn" />
            </div>
    </div>

    <template #footer>
      <div class="flex justify-between w-full">
          <button 
            @click="deleteTxn" 
            class="btn-primary !bg-red-50 !text-red-600 !border-red-100 hover:!bg-red-100 border !py-2 !px-4"
          >
            <i class="bi bi-trash3 me-2"></i> Delete
          </button>
          
          <button @click="close" class="btn-secondary">Close</button>
      </div>
    </template>
  </BaseModal>
</template>

<script setup>
import { computed, toRefs } from 'vue';
import BaseModal from '../ui/BaseModal.vue';
import { useHistoryStore } from '../../stores/history';
import HppDetailSection from './HppDetailSection.vue';

const props = defineProps({
  isOpen: Boolean,
  transaction: Object
});

const emit = defineEmits(['close', 'assign-mark']);
const store = useHistoryStore();
const { transaction: localTxn } = toRefs(props);

const markDetails = computed(() => {
    if (!localTxn.value || !localTxn.value.mark_id) return null;
    return store.marks.find(m => m.id === localTxn.value.mark_id);
});

const close = () => emit('close');
const openAssignMark = () => emit('assign-mark', localTxn.value);

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

// Notes Logic
const notes = ref('');
const isSavingNotes = ref(false);
const notesSaved = ref(false);
const showSavedMessage = ref(false);

import { watch, ref } from 'vue';

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
        // Data is optimistic updated in store, but we can refetch/refresh if needed
        // The watcher on localTxn will handle prop updates if the parent repasses it
    } catch (e) {
        alert('Failed to update company');
    }
};
</script>
