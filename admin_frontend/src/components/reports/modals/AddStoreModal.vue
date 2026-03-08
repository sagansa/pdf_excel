<template>
  <div v-if="isOpen" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" @click.self="$emit('close')">
    <div class="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
      <div class="p-6 border-b border-gray-200">
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold text-gray-900">{{ editMode ? 'Edit Store' : 'Add New Store' }}</h3>
          <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600">
            <i class="bi bi-x-lg"></i>
          </button>
        </div>
      </div>
      
      <form @submit.prevent="handleSubmit" class="p-6 space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Store Code *</label>
            <input
              v-model="form.store_code"
              type="text"
              required
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              placeholder="e.g., APB"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Store Name *</label>
            <input
              v-model="form.store_name"
              type="text"
              required
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              placeholder="e.g., Alam Sutera"
            />
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Current Location</label>
          <select
            v-model="form.current_location_id"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="">No location assigned</option>
            <option v-for="loc in locations" :key="loc.id" :value="loc.id">
              {{ loc.location_name }} - {{ loc.address }}
            </option>
          </select>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Status</label>
            <select
              v-model="form.status"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            >
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
              <option value="closed">Closed</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Opened Date</label>
            <input
              v-model="form.opened_date"
              type="date"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>
        </div>

        <div v-if="form.status === 'closed'">
          <label class="block text-sm font-medium text-gray-700 mb-1">Closed Date</label>
          <input
            v-model="form.closed_date"
            type="date"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
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
import { ref, watch, onMounted } from 'vue';
import { rentalApi } from '../../../api';

const props = defineProps({
  isOpen: Boolean,
  store: Object,
  companyId: String
});

const emit = defineEmits(['close', 'saved']);

const editMode = ref(false);
const loading = ref(false);
const locations = ref([]);

const form = ref({
  store_code: '',
  store_name: '',
  current_location_id: '',
  status: 'active',
  opened_date: '',
  closed_date: '',
  notes: ''
});

watch(() => props.store, (newStore) => {
  if (newStore && newStore.id) {
    editMode.value = true;
    form.value = { ...newStore };
  } else {
    editMode.value = false;
    if (!props.isOpen) {
      resetForm();
    }
  }
});

watch(() => props.isOpen, async (isOpen) => {
  if (isOpen) {
    await loadLocations();
    if (!props.store) {
      resetForm();
    }
  } else {
    resetForm();
    editMode.value = false;
  }
});

const loadLocations = async () => {
  try {
    const response = await rentalApi.getLocations(props.companyId);
    locations.value = response.data.locations || [];
  } catch (error) {
    console.error('Failed to load locations:', error);
  }
};

const resetForm = () => {
  form.value = {
    store_code: '',
    store_name: '',
    current_location_id: '',
    status: 'active',
    opened_date: '',
    closed_date: '',
    notes: ''
  };
};

const handleSubmit = async () => {
  loading.value = true;
  try {
    const data = {
      ...form.value,
      company_id: props.companyId,
      current_location_id: form.value.current_location_id || null
    };

    if (editMode.value) {
      await rentalApi.updateStore(props.store.id, data);
    } else {
      await rentalApi.createStore(data);
    }

    emit('saved');
    emit('close');
  } catch (error) {
    console.error('Failed to save store:', error);
    alert('Failed to save store: ' + (error.response?.data?.error || error.message));
  } finally {
    loading.value = false;
  }
};
</script>
