<template>
  <div class="space-y-6">
    <PageHeader
      eyebrow="Statement Intake"
      icon="bi bi-file-earmark-arrow-up-fill"
      title="Convert bank statements"
      subtitle="Pilih bank, format statement, dan file sumber. Preview tetap tersedia sebelum transaksi disimpan, tetapi layout intake mengikuti shell default aplikasi."
    />

    <SectionCard
      title="Statement Intake"
      subtitle="Gunakan alur sederhana: pilih sumber, isi parameter dasar, unggah file, lalu proses preview."
      body-class="p-5 space-y-6"
    >
      <form class="space-y-6" @submit.prevent="handleSubmit">
        <FormField label="Select Bank">
          <div class="grid grid-cols-3 gap-2 lg:grid-cols-12">
            <button
              v-for="group in bankGroups"
              :key="group.id"
              type="button"
              :aria-label="`Pilih ${group.name}`"
              :title="group.name"
              class="bank-card"
              :class="selectedBankGroup === group.id ? 'bank-card--active' : 'bank-card--idle'"
              @click="selectedBankGroup = group.id"
            >
              <img
                v-if="group.logo"
                :src="group.logo"
                :alt="`${group.name} logo`"
                class="h-full w-full object-contain"
              >
              <i v-else :class="['bi text-xl text-muted', group.icon]"></i>

              <div
                v-if="selectedBankGroup === group.id"
                class="bank-card__check absolute right-1 top-1 z-10 flex h-5 w-5 items-center justify-center rounded-full"
              >
                <i class="bi bi-check-circle-fill leading-none" style="color: var(--color-primary)"></i>
              </div>
            </button>
          </div>
        </FormField>

        <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
          <FormField label="Format">
            <SelectInput
              v-model="formData.bankType"
              :options="formatOptions"
              :placeholder="selectedBankGroup ? 'Choose format...' : 'Select bank first'"
              :disabled="!selectedBankGroup"
            />
          </FormField>

          <FormField label="Year">
            <SelectInput
              v-model="formData.statementYear"
              :options="yearOptions"
            />
          </FormField>

          <FormField label="Company (Optional)">
            <SelectInput
              v-model="formData.companyId"
              :options="companyOptions"
              placeholder="-- No Company --"
            />
          </FormField>
        </div>

        <SectionCard
          v-if="selectedBankCode"
          title="Target Account"
          :subtitle="availableBankAccounts.length > 0 ? 'Jika bank ini punya beberapa rekening, pilih akun yang sesuai sebelum upload.' : 'Belum ada definisi akun bank untuk bank ini. Upload tetap bisa lanjut, atau definisikan dulu di Upload Checklist.'"
          body-class="p-4 space-y-4"
        >
          <FormField label="Bank Account Definition">
            <SelectInput
              v-model="formData.bankAccountNumber"
              :options="bankAccountOptions"
              placeholder="Auto-detect from statement"
            />
          </FormField>

          <div v-if="selectedBankAccountMeta" class="upload-account-note">
            Upload ini akan ditandai ke akun <strong>{{ selectedBankAccountMeta.display_name }}</strong>
            <span v-if="selectedBankAccountMeta.account_number">({{ selectedBankAccountMeta.account_number }})</span>.
          </div>
        </SectionCard>

        <SectionCard body-class="p-4">
          <FormField
            label="Upload Statement"
            hint="PDF dan CSV didukung. Setelah file dipilih, sistem akan tetap melakukan preview sebelum data masuk ke database."
          >
            <FileDropZone @file-selected="handleFileSelection" />
          </FormField>
        </SectionCard>

        <div class="flex flex-col gap-3 border-t pt-4 md:flex-row md:items-center md:justify-between" style="border-color: var(--color-border)">
          <div class="text-sm text-muted">
            <span class="font-semibold text-theme">{{ selectedBankLabel || 'No bank selected' }}</span>
            <span class="mx-2">•</span>
            <span>{{ selectedCompanyName }}</span>
          </div>

          <button
            type="submit"
            :disabled="converterStore.isLoading"
            class="btn-primary gap-2 px-5 py-3 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <i
              v-if="!converterStore.isLoading"
              class="bi bi-lightning-charge-fill"
            ></i>
            <span
              v-else
              class="spinner-border text-white h-4 w-4"
              role="status"
            ></span>
            {{ converterStore.isLoading ? 'Processing...' : 'Convert & Preview' }}
          </button>
        </div>

        <div
          v-if="converterStore.error"
          class="feedback-box feedback-box--danger rounded-2xl p-4 text-sm"
        >
          {{ converterStore.error }}
        </div>

        <div
          v-if="converterStore.successMessage"
          class="feedback-box feedback-box--success rounded-2xl p-4 text-sm"
        >
          <div class="flex items-center">
            <i class="bi bi-check-circle-fill me-3 text-lg"></i>
            <span>{{ converterStore.successMessage }}</span>
          </div>
        </div>
      </form>
    </SectionCard>

    <PreviewModal
      :isOpen="showPreview"
      :loading="converterStore.isLoading"
      :transactions="previewTransactions"
      :companyName="selectedCompanyName"
      @close="showPreview = false"
      @confirm="handleConfirmSave"
    />

    <PasswordModal
      :isOpen="converterStore.requiresPassword"
      :isLoading="converterStore.isLoading"
      :error="converterStore.error"
      @close="converterStore.requiresPassword = false"
      @submit="handlePasswordSubmit"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { historyApi } from '../api';
import { useCompanyStore } from '../stores/companies';
import { useConverterStore } from '../stores/converter';
import FileDropZone from '../components/converter/FileDropZone.vue';
import PasswordModal from '../components/converter/PasswordModal.vue';
import PreviewModal from '../components/converter/PreviewModal.vue';
import FormField from '../components/ui/FormField.vue';
import PageHeader from '../components/ui/PageHeader.vue';
import SectionCard from '../components/ui/SectionCard.vue';
import SelectInput from '../components/ui/SelectInput.vue';
import logoBca from '../../logo/bca.svg';
import logoBluBca from '../../logo/blubca.svg';
import logoBri from '../../logo/bri.svg';
import logoDbs from '../../logo/dbs.svg';
import logoMandiri from '../../logo/mandiri.svg';
import logoSaqu from '../../logo/saqu.svg';

const converterStore = useConverterStore();
const companyStore = useCompanyStore();

onMounted(() => {
  companyStore.fetchCompanies();
});

const currentYear = new Date().getFullYear();
const selectedBankGroup = ref('');
const showPreview = ref(false);
const previewTransactions = ref([]);
const availableBankAccounts = ref([]);

const years = computed(() => {
  const list = [];
  for (let year = currentYear; year >= 2018; year -= 1) {
    list.push(year);
  }
  return list;
});

const yearOptions = computed(() => (
  years.value.map((year) => ({ value: year, label: year }))
));

const companyOptions = computed(() => (
  (companyStore.companies || []).map((company) => ({
    value: company.id,
    label: company.short_name || company.name
  }))
));

const bankGroups = [
  {
    id: 'mandiri',
    name: 'Mandiri',
    icon: 'bi-bank',
    logo: logoMandiri,
    types: [
      { label: 'Credit Card', value: 'ccmandiri' },
      { label: 'Bank Account (Email PDF)', value: 'mandiri_email' },
      { label: 'Bank Account (App)', value: 'mandiri' }
    ]
  },
  {
    id: 'bca',
    name: 'BCA',
    icon: 'bi-building',
    logo: logoBca,
    types: [
      { label: 'Credit Card', value: 'ccbca' },
      { label: 'Bank Account', value: 'bca' }
    ]
  },
  {
    id: 'bri',
    name: 'BRI',
    icon: 'bi-buildings',
    logo: logoBri,
    types: [{ label: 'Bank Account (CSV)', value: 'bri' }]
  },
  {
    id: 'dbs',
    name: 'DBS',
    icon: 'bi-cash-coin',
    logo: logoDbs,
    types: [{ label: 'Credit Card', value: 'dbs' }]
  },
  {
    id: 'blu',
    name: 'Blu by BCA',
    icon: 'bi-phone',
    logo: logoBluBca,
    types: [{ label: 'Bank Account', value: 'blu' }]
  },
  {
    id: 'saqu',
    name: 'Bank Saqu',
    icon: 'bi-wallet2',
    logo: logoSaqu,
    types: [{ label: 'Bank Account', value: 'saqu' }]
  }
];

const availableStatementTypes = computed(() => {
  if (!selectedBankGroup.value) return [];
  const group = bankGroups.find((item) => item.id === selectedBankGroup.value);
  return group ? group.types : [];
});

const formatOptions = computed(() => (
  availableStatementTypes.value.map((type) => ({
    value: type.value,
    label: type.label
  }))
));

const selectedBankLabel = computed(() => {
  const group = bankGroups.find((item) => item.id === selectedBankGroup.value);
  return group ? group.name : '';
});

const formData = reactive({
  bankType: '',
  statementYear: currentYear,
  companyId: '',
  bankAccountNumber: '',
});

watch(selectedBankGroup, () => {
  formData.bankType = '';
  formData.bankAccountNumber = '';
});

const selectedBankCode = computed(() => {
  const bankType = String(formData.bankType || '').trim().toLowerCase();
  if (!bankType) return '';
  if (bankType === 'ccbca') return 'BCA_CC';
  if (bankType === 'ccmandiri') return 'MANDIRI_CC';
  if (bankType === 'mandiri_email') return 'MANDIRI';
  return bankType.toUpperCase();
});

const bankAccountOptions = computed(() => (
  availableBankAccounts.value.map((definition) => ({
    value: definition.account_number,
    label: `${definition.display_name} (${definition.account_number})`
  }))
));

const selectedBankAccountMeta = computed(() => (
  availableBankAccounts.value.find((definition) => definition.account_number === formData.bankAccountNumber) || null
));

const selectedCompanyName = computed(() => {
  if (!formData.companyId) return 'No Company';
  const company = companyStore.companies.find((item) => item.id === formData.companyId);
  return company ? (company.short_name || company.name) : 'No Company';
});

const handleFileSelection = (file) => {
  converterStore.setFile(file);
};

const loadBankAccountDefinitions = async () => {
  if (!selectedBankCode.value) {
    availableBankAccounts.value = [];
    return;
  }

  try {
    const response = await historyApi.getBankAccountDefinitions(selectedBankCode.value);
    availableBankAccounts.value = response.data.definitions || [];
    if (!availableBankAccounts.value.some((definition) => definition.account_number === formData.bankAccountNumber)) {
      formData.bankAccountNumber = '';
    }
  } catch (error) {
    console.error('Failed to load bank account definitions', error);
    availableBankAccounts.value = [];
  }
};

const handleSubmit = async () => {
  if (!converterStore.file) {
    alert('Please upload a file');
    return;
  }

  const fileName = (converterStore.file?.name || '').trim();

  try {
    const uploadNameStatus = await converterStore.checkUploadName(fileName);
    if (uploadNameStatus?.exists) {
      const count = Number(uploadNameStatus.count || 0);
      converterStore.error = `File "${uploadNameStatus.source_file || fileName}" sudah pernah diupload${count > 1 ? ` (${count}x)` : ''}.`;
      return;
    }
  } catch (error) {
    console.error('Failed to check existing upload name', error);
    return;
  }

  const isPdf = fileName.toLowerCase().endsWith('.pdf');
  if (!isPdf) {
    await executeUpload();
    return;
  }

  const checkFd = new FormData();
  checkFd.append('pdf_file', converterStore.file);

  try {
    const checkResult = await converterStore.checkPassword(checkFd);
    if (checkResult.password_protected) {
      converterStore.requiresPassword = true;
      return;
    }
  } catch (error) {
    console.error('Failed to check password protection', error);
    converterStore.error = 'Gagal memeriksa password PDF. Silakan coba lagi.';
    return;
  }

  await executeUpload();
};

const handlePasswordSubmit = async (password) => {
  await executeUpload(password);
};

const executeUpload = async (password = null) => {
  if (password) {
    converterStore.pdfPassword = password;
  }

  const normalizedCompanyId = (formData.companyId || '').toString().trim();
  const fd = new FormData();
  fd.append('pdf_file', converterStore.file);
  fd.append('bank_type', formData.bankType);
  fd.append('statement_year', formData.statementYear);
  fd.append('company_id', normalizedCompanyId);
  fd.append('preview', 'true');
  fd.append('bank_account_number_override', formData.bankAccountNumber || '');
  if (converterStore.pdfPassword) {
    fd.append('password', converterStore.pdfPassword);
  }

  try {
    const result = await converterStore.uploadFile(fd);
    previewTransactions.value = result.data || [];
    showPreview.value = true;
    converterStore.requiresPassword = false;
  } catch (error) {
    // Error handled in store
  }
};

const handleConfirmSave = async () => {
  const normalizedCompanyId = (formData.companyId || '').toString().trim();
  const fd = new FormData();
  fd.append('pdf_file', converterStore.file);
  fd.append('bank_type', formData.bankType);
  fd.append('statement_year', formData.statementYear);
  fd.append('company_id', normalizedCompanyId);
  fd.append('bank_account_number_override', formData.bankAccountNumber || '');
  if (converterStore.pdfPassword) {
    fd.append('password', converterStore.pdfPassword);
  }

  try {
    await converterStore.confirmSave(fd);
    showPreview.value = false;
  } catch (error) {
    // Error handled in store
  }
};

watch(() => formData.bankType, () => {
  loadBankAccountDefinitions();
});
</script>

<style scoped>
.bank-card {
  @apply relative flex aspect-square w-full items-center justify-center overflow-hidden rounded-2xl p-0 transition-all duration-200;
  border: 1px solid var(--color-border);
  background: var(--color-surface-raised);
}

.bank-card--idle:hover {
  border-color: var(--color-border-strong);
  background: var(--color-surface-muted);
}

.bank-card--active {
  border-color: var(--color-primary);
  background: rgba(15, 118, 110, 0.10);
  box-shadow: 0 14px 30px rgba(15, 118, 110, 0.16);
}

.bank-card__check {
  background: var(--color-surface);
  box-shadow: var(--shadow-soft);
}

.feedback-box {
  border: 1px solid transparent;
}

.feedback-box--danger {
  background: rgba(185, 28, 28, 0.08);
  border-color: rgba(185, 28, 28, 0.18);
  color: var(--color-danger);
}

.feedback-box--success {
  background: rgba(22, 101, 52, 0.08);
  border-color: rgba(22, 101, 52, 0.18);
  color: var(--color-success);
}

.upload-account-note {
  @apply rounded-xl px-3 py-2 text-xs leading-relaxed;
  background: rgba(15, 118, 110, 0.08);
  border: 1px solid rgba(15, 118, 110, 0.16);
  color: var(--color-text-muted);
}
</style>
