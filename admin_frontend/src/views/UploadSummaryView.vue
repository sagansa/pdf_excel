<template>
  <div class="space-y-4">
    <PageHeader
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

    <UploadAttentionQueue
      :groups="attentionGroups"
      :total-issues="totalIssues"
      :busy-key="savingRowKey"
      :options-for="getAccountOptions"
      :row-key-of="getRowKey"
      @assign="handleAssign"
    />

    <TableShell>
      <template #toolbar>
        <div class="upload-toolbar">
          <div class="upload-toolbar__filters">
            <div class="upload-toolbar__field">
              <label class="upload-toolbar__label" for="upload-filter-bank">Bank</label>
              <SelectInput
                id="upload-filter-bank"
                v-model="filterBank"
                :options="bankOptions"
                placeholder="All Banks"
                size="sm"
                class="upload-toolbar__bank"
              />
            </div>
            <div class="upload-toolbar__field">
              <label class="upload-toolbar__label" for="upload-filter-year">Year</label>
              <SelectInput
                id="upload-filter-year"
                v-model="filterYear"
                :options="yearOptions"
                placeholder="All Years"
                size="sm"
                class="upload-toolbar__year"
              />
            </div>
            <div class="upload-toolbar__field">
              <label class="upload-toolbar__label" for="upload-filter-status">Status</label>
              <SelectInput
                id="upload-filter-status"
                v-model="filterStatus"
                :options="statusOptions"
                placeholder="All statuses"
                size="sm"
                class="upload-toolbar__status"
              />
            </div>
            <div class="upload-toolbar__field">
              <label class="upload-toolbar__label" for="upload-filter-name">File</label>
              <div class="upload-toolbar__search">
                <i class="bi bi-search" aria-hidden="true"></i>
                <TextInput
                  id="upload-filter-name"
                  v-model="filterName"
                  placeholder="Cari nama file…"
                  size="sm"
                />
              </div>
            </div>
          </div>
          <span class="upload-toolbar__total" role="status">
            {{ filteredAndSortedSummary.length }} of {{ store.uploadSummary.length }} files
          </span>
        </div>
      </template>

      <table class="min-w-full upload-table">
        <thead class="upload-table-head">
          <tr>
            <th
              scope="col"
              @click="toggleSort('source_file')"
              class="upload-th upload-th--sortable group"
            >
              <span class="upload-th__inner">
                Source File
                <i v-if="sortBy === 'source_file'" class="bi" :class="sortDir === 'asc' ? 'bi-sort-alpha-down' : 'bi-sort-alpha-up-alt'"></i>
              </span>
            </th>
            <th scope="col" class="upload-th">Bank</th>
            <th scope="col" class="upload-th">Account</th>
            <th scope="col" class="upload-th upload-th--r">Txns</th>
            <th scope="col" class="upload-th">Period</th>
            <th scope="col" class="upload-th upload-th--r">Debit</th>
            <th scope="col" class="upload-th upload-th--r">Credit</th>
            <th
              scope="col"
              @click="toggleSort('last_upload')"
              class="upload-th upload-th--sortable"
            >
              <span class="upload-th__inner">
                Last Upload
                <i v-if="sortBy === 'last_upload'" class="bi" :class="sortDir === 'asc' ? 'bi-sort-numeric-down' : 'bi-sort-numeric-up-alt'"></i>
              </span>
            </th>
            <th scope="col" class="upload-th upload-th--c"><span class="sr-only">Actions</span></th>
          </tr>
        </thead>
        <tbody class="upload-tbody">
          <tr v-if="store.isLoading && store.uploadSummary.length === 0">
            <td colspan="9" class="upload-state">
              <span class="spinner-border h-8 w-8" style="color: var(--color-primary)" role="status"></span>
            </td>
          </tr>
          <tr v-else-if="store.uploadSummary.length === 0">
            <td colspan="9" class="upload-state">
              <i class="bi bi-cloud-arrow-up upload-state__icon" aria-hidden="true"></i>
              <p class="upload-state__title">No upload history found</p>
              <p class="upload-state__hint">Transaksi hasil impor statement akan muncul di sini.</p>
            </td>
          </tr>
          <tr v-else-if="filteredAndSortedSummary.length === 0">
            <td colspan="9" class="upload-state">
              <i class="bi bi-funnel upload-state__icon" aria-hidden="true"></i>
              <p class="upload-state__title">No matches found for active filters</p>
              <button type="button" class="upload-state__action" @click="clearFilters">
                Bersihkan filter
              </button>
            </td>
          </tr>
          <tr
            v-for="item in filteredAndSortedSummary"
            :key="getRowKey(item)"
            class="upload-row"
          >
            <td class="upload-td upload-td--file">
              <div class="upload-file">
                <i class="bi bi-file-earmark-pdf upload-file__icon" aria-hidden="true"></i>
                <span class="upload-file__name" :title="item.source_file">
                  {{ item.source_file || '(no filename)' }}
                </span>
              </div>
            </td>
            <td class="upload-td upload-td--bank">{{ formatBankCode(item.bank_code) }}</td>
            <td class="upload-td upload-td--account">
              <UploadAccountChip
                :item="item"
                :label="accountLabel(item)"
                :options="getAccountOptions(item)"
                :busy="savingRowKey === getRowKey(item)"
                :disabled="store.isLoading"
                @assign="handleAssign"
              />
            </td>
            <td class="upload-td upload-td--r upload-td--mono">{{ item.transaction_count }}</td>
            <td class="upload-td upload-td--mono upload-td--period">{{ periodLine(item) }}</td>
            <td class="upload-td upload-td--r upload-td--mono" :class="{ 'upload-td--zero': !item.total_debit }">
              {{ formatAmount(item.total_debit) }}
            </td>
            <td class="upload-td upload-td--r upload-td--mono">{{ formatAmount(item.total_credit) }}</td>
            <td class="upload-td upload-td--mono upload-td--time">{{ formatDateTime(item.last_upload) }}</td>
            <td class="upload-td upload-td--c">
              <button
                type="button"
                @click="openDeleteModal(item)"
                class="upload-delete"
                :title="'Delete transactions from ' + (item.source_file || 'this upload')"
                :aria-label="'Delete transactions from ' + (item.source_file || 'this upload')"
                :disabled="store.isLoading"
              >
                <i class="bi bi-trash3"></i>
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <template #footer>
        <div class="upload-footer">
          <span>Showing {{ filteredAndSortedSummary.length }} row{{ filteredAndSortedSummary.length !== 1 ? 's' : '' }}</span>
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
import UploadAccountChip from '../components/history/UploadAccountChip.vue';
import UploadAttentionQueue from '../components/history/UploadAttentionQueue.vue';
import PageHeader from '../components/ui/PageHeader.vue';
import SelectInput from '../components/ui/SelectInput.vue';
import TableShell from '../components/ui/TableShell.vue';
import TextInput from '../components/ui/TextInput.vue';
import { useHistoryStore } from '../stores/history';

const store = useHistoryStore();
const notifications = useNotifications();
const filterBank = ref('');
const filterYear = ref('');
const filterName = ref('');
const filterStatus = ref('');
const statusOptions = [
  { value: 'mapped', label: 'Mapped' },
  { value: 'unmapped', label: 'Unmapped' },
  { value: 'mixed', label: 'Mixed' }
];
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

// ---------------------------------------------------------------- attention queue

const attentionGroups = computed(() => {
  const items = store.uploadSummary;
  return [
    {
      id: 'unmapped',
      label: 'Unmapped accounts',
      tone: 'amber',
      items: items.filter((item) => !item.is_account_mixed && !item.bank_account_number)
    },
    {
      id: 'mixed',
      label: 'Mixed accounts',
      tone: 'amber',
      items: items.filter((item) => item.is_account_mixed)
    }
  ];
});

const totalIssues = computed(() =>
  attentionGroups.value.reduce((sum, group) => sum + group.items.length, 0)
);

// ---------------------------------------------------------------- filters & sort

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

const clearFilters = () => {
  filterBank.value = '';
  filterYear.value = '';
  filterName.value = '';
  filterStatus.value = '';
};

const matchesStatus = (item) => {
  if (!filterStatus.value) return true;
  if (filterStatus.value === 'mapped') {
    return !item.is_account_mixed && !!item.bank_account_number;
  }
  if (filterStatus.value === 'unmapped') return !item.is_account_mixed && !item.bank_account_number;
  if (filterStatus.value === 'mixed') return item.is_account_mixed;
  return true;
};

const filteredAndSortedSummary = computed(() => {
  const needle = filterName.value.trim().toLowerCase();

  const filtered = store.uploadSummary.filter(item => {
    if (filterBank.value && item.bank_code !== filterBank.value) return false;
    if (filterYear.value) {
      const startYear = item.start_date ? item.start_date.split('-')[0] : '';
      const endYear = item.end_date ? item.end_date.split('-')[0] : '';
      if (startYear !== filterYear.value && endYear !== filterYear.value) return false;
    }
    if (needle && !(item.source_file || '').toLowerCase().includes(needle)) return false;
    if (!matchesStatus(item)) return false;
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

// ---------------------------------------------------------------- account mapping

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

const accountLabel = (item) => {
  if (item.is_account_mixed) return 'Mixed';
  const number = item.bank_account_number;
  if (!number) return 'Unmapped';
  const match = getAccountOptions(item).find((option) => option.value === number);
  return match ? match.label : number;
};

const handleAssign = async (item, nextValue) => {
  const key = getRowKey(item);
  const previousValue = item.is_account_mixed ? '' : (item.bank_account_number || '');

  if ((nextValue || '') === previousValue) return;

  savingRowKey.value = key;
  try {
    await historyApi.assignUploadedFileBankAccount({
      source_file: item.source_file,
      bank_code: item.bank_code,
      account_number: nextValue || null,
    });
    await Promise.all([store.fetchUploadSummary(), loadBankAccountDefinitions()]);
    notifications.success(`Account updated for ${item.source_file || 'upload'}`);
  } catch (error) {
    notifications.error(error?.response?.data?.error || 'Failed to update uploaded file account');
  } finally {
    savingRowKey.value = '';
  }
};

// ---------------------------------------------------------------- delete

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
    notifications.error(`Failed to delete transactions: ${err.response?.data?.error || err.message}`);
  }
};

// ---------------------------------------------------------------- formatting

const periodLine = (item) => {
  const start = (item.start_date || '').split(' ')[0];
  const end = (item.end_date || '').split(' ')[0];
  if (!start && !end) return '-';
  return `${start || '-'} – ${end || '-'}`;
};

const formatDateTime = (dateTimeStr) => {
  if (!dateTimeStr) return '-';
  const parts = dateTimeStr.split(' ');
  const time = (parts[1] || '').slice(0, 5);
  return `${parts[0]} ${time}`.trim();
};

const formatAmount = (amount) => new Intl.NumberFormat('id-ID').format(amount || 0);

const formatBankCode = (bankCode) => {
  const value = (bankCode || '').toString();
  if (!value) return 'Unknown Bank';
  return value.replace('_CC', ' Credit Card');
};
</script>

<style scoped>
.upload-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 16px;
}

.upload-toolbar__filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}

.upload-toolbar__field {
  display: flex;
  align-items: center;
  gap: 8px;
}

.upload-toolbar__label {
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-text-muted);
}

.upload-toolbar__bank {
  width: 150px;
}

.upload-toolbar__status {
  width: 140px;
}

.upload-toolbar__year {
  width: 110px;
}

.upload-toolbar__search {
  position: relative;
  width: 220px;
}

.upload-toolbar__search > i {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 11px;
  color: var(--color-text-muted);
  pointer-events: none;
}

.upload-toolbar__search :deep(input) {
  padding-left: 28px;
}

.upload-toolbar__total {
  font: 500 12px var(--font-mono);
  color: var(--color-text-muted);
  white-space: nowrap;
}

.upload-table-head {
  background: var(--color-surface-muted);
}

.upload-th {
  padding: 10px;
  text-align: left;
  font-size: 10.5px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-text-muted);
  border-bottom: 1px solid var(--color-border-strong);
  white-space: nowrap;
}

.upload-th--sortable {
  cursor: pointer;
}

.upload-th--sortable:hover {
  color: var(--color-text);
}

.upload-th--r {
  text-align: right;
}

.upload-th--c {
  text-align: center;
}

.upload-th__inner {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.upload-tbody :deep(tr),
.upload-tbody tr {
  transition: background-color 160ms ease;
}

.upload-td {
  height: 46px;
  padding: 0 10px;
  border-bottom: 1px solid var(--color-border);
  font-size: 13px;
  color: var(--color-text);
  white-space: nowrap;
  vertical-align: middle;
}

.upload-tbody tr:last-child .upload-td {
  border-bottom: none;
}

.upload-tbody tr:hover .upload-td {
  background: rgba(15, 118, 110, 0.04);
}

.upload-td--file {
  max-width: 185px;
}

.upload-file {
  display: flex;
  align-items: center;
  gap: 9px;
  min-width: 0;
}

.upload-file__icon {
  color: var(--color-danger);
  font-size: 14px;
  flex: none;
}

.upload-file__name {
  font-weight: 600;
  font-size: 12.5px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.upload-td--bank {
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  color: var(--color-text-muted);
}

.upload-td--account {
  position: relative;
}

.upload-td--account :deep(.acct-chip__editor) {
  position: absolute;
  left: 8px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 5;
  background: var(--color-surface);
  border: 1px solid var(--color-border-strong);
  border-radius: 10px;
  padding: 6px;
  box-shadow: var(--shadow-soft);
}

.upload-td--r {
  text-align: right;
}

.upload-td--c {
  text-align: center;
}

.upload-td--mono {
  font-family: var(--font-mono);
  font-size: 12px;
}

.upload-td--period {
  font-size: 11px;
  color: var(--color-text-muted);
}

.upload-td--zero {
  color: var(--color-text-muted);
}

.upload-td--time {
  font-size: 11px;
  color: var(--color-text-muted);
}

.upload-delete {
  border: 1px solid transparent;
  border-radius: 8px;
  background: none;
  padding: 5px 7px;
  color: var(--color-text-muted);
  cursor: pointer;
  transition: color 140ms ease, background-color 140ms ease, border-color 140ms ease;
}

.upload-delete:hover:not(:disabled) {
  color: var(--color-danger);
  background: rgba(185, 28, 28, 0.08);
  border-color: rgba(185, 28, 28, 0.18);
}

.upload-delete:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.upload-delete:focus-visible {
  outline: 2px solid var(--color-primary-ring);
  outline-offset: 1px;
}

.upload-state {
  padding: 44px 16px;
  text-align: center;
  color: var(--color-text-muted);
}

.upload-state__icon {
  display: block;
  font-size: 26px;
  margin: 0 auto 10px;
  color: var(--color-border-strong);
}

.upload-state__title {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
  color: var(--color-text);
}

.upload-state__hint {
  margin: 4px 0 0;
  font-size: 12px;
}

.upload-state__action {
  margin-top: 10px;
  border: 1px solid var(--color-border-strong);
  border-radius: 9px;
  background: var(--color-surface-raised);
  padding: 6px 12px;
  font: 600 12px var(--font-sans);
  color: var(--color-text);
  cursor: pointer;
  transition: border-color 140ms ease, color 140ms ease;
}

.upload-state__action:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.upload-state__action:focus-visible {
  outline: 2px solid var(--color-primary-ring);
  outline-offset: 1px;
}

.upload-footer {
  padding: 10px 16px;
  font-size: 12px;
  color: var(--color-text-muted);
}

@media (max-width: 1200px) {
  .upload-td--time,
  .upload-td--bank {
    display: none;
  }

  .upload-th:nth-child(2),
  .upload-th:nth-child(8) {
    display: none;
  }
}

@media (max-width: 900px) {
  .upload-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .upload-toolbar__total {
    align-self: flex-end;
  }
}
</style>
