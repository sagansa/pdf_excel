<template>
  <div class="w-full px-6 space-y-6" @click="showExportMenu = false">
    <!-- Header -->
    <div class="bg-white border-b border-gray-200 -mx-6 -mt-6 px-6 py-4 mb-6 sticky top-0 z-30 shadow-sm flex items-center justify-between">
      <div>
        <h3 class="text-xl font-bold text-gray-900">History & Database</h3>
        <p class="text-[10px] text-gray-500 uppercase tracking-widest mt-0.5">Manage source data and transactional adjustments</p>
      </div>
      
      <!-- Tab Navigation -->
      <div class="flex bg-gray-100 p-1 rounded-xl border border-gray-200">
        <button 
          v-for="tab in tabs" 
          :key="tab.id"
          @click="activeTab = tab.id"
          class="px-4 py-2 text-xs font-bold rounded-lg transition-all flex items-center gap-2"
          :class="activeTab === tab.id ? 'bg-white text-indigo-600 shadow-sm' : 'text-gray-500 hover:text-gray-700'"
        >
          <i :class="tab.icon"></i>
          {{ tab.name }}
        </button>
      </div>
    </div>

    <!-- Active Content Area -->
    <div class="space-y-6">
      <!-- 1. Transactions Tab -->
      <div v-show="activeTab === 'transactions'" class="space-y-6">
        <div class="flex justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
            <div>
                <h3 class="text-lg font-bold text-gray-900">Database Transactions</h3>
                <p class="text-xs text-gray-500">Manage and analyze your historical statement data</p>
            </div>
            <div class="flex gap-2">
                <button
                    @click="isImportModalOpen = true"
                    class="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors flex items-center gap-2 text-sm font-medium"
                >
                    <i class="bi bi-upload"></i>
                    Import
                </button>

                <div class="relative" @click.stop>
                    <button
                        @click="showExportMenu = !showExportMenu"
                        class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center gap-2 text-sm font-medium"
                    >
                        <i class="bi bi-download"></i>
                        Export
                        <i class="bi bi-chevron-down text-xs"></i>
                    </button>

                    <div v-if="showExportMenu" class="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 z-50">
                        <button
                            @click="handleExport('csv')"
                            class="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 rounded-t-lg flex items-center gap-2"
                        >
                            <i class="bi bi-file-earmark-spreadsheet"></i>
                            Export CSV
                        </button>
                        <button
                            @click="handleExport('excel')"
                            class="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 rounded-b-lg flex items-center gap-2"
                        >
                            <i class="bi bi-file-earmark-excel"></i>
                            Export Excel
                        </button>
                    </div>
                </div>
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

        <HistoryFilters />
        <HistoryTable @view-details="openDetails" @split-transaction="openSplitModal" />
      </div>

      <!-- Adjustment Filters (Sticky for sub-tabs) -->
      <div v-if="activeTab !== 'transactions'" class="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
        <div class="flex items-center gap-4">
            <div class="flex-1">
                <label class="block text-xs font-semibold text-gray-500 mb-1">Company</label>
                <select
                    v-model="reportStore.filters.companyId"
                    class="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
                >
                    <option value="">Select Company...</option>
                    <option v-for="c in store.companies" :key="c.id" :value="c.id">
                        {{ c.name }}
                    </option>
                </select>
            </div>
            <div class="w-32">
                <label class="block text-xs font-semibold text-gray-500 mb-1">Year</label>
                <input
                    v-model="reportStore.filters.year"
                    type="number"
                    class="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
                />
            </div>
            <div v-if="activeTab === 'rent'" class="w-40">
                <label class="block text-xs font-semibold text-gray-500 mb-1">As Of Date</label>
                <input
                    v-model="reportStore.filters.asOfDate"
                    type="date"
                    class="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
                />
            </div>
        </div>
      </div>

      <!-- 2. Inventory Tab -->
      <div v-if="activeTab === 'inventory'">
        <InventoryAdjustments 
          :key="`inv-${reportStore.filters.companyId}-${reportStore.filters.year}`"
          :company-id="reportStore.filters.companyId" 
          :year="reportStore.filters.year"
        />
      </div>

      <!-- 3. Amortization Tab -->
      <div v-if="activeTab === 'amortization'">
        <AmortizationAdjustments 
          :key="`amort-${reportStore.filters.companyId}-${reportStore.filters.year}`"
          :company-id="reportStore.filters.companyId"
          :year="reportStore.filters.year"
        />
      </div>

      <!-- 4. Rent & Prepaid Tab -->
      <div v-if="activeTab === 'rent'">
        <PrepaidExpenses 
          :key="`prepaid-${reportStore.filters.companyId}`"
          :filters="reportStore.filters" 
          @navigate-to-contract="navigateToContract"
        />
      </div>

      <!-- 5. Rental Contracts Tab -->
      <div v-if="activeTab === 'rental'">
        <RentalContracts 
          :key="`rental-${reportStore.filters.companyId}`"
          :companyId="reportStore.filters.companyId" 
          @navigate-to-prepaid="navigateToPrepaid"
        />
      </div>
    </div>

    <!-- Modals -->
    <ImportTransactionsModal
        :isOpen="isImportModalOpen"
        :companies="store.companies"
        @close="isImportModalOpen = false"
        @imported="handleImport"
    />

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

    <SplitTransactionModal
        :isOpen="showSplitModal"
        :transaction="selectedTxn"
        @close="showSplitModal = false"
        @saved="handleSplitSaved"
    />

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
import { onMounted, ref, watch } from 'vue';
import { useHistoryStore } from '../stores/history';
import { useReportsStore } from '../stores/reports';
import HistoryFilters from '../components/history/HistoryFilters.vue';
import HistoryTable from '../components/history/HistoryTable.vue';
import ImportTransactionsModal from '../components/history/ImportTransactionsModal.vue';
import TransactionDetailsModal from '../components/history/TransactionDetailsModal.vue';
import AssignMarkModal from '../components/history/AssignMarkModal.vue';
import SplitTransactionModal from '../components/history/SplitTransactionModal.vue';
import ConfirmModal from '../components/ui/ConfirmModal.vue';
import api from '../api';

// Components relocated from Reports
import InventoryAdjustments from '../components/reports/InventoryAdjustments.vue';
import AmortizationAdjustments from '../components/reports/AmortizationAdjustments.vue';
import PrepaidExpenses from '../components/reports/PrepaidExpenses.vue';
import RentalContracts from '../components/reports/RentalContracts.vue';

const store = useHistoryStore();
const reportStore = useReportsStore();

const activeTab = ref('transactions');
const tabs = [
  { id: 'transactions', name: 'Transactions', icon: 'bi bi-database-fill' },
  { id: 'inventory', name: 'Inventory', icon: 'bi bi-box-seam' },
  { id: 'amortization', name: 'Amortization', icon: 'bi bi-calendar-check' },
  { id: 'rent', name: 'Rent & Prepaid', icon: 'bi bi-house-door' },
  { id: 'rental', name: 'Rental Contracts', icon: 'bi bi-file-earmark-text' }
];

const showDetails = ref(false);
const showAssignMark = ref(false);
const showSplitModal = ref(false);
const selectedTxn = ref(null);
const isImportModalOpen = ref(false);
const showExportMenu = ref(false);

const isBulkDeleteModalOpen = ref(false);
const isBulkDeleting = ref(false);

onMounted(async () => {
    await store.loadFilters();
    store.loadData();
    
    // Ensure reportStore filters are loaded
    if (!reportStore.filters.companyId) {
      await reportStore.loadFilters();
    }
});

// Logic to sync history company filter with reportStore company filter
watch(() => store.filters.company, (val) => {
  if (val && val !== reportStore.filters.companyId) {
    reportStore.filters.companyId = val;
  }
});

const openDetails = (txn) => {
    selectedTxn.value = txn;
    showDetails.value = true;
};

const openAssignMark = (txn) => {
    if (txn) selectedTxn.value = txn;
    showDetails.value = false;
    showAssignMark.value = true;
};

const handleMarkAssigned = async () => {
    await store.loadData();
    showAssignMark.value = false;
};

const openSplitModal = (txn) => {
    selectedTxn.value = txn;
    showSplitModal.value = true;
};

const handleSplitSaved = async () => {
    await store.loadData();
    showSplitModal.value = false;
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

const handleImport = async ({ file, bankCode, companyId }) => {
    try {
        const result = await store.importTransactions(file, bankCode, companyId);
        isImportModalOpen.value = false;
        alert(`Successfully imported ${result.imported_count} transactions`);
    } catch (e) {
        alert(`Failed to import: ${e.response?.data?.error || e.message}`);
    }
};

const handleExport = async (format) => {
    showExportMenu.value = false;
    try {
        await store.exportTransactions(format);
    } catch (e) {
        alert(`Failed to export: ${e.response?.data?.error || e.message}`);
    }
};

const navigateToPrepaid = (prepaidId) => {
    activeTab.value = 'rent';
};

const navigateToContract = (contractId) => {
    activeTab.value = 'rental';
};
</script>
