<template>
  <BaseModal :isOpen="isOpen" @close="close">
    <template #title>
      <div class="flex items-center gap-2">
        <i :class="['bi', isEdit ? 'bi-pencil-square' : 'bi-plus-circle-fill', 'text-primary']"></i>
        <span>{{ isEdit ? 'Edit Company' : 'Add New Company' }}</span>
      </div>
    </template>

    <div class="p-6 space-y-6">
      <div class="field-stack">
        <label class="label-base">Company Name</label>
        <TextInput 
          v-model="form.name" 
          placeholder="e.g. PT Asa Pangan Bangsa"
          required
        >
          <template #leading>
            <i class="bi bi-building text-muted"></i>
          </template>
        </TextInput>
        <p class="field-hint">Full legal entity name.</p>
      </div>

      <div class="field-stack">
        <label class="label-base">Short Name (Abbreviation)</label>
        <TextInput 
          v-model="form.short_name" 
          placeholder="e.g. APB"
        >
          <template #leading>
            <i class="bi bi-hash text-muted"></i>
          </template>
        </TextInput>
        <p class="field-hint">Used for compact displays and report headers.</p>
      </div>
      
      <div v-if="error" class="bg-danger/5 border border-danger/10 p-3 rounded-xl flex gap-3 text-danger">
        <i class="bi bi-exclamation-circle-fill mt-0.5"></i>
        <p class="text-xs font-medium leading-relaxed">{{ error }}</p>
      </div>
    </div>

    <template #footer>
      <div class="flex items-center justify-end gap-3 w-full">
        <button @click="close" class="btn-secondary" :disabled="loading">
          Cancel
        </button>
        <button 
          @click="handleSubmit" 
          class="btn-primary"
          :disabled="loading || !form.name"
        >
          <i v-if="loading" class="bi bi-arrow-repeat spin mr-2"></i>
          <i v-else class="bi bi-check-lg mr-2"></i>
          {{ isEdit ? 'Update Company' : 'Create Company' }}
        </button>
      </div>
    </template>
  </BaseModal>
</template>

<script setup>
import { ref, watch, reactive } from 'vue';
import BaseModal from '../ui/BaseModal.vue';
import TextInput from '../ui/TextInput.vue';
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

<style scoped>
.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
