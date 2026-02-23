<template>
  <div class="max-w-3xl mx-auto space-y-6">
    <div class="bg-white rounded-2xl shadow-sm border border-gray-200 p-8">
      <form @submit.prevent="handleSubmit">
        <div class="space-y-6">
          <!-- 1. Bank Selection Cards (Horizontal & Compact) -->
          <div class="space-y-2">
            <label class="label-base text-base">Select Bank</label>
            <div class="grid grid-cols-2 md:grid-cols-3 gap-3">
              <button 
                type="button"
                v-for="group in bankGroups" 
                :key="group.id" 
                @click="selectedBankGroup = group.id"
                class="relative flex items-center p-3 rounded-lg border-2 transition-all duration-200"
                :class="[
                  selectedBankGroup === group.id 
                    ? `border-${group.color}-500 bg-${group.color}-50 ring-2 ring-${group.color}-500/10 shadow-sm` 
                    : 'border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50'
                ]"
              >
                <!-- Icon -->
                <div 
                  class="w-8 h-8 rounded-full flex shrink-0 items-center justify-center mr-3 transition-colors duration-200"
                  :class="[
                    selectedBankGroup === group.id 
                      ? `bg-${group.color}-100 text-${group.color}-600` 
                      : 'bg-gray-100 text-gray-500 group-hover:bg-gray-200'
                  ]"
                >
                  <i :class="['bi text-sm', group.icon]"></i>
                </div>
                
                <!-- Label -->
                <span 
                  class="font-semibold text-sm truncate"
                  :class="selectedBankGroup === group.id ? `text-${group.color}-900` : 'text-gray-700'"
                >
                  {{ group.name }}
                </span>

                <!-- Active Indicator -->
                <div v-if="selectedBankGroup === group.id" class="absolute -top-1.5 -right-1.5 bg-white rounded-full">
                  <i :class="`bi bi-check-circle-fill text-${group.color}-500 text-sm`"></i>
                </div>
              </button>
            </div>
          </div>
          
          <!-- Selected Options Row (Compact 3-column layout) -->
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <!-- 2. Statement Type -->
            <div class="space-y-1">
              <label class="label-base text-sm">Format</label>
              <select class="input-base bg-white py-2" v-model="formData.bankType" required :disabled="!selectedBankGroup">
                <option value="">{{ selectedBankGroup ? 'Choose format...' : 'Select bank first' }}</option>
                <option v-for="type in availableStatementTypes" :key="type.value" :value="type.value">
                  {{ type.label }}
                </option>
              </select>
            </div>
            
            <!-- 3. Year -->
            <div class="space-y-1">
              <label class="label-base text-sm">Year</label>
              <select class="input-base bg-white py-2" v-model="formData.statementYear">
                 <option v-for="year in years" :key="year" :value="year">{{ year }}</option>
              </select>
            </div>

            <!-- 4. Company -->
             <div class="space-y-1">
              <label class="label-base text-sm">Company (Optional)</label>
              <select class="input-base bg-white py-2" v-model="formData.companyId">
                <option value="">-- No Company --</option>
                <option v-for="c in companyStore.companies" :key="c.id" :value="c.id">
                    {{ c.short_name }}
                </option>
              </select>
            </div>
          </div>



          <!-- Upload Area -->
          <div class="space-y-2">
            <label class="label-base">Upload Statement (PDF or CSV)</label>
            <FileDropZone @file-selected="handleFileSelection" />
            <div class="text-center text-xs text-gray-400 mt-2">
               Please select a bank to see format requirements
            </div>
          </div>

          <!-- Actions -->
          <div class="pt-4">
            <button 
                type="submit" 
                :disabled="converterStore.isLoading"
                class="btn-primary w-full py-4 text-base font-bold rounded-2xl disabled:opacity-50 disabled:cursor-not-allowed">
              <i class="bi bi-lightning-charge-fill me-2" v-if="!converterStore.isLoading"></i>
              <span v-if="converterStore.isLoading" class="spinner-border text-white w-5 h-5 me-2" role="status"></span>
              {{ converterStore.isLoading ? 'Processing...' : 'Convert & Extract Data' }}
            </button>
            
            <div v-if="converterStore.error" class="mt-4 p-4 bg-red-50 border border-red-100 rounded-xl text-red-700 text-sm">
                {{ converterStore.error }}
            </div>
            
             <div v-if="converterStore.successMessage" class="mt-4 p-4 bg-green-50 border border-green-100 rounded-xl text-green-700 text-sm">
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
import { onMounted, reactive, computed, ref, watch } from 'vue';
import { useConverterStore } from '../stores/converter';
import { useCompanyStore } from '../stores/companies';
import FileDropZone from '../components/converter/FileDropZone.vue';
import PreviewModal from '../components/converter/PreviewModal.vue';
import PasswordModal from '../components/converter/PasswordModal.vue';


const converterStore = useConverterStore();
const companyStore = useCompanyStore();

onMounted(() => {
    companyStore.fetchCompanies();
});


const currentYear = new Date().getFullYear();
const years = computed(() => {
    const list = [];
    for (let y = currentYear; y >= 2020; y--) list.push(y);
    return list;
});

const selectedBankGroup = ref('');

const bankGroups = [
  {
    id: 'mandiri',
    name: 'Mandiri',
    icon: 'bi-bank',
    color: 'amber',
    types: [
      { label: 'Credit Card', value: 'ccmandiri' },
      { label: 'Bank Account (Email PDF)', value: 'mandiri_email' },
      { label: 'Bank Account (App)', value: 'mandiri' },
    ]
  },
  {
    id: 'bca',
    name: 'BCA',
    icon: 'bi-building',
    color: 'blue',
    types: [
      { label: 'Credit Card', value: 'ccbca' },
      { label: 'Bank Account', value: 'bca' },
    ]
  },
  {
    id: 'bri',
    name: 'BRI',
    icon: 'bi-buildings',
    color: 'orange',
    types: [
      { label: 'Bank Account (CSV)', value: 'bri' },
    ]
  },
  {
    id: 'dbs',
    name: 'DBS',
    icon: 'bi-cash-coin',
    color: 'red',
    types: [
      { label: 'Credit Card', value: 'dbs' },
    ]
  },
  {
    id: 'blu',
    name: 'Blu by BCA',
    icon: 'bi-phone',
    color: 'cyan',
    types: [
      { label: 'Bank Account', value: 'blu' },
    ]
  },
  {
    id: 'saqu',
    name: 'Bank Saqu',
    icon: 'bi-wallet2',
    color: 'rose',
    types: [
      { label: 'Bank Account', value: 'saqu' },
    ]
  }
];

const availableStatementTypes = computed(() => {
  if (!selectedBankGroup.value) return [];
  const group = bankGroups.find(g => g.id === selectedBankGroup.value);
  return group ? group.types : [];
});

watch(selectedBankGroup, () => {
  formData.bankType = '';
});

const formData = reactive({
    bankType: '',
    statementYear: currentYear,
    companyId: ''
});


const handleFileSelection = (file) => {
    converterStore.setFile(file);
};

const showPreview = ref(false);
const previewTransactions = ref([]);

const selectedCompanyName = computed(() => {
    if (!formData.companyId) return 'No Company';
    const company = companyStore.companies.find(c => c.id === formData.companyId);
    return company ? company.short_name : 'No Company';
});


const handleSubmit = async () => {
    if (!converterStore.file) {
        alert("Please upload a file");
        return;
    }
    
    // Check for password protection first
    const checkFd = new FormData();
    checkFd.append('pdf_file', converterStore.file);
    
    try {
        const checkResult = await converterStore.checkPassword(checkFd);
        if (checkResult.password_protected) {
            converterStore.requiresPassword = true;
            return;
        }
    } catch (e) {
        console.error("Failed to check password protection", e);
    }

    // Direct upload if no password or check failed (backend will catch it anyway)
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
    if (converterStore.pdfPassword) {
        fd.append('password', converterStore.pdfPassword);
    }
    
    try {
        const result = await converterStore.uploadFile(fd);
        previewTransactions.value = result.data || [];
        showPreview.value = true;
        converterStore.requiresPassword = false;
    } catch (e) {
        // Error handled in store
    }
}

const handleConfirmSave = async () => {
    const normalizedCompanyId = (formData.companyId || '').toString().trim();
    const fd = new FormData();
    fd.append('pdf_file', converterStore.file);
    fd.append('bank_type', formData.bankType);
    fd.append('statement_year', formData.statementYear);
    fd.append('company_id', normalizedCompanyId);
    if (converterStore.pdfPassword) {
        fd.append('password', converterStore.pdfPassword);
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
