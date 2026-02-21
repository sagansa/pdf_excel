<template>
  <BaseModal :isOpen="isOpen" @close="close">
    <template #title>{{ isEdit ? 'Edit Reporting Mark' : 'Add New Mark' }}</template>

    <form @submit.prevent="handleSubmit" class="p-6 space-y-4">
      <div class="space-y-1">
        <label class="label-base">Internal Report Description</label>
        <textarea v-model="form.internal_report" rows="2" class="input-base" placeholder="e.g. Office Expenses Q1"></textarea>
      </div>
      <div class="space-y-1">
        <label class="label-base">Personal Use Description</label>
        <textarea v-model="form.personal_use" rows="2" class="input-base" placeholder="e.g. Family Vacation"></textarea>
      </div>
      <div class="space-y-1">
        <label class="label-base">Tax Report Description</label>
        <textarea v-model="form.tax_report" rows="2" class="input-base" placeholder="e.g. Tax Deductible Donation"></textarea>
      </div>

      <div class="flex items-center gap-2 p-3 bg-indigo-50 rounded-lg border border-indigo-100">
        <input
          type="checkbox"
          id="is_asset"
          v-model="form.is_asset"
          class="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 h-5 w-5"
        />
        <div class="flex-1">
          <label for="is_asset" class="text-sm font-semibold text-gray-900 cursor-pointer">
            Adalah Aset (Untuk Amortisasi)
          </label>
          <p class="text-xs text-gray-500 mt-0.5">
            Centang jika mark ini merepresentasikan pembelian aset yang akan diamortisasi
          </p>
        </div>
      </div>

      <div class="flex items-center gap-2 p-3 bg-amber-50 rounded-lg border border-amber-100">
        <input
          type="checkbox"
          id="is_service"
          v-model="form.is_service"
          class="rounded border-gray-300 text-amber-600 focus:ring-amber-500 h-5 w-5"
        />
        <div class="flex-1">
          <label for="is_service" class="text-sm font-semibold text-gray-900 cursor-pointer">
            Adalah Jasa (Objek Pengelolaan NPWP)
          </label>
          <p class="text-xs text-gray-500 mt-0.5">
            Centang jika mark ini termasuk transaksi jasa (misal handling, trucking, SSM)
          </p>
        </div>
      </div>

      <div class="flex items-center gap-2 p-3 bg-emerald-50 rounded-lg border border-emerald-100">
        <input
          type="checkbox"
          id="is_salary_component"
          v-model="form.is_salary_component"
          class="rounded border-gray-300 text-emerald-600 focus:ring-emerald-500 h-5 w-5"
        />
        <div class="flex-1">
          <label for="is_salary_component" class="text-sm font-semibold text-gray-900 cursor-pointer">
            Salary Component
          </label>
          <p class="text-xs text-gray-500 mt-0.5">
            Centang jika mark ini adalah komponen gaji (untuk rekap payroll per pegawai)
          </p>
        </div>
      </div>

      <div v-if="error" class="text-sm text-red-600 bg-red-50 p-2 rounded">
          {{ error }}
      </div>
    </form>

    <template #footer>
      <button @click="close" class="btn-secondary">Cancel</button>
      <button 
        @click="handleSubmit" 
        class="btn-primary shadow-lg shadow-indigo-100"
        :disabled="loading"
      >
        <span v-if="loading" class="spinner-border w-4 h-4 me-2"></span>
        Save Changes
      </button>
    </template>
  </BaseModal>
</template>

<script setup>
import { ref, watch, reactive } from 'vue';
import BaseModal from '../ui/BaseModal.vue';
import { useMarksStore } from '../../stores/marks';

const props = defineProps({
  isOpen: Boolean,
  markToEdit: Object
});

const emit = defineEmits(['close', 'saved']);
const store = useMarksStore();

const isEdit = ref(false);
const loading = ref(false);
const error = ref(null);

const form = reactive({
    internal_report: '',
    personal_use: '',
    tax_report: '',
    is_asset: false,
    is_service: false,
    is_salary_component: false
});

watch(() => props.markToEdit, (newVal) => {
    console.log('MarkFormModal: markToEdit changed:', newVal);
    if (newVal) {
        isEdit.value = true;
        // Create a fresh copy of the data to avoid reactivity issues
        form.internal_report = newVal.internal_report || '';
        form.personal_use = newVal.personal_use || '';
        form.tax_report = newVal.tax_report || '';
        // Handle both integer (0/1) and boolean values for is_asset
        form.is_asset = Boolean(newVal.is_asset === 1 || newVal.is_asset === true);
        form.is_service = Boolean(newVal.is_service === 1 || newVal.is_service === true);
        form.is_salary_component = Boolean(newVal.is_salary_component === 1 || newVal.is_salary_component === true);
        console.log('MarkFormModal: Form populated:', form);
    } else {
        isEdit.value = false;
        form.internal_report = '';
        form.personal_use = '';
        form.tax_report = '';
        form.is_asset = false;
        form.is_service = false;
        form.is_salary_component = false;
        console.log('MarkFormModal: Form reset to empty');
    }
}, { immediate: true });

// Also watch for modal opening to ensure data is fresh
watch(() => props.isOpen, (isOpen) => {
    console.log('MarkFormModal: isOpen changed:', isOpen);
    if (isOpen && props.markToEdit) {
        // When modal opens with data, ensure form is properly populated
        const mark = props.markToEdit;
        form.internal_report = mark.internal_report || '';
        form.personal_use = mark.personal_use || '';
        form.tax_report = mark.tax_report || '';
        form.is_asset = Boolean(mark.is_asset === 1 || mark.is_asset === true);
        form.is_service = Boolean(mark.is_service === 1 || mark.is_service === true);
        form.is_salary_component = Boolean(mark.is_salary_component === 1 || mark.is_salary_component === true);
        console.log('MarkFormModal: Form refreshed on modal open:', form);
    }
});

const close = () => {
    error.value = null;
    emit('close');
};

const handleSubmit = async () => {
    loading.value = true;
    error.value = null;

    try {
        // Create a copy of form data and ensure is_asset is properly converted
        const formData = {
            ...form,
            is_asset: Boolean(form.is_asset),
            is_service: Boolean(form.is_service),
            is_salary_component: Boolean(form.is_salary_component)
        };
        
        // Debug logging to see what data is being sent
        console.log('Submitting form data:', formData);
        console.log('is_asset value:', formData.is_asset, typeof formData.is_asset);
        
        if (isEdit.value) {
            await store.updateMark(props.markToEdit.id, formData);
        } else {
            await store.createMark(formData);
        }
        emit('saved');
        close();
    } catch (err) {
        error.value = err.response?.data?.error || err.message;
        console.error('Error submitting form:', err);
    } finally {
        loading.value = false;
    }
};
</script>
