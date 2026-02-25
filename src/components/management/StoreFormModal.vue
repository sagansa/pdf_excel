<template>
  <div v-if="isOpen" class="fixed inset-0 z-[100] flex items-center justify-center overflow-y-auto overflow-x-hidden bg-black/50 backdrop-blur-sm p-4" @click.self="$emit('close')">
    <div class="relative w-full max-w-2xl bg-white rounded-2xl shadow-2xl flex flex-col max-h-[90vh]">
      <!-- Header -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100 bg-gray-50/80 rounded-t-2xl shrink-0">
        <div>
          <h3 class="text-xl font-bold text-gray-900">{{ storeId ? 'Edit Store' : 'Add New Store' }}</h3>
          <p class="text-xs text-gray-500 mt-0.5">Manage rental stores and outlets</p>
        </div>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 bg-white hover:bg-gray-100 rounded-full p-2 transition-colors shadow-sm border border-gray-200">
          <i class="bi bi-x-lg text-lg"></i>
        </button>
      </div>

      <!-- Scrollable Content -->
      <div class="p-6 overflow-y-auto flex-1 space-y-4">
        <!-- Error Alert -->
        <div v-if="error" class="bg-red-50 text-red-700 p-4 rounded-xl border border-red-100 flex items-start gap-3">
          <i class="bi bi-exclamation-triangle-fill mt-0.5"></i>
          <div>
            <h4 class="font-bold text-sm">Error saving store</h4>
            <p class="text-xs">{{ error }}</p>
          </div>
        </div>

        <div>
          <label class="block text-sm font-bold text-gray-700 mb-2">Store Name *</label>
          <input
            v-model="form.name"
            type="text"
            required
            class="w-full px-4 py-2 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
            placeholder="e.g., Store A"
          />
        </div>

        <div>
          <label class="block text-sm font-bold text-gray-700 mb-2">Location</label>
          <select
            v-model="form.location_id"
            class="w-full px-4 py-2 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
          >
            <option value="">-- Select Location (Optional) --</option>
            <option v-for="loc in locations" :key="loc.id" :value="loc.id">
              {{ loc.location_name || loc.name }}
            </option>
          </select>
        </div>

        <div>
          <label class="block text-sm font-bold text-gray-700 mb-2">Address</label>
          <textarea
            v-model="form.address"
            rows="3"
            class="w-full px-4 py-2 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
            placeholder="Store address (optional)"
          ></textarea>
        </div>

        <div>
          <label class="block text-sm font-bold text-gray-700 mb-2">Notes</label>
          <textarea
            v-model="form.notes"
            rows="2"
            class="w-full px-4 py-2 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
            placeholder="Additional notes (optional)"
          ></textarea>
        </div>
      </div>

      <!-- Footer -->
      <div class="px-6 py-4 border-t border-gray-100 bg-gray-50/80 rounded-b-2xl shrink-0 flex justify-end gap-3">
        <button @click="$emit('close')" class="px-5 py-2.5 text-sm font-bold text-gray-600 hover:bg-gray-100 rounded-xl transition-colors">
          Cancel
        </button>
        <button
          @click="handleSubmit"
          :disabled="isSaving"
          class="px-6 py-2.5 bg-indigo-600 text-white text-sm font-bold rounded-xl hover:bg-indigo-700 active:bg-indigo-800 transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          <span v-if="isSaving" class="spinner-border w-4 h-4 text-white border-2"></span>
          <i v-else class="bi bi-check2-circle"></i>
          {{ isSaving ? 'Saving...' : 'Save Store' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import { rentalApi } from '../../api';

const props = defineProps({
  isOpen: Boolean,
  storeId: String,
  companyId: String
});

const emit = defineEmits(['close', 'saved']);

const form = ref({
  name: '',
  location_id: '',
  address: '',
  notes: ''
});

const locations = ref([]);
const isSaving = ref(false);
const error = ref('');

const loadLocations = async () => {
  if (!props.companyId) return;
  try {
    const response = await rentalApi.getLocations(props.companyId);
    locations.value = response.data.locations || [];
    console.log('Loaded locations:', locations.value);
  } catch (e) {
    console.error('Failed to load locations:', e);
  }
};

const init = async () => {
  error.value = '';
  form.value = {
    name: '',
    location_id: '',
    address: '',
    notes: ''
  };

  await loadLocations();

  if (props.storeId) {
    try {
      const response = await rentalApi.getStores(props.companyId);
      const stores = response.data.stores || [];
      const store = stores.find(s => s.id === props.storeId);
      console.log('Editing store:', store);
      if (store) {
        form.value = {
          name: store.store_name || store.name || '',
          location_id: store.location_id || store.current_location_id || '',
          address: store.address || '',
          notes: store.notes || ''
        };
      } else {
        error.value = 'Store not found';
      }
    } catch (e) {
      console.error('Failed to load store details:', e);
      error.value = 'Failed to load store details: ' + (e.response?.data?.error || e.message);
    }
  }
};

onMounted(() => {
  if (props.isOpen) init();
});

watch(() => props.isOpen, (newVal) => {
  if (newVal) init();
});

const handleSubmit = async () => {
  isSaving.value = true;
  error.value = '';

  // Map form fields to backend expected fields
  const payload = {
    store_code: form.value.name, // Backend expects store_code
    store_name: form.value.name, // Backend expects store_name
    current_location_id: form.value.location_id || null,
    status: 'active', // Default status
    notes: form.value.notes
  };

  console.log('Saving store with payload:', payload);

  try {
    if (props.storeId) {
      await rentalApi.updateStore(props.storeId, payload);
    } else {
      await rentalApi.createStore({
        ...payload,
        company_id: props.companyId
      });
    }
    emit('saved');
  } catch (e) {
    console.error('Error saving store:', e);
    error.value = e.response?.data?.error || e.message || 'Failed to save store';
  } finally {
    isSaving.value = false;
  }
};
</script>
