<template>
  <BaseModal :isOpen="isOpen" @close="close">
    <template #title>{{ isEdit ? 'Edit Company' : 'Add Company' }}</template>

    <form @submit.prevent="handleSubmit" class="p-6 space-y-4">
      <div class="space-y-1">
        <label class="label-base">Company Name</label>
        <input 
            v-model="form.name" 
            type="text" 
            class="input-base" 
            placeholder="e.g. PT Asa Pangan Bangsa"
            required
        >
      </div>
      <div class="space-y-1">
        <label class="label-base">Short Name (Abbreviation)</label>
        <input 
            v-model="form.short_name" 
            type="text" 
            class="input-base" 
            placeholder="e.g. APB"
        >
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
import { useCompanyStore } from '../../stores/companies';

const props = defineProps({
  isOpen: Boolean,
  companyToEdit: Object // null if adding
});

const emit = defineEmits(['close', 'saved']);
const store = useCompanyStore();

const isEdit = ref(false);
const loading = ref(false);
const error = ref(null);

const form = reactive({
    name: '',
    short_name: ''
});

watch(() => props.companyToEdit, (newVal) => {
    if (newVal) {
        isEdit.value = true;
        form.name = newVal.name;
        form.short_name = newVal.short_name || '';
    } else {
        isEdit.value = false;
        form.name = '';
        form.short_name = '';
    }
}, { immediate: true });

const close = () => {
    error.value = null;
    emit('close');
};

const handleSubmit = async () => {
    if (!form.name) {
        error.value = "Company name is required";
        return;
    }

    loading.value = true;
    error.value = null;

    try {
        if (isEdit.value) {
            await store.updateCompany(props.companyToEdit.id, form);
        } else {
            await store.createCompany(form);
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
