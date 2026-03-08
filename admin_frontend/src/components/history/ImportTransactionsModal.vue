<template>
  <BaseModal :isOpen="isOpen" @close="$emit('close')">
    <div class="bg-white rounded-2xl p-6 w-full max-w-md">
      <h2 class="text-xl font-bold text-gray-900 mb-4">Import Transactions</h2>

      <div class="space-y-4">
        <!-- File Upload -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">Select File (CSV or Excel)</label>
          <input
            type="file"
            ref="fileInput"
            accept=".csv,.xlsx,.xls"
            @change="handleFileChange"
            class="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
          />
          <p class="mt-1 text-xs text-gray-500">Supported formats: CSV, XLSX, XLS</p>
        </div>

        <!-- Bank Code -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">Bank Code (Optional)</label>
          <select
            v-model="bankCode"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="MANUAL">Manual Entry</option>
            <option value="BCA">BCA</option>
            <option value="MANDIRI">Mandiri</option>
            <option value="DBS">DBS</option>
            <option value="BRI">BRI</option>
            <option value="BCA_CC">BCA Credit Card</option>
            <option value="MANDIRI_CC">Mandiri Credit Card</option>
          </select>
        </div>

        <!-- Company -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">Company (Optional)</label>
          <select
            v-model="companyId"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="">No Company</option>
            <option v-for="company in companies" :key="company.id" :value="company.id">
              {{ company.name }}
            </option>
          </select>
        </div>

        <!-- Format Info -->
        <div class="bg-blue-50 border border-blue-200 rounded-lg p-3">
          <h3 class="text-sm font-semibold text-blue-900 mb-2">Required Columns:</h3>
          <p class="text-xs text-blue-700">
            Your file must contain: <strong>date/tanggal</strong>, 
            <strong>description/keterangan</strong>, <strong>amount</strong>, 
            and <strong>db_cr/debit_credit</strong> (or negative amounts for credits)
          </p>
        </div>

        <!-- Actions -->
        <div class="flex gap-3 pt-2">
          <button
            @click="$emit('close')"
            class="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
            :disabled="isLoading"
          >
            Cancel
          </button>
          <button
            @click="handleImport"
            :disabled="!selectedFile || isLoading"
            class="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            <i v-if="isLoading" class="bi bi-arrow-repeat animate-spin"></i>
            <span>{{ isLoading ? 'Importing...' : 'Import' }}</span>
          </button>
        </div>
      </div>
    </div>
  </BaseModal>
</template>

<script setup>
import { ref, watch } from 'vue';
import BaseModal from '../ui/BaseModal.vue';

const props = defineProps({
  isOpen: Boolean,
  companies: Array
});

const emit = defineEmits(['close', 'imported']);

const fileInput = ref(null);
const selectedFile = ref(null);
const bankCode = ref('MANUAL');
const companyId = ref('');
const isLoading = ref(false);

const handleFileChange = (e) => {
  const file = e.target.files[0];
  if (file) {
    selectedFile.value = file;
  }
};

const handleImport = async () => {
  if (!selectedFile.value) return;

  isLoading.value = true;
  try {
    emit('imported', {
      file: selectedFile.value,
      bankCode: bankCode.value,
      companyId: companyId.value || null
    });
    selectedFile.value = null;
    if (fileInput.value) {
      fileInput.value.value = '';
    }
  } finally {
    isLoading.value = false;
  }
};

watch(() => props.isOpen, (newVal) => {
  if (!newVal) {
    selectedFile.value = null;
    bankCode.value = 'MANUAL';
    companyId.value = '';
    if (fileInput.value) {
      fileInput.value.value = '';
    }
  }
});
</script>
