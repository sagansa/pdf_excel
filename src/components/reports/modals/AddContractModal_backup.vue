<!-- Backup of current AddContractModal.vue -->
<template>
  <div v-if="isOpen" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" @click.self="$emit('close')">
    <div class="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
      <div class="p-6 border-b border-gray-200">
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold text-gray-900">{{ editMode ? 'Edit Contract' : 'Add New Contract' }}</h3>
          <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600">
            <i class="bi bi-x-lg"></i>
          </button>
        </div>
      </div>
      
      <form @submit.prevent="handleSubmit" class="p-6 space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Store *</label>
          <select
            v-model="form.store_id"
            required
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="">Select a store...</option>
            <option v-for="store in stores" :key="store.id" :value="store.id">
              {{ store.store_code }} - {{ store.store_name }}
            </option>
          </select>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Location *</label>
          <select
            v-model="form.location_id"
            required
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="">Select a location...</option>
            <option v-for="loc in locations" :key="loc.id" :value="loc.id">
              {{ loc.location_name }} - {{ loc.address }}
            </option>
          </select>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Start Date *</label>
            <input
              v-model="form.start_date"
              type="date"
              required
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">End Date *</label>
            <input
              v-model="form.end_date"
              type="date"
              required
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Total Amount *</label>
          <input
            :value="formatCurrency(calculatedBrutoAmount || 0)"
            type="text"
            readonly
            disabled
            class="w-full px-3 py-2 border border-gray-200 rounded-lg bg-gray-50 text-gray-700 cursor-not-allowed"
            placeholder="Select transactions to calculate total"
          />
          <p class="mt-1 text-xs text-gray-500">
            <i class="bi bi-info-circle mr-1"></i>
            Total is automatically calculated from selected transactions
          </p>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Status</label>
          <select
            v-model="form.status"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="active">Active</option>
            <option value="expired">Expired</option>
            <option value="terminated">Terminated</option>
          </select>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Notes</label>
          <textarea
            v-model="form.notes"
            rows="3"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          ></textarea>
        </div>

        <div class="flex justify-end gap-3 pt-4 border-t border-gray-200">
          <button
            type="button"
            @click="$emit('close')"
            class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            :disabled="loading"
            class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50"
          >
            {{ loading ? 'Saving...' : (editMode ? 'Update' : 'Create') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue';
import { rentalApi } from '../../../api';

const props = defineProps({
  isOpen: Boolean,
  contract: Object,
  companyId: String
});

const emit = defineEmits(['close', 'saved']);

const editMode = ref(false);
const loading = ref(false);
const stores = ref([]);
const locations = ref([]);

const form = ref({
  store_id: '',
  location_id: '',
  start_date: '',
  end_date: '',
  total_amount: 0,
  status: 'active',
  notes: ''
});

const calculatedBrutoAmount = ref(0);

const formatCurrency = (amount) => {
  if (!amount) return 'Rp 0';
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    minimumFractionDigits: 0
  }).format(amount);
};

const loadStores = async () => {
  try {
    const response = await rentalApi.getStores(null);
    stores.value = response.data.stores || [];
  } catch (error) {
    console.error('Failed to load stores:', error);
    stores.value = [];
  }
};

const loadLocations = async () => {
  try {
    const response = await rentalApi.getLocations(props.companyId);
    locations.value = response.data.locations || [];
    console.log('Loaded locations:', locations.value);
  } catch (error) {
    console.error('Failed to load locations:', error);
    locations.value = [];
  }
};

watch(() => props.isOpen, async (isOpen) => {
  if (isOpen) {
    await Promise.all([loadStores(), loadLocations()]);
  }
});

const handleSubmit = async () => {
  loading.value = true;
  try {
    const data = {
      ...form.value,
      company_id: props.companyId
    };

    if (editMode.value) {
      await rentalApi.updateContract(props.contract.id, data);
    } else {
      await rentalApi.createContract(data);
    }

    emit('saved');
    emit('close');
  } catch (error) {
    console.error('Failed to save contract:', error);
    alert('Failed to save contract: ' + (error.response?.data?.error || error.message));
  } finally {
    loading.value = false;
  }
};
</script>
