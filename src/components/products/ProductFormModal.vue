<template>
  <BaseModal :isOpen="isOpen" @close="close">
    <template #title>{{ isEdit ? 'Edit Product' : 'Add Product' }}</template>

    <form @submit.prevent="handleSubmit" class="p-6 space-y-4">
      <div class="space-y-1">
        <label class="label-base">Product Name</label>
        <input 
            v-model="form.name" 
            type="text" 
            class="input-base" 
            placeholder="e.g. Server X1"
            required
        >
      </div>
      <div class="grid grid-cols-2 gap-4">
        <div class="space-y-1">
          <label class="label-base">Product Code / SKU</label>
          <input 
              v-model="form.code" 
              type="text" 
              class="input-base" 
              placeholder="e.g. SVR-X1"
          >
        </div>
        <div class="space-y-1">
          <label class="label-base">Category</label>
          <input 
              v-model="form.category" 
              type="text" 
              class="input-base" 
              placeholder="e.g. Electronics"
          >
        </div>
      </div>
      <div class="grid grid-cols-2 gap-4">
        <div class="space-y-1">
          <label class="label-base">Default Currency</label>
          <select v-model="form.default_currency" class="input-base">
            <option value="USD">USD</option>
            <option value="CNY">CNY</option>
            <option value="IDR">IDR</option>
            <option value="EUR">EUR</option>
            <option value="SGD">SGD</option>
          </select>
        </div>
        <div class="space-y-1">
          <label class="label-base">Default Price</label>
          <input 
              v-model.number="form.default_price" 
              type="number" 
              step="0.01"
              class="input-base" 
              placeholder="e.g. 500.00"
          >
        </div>
      </div>
      <div class="space-y-1">
          <label class="label-base">Company Mapping</label>
          <select v-model="form.company_id" class="input-base">
              <option :value="null">All Companies (Global)</option>
              <option v-for="c in companies" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
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
import { ref, watch, reactive, onMounted } from 'vue';
import BaseModal from '../ui/BaseModal.vue';
import { useProductStore } from '../../stores/products';
import { useCompanyStore } from '../../stores/companies';

const props = defineProps({
  isOpen: Boolean,
  productToEdit: Object // null if adding
});

const emit = defineEmits(['close', 'saved']);
const store = useProductStore();
const companyStore = useCompanyStore();

const isEdit = ref(false);
const loading = ref(false);
const error = ref(null);
const companies = ref([]);

const form = reactive({
    company_id: null,
    code: '',
    name: '',
    category: '',
    default_currency: 'USD',
    default_price: 0.0
});

onMounted(async () => {
    if (companyStore.companies.length === 0) {
        await companyStore.fetchCompanies();
    }
    companies.value = companyStore.companies;
});

watch(() => props.productToEdit, (newVal) => {
    if (newVal && newVal.id) {
        isEdit.value = true;
        form.company_id = newVal.company_id || null;
        form.code = newVal.code || '';
        form.name = newVal.name || '';
        form.category = newVal.category || '';
        form.default_currency = newVal.default_currency || 'USD';
        form.default_price = newVal.default_price || 0;
    } else {
        isEdit.value = false;
        form.company_id = newVal ? (newVal.company_id || null) : null;
        form.code = '';
        form.name = '';
        form.category = '';
        form.default_currency = 'USD';
        form.default_price = 0;
    }
}, { immediate: true });

const close = () => {
    error.value = null;
    emit('close');
};

const handleSubmit = async () => {
    if (!form.name) {
        error.value = "Product name is required";
        return;
    }

    loading.value = true;
    error.value = null;

    try {
        const payload = { ...form };
        if (isEdit.value) {
            await store.updateProduct(props.productToEdit.id, payload);
        } else {
            await store.createProduct(payload);
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
