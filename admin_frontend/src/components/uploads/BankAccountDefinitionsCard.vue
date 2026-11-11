<template>
  <section ref="rootEl" class="section-card defs-card">
    <button
      type="button"
      class="defs-toggle"
      :aria-expanded="expanded"
      @click="expanded = !expanded"
    >
      <span class="defs-toggle__left">
        <span class="defs-toggle__icon"><i class="bi bi-gear"></i></span>
        <span class="defs-toggle__title">Kelola Akun Bank</span>
        <span v-if="!isLoading" class="defs-toggle__summary">
          {{ definitions.length }} definisi aktif<template v-if="candidates.length"> · {{ candidates.length }} kandidat belum terlabel</template>
        </span>
        <span v-else class="defs-toggle__summary">memuat…</span>
      </span>
      <i class="bi bi-chevron-down defs-toggle__chev" :class="{ 'defs-toggle__chev--open': expanded }"></i>
    </button>

    <div v-show="expanded" class="defs-body">
      <div class="defs-note">
        Upload baru akan otomatis dipisah berdasarkan nomor rekening yang terbaca dari statement. Upload lama yang belum menyimpan nomor rekening akan tetap masuk ke kolom bank umum atau Unmapped.
      </div>

      <div class="defs-cols">
        <!-- Form -->
        <form class="defs-form" @submit.prevent="saveDefinition">
          <h4 class="defs-form__title">
            {{ editingId ? 'Edit Definisi' : 'Tambah Definisi' }}
            <span v-if="editingId" class="defs-form__editing">mode edit</span>
          </h4>

          <label class="defs-field">
            <span>Bank</span>
            <SelectInput v-model="form.bankCode" :options="bankOptions" placeholder="Select bank" />
          </label>

          <label class="defs-field">
            <span>Nomor rekening</span>
            <TextInput v-model="form.accountNumber" placeholder="Account number" maxlength="100" />
          </label>

          <label class="defs-field defs-field--wide">
            <span>Label tampilan</span>
            <TextInput v-model="form.displayName" placeholder="Contoh: BCA Operasional 1" maxlength="255" />
          </label>

          <label class="defs-field">
            <span>Mulai digunakan</span>
            <TextInput v-model="form.activeFrom" type="date" placeholder="Mulai digunakan" />
          </label>

          <label class="defs-field">
            <span>Tidak digunakan lagi</span>
            <TextInput v-model="form.activeUntil" type="date" placeholder="Tidak digunakan lagi" />
          </label>

          <div class="defs-form__actions">
            <button
              v-if="editingId"
              type="button"
              class="btn-secondary"
              @click="cancelEdit"
            >
              Batal
            </button>
            <button type="submit" class="btn-primary" :disabled="isSaving">
              <i v-if="isSaving" class="bi bi-arrow-repeat spin mr-2"></i>
              <i v-else class="bi bi-plus-lg mr-2"></i>
              {{ editingId ? 'Simpan Perubahan' : 'Save' }}
            </button>
          </div>
        </form>

        <!-- Definitions list -->
        <div class="defs-list">
          <div v-if="isLoading" class="defs-list__state">
            <div class="defs-loading__spinner"></div>
            <span>Loading definitions...</span>
          </div>

          <div v-else-if="definitions.length === 0" class="defs-list__state">
            Belum ada definisi akun bank.
          </div>

          <template v-else>
            <div class="defs-row defs-row--head">
              <span>Rekening</span>
              <span>Label</span>
              <span>Periode Aktif</span>
              <span class="defs-row__actions-label">Aksi</span>
            </div>
            <div v-for="definition in definitions" :key="definition.id" class="defs-row">
              <span class="defs-row__bank">
                <b>{{ formatBankCode(definition.bank_code) }}</b>
                <code>{{ definition.account_number }}</code>
              </span>
              <span class="defs-row__label">{{ definition.display_name }}</span>
              <span class="defs-row__period">{{ formatActivePeriod(definition) }}</span>
              <span class="defs-row__actions">
                <button
                  type="button"
                  class="defs-iconbtn"
                  title="Edit definisi"
                  @click="editDefinition(definition)"
                >
                  <i class="bi bi-pencil"></i>
                </button>
                <button
                  type="button"
                  class="defs-iconbtn defs-iconbtn--danger"
                  title="Hapus definisi"
                  :disabled="deletingId === definition.id"
                  @click="askDelete(definition)"
                >
                  <i class="bi bi-trash"></i>
                </button>
              </span>
            </div>
          </template>
        </div>
      </div>

      <div v-if="candidates.length > 0" class="defs-candidates">
        <h4 class="defs-candidates__title">Existing Unmapped Accounts</h4>
        <p class="defs-candidates__subtitle">Ini diambil dari transaksi existing yang sudah punya nomor rekening tetapi belum diberi label. Klik untuk mengisinya ke form.</p>
        <div class="defs-candidates__list">
          <button
            v-for="candidate in candidates"
            :key="`${candidate.bank_code}-${candidate.account_number}`"
            type="button"
            class="defs-candidate"
            @click="useCandidate(candidate)"
          >
            <span class="defs-candidate__title">{{ formatBankCode(candidate.bank_code) }} · {{ candidate.account_number }}</span>
            <span class="defs-candidate__meta">{{ candidate.transaction_count }} txn · {{ candidate.source_file_count }} file</span>
          </button>
        </div>
      </div>
    </div>

    <ConfirmModal
      :isOpen="deleteTarget !== null"
      variant="danger"
      :title="`Hapus definisi ${deleteTarget ? formatBankCode(deleteTarget.bank_code) + ' ' + deleteTarget.account_number : ''}?`"
      message="Transaksi yang sudah terupload tidak ikut terhapus, tapi statement berikutnya tidak lagi dipisah ke rekening ini."
      confirm-text="Hapus"
      :loading="deleteTarget !== null && deletingId === deleteTarget.id"
      @close="deleteTarget = null"
      @confirm="deleteDefinition"
    />
  </section>
</template>

<script setup>
import { nextTick, onMounted, ref } from 'vue';
import { historyApi } from '../../api';
import { useNotifications } from '../../composables/useNotifications';
import ConfirmModal from '../ui/ConfirmModal.vue';
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

const expanded = ref(false);
const rootEl = ref(null);

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
const deleteTarget = ref(null);
const editingId = ref(null);

const formatBankCode = (bankCode) => String(bankCode || '').replace('_CC', ' CC');

const resetForm = () => {
  form.value = {
    bankCode: 'BCA',
    accountNumber: '',
    displayName: '',
    activeFrom: '',
    activeUntil: '',
  };
  editingId.value = null;
};

const expand = () => {
  expanded.value = true;
  nextTick(() => rootEl.value?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
};

const collapse = () => {
  expanded.value = false;
  // Keep the collapsed bar in view — returning to the pre-expand state explicitly
  nextTick(() => rootEl.value?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }));
};

const toggleFromParent = () => (expanded.value ? collapse() : expand());

const cancelEdit = () => resetForm();

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
  editingId.value = null;
  form.value = {
    bankCode: candidate.bank_code || 'BCA',
    accountNumber: candidate.account_number || '',
    displayName: '',
    activeFrom: '',
    activeUntil: '',
  };
  expanded.value = true;
};

const editDefinition = (definition) => {
  editingId.value = definition.id;
  form.value = {
    bankCode: definition.bank_code || 'BCA',
    accountNumber: definition.account_number || '',
    displayName: definition.display_name || '',
    activeFrom: definition.active_from || '',
    activeUntil: definition.active_until || '',
  };
  expanded.value = true;
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
    // Backend upserts on (bank_code, account_number), so edit mode re-saves the same key
    await historyApi.saveBankAccountDefinition(payload);
    notifications.success(editingId.value ? 'Bank account definition updated' : 'Bank account definition saved');
    resetForm();
    await loadDefinitions();
    emit('changed');
  } catch (error) {
    notifications.error(error?.response?.data?.error || 'Failed to save bank account definition');
  } finally {
    isSaving.value = false;
  }
};

const askDelete = (definition) => {
  deleteTarget.value = definition;
};

const deleteDefinition = async () => {
  if (!deleteTarget.value) return;
  const definition = deleteTarget.value;

  deletingId.value = definition.id;
  try {
    await historyApi.deleteBankAccountDefinition(definition.id);
    notifications.success('Bank account definition deleted');
    deleteTarget.value = null;
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

defineExpose({ expanded, expand, collapse, toggleFromParent });
</script>

<style scoped>
.defs-card {
  scroll-margin-top: 16px;
  scroll-margin-bottom: 24px;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* ── Toggle bar ────────────────────────────────── */
.defs-toggle {
  @apply flex w-full cursor-pointer items-center justify-between gap-3 px-5 py-3.5 text-left transition-colors;
  background: transparent;
}
.defs-toggle:hover { background: color-mix(in srgb, var(--color-primary) 4%, transparent); }
.defs-toggle:focus-visible {
  outline: none;
  box-shadow: inset 0 0 0 2px var(--color-primary-ring);
  border-radius: var(--radius-md);
}
.defs-toggle__left { @apply flex min-w-0 items-center gap-3; }
.defs-toggle__icon {
  @apply flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-sm;
  background: color-mix(in srgb, var(--color-primary) 10%, transparent);
  color: var(--color-primary);
}
.defs-toggle__title {
  @apply text-[13px] font-extrabold;
  color: var(--color-text);
}
.defs-toggle__summary {
  @apply truncate text-[11px];
  color: var(--color-text-muted);
}
.defs-toggle__chev { @apply text-xs transition-transform; color: var(--color-text-muted); }
.defs-toggle__chev--open { transform: rotate(180deg); }

/* ── Body ──────────────────────────────────────── */
.defs-body {
  @apply space-y-4 border-t px-5 pb-5 pt-4;
  border-color: var(--color-border);
}

.defs-note {
  @apply rounded-2xl px-4 py-3 text-xs leading-relaxed;
  background: color-mix(in srgb, var(--color-primary) 6%, transparent);
  border: 1px solid color-mix(in srgb, var(--color-primary) 14%, transparent);
  color: var(--color-text-muted);
}

.defs-cols {
  @apply grid gap-5;
  grid-template-columns: 360px minmax(0, 1fr);
}

/* ── Form ──────────────────────────────────────── */
.defs-form {
  @apply grid content-start gap-3;
  grid-template-columns: 1fr 1fr;
}
.defs-form__title {
  @apply col-span-2 flex items-center gap-2 text-[13px] font-extrabold;
  color: var(--color-text);
}
.defs-form__editing {
  @apply rounded-full px-2 py-0.5 text-[11px] font-extrabold uppercase tracking-wider;
  background: color-mix(in srgb, var(--color-accent) 14%, transparent);
  color: var(--color-accent);
}
.defs-field { @apply flex flex-col gap-1 min-w-0; }
.defs-field > span {
  @apply text-[11px] font-bold;
  color: var(--color-text-muted);
}
.defs-field--wide { grid-column: span 2; }
.defs-form__actions { @apply col-span-2 mt-1 flex items-center justify-end gap-2; }

/* ── Definitions list ──────────────────────────── */
.defs-list { @apply overflow-hidden rounded-2xl border; border-color: var(--color-border); }
.defs-list__state {
  @apply flex items-center justify-center gap-3 px-4 py-8 text-sm;
  color: var(--color-text-muted);
}
.defs-loading__spinner {
  @apply h-4 w-4 animate-spin rounded-full border-2 border-t-transparent;
  border-color: var(--color-primary);
}
.defs-row {
  @apply grid items-center px-4 py-2.5;
  grid-template-columns: minmax(150px, 190px) minmax(140px, 1fr) minmax(150px, 200px) 88px;
  border-top: 1px solid var(--color-border);
  background: var(--color-surface);
}
.defs-row--head {
  @apply px-4 py-2.5 text-[11px] font-extrabold uppercase tracking-widest;
  border-top: none;
  background: var(--color-surface-muted);
  color: var(--color-text-muted);
}
.defs-row__bank { @apply flex flex-col; }
.defs-row__bank b { @apply text-[13px] font-bold; color: var(--color-text); }
.defs-row__bank code {
  @apply font-mono text-[11px];
  color: var(--color-text-muted);
}
.defs-row__label { @apply text-[13px]; color: var(--color-text); }
.defs-row__period { @apply text-[12px]; color: var(--color-text-muted); }
.defs-row__actions { @apply flex items-center justify-end gap-1.5; }
.defs-row__actions-label { @apply text-right; }
.defs-iconbtn {
  @apply flex h-7 w-7 cursor-pointer items-center justify-center rounded-lg border text-xs transition-colors;
  background: var(--color-surface);
  border-color: var(--color-border);
  color: var(--color-text-muted);
}
.defs-iconbtn:hover { border-color: var(--color-primary); color: var(--color-primary); }
.defs-iconbtn--danger:hover { border-color: var(--color-danger); color: var(--color-danger); }
.defs-iconbtn:disabled { @apply cursor-not-allowed opacity-50; }

/* ── Candidates ────────────────────────────────── */
.defs-candidates {
  @apply space-y-2.5 rounded-2xl p-4;
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
}
.defs-candidates__title { @apply text-[13px] font-extrabold; color: var(--color-text); }
.defs-candidates__subtitle { @apply text-xs; color: var(--color-text-muted); }
.defs-candidates__list { @apply flex flex-wrap gap-2 pt-1; }
.defs-candidate {
  @apply flex cursor-pointer flex-col rounded-xl border px-3 py-2 text-left transition-colors;
  background: var(--color-surface);
  border-color: var(--color-border);
}
.defs-candidate:hover {
  border-color: var(--color-primary);
  background: color-mix(in srgb, var(--color-primary) 5%, transparent);
}
.defs-candidate__title { @apply text-xs font-semibold; color: var(--color-text); }
.defs-candidate__meta { @apply mt-0.5 text-[11px]; color: var(--color-text-muted); }

/* ── Responsive ────────────────────────────────── */
@media (max-width: 1000px) {
  .defs-cols { grid-template-columns: 1fr; }
}
@media (max-width: 720px) {
  .defs-row { grid-template-columns: 1fr 1fr; }
  .defs-row--head { display: none; }
  .defs-row__actions { @apply col-span-2 justify-start; }
}
</style>
