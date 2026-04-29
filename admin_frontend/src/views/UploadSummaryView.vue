<template>
  <div class="space-y-6">
    <PageHeader
      eyebrow="Upload Summary"
      icon="bi bi-cloud-arrow-up-fill"
      title="Uploaded file history and transaction totals"
      subtitle="Pantau file yang pernah diunggah, periode datanya, dan lakukan pembersihan jika diperlukan."
    >
      <template #actions>
        <button
          @click="refresh"
          class="btn-secondary flex items-center gap-2 py-2"
          :disabled="store.isLoading"
        >
          <i class="bi bi-arrow-clockwise" :class="{ 'animate-spin': store.isLoading }"></i>
          <span>Refresh</span>
        </button>
      </template>
    </PageHeader>

    <SectionCard
      title="Filters"
      subtitle="Saring histori upload berdasarkan bank dan tahun periode."
      body-class="p-4"
    >
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
        <FormField label="Bank">
          <SelectInput
            v-model="filterBank"
            :options="bankOptions"
            placeholder="All Banks"
          />
        </FormField>

        <FormField label="Year">
          <SelectInput
            v-model="filterYear"
            :options="yearOptions"
            placeholder="All Years"
          />
        </FormField>
      </div>
    </SectionCard>

    <TableShell>
      <table class="min-w-full upload-table">
        <thead class="upload-table-head">
          <tr>
            <th
              @click="toggleSort('source_file')"
              class="cursor-pointer px-6 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted transition-colors hover:bg-[var(--color-surface-raised)] group"
            >
              <div class="flex items-center gap-2">
                Source File
                <i v-if="sortBy === 'source_file'" class="bi" :class="sortDir === 'asc' ? 'bi-sort-alpha-down' : 'bi-sort-alpha-up-alt'"></i>
                <i v-else class="bi bi-hash text-muted opacity-0 group-hover:opacity-100"></i>
              </div>
            </th>
            <th class="px-6 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted">Bank</th>
            <th class="px-6 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted">Account</th>
            <th class="px-6 py-3 text-center text-xs font-bold uppercase tracking-wider text-muted">Txns</th>
            <th class="px-6 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted">Period</th>
            <th class="px-6 py-3 text-right text-xs font-bold uppercase tracking-wider text-muted">Totals</th>
            <th
              @click="toggleSort('last_upload')"
              class="cursor-pointer px-6 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted transition-colors hover:bg-[var(--color-surface-raised)] group"
            >
              <div class="flex items-center gap-2">
                Last Upload
                <i v-if="sortBy === 'last_upload'" class="bi" :class="sortDir === 'asc' ? 'bi-sort-numeric-down' : 'bi-sort-numeric-up-alt'"></i>
                <i v-else class="bi bi-clock text-muted opacity-0 group-hover:opacity-100"></i>
              </div>
            </th>
            <th class="px-6 py-3 text-center text-xs font-bold uppercase tracking-wider text-muted">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y" style="border-color: var(--color-border)">
          <tr v-if="store.isLoading && store.uploadSummary.length === 0">
            <td colspan="8" class="py-12 text-center">
              <span class="spinner-border h-8 w-8" style="color: var(--color-primary)" role="status"></span>
            </td>
          </tr>
          <tr v-else-if="filteredAndSortedSummary.length === 0">
            <td colspan="8" class="py-12 text-center text-muted italic">
              {{ store.uploadSummary.length === 0 ? 'No upload history found' : 'No matches found for active filters' }}
            </td>
          </tr>
          <tr v-for="item in filteredAndSortedSummary" :key="item.source_file + item.bank_code" class="upload-row">
            <td class="px-6 py-4">
              <div class="flex items-center gap-2">
                <i class="bi bi-file-earmark-pdf text-red-500 text-lg"></i>
                <span class="max-w-xs truncate text-sm font-semibold text-theme" :title="item.source_file">
                  {{ item.source_file }}
                </span>
              </div>
            </td>
            <td class="px-6 py-4 text-xs font-medium uppercase">
              <span class="border-b pb-0.5 text-theme upload-border">{{ formatBankCode(item.bank_code) }}</span>
            </td>
            <td class="px-6 py-4 text-xs">
              <div class="flex min-w-[240px] flex-col gap-2">
                <SelectInput
                  :model-value="getPendingAccountNumber(item)"
                  :options="getAccountOptions(item)"
                  placeholder="Unmapped"
                  size="sm"
                  :disabled="store.isLoading || savingRowKey === getRowKey(item)"
                  @update:model-value="updateAccountSelection(item, $event)"
                />
                <div class="flex flex-col gap-1">
                  <span v-if="item.bank_account_number" class="text-muted mono">{{ item.bank_account_number }}</span>
                  <span v-if="item.is_account_mixed" class="text-[10px] text-amber-600">Multiple accounts detected</span>
                  <span
                    v-if="savingRowKey === getRowKey(item)"
                    class="text-[10px] text-[var(--color-primary)]"
                  >
                    Saving...
                  </span>
                </div>
              </div>
            </td>
            <td class="px-6 py-4 text-center">
              <span class="upload-badge">
                {{ item.transaction_count }}
              </span>
            </td>
            <td class="px-6 py-4 text-xs text-muted mono">
              <div class="flex flex-col">
                <span>{{ formatDate(item.start_date) }}</span>
                <span class="text-[10px] text-center text-muted">to</span>
                <span>{{ formatDate(item.end_date) }}</span>
              </div>
            </td>
            <td class="px-6 py-4 text-right mono whitespace-nowrap">
              <div class="flex flex-col gap-0.5">
                <div class="text-[10px] text-red-500">DB: {{ formatAmount(item.total_debit) }}</div>
                <div class="text-[10px] text-green-600">CR: {{ formatAmount(item.total_credit) }}</div>
              </div>
            </td>
            <td class="px-6 py-4 text-[10px] text-muted mono">
              {{ formatDateTime(item.last_upload) }}
            </td>
            <td class="px-6 py-4 text-center">
              <button
                @click="openDeleteModal(item)"
                class="upload-delete"
                :title="'Delete transactions from ' + item.source_file"
                :disabled="store.isLoading"
              >
                <i class="bi bi-trash"></i>
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <template #footer>
        <div class="px-6 py-3 text-xs text-muted">
          Showing {{ filteredAndSortedSummary.length }} row{{ filteredAndSortedSummary.length !== 1 ? 's' : '' }}
        </div>
      </template>
    </TableShell>

    <DeleteSummaryModal
      :show="showDeleteModal"
      :item="itemToDelete"
      :is-loading="store.isLoading"
      @close="closeDeleteModal"
      @confirm="confirmDelete"
    />

  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { historyApi } from '../api';
import { useNotifications } from '../composables/useNotifications';
import DeleteSummaryModal from '../components/history/DeleteSummaryModal.vue';
import FormField from '../components/ui/FormField.vue';
import PageHeader from '../components/ui/PageHeader.vue';
import SectionCard from '../components/ui/SectionCard.vue';
import SelectInput from '../components/ui/SelectInput.vue';
import TableShell from '../components/ui/TableShell.vue';
import { useHistoryStore } from '../stores/history';

const store = useHistoryStore();
const notifications = useNotifications();
const filterBank = ref('');
const filterYear = ref('');
const sortBy = ref('last_upload');
const sortDir = ref('desc');
const showDeleteModal = ref(false);
const itemToDelete = ref(null);
const bankAccountDefinitions = ref([]);
const pendingAssignments = ref({});
const savingRowKey = ref('');

const refresh = async () => {
  await Promise.all([
    store.fetchUploadSummary(),
    loadBankAccountDefinitions()
  ]);
};

onMounted(() => {
  refresh();
});

const availableBanks = computed(() => {
  const banks = new Set(
    store.uploadSummary
      .map(item => item.bank_code)
      .filter(bank => bank !== null && bank !== undefined && String(bank).trim() !== '')
  );
  return Array.from(banks).sort();
});

const bankOptions = computed(() => (
  availableBanks.value.map(bank => ({
    value: bank,
    label: formatBankCode(bank)
  }))
));

const availableYears = computed(() => {
  const years = new Set();
  store.uploadSummary.forEach(item => {
    if (item.start_date) years.add(item.start_date.split('-')[0]);
    if (item.end_date) years.add(item.end_date.split('-')[0]);
  });
  return Array.from(years).sort().reverse();
});

const yearOptions = computed(() => (
  availableYears.value.map(year => ({ value: year, label: year }))
));

const filteredAndSortedSummary = computed(() => {
  const result = [...store.uploadSummary];

  const filtered = result.filter(item => {
    if (filterBank.value && item.bank_code !== filterBank.value) return false;
    if (filterYear.value) {
      const startYear = item.start_date ? item.start_date.split('-')[0] : '';
      const endYear = item.end_date ? item.end_date.split('-')[0] : '';
      if (startYear !== filterYear.value && endYear !== filterYear.value) return false;
    }
    return true;
  });

  filtered.sort((a, b) => {
    const dir = sortDir.value === 'asc' ? 1 : -1;
    let valA = a[sortBy.value];
    let valB = b[sortBy.value];

    if (sortBy.value === 'source_file') {
      valA = (valA || '').toLowerCase();
      valB = (valB || '').toLowerCase();
    }

    if (valA < valB) return -1 * dir;
    if (valA > valB) return 1 * dir;
    return 0;
  });

  return filtered;
});

const toggleSort = (key) => {
  if (sortBy.value === key) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc';
  } else {
    sortBy.value = key;
    sortDir.value = 'asc';
  }
};

const getRowKey = (item) => `${item.source_file}::${item.bank_code}`;

const loadBankAccountDefinitions = async () => {
  try {
    const response = await historyApi.getBankAccountDefinitions();
    bankAccountDefinitions.value = response.data.definitions || [];
  } catch (error) {
    console.error('Failed to load bank account definitions', error);
  }
};

const getAccountOptions = (item) => {
  const bankCode = String(item?.bank_code || '').trim().toUpperCase();
  return bankAccountDefinitions.value
    .filter((definition) => String(definition.bank_code || '').trim().toUpperCase() === bankCode)
    .map((definition) => ({
      value: definition.account_number,
      label: `${definition.display_name} (${definition.account_number})`
    }));
};

const getPendingAccountNumber = (item) => {
  const key = getRowKey(item);
  if (Object.prototype.hasOwnProperty.call(pendingAssignments.value, key)) {
    return pendingAssignments.value[key];
  }
  if (item.is_account_mixed) return '';
  return item.bank_account_number || '';
};

const updateAccountSelection = async (item, nextValue) => {
  const key = getRowKey(item);
  const previousValue = item.is_account_mixed ? '' : (item.bank_account_number || '');
  pendingAssignments.value = {
    ...pendingAssignments.value,
    [key]: nextValue || ''
  };

  if ((nextValue || '') === previousValue) {
    return;
  }

  savingRowKey.value = key;
  try {
    await historyApi.assignUploadedFileBankAccount({
      source_file: item.source_file,
      bank_code: item.bank_code,
      account_number: nextValue || null,
    });
    await store.fetchUploadSummary();
    notifications.success(`Account updated for ${item.source_file}`);
  } catch (error) {
    pendingAssignments.value = {
      ...pendingAssignments.value,
      [key]: previousValue
    };
    notifications.error(error?.response?.data?.error || 'Failed to update uploaded file account');
  } finally {
    savingRowKey.value = '';
  }
};

const openDeleteModal = (item) => {
  itemToDelete.value = item;
  showDeleteModal.value = true;
};

const closeDeleteModal = () => {
  showDeleteModal.value = false;
  itemToDelete.value = null;
};

const confirmDelete = async () => {
  if (!itemToDelete.value) return;
  try {
    const item = itemToDelete.value;
    await store.deleteBySourceFile(item.source_file, item.bank_code);
    closeDeleteModal();
  } catch (err) {
    alert(`Failed to delete transactions: ${err.response?.data?.error || err.message}`);
  }
};

const formatDate = (dateStr) => {
  if (!dateStr) return '-';
  return dateStr.split(' ')[0];
};

const formatDateTime = (dateTimeStr) => {
  if (!dateTimeStr) return '-';
  const parts = dateTimeStr.split(' ');
  return `${parts[0]} ${parts[1]}`;
};

const formatAmount = (amount) => new Intl.NumberFormat('id-ID').format(amount);

const formatBankCode = (bankCode) => {
  const value = (bankCode || '').toString();
  if (!value) return 'Unknown Bank';
  return value.replace('_CC', ' Credit Card');
};
</script>

<style scoped>
.upload-table-head {
  background: var(--color-surface-muted);
}

.upload-row {
  transition: background-color 160ms ease;
}

.upload-row:hover {
  background: rgba(15, 118, 110, 0.05);
}

.upload-border {
  border-color: var(--color-border);
}

.upload-badge {
  @apply rounded-lg px-2.5 py-1 text-xs font-bold;
  background: rgba(15, 118, 110, 0.10);
  border: 1px solid rgba(15, 118, 110, 0.18);
  color: var(--color-primary);
}

.upload-delete {
  @apply rounded-lg border border-transparent p-2 transition-colors;
  color: var(--color-text-muted);
}

.upload-delete:hover {
  color: var(--color-danger);
  background: rgba(185, 28, 28, 0.08);
  border-color: rgba(185, 28, 28, 0.18);
}
</style>
