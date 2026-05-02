<template>
  <div class="w-full space-y-6" @click="showExportMenu = false">
    <PageHeader
      eyebrow="History & Database"
      icon="bi bi-database-fill"
      title="Transaction review and adjustment workspace"
      subtitle="Kelola transaksi mentah, lakukan bulk action, dan masuk ke modul penyesuaian tanpa keluar dari satu area kerja."
      :badges="headerBadges"
    />

    <SectionCard body-class="p-3">
      <div class="history-tabs-wrap">
          <button 
            v-for="tab in tabs" 
            :key="tab.id"
            @click="activeTab = tab.id"
            class="history-tab"
            :class="{ 'history-tab--active': activeTab === tab.id }"
          >
            <i :class="tab.icon"></i>
            {{ tab.name }}
          </button>
      </div>
    </SectionCard>

    <!-- Active Content Area -->
    <div class="space-y-6">
      <!-- 1. Transactions Tab -->
      <div v-show="activeTab === 'transactions'" class="space-y-5">
        <SectionCard
          title="Database Transactions"
          subtitle="Manage and analyze your historical statement data"
          body-class="hidden"
        >
          <template #actions>
            <div class="flex flex-wrap gap-2">
                <button
                    @click="isImportModalOpen = true"
                    class="btn-primary !rounded-xl gap-2 text-sm"
                >
                    <i class="bi bi-upload"></i>
                    Import
                </button>

                <button
                    @click="isManualJournalModalOpen = true"
                    class="btn-secondary !rounded-xl gap-2 text-sm"
                >
                    <i class="bi bi-journal-plus"></i>
                    Manual Journal
                </button>

                <div class="relative" @click.stop>
                    <button
                        @click="showExportMenu = !showExportMenu"
                        class="btn-secondary !rounded-xl gap-2 text-sm"
                    >
                        <i class="bi bi-download"></i>
                        Export
                        <i class="bi bi-chevron-down text-xs"></i>
                    </button>

                    <div v-if="showExportMenu" class="history-menu absolute right-0 mt-2 w-48 z-50">
                        <button
                            @click="handleExport('csv')"
                            class="history-menu__item rounded-t-xl"
                        >
                            <i class="bi bi-file-earmark-spreadsheet"></i>
                            Export CSV
                        </button>
                        <button
                            @click="handleExport('excel')"
                            class="history-menu__item rounded-b-xl"
                        >
                            <i class="bi bi-file-earmark-excel"></i>
                            Export Excel
                        </button>
                    </div>
                </div>
            </div>
          </template>
        </SectionCard>

        <!-- Bulk Actions (Floaty) -->
        <transition enter-active-class="transition duration-200 ease-out" enter-from-class="translate-y-4 opacity-0" enter-to-class="translate-y-0 opacity-100" leave-active-class="transition duration-150 ease-in" leave-from-class="translate-y-0 opacity-100" leave-to-class="translate-y-4 opacity-0">
            <div v-if="store.selectedTxnIds.length > 0" class="bulk-bar fixed bottom-6 left-1/2 z-50 flex w-[min(92vw,920px)] -translate-x-1/2 flex-col gap-4 rounded-3xl px-5 py-4 md:flex-row md:items-center md:justify-between">
                <div class="flex items-center gap-3 md:pr-6 md:border-r md:border-white/10">
                    <span class="bulk-bar__count">{{ store.selectedTxnIds.length }}</span>
                    <span class="text-sm font-medium">Selected</span>
                </div>

                <div class="flex flex-col gap-3 md:flex-row md:items-center md:gap-3 flex-1">
                    <div class="flex flex-1 items-center gap-3">
                        <div class="w-48 group/select">
                           <SelectInput
                               v-model="bulkActionForm.companyId"
                               :options="bulkCompanyOptions"
                               placeholder="Assign Company..."
                               size="sm"
                               class="bulk-bar__input"
                           />
                        </div>
                        <div class="w-64 group/select">
                           <SearchableSelect
                               v-model="bulkActionForm.markId"
                               :options="bulkMarkOptions"
                               placeholder="Assign Mark..."
                               size="sm"
                               class="bulk-bar__input"
                           />
                        </div>
                        <button 
                            @click="handleBulkApply" 
                            class="h-8 px-4 rounded-xl bg-primary text-white text-xs font-bold hover:bg-primary-strong transition-all shadow-lg shadow-primary/20 disabled:opacity-50 disabled:cursor-not-allowed"
                            :disabled="isBulkAssigning || (!bulkActionForm.companyId && !bulkActionForm.markId)"
                        >
                            <span v-if="isBulkAssigning" class="spinner-border w-3 h-3 me-1"></span>
                            Apply
                        </button>
                    </div>
                </div>

                <div class="flex items-center gap-2 pl-4 border-l border-white/10">
                    <button class="bulk-bar__icon bulk-bar__icon--danger" title="Bulk Delete" @click="isBulkDeleteModalOpen = true">
                         <i class="bi bi-trash3-fill text-sm"></i>
                    </button>

                    <button class="bulk-bar__icon" title="Deselect All" @click="store.deselectAll">
                        <i class="bi bi-x-lg text-sm"></i>
                    </button>
                </div>
            </div>
        </transition>

        <HistoryFilters />
        <HistoryTable @view-details="openDetails" @split-transaction="openSplitModal" />
      </div>

      <!-- Adjustment Filters (Sticky for sub-tabs) -->
      <SectionCard
        v-if="activeTab !== 'transactions' && activeTab !== 'remaining_storages'"
        content-class="mb-6"
        body-class="p-4"
      >
        <div class="flex items-center gap-4">
            <FormField label="Company" label-class="!text-xs" wrapper-class="flex-1">
                <SelectInput
                    v-model="reportStore.filters.companyId"
                    :options="reportCompanyOptions"
                    placeholder="Select Company..."
                />
            </FormField>
            <FormField label="Year" label-class="!text-xs" wrapper-class="w-32">
                <TextInput
                    v-model="reportStore.filters.year"
                    type="number"
                />
            </FormField>
        </div>
      </SectionCard>

      <!-- 1.1. Remaining Storages Tab -->
      <div v-if="activeTab === 'remaining_storages'">
        <RemainingStoragesTable />
      </div>

      <!-- 1.5. COGS Batches Tab -->
      <div v-if="activeTab === 'hpp_batches'">
        <HppBatchesTab 
          :key="`hpp-${reportStore.filters.companyId}-${reportStore.filters.year}`"
          :company-id="reportStore.filters.companyId"
          :year="reportStore.filters.year"
        />
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

      <!-- 4. Service Tax Handling Tab -->
      <div v-if="activeTab === 'services'">
        <ServiceTaxHandling
          :key="`service-${reportStore.filters.companyId}-${reportStore.filters.year}`"
          :company-id="reportStore.filters.companyId"
          :year="reportStore.filters.year"
        />
      </div>

      <!-- 5. Rental Contracts Tab -->
      <div v-if="activeTab === 'rental'">
        <RentalContracts 
          :key="`rental-${reportStore.filters.companyId}`"
          :companyId="reportStore.filters.companyId" 
        />
      </div>

      <!-- 6. Payroll Tab -->
      <div v-if="activeTab === 'payroll'">
        <PayrollSalaryHandling
          :key="`payroll-${reportStore.filters.companyId}-${reportStore.filters.year}`"
          :company-id="reportStore.filters.companyId"
          :year="reportStore.filters.year"
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

    <ManualJournalModal
        :isOpen="isManualJournalModalOpen"
        :editId="journalEditId"
        :companies="store.companies"
        :marks="store.sortedMarks"
        :coaList="store.coaList"
        @close="handleManualJournalClose"
        @saved="handleManualJournalSaved"
    />

    <TransactionDetailsModal
        :isOpen="showDetails"
        :transaction="selectedTxn"
        @close="showDetails = false"
        @assign-mark="openAssignMark"
        @edit-journal="handleEditJournal"
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
import { computed, onMounted, ref, watch } from 'vue';
import { useHistoryStore } from '../stores/history';
import { useReportsStore } from '../stores/reports';
import HistoryFilters from '../components/history/HistoryFilters.vue';
import HistoryTable from '../components/history/HistoryTable.vue';
import SearchableSelect from '../components/ui/SearchableSelect.vue';
import ImportTransactionsModal from '../components/history/ImportTransactionsModal.vue';
import ManualJournalModal from '../components/history/ManualJournalModal.vue';
import TransactionDetailsModal from '../components/history/TransactionDetailsModal.vue';
import AssignMarkModal from '../components/history/AssignMarkModal.vue';
import SplitTransactionModal from '../components/history/SplitTransactionModal.vue';
import ConfirmModal from '../components/ui/ConfirmModal.vue';
import FormField from '../components/ui/FormField.vue';
import PageHeader from '../components/ui/PageHeader.vue';
import SectionCard from '../components/ui/SectionCard.vue';
import SelectInput from '../components/ui/SelectInput.vue';
import TextInput from '../components/ui/TextInput.vue';
import api from '../api';

// Components relocated from Reports
import InventoryAdjustments from '../components/reports/InventoryAdjustments.vue';
import AmortizationAdjustments from '../components/reports/AmortizationAdjustments.vue';
import RentalContracts from '../components/reports/RentalContracts.vue';
import ServiceTaxHandling from '../components/history/ServiceTaxHandling.vue';
import PayrollSalaryHandling from '../components/history/PayrollSalaryHandling.vue';
import HppBatchesTab from '../components/history/HppBatchesTab.vue';
import RemainingStoragesTable from '../components/history/RemainingStoragesTable.vue';

const store = useHistoryStore();
const reportStore = useReportsStore();

const activeTab = ref('transactions');
const headerBadges = [
  { icon: 'bi bi-filter', label: 'Filter-heavy' },
  { icon: 'bi bi-stack', label: 'Bulk edits' },
  { icon: 'bi bi-box-seam', label: 'Operational data' }
];
const tabs = [
  { id: 'transactions', name: 'Transactions', icon: 'bi bi-database-fill' },
  { id: 'remaining_storages', name: 'Remaining Storage', icon: 'bi bi-archive' },
  { id: 'hpp_batches', name: 'COGS Batches', icon: 'bi bi-boxes' },
  { id: 'inventory', name: 'Inventory', icon: 'bi bi-box-seam' },
  { id: 'amortization', name: 'Amortization', icon: 'bi bi-calendar-check' },
  { id: 'services', name: 'Service Tax', icon: 'bi bi-receipt-cutoff' },
  { id: 'rental', name: 'Rental Contracts', icon: 'bi bi-file-earmark-text' },
  { id: 'payroll', name: 'Payroll', icon: 'bi bi-people' }
];

const showDetails = ref(false);
const showAssignMark = ref(false);
const showSplitModal = ref(false);
const selectedTxn = ref(null);
const isImportModalOpen = ref(false);
const isManualJournalModalOpen = ref(false);
const journalEditId = ref(null);
const showExportMenu = ref(false);

const isBulkDeleteModalOpen = ref(false);
const isBulkDeleting = ref(false);
const isBulkAssigning = ref(false);

const bulkActionForm = ref({
    companyId: '',
    markId: ''
});

const buildMarkLabel = (mark) => {
  const parts = [mark?.internal_report, mark?.personal_use, mark?.tax_report]
    .map(value => String(value || '').trim())
    .filter(Boolean);
  const uniqueParts = [...new Set(parts)];
  return uniqueParts.length ? uniqueParts.join(' / ') : 'Marked';
};

const bulkCompanyOptions = computed(() => [
  { id: 'none', label: '-- Unassign Company --' },
  ...(store.companies || []).map(c => ({ id: c.id, label: c.name }))
]);

const bulkMarkOptions = computed(() => [
  { id: 'none', label: '-- Unmark --' },
  ...(store.sortedMarks || []).map(m => ({ 
    id: m.id, 
    label: buildMarkLabel(m)
  }))
]);

watch(() => store.selectedTxnIds.length, (newVal) => {
    if (newVal === 0) {
        bulkActionForm.value.companyId = '';
        bulkActionForm.value.markId = '';
    }
});

const reportCompanyOptions = computed(() => (
  (store.companies || []).map(company => ({
    value: company.id,
    label: company.name
  }))
));

const ensureAdjustmentCompanySelected = async () => {
  if (reportStore.filters.companyId) return;

  const fallbackCompanyId = store.filters.company || store.companies?.[0]?.id || null;
  if (!fallbackCompanyId) return;

  reportStore.filters.companyId = fallbackCompanyId;
  await reportStore.saveFilters();
};

onMounted(async () => {
    await store.loadFilters();
    await store.loadData();
    
    // Ensure reportStore filters are loaded
    if (!reportStore.filters.companyId) {
      await reportStore.loadFilters();
    }

    await ensureAdjustmentCompanySelected();
});

// Logic to sync history company filter with reportStore company filter
watch(() => store.filters.company, (val) => {
  if (val && val !== reportStore.filters.companyId) {
    reportStore.filters.companyId = val;
  }
});

// Watch reportStore company changes and reload history data
watch(() => reportStore.filters.companyId, async (newCompanyId, oldCompanyId) => {
  if (newCompanyId !== oldCompanyId) {
    console.log('Report company changed, reloading history transactions...');
    store.setFilter('company', newCompanyId || '');
    await store.loadData();
  }
});

watch(() => store.companies, async () => {
  await ensureAdjustmentCompanySelected();
}, { deep: true });

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

const handleBulkApply = async () => {
    const { companyId, markId } = bulkActionForm.value;
    isBulkAssigning.value = true;
    try {
        if (companyId) {
            const finalCompanyId = companyId === 'none' ? null : companyId;
            await store.bulkAssignCompany(finalCompanyId);
        }
        if (markId) {
            const finalMarkId = markId === 'none' ? null : markId;
            await store.bulkAssignMark(finalMarkId);
        }
        // Reset form on success
        bulkActionForm.value.companyId = '';
        bulkActionForm.value.markId = '';
    } catch (e) {
        console.error(e);
    } finally {
        isBulkAssigning.value = false;
    }
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

const handleImport = async ({ file, bankCode, companyId, bankAccountNumber }) => {
    try {
        const result = await store.importTransactions(file, bankCode, companyId, bankAccountNumber);
        isImportModalOpen.value = false;
        alert(`Successfully imported ${result.imported_count} transactions`);
    } catch (e) {
        alert(`Failed to import: ${e.response?.data?.error || e.message}`);
    }
};

const handleManualJournalSaved = async () => {
    await store.loadData();
    journalEditId.value = null;
    isManualJournalModalOpen.value = false;
};

const handleEditJournal = (id) => {
    journalEditId.value = id;
    showDetails.value = false;
    isManualJournalModalOpen.value = true;
};

const handleManualJournalClose = () => {
    isManualJournalModalOpen.value = false;
    journalEditId.value = null;
};

const handleExport = async (format) => {
    showExportMenu.value = false;
    try {
        await store.exportTransactions(format);
    } catch (e) {
        alert(`Failed to export: ${e.response?.data?.error || e.message}`);
    }
};

</script>

<style scoped>
.history-tabs-wrap {
  @apply flex gap-2 overflow-x-auto;
}

.history-tab {
  @apply inline-flex items-center gap-2 whitespace-nowrap rounded-2xl px-4 py-2.5 text-sm font-medium transition-all;
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
  color: var(--color-text-muted);
}

.history-tab:hover {
  color: var(--color-text);
  border-color: var(--color-border-strong);
}

.history-tab--active {
  background: rgba(15, 118, 110, 0.12);
  border-color: rgba(15, 118, 110, 0.18);
  color: var(--color-primary);
  box-shadow: var(--shadow-soft);
}

.history-menu {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 16px;
  box-shadow: var(--shadow-card);
  overflow: hidden;
}

.history-menu__item {
  @apply flex w-full items-center gap-2 px-4 py-2 text-left text-sm transition-colors;
  color: var(--color-text);
}

.history-menu__item:hover {
  background: var(--color-surface-muted);
}

.bulk-bar {
  background: rgba(15, 21, 28, 0.92);
  color: #fff;
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 24px 48px rgba(0, 0, 0, 0.26);
  backdrop-filter: blur(18px);
}

.bulk-bar__count {
  @apply inline-flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-strong));
}

.bulk-bar__select {
  @apply block w-40 rounded-xl px-3 py-2 text-sm;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: #fff;
}

.bulk-bar__icon {
  @apply rounded-xl p-2 transition-colors;
  color: rgba(255, 255, 255, 0.7);
}

.bulk-bar__icon:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}

.bulk-bar__icon--danger {
  color: #fca5a5;
}

.bulk-bar__input :deep(.ui-input-shell) {
  @apply !bg-white/5 !border-white/10 !rounded-xl !h-8 !border;
}

.bulk-bar__input :deep(input), .bulk-bar__input :deep(select) {
  @apply !text-white !text-[11px] !font-medium !py-0;
}

.bulk-bar__input :deep(.text-muted) {
  @apply !text-white/40;
}

.bulk-bar__button {
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 0;
  display: flex;
  align-items: center;
}
</style>
