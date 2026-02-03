<template>
  <div class="max-w-7xl mx-auto space-y-6">
    <!-- Header -->
    <div class="flex justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
        <div>
            <h3 class="text-xl font-bold text-gray-900">Database Transactions</h3>
            <p class="text-xs text-gray-500">Manage and analyze your historical statement data</p>
        </div>
        <div class="flex gap-2">
            <!-- Buttons removed as per request -->
        </div>
    </div>
    
    <!-- Bulk Actions (Floaty) -->
    <transition enter-active-class="transition duration-200 ease-out" enter-from-class="translate-y-4 opacity-0" enter-to-class="translate-y-0 opacity-100" leave-active-class="transition duration-150 ease-in" leave-from-class="translate-y-0 opacity-100" leave-to-class="translate-y-4 opacity-0">
        <div v-if="store.selectedTxnIds.length > 0" class="fixed bottom-8 left-1/2 -translate-x-1/2 z-50 bg-gray-900 text-white px-6 py-4 rounded-2xl shadow-2xl flex items-center gap-6 border border-gray-700">
            <div class="flex items-center gap-3 pr-6 border-r border-gray-700">
                <span class="bg-indigo-500 text-white w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold">{{ store.selectedTxnIds.length }}</span>
                <span class="text-sm font-medium">Selected</span>
            </div>
            
            <div class="flex items-center gap-4">
                <div class="flex flex-col gap-1">
                    <label class="text-[10px] text-gray-400 font-bold uppercase tracking-wider">Bulk Mark</label>
                    <select class="bg-gray-800 border-gray-700 text-sm rounded-lg focus:ring-indigo-500 focus:border-indigo-500 block w-40 p-1.5 text-white" @change="handleBulkMark($event.target.value)">
                        <option value="">Select Mark...</option>
                        <option value="none">-- Unmark --</option>
                        <option v-for="m in store.sortedMarks" :key="m.id" :value="m.id">
                            {{ m.internal_report || m.personal_use || 'Unnamed Mark' }}
                        </option>
                    </select>
                </div>

                <div class="flex flex-col gap-1">
                    <label class="text-[10px] text-gray-400 font-bold uppercase tracking-wider">Bulk Company</label>
                    <select class="bg-gray-800 border-gray-700 text-sm rounded-lg focus:ring-indigo-500 focus:border-indigo-500 block w-40 p-1.5 text-white" @change="handleBulkCompany($event.target.value)">
                        <option value="">Select Company...</option>
                        <option value="none">-- No Company --</option>
                        <option v-for="c in store.companies" :key="c.id" :value="c.id">
                            {{ c.name }}
                        </option>
                    </select>
                </div>

                <div class="flex items-center gap-2 ml-2">
                    <button class="p-2 hover:bg-gray-800 rounded-lg text-red-400 transition-colors" title="Bulk Delete" @click="isBulkDeleteModalOpen = true">
                         <i class="bi bi-trash3-fill"></i>
                    </button>

                    <button class="p-2 hover:bg-gray-800 rounded-lg text-gray-400 transition-colors" title="Deselect All" @click="store.deselectAll">
                        <i class="bi bi-x-lg"></i>
                    </button>
                </div>
            </div>
        </div>
    </transition>
    
    <!-- Filters -->
    <HistoryFilters />

    <!-- Table -->
    <HistoryTable @view-details="openDetails" />

    <!-- Details Modal -->
    <TransactionDetailsModal 
        :isOpen="showDetails"
        :transaction="selectedTxn"
        @close="showDetails = false"
        @assign-mark="openAssignMark"
    />

    <AssignMarkModal
        :isOpen="showAssignMark"
        :transaction="selectedTxn"
        @close="showAssignMark = false"
        @assigned="handleMarkAssigned"
    />

    <!-- Bulk Delete Confirmation Modal -->
    <ConfirmModal 
        :isOpen="isBulkDeleteModalOpen"
        title="Bulk Delete Transactions"
        :message="`Are you sure you want to delete ${store.selectedTxnIds.length} transactions? This action will permanently remove them from the database.`"
        confirmText="Delete All"
        :loading="isBulkDeleting"
        variant="danger"
        @close="isBulkDeleteModalOpen = false"
        @confirm="handleConfirmBulkDelete"
    />
  </div>
</template>


<script setup>
import { onMounted, ref } from 'vue';
import { useHistoryStore } from '../stores/history';
import HistoryFilters from '../components/history/HistoryFilters.vue';
import HistoryTable from '../components/history/HistoryTable.vue';
import TransactionDetailsModal from '../components/history/TransactionDetailsModal.vue';
import AssignMarkModal from '../components/history/AssignMarkModal.vue';
import ConfirmModal from '../components/ui/ConfirmModal.vue';

const store = useHistoryStore();
const showDetails = ref(false);
const showAssignMark = ref(false);
const selectedTxn = ref(null);

// Bulk Action State
const isBulkDeleteModalOpen = ref(false);
const isBulkDeleting = ref(false);


onMounted(() => {
    store.loadData();
});

const openDetails = (txn) => {
    selectedTxn.value = txn;
    showDetails.value = true;
};

const openAssignMark = (txn) => {
    // If called from DetailsModal, txn might be passed, otherwise reuse selectedTxn
    if (txn) selectedTxn.value = txn;
    showDetails.value = false; // Close details
    showAssignMark.value = true;
};

const handleMarkAssigned = async () => {
    await store.loadData(); // Refresh to show new mark
    showAssignMark.value = false;
};

const handleBulkMark = async (markId) => {
    if (!markId) return;
    const finalMarkId = markId === 'none' ? null : markId;
    await store.bulkAssignMark(finalMarkId);
};

const handleBulkCompany = async (companyId) => {
    if (!companyId) return;
    const finalCompanyId = companyId === 'none' ? null : companyId;
    await store.bulkAssignCompany(finalCompanyId);
};

const handleConfirmBulkDelete = async () => {
    isBulkDeleting.value = true;
    try {
        await store.bulkDelete();
        isBulkDeleteModalOpen.value = false;
    } catch (e) {
        console.error(e);
    } finally {
        isBulkDeleting.value = false;
    }
};
</script>

