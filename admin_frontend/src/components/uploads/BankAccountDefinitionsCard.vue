<template>
  <SectionCard
    title="Bank Account Definitions"
    subtitle="Definisikan rekening per bank supaya checklist bisa memecah BCA, DBS, dan bank lain menjadi beberapa akun terpisah."
    body-class="p-6 space-y-6"
  >
    <form class="grid grid-cols-1 gap-4 lg:grid-cols-6" @submit.prevent="saveDefinition">
      <SelectInput
        v-model="form.bankCode"
        :options="bankOptions"
        placeholder="Select bank"
        class="lg:col-span-1"
      />

      <TextInput
        v-model="form.accountNumber"
        placeholder="Account number"
        maxlength="100"
        class="lg:col-span-1"
      />

      <TextInput
        v-model="form.displayName"
        placeholder="Display name, contoh: BCA Operasional 1"
        maxlength="255"
        class="lg:col-span-2"
      />

      <TextInput
        v-model="form.activeFrom"
        type="date"
        placeholder="Mulai digunakan"
        class="lg:col-span-1"
      />

      <TextInput
        v-model="form.activeUntil"
        type="date"
        placeholder="Tidak digunakan lagi"
        class="lg:col-span-1"
      />

      <button
        type="submit"
        class="btn-primary whitespace-nowrap lg:col-span-6 lg:justify-self-end"
        :disabled="isSaving"
      >
        <i v-if="isSaving" class="bi bi-arrow-repeat spin mr-2"></i>
        <i v-else class="bi bi-plus-lg mr-2"></i>
        Save
      </button>
    </form>

    <div class="definition-note">
      Upload baru akan otomatis dipisah berdasarkan nomor rekening yang terbaca dari statement. Upload lama yang belum menyimpan nomor rekening akan tetap masuk ke kolom bank umum atau `Unmapped`.
    </div>

    <div v-if="candidates.length > 0" class="definition-candidates">
      <div class="definition-candidates__header">
        <div>
          <h4 class="definition-candidates__title">Existing Unmapped Accounts</h4>
          <p class="definition-candidates__subtitle">Ini diambil dari transaksi existing yang sudah punya nomor rekening tetapi belum diberi label.</p>
        </div>
      </div>

      <div class="definition-candidates__list">
        <button
          v-for="candidate in candidates"
          :key="`${candidate.bank_code}-${candidate.account_number}`"
          type="button"
          class="definition-candidate"
          @click="useCandidate(candidate)"
        >
          <div class="definition-candidate__title">
            {{ formatBankCode(candidate.bank_code) }} · {{ candidate.account_number }}
          </div>
          <div class="definition-candidate__meta">
            {{ candidate.transaction_count }} txn · {{ candidate.source_file_count }} file
          </div>
        </button>
      </div>
    </div>

    <div v-if="isLoading" class="definition-loading">
      <div class="definition-loading__spinner"></div>
      <span>Loading definitions...</span>
    </div>

    <div v-else-if="definitions.length === 0" class="definition-empty">
      Belum ada definisi akun bank.
    </div>

    <div v-else class="definition-table">
        <div class="definition-table__head">
        <div>Bank</div>
        <div>Account Number</div>
        <div>Label</div>
        <div>Active Period</div>
        <div>Actions</div>
      </div>

      <div
        v-for="definition in definitions"
        :key="definition.id"
        class="definition-row"
      >
        <div class="definition-row__bank">{{ formatBankCode(definition.bank_code) }}</div>
        <div class="definition-row__account">{{ definition.account_number }}</div>
        <div class="definition-row__label">{{ definition.display_name }}</div>
        <div class="definition-row__period">{{ formatActivePeriod(definition) }}</div>
        <div class="definition-row__actions">
          <button
            type="button"
            class="btn-secondary !px-3 !py-1.5 !text-xs"
            @click="editDefinition(definition)"
          >
            Edit
          </button>
          <button
            type="button"
            class="btn-danger !px-3 !py-1.5 !text-xs"
            :disabled="deletingId === definition.id"
            @click="deleteDefinition(definition)"
          >
            <i v-if="deletingId === definition.id" class="bi bi-arrow-repeat spin mr-1"></i>
            Delete
          </button>
        </div>
      </div>
    </div>
  </SectionCard>
</template>

<script setup>
import { onMounted, ref } from 'vue';
import { historyApi } from '../../api';
import { useNotifications } from '../../composables/useNotifications';
import SectionCard from '../ui/SectionCard.vue';
import SelectInput from '../ui/SelectInput.vue';
import TextInput from '../ui/TextInput.vue';

const emit = defineEmits(['changed']);

const notifications = useNotifications();

const bankOptions = [
  { value: 'BCA', label: 'BCA' },
  { value: 'BCA_CC', label: 'BCA CC' },
  { value: 'MANDIRI', label: 'Mandiri' },
  { value: 'MANDIRI_CC', label: 'Mandiri CC' },
  { value: 'DBS', label: 'DBS' },
  { value: 'BRI', label: 'BRI' },
  { value: 'BLU', label: 'Blu by BCA' },
  { value: 'SAQU', label: 'Saqu' },
];

const form = ref({
  bankCode: 'BCA',
  accountNumber: '',
  displayName: '',
  activeFrom: '',
  activeUntil: '',
});

const definitions = ref([]);
const candidates = ref([]);
const isLoading = ref(false);
const isSaving = ref(false);
const deletingId = ref('');

const formatBankCode = (bankCode) => String(bankCode || '').replace('_CC', ' CC');

const resetForm = () => {
  form.value = {
    bankCode: 'BCA',
    accountNumber: '',
    displayName: '',
    activeFrom: '',
    activeUntil: '',
  };
};

const formatActivePeriod = (definition) => {
  const activeFrom = definition?.active_from || '';
  const activeUntil = definition?.active_until || '';
  if (!activeFrom && !activeUntil) return 'Always';
  if (activeFrom && !activeUntil) return `${activeFrom} onwards`;
  if (!activeFrom && activeUntil) return `Until ${activeUntil}`;
  return `${activeFrom} to ${activeUntil}`;
};

const loadDefinitions = async () => {
  isLoading.value = true;
  try {
    const [definitionsResponse, candidatesResponse] = await Promise.all([
      historyApi.getBankAccountDefinitions(),
      historyApi.getBankAccountDefinitionCandidates(),
    ]);
    definitions.value = definitionsResponse.data.definitions || [];
    candidates.value = candidatesResponse.data.candidates || [];
  } catch (error) {
    notifications.error(error?.response?.data?.error || 'Failed to load bank account definitions');
  } finally {
    isLoading.value = false;
  }
};

const useCandidate = (candidate) => {
  form.value = {
    bankCode: candidate.bank_code || 'BCA',
    accountNumber: candidate.account_number || '',
    displayName: '',
    activeFrom: '',
    activeUntil: '',
  };
};

const editDefinition = (definition) => {
  form.value = {
    bankCode: definition.bank_code || 'BCA',
    accountNumber: definition.account_number || '',
    displayName: definition.display_name || '',
    activeFrom: definition.active_from || '',
    activeUntil: definition.active_until || '',
  };
};

const saveDefinition = async () => {
  const payload = {
    bank_code: String(form.value.bankCode || '').trim().toUpperCase(),
    account_number: String(form.value.accountNumber || '').trim(),
    display_name: String(form.value.displayName || '').trim(),
    active_from: String(form.value.activeFrom || '').trim() || null,
    active_until: String(form.value.activeUntil || '').trim() || null,
  };

  if (!payload.bank_code || !payload.account_number || !payload.display_name) {
    notifications.error('Bank, account number, dan label wajib diisi');
    return;
  }
  if (payload.active_from && payload.active_until && payload.active_until < payload.active_from) {
    notifications.error('Tanggal akhir harus sama atau setelah tanggal mulai');
    return;
  }

  isSaving.value = true;
  try {
    await historyApi.saveBankAccountDefinition(payload);
    notifications.success('Bank account definition saved');
    resetForm();
    await loadDefinitions();
    emit('changed');
  } catch (error) {
    notifications.error(error?.response?.data?.error || 'Failed to save bank account definition');
  } finally {
    isSaving.value = false;
  }
};

const deleteDefinition = async (definition) => {
  if (!confirm(`Delete definition for ${formatBankCode(definition.bank_code)} ${definition.account_number}?`)) return;

  deletingId.value = definition.id;
  try {
    await historyApi.deleteBankAccountDefinition(definition.id);
    notifications.success('Bank account definition deleted');
    await loadDefinitions();
    emit('changed');
  } catch (error) {
    notifications.error(error?.response?.data?.error || 'Failed to delete bank account definition');
  } finally {
    deletingId.value = '';
  }
};

onMounted(() => {
  loadDefinitions();
});
</script>

<style scoped>
.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.definition-note {
  @apply rounded-2xl px-4 py-3 text-xs leading-relaxed;
  background: rgba(15, 118, 110, 0.08);
  border: 1px solid rgba(15, 118, 110, 0.16);
  color: var(--color-text-muted);
}

.definition-loading,
.definition-empty {
  @apply flex items-center justify-center rounded-2xl px-4 py-6 text-sm;
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
  color: var(--color-text-muted);
}

.definition-loading {
  @apply gap-3;
}

.definition-loading__spinner {
  @apply h-4 w-4 animate-spin rounded-full border-2 border-t-transparent;
  border-color: var(--color-primary);
}

.definition-candidates {
  @apply space-y-3 rounded-2xl p-4;
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
}

.definition-candidates__header {
  @apply flex items-start justify-between gap-3;
}

.definition-candidates__title {
  @apply text-sm font-bold;
  color: var(--color-text);
}

.definition-candidates__subtitle {
  @apply mt-1 text-xs;
  color: var(--color-text-muted);
}

.definition-candidates__list {
  @apply flex flex-wrap gap-2;
}

.definition-candidate {
  @apply rounded-xl px-3 py-2 text-left transition-colors;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
}

.definition-candidate:hover {
  border-color: var(--color-primary);
  background: rgba(15, 118, 110, 0.06);
}

.definition-candidate__title {
  @apply text-xs font-semibold;
  color: var(--color-text);
}

.definition-candidate__meta {
  @apply mt-1 text-[11px];
  color: var(--color-text-muted);
}

.definition-table {
  @apply overflow-hidden rounded-2xl;
  border: 1px solid var(--color-border);
}

.definition-table__head,
.definition-row {
  display: grid;
  grid-template-columns: minmax(120px, 160px) minmax(180px, 220px) minmax(220px, 1fr) minmax(180px, 220px) 120px;
  gap: 0;
}

.definition-table__head {
  @apply text-[11px] font-bold uppercase tracking-wider;
  background: var(--color-surface-muted);
  color: var(--color-text-muted);
}

.definition-table__head > div,
.definition-row > div {
  @apply px-4 py-3;
  border-right: 1px solid var(--color-border);
}

.definition-table__head > div:last-child,
.definition-row > div:last-child {
  border-right: none;
}

.definition-row {
  border-top: 1px solid var(--color-border);
  background: var(--color-surface);
}

.definition-row__bank {
  @apply text-sm font-semibold;
  color: var(--color-text);
}

.definition-row__account {
  @apply text-sm font-mono;
  color: var(--color-text);
}

.definition-row__label {
  @apply text-sm;
  color: var(--color-text);
}

.definition-row__period {
  @apply text-sm;
  color: var(--color-text-muted);
}

.definition-row__actions {
  @apply flex items-center gap-2;
}

@media (max-width: 900px) {
  .definition-table__head {
    display: none;
  }

  .definition-row {
    grid-template-columns: 1fr;
  }

  .definition-row > div {
    border-right: none;
    border-top: 1px solid var(--color-border);
  }

  .definition-row > div:first-child {
    border-top: none;
  }
}
</style>
