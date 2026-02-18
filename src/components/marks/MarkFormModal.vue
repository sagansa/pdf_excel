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
    is_asset: false
});

watch(() => props.markToEdit, (newVal) => {
    if (newVal) {
        isEdit.value = true;
        form.internal_report = newVal.internal_report || '';
        form.personal_use = newVal.personal_use || '';
        form.tax_report = newVal.tax_report || '';
        form.is_asset = newVal.is_asset || false;
    } else {
        isEdit.value = false;
        form.internal_report = '';
        form.personal_use = '';
        form.tax_report = '';
        form.is_asset = false;
    }
}, { immediate: true });

const close = () => {
    error.value = null;
    emit('close');
};

const handleSubmit = async () => {
    loading.value = true;
    error.value = null;

    try {
        if (isEdit.value) {
            await store.updateMark(props.markToEdit.id, form);
        } else {
            await store.createMark(form);
        }
        emit('saved');
        close();
    } catch (err) {
        error.value = err.response?.data?.error || err.message;
    } finally {
        loading.value = false;
    }
};
</script>
