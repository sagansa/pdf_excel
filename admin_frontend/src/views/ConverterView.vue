<template>
  <div class="max-w-3xl mx-auto space-y-6">
    <div class="flex justify-end">
      <button
        type="button"
        class="px-3 py-1.5 text-xs font-semibold rounded-lg border transition-colors"
        :class="isDarkPreview ? 'bg-slate-800 text-slate-100 border-slate-600 hover:bg-slate-700' : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'"
        @click="isDarkPreview = !isDarkPreview"
      >
        {{ isDarkPreview ? "Light Preview" : "Dark Preview" }}
      </button>
    </div>

    <div
      class="rounded-2xl shadow-sm border p-8 transition-colors duration-300"
      :class="isDarkPreview ? 'bg-slate-900 border-slate-700 text-slate-100' : 'bg-white border-gray-200'"
    >
      <form @submit.prevent="handleSubmit">
        <div class="space-y-6">
          <!-- 1. Bank Selection Cards (Horizontal & Compact) -->
          <div class="space-y-2">
            <label class="label-base text-base" :class="isDarkPreview ? '!text-slate-200' : ''">Select Bank</label>
            <div class="grid grid-cols-3 lg:grid-cols-6 gap-2">
              <button
                type="button"
                v-for="group in bankGroups"
                :key="group.id"
                @click="selectedBankGroup = group.id"
                :aria-label="`Pilih ${group.name}`"
                :title="group.name"
                class="relative w-full aspect-square flex items-center justify-center p-0 rounded-md border overflow-hidden transition-all duration-200"
                :class="[
                  selectedBankGroup === group.id
                    ? (isDarkPreview
                      ? 'border-indigo-400 bg-indigo-500/10 shadow-sm'
                      : 'border-indigo-500 bg-indigo-50 shadow-sm')
                    : (isDarkPreview
                      ? 'border-slate-700 bg-slate-900 hover:border-slate-500 hover:bg-slate-800'
                      : 'border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50'),
                ]"
              >
                <img
                  v-if="group.logo"
                  :src="group.logo"
                  :alt="`${group.name} logo`"
                  class="w-full h-full object-contain"
                />
                <i v-else :class="['bi text-xl text-gray-500', group.icon]"></i>

                <!-- Active Indicator -->
                <div
                  v-if="selectedBankGroup === group.id"
                  class="absolute top-1 right-1 z-10 w-4 h-4 rounded-full flex items-center justify-center"
                  :class="isDarkPreview ? 'bg-slate-800' : 'bg-white shadow-sm'"
                >
                  <i class="bi bi-check-circle-fill text-indigo-500 leading-none"></i>
                </div>
              </button>
            </div>
          </div>

          <!-- Selected Options Row (Compact 3-column layout) -->
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <!-- 2. Statement Type -->
            <div class="space-y-1">
              <label class="label-base text-sm" :class="isDarkPreview ? '!text-slate-200' : ''">Format</label>
              <select
                class="input-base py-2"
                :class="isDarkPreview ? '!bg-slate-800 !border-slate-600 !text-slate-100 focus:!border-indigo-400 focus:!ring-indigo-400' : 'bg-white'"
                v-model="formData.bankType"
                required
                :disabled="!selectedBankGroup"
              >
                <option value="">
                  {{
                    selectedBankGroup ? "Choose format..." : "Select bank first"
                  }}
                </option>
                <option
                  v-for="type in availableStatementTypes"
                  :key="type.value"
                  :value="type.value"
                >
                  {{ type.label }}
                </option>
              </select>
            </div>

            <!-- 3. Year -->
            <div class="space-y-1">
              <label class="label-base text-sm" :class="isDarkPreview ? '!text-slate-200' : ''">Year</label>
              <select
                class="input-base py-2"
                :class="isDarkPreview ? '!bg-slate-800 !border-slate-600 !text-slate-100 focus:!border-indigo-400 focus:!ring-indigo-400' : 'bg-white'"
                v-model="formData.statementYear"
              >
                <option v-for="year in years" :key="year" :value="year">
                  {{ year }}
                </option>
              </select>
            </div>

            <!-- 4. Company -->
            <div class="space-y-1">
              <label class="label-base text-sm" :class="isDarkPreview ? '!text-slate-200' : ''">Company (Optional)</label>
              <select
                class="input-base py-2"
                :class="isDarkPreview ? '!bg-slate-800 !border-slate-600 !text-slate-100 focus:!border-indigo-400 focus:!ring-indigo-400' : 'bg-white'"
                v-model="formData.companyId"
              >
                <option value="">-- No Company --</option>
                <option
                  v-for="c in companyStore.companies"
                  :key="c.id"
                  :value="c.id"
                >
                  {{ c.short_name }}
                </option>
              </select>
            </div>
          </div>

          <!-- Upload Area -->
          <div class="space-y-2">
            <label class="label-base" :class="isDarkPreview ? '!text-slate-200' : ''">Upload Statement (PDF or CSV)</label>
            <FileDropZone :is-dark="isDarkPreview" @file-selected="handleFileSelection" />
            <div class="text-center text-xs mt-2" :class="isDarkPreview ? 'text-slate-400' : 'text-gray-400'">
              Please select a bank to see format requirements
            </div>
          </div>

          <!-- Actions -->
          <div class="pt-4">
            <button
              type="submit"
              :disabled="converterStore.isLoading"
              class="btn-primary w-full py-4 text-base font-bold rounded-2xl disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <i
                class="bi bi-lightning-charge-fill me-2"
                v-if="!converterStore.isLoading"
              ></i>
              <span
                v-if="converterStore.isLoading"
                class="spinner-border text-white w-5 h-5 me-2"
                role="status"
              ></span>
              {{
                converterStore.isLoading
                  ? "Processing..."
                  : "Convert & Extract Data"
              }}
            </button>

            <div
              v-if="converterStore.error"
              class="mt-4 p-4 border rounded-xl text-sm"
              :class="isDarkPreview ? 'bg-red-950/40 border-red-900 text-red-200' : 'bg-red-50 border-red-100 text-red-700'"
            >
              {{ converterStore.error }}
            </div>

            <div
              v-if="converterStore.successMessage"
              class="mt-4 p-4 border rounded-xl text-sm"
              :class="isDarkPreview ? 'bg-emerald-950/40 border-emerald-900 text-emerald-200' : 'bg-green-50 border-green-100 text-green-700'"
            >
              <div class="flex items-center">
                <i class="bi bi-check-circle-fill me-3 text-lg"></i>
                <span>{{ converterStore.successMessage }}</span>
              </div>
            </div>
          </div>
        </div>
      </form>
    </div>

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
import { onMounted, reactive, computed, ref, watch } from "vue";
import { useConverterStore } from "../stores/converter";
import { useCompanyStore } from "../stores/companies";
import FileDropZone from "../components/converter/FileDropZone.vue";
import PreviewModal from "../components/converter/PreviewModal.vue";
import PasswordModal from "../components/converter/PasswordModal.vue";
import logoBca from "../../logo/bca.svg";
import logoBluBca from "../../logo/blubca.svg";
import logoBri from "../../logo/bri.svg";
import logoDbs from "../../logo/dbs.svg";
import logoMandiri from "../../logo/mandiri.svg";
import logoSaqu from "../../logo/saqu.svg";

const converterStore = useConverterStore();
const companyStore = useCompanyStore();

onMounted(() => {
  companyStore.fetchCompanies();
});

const currentYear = new Date().getFullYear();
const isDarkPreview = ref(false);
const years = computed(() => {
  const list = [];
  for (let y = currentYear; y >= 2018; y--) list.push(y);
  return list;
});

const selectedBankGroup = ref("");

const bankGroups = [
  {
    id: "mandiri",
    name: "Mandiri",
    icon: "bi-bank",
    color: "amber",
    logo: logoMandiri,
    types: [
      { label: "Credit Card", value: "ccmandiri" },
      { label: "Bank Account (Email PDF)", value: "mandiri_email" },
      { label: "Bank Account (App)", value: "mandiri" },
    ],
  },
  {
    id: "bca",
    name: "BCA",
    icon: "bi-building",
    color: "blue",
    logo: logoBca,
    types: [
      { label: "Credit Card", value: "ccbca" },
      { label: "Bank Account", value: "bca" },
    ],
  },
  {
    id: "bri",
    name: "BRI",
    icon: "bi-buildings",
    color: "orange",
    logo: logoBri,
    types: [{ label: "Bank Account (CSV)", value: "bri" }],
  },
  {
    id: "dbs",
    name: "DBS",
    icon: "bi-cash-coin",
    color: "red",
    logo: logoDbs,
    types: [{ label: "Credit Card", value: "dbs" }],
  },
  {
    id: "blu",
    name: "Blu by BCA",
    icon: "bi-phone",
    color: "cyan",
    logo: logoBluBca,
    types: [{ label: "Bank Account", value: "blu" }],
  },
  {
    id: "saqu",
    name: "Bank Saqu",
    icon: "bi-wallet2",
    color: "rose",
    logo: logoSaqu,
    types: [{ label: "Bank Account", value: "saqu" }],
  },
];

const availableStatementTypes = computed(() => {
  if (!selectedBankGroup.value) return [];
  const group = bankGroups.find((g) => g.id === selectedBankGroup.value);
  return group ? group.types : [];
});

watch(selectedBankGroup, () => {
  formData.bankType = "";
});

const formData = reactive({
  bankType: "",
  statementYear: currentYear,
  companyId: "",
});

const handleFileSelection = (file) => {
  converterStore.setFile(file);
};

const showPreview = ref(false);
const previewTransactions = ref([]);

const selectedCompanyName = computed(() => {
  if (!formData.companyId) return "No Company";
  const company = companyStore.companies.find(
    (c) => c.id === formData.companyId,
  );
  return company ? company.short_name : "No Company";
});

const handleSubmit = async () => {
  if (!converterStore.file) {
    alert("Please upload a file");
    return;
  }

  const fileName = (converterStore.file?.name || "").trim();

  // 1) Check whether filename has been uploaded before
  try {
    const uploadNameStatus = await converterStore.checkUploadName(fileName);
    if (uploadNameStatus?.exists) {
      const count = Number(uploadNameStatus.count || 0);
      converterStore.error = `File "${uploadNameStatus.source_file || fileName}" sudah pernah diupload${count > 1 ? ` (${count}x)` : ""}.`;
      return;
    }
  } catch (e) {
    console.error("Failed to check existing upload name", e);
    return;
  }

  // 2) Check password only for PDF
  const isPdf = fileName.toLowerCase().endsWith(".pdf");
  if (!isPdf) {
    await executeUpload();
    return;
  }

  const checkFd = new FormData();
  checkFd.append("pdf_file", converterStore.file);

  try {
    const checkResult = await converterStore.checkPassword(checkFd);
    if (checkResult.password_protected) {
      converterStore.requiresPassword = true;
      return;
    }
  } catch (e) {
    console.error("Failed to check password protection", e);
    converterStore.error = "Gagal memeriksa password PDF. Silakan coba lagi.";
    return;
  }

  // 3) Convert after upload-name and password checks pass
  await executeUpload();
};

const handlePasswordSubmit = async (password) => {
  await executeUpload(password);
};

const executeUpload = async (password = null) => {
  if (password) {
    converterStore.pdfPassword = password;
  }

  const normalizedCompanyId = (formData.companyId || "").toString().trim();
  const fd = new FormData();
  fd.append("pdf_file", converterStore.file);
  fd.append("bank_type", formData.bankType);
  fd.append("statement_year", formData.statementYear);
  fd.append("company_id", normalizedCompanyId);
  fd.append("preview", "true");
  if (converterStore.pdfPassword) {
    fd.append("password", converterStore.pdfPassword);
  }

  try {
    const result = await converterStore.uploadFile(fd);
    previewTransactions.value = result.data || [];
    showPreview.value = true;
    converterStore.requiresPassword = false;
  } catch (e) {
    // Error handled in store
  }
};

const handleConfirmSave = async () => {
  const normalizedCompanyId = (formData.companyId || "").toString().trim();
  const fd = new FormData();
  fd.append("pdf_file", converterStore.file);
  fd.append("bank_type", formData.bankType);
  fd.append("statement_year", formData.statementYear);
  fd.append("company_id", normalizedCompanyId);
  if (converterStore.pdfPassword) {
    fd.append("password", converterStore.pdfPassword);
  }

  try {
    await converterStore.confirmSave(fd);
    showPreview.value = false;
  } catch (e) {
    // Error handled in store
  }
};
</script>

<style scoped>
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-fade-in-up {
  animation: fadeInUp 0.4s ease-out forwards;
}
</style>
