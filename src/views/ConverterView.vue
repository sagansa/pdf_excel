<template>
  <div class="max-w-3xl mx-auto space-y-6">
    <div class="bg-white rounded-2xl shadow-sm border border-gray-200 p-8">
      <form @submit.prevent="handleSubmit">
        <div class="space-y-8">
          <!-- Bank & Year Selection -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div class="space-y-2">
              <label class="label-base">Select Your Bank</label>
              <select class="input-base" v-model="formData.bankType" required>
                <option value="">Choose bank...</option>
                <option value="bca">REK BCA</option>
                <option value="mandiri">REK Mandiri</option>
                <option value="bri">REK BRI (CSV)</option>
                <option value="saqu">SAQU</option>
                <option value="blu">BLU BY BCA</option>
                <option value="ccbca">CC BCA</option>
                <option value="dbs">CC DBS</option>
                <option value="ccmandiri">CC Mandiri</option>
              </select>
            </div>
            
            <div class="space-y-2">
              <label class="label-base">Statement Year</label>
              <select class="input-base" v-model="formData.statementYear">
                 <option v-for="year in years" :key="year" :value="year">{{ year }}</option>
              </select>
            </div>
          </div>

          <!-- Company Selection -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
             <div class="space-y-2">
              <label class="label-base">Select Company (Optional)</label>
              <select class="input-base" v-model="formData.companyId">
                <option value="">-- No Company --</option>
                <option v-for="c in companyStore.companies" :key="c.id" :value="c.id">
                    {{ c.short_name }} - {{ c.name }}
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
import { onMounted, reactive, computed, ref } from 'vue';
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
