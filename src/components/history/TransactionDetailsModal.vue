<template>
  <BaseModal :isOpen="isOpen" @close="close">
    <template #title>Transaction Details</template>
    
    <div v-if="localTxn" class="p-6 space-y-5">
        <div class="grid grid-cols-2 gap-y-4 gap-x-6">
            <div class="space-y-1">
                <p class="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Date</p>
                <p class="text-sm font-semibold text-gray-900">{{ formatDate(localTxn.txn_date) }}</p>
            </div>
            <div class="space-y-1">
                <p class="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Company</p>
                <p class="text-sm font-semibold text-gray-900">
                    {{ localTxn.company_name || '-' }} {{ localTxn.company_short_name ? `(${localTxn.company_short_name})` : '' }}
                </p>
            </div>
            <div class="space-y-1">
                <p class="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Amount</p>
                <p class="text-sm font-bold" :class="localTxn.db_cr === 'CR' ? 'text-green-600' : 'text-red-600'">
                    {{ localTxn.db_cr === 'CR' ? '+' : '-' }}{{ formatAmount(localTxn.amount) }}
                </p>
            </div>
            <div class="space-y-1">
                <p class="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Bank</p>
                <p class="text-sm text-gray-700">{{ localTxn.bank_code }}</p>
            </div>
            <div class="col-span-2 space-y-1">
                <p class="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Description</p>
                <p class="text-sm text-gray-700 leading-relaxed">{{ localTxn.description }}</p>
            </div>
            <div class="col-span-2 space-y-1">
                <p class="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Source File</p>
                <p class="text-xs text-gray-400 truncate">{{ localTxn.source_file }}</p>
            </div>
        </div>

        <!-- Marks Section -->
        <div class="bg-indigo-50/50 p-4 rounded-xl border border-indigo-100">
            <div class="text-xs font-bold text-indigo-400 uppercase mb-2">Category Marks</div>
            <div v-if="markDetails" class="space-y-2">
                <div><p class="text-[10px] text-gray-500 uppercase font-bold">Internal</p><p class="text-sm font-medium">{{ markDetails.internal_report }}</p></div>
                <div><p class="text-[10px] text-gray-500 uppercase font-bold">Personal</p><p class="text-sm font-medium">{{ markDetails.personal_use }}</p></div>
                <div><p class="text-[10px] text-gray-500 uppercase font-bold">Tax</p><p class="text-sm font-medium">{{ markDetails.tax_report }}</p></div>
            </div>
            <p v-else class="text-sm text-gray-500 italic">No marks assigned to this transaction.</p>
            
            <button class="mt-3 text-xs font-bold text-indigo-600 hover:text-indigo-800" @click="openAssignMark">
                <i class="bi bi-tag-fill me-1"></i> {{ markDetails ? 'Change Mark' : 'Assign Mark' }}
            </button>
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
</script>
