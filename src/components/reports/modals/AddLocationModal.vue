<template>
  <div v-if="isOpen" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" @click.self="$emit('close')">
    <div class="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
      <div class="p-6 border-b border-gray-200">
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold text-gray-900">{{ editMode ? 'Edit Location' : 'Add New Location' }}</h3>
          <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600">
            <i class="bi bi-x-lg"></i>
          </button>
        </div>
      </div>
      
      <form @submit.prevent="handleSubmit" class="p-6 space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Location Name *</label>
          <input
            v-model="form.location_name"
            type="text"
            required
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            placeholder="e.g., Ruko Permata Hijau"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Address *</label>
          <textarea
            v-model="form.address"
            required
            rows="3"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            placeholder="Full address"
          ></textarea>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">City</label>
            <input
              v-model="form.city"
              type="text"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Province</label>
            <input
              v-model="form.province"
              type="text"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Postal Code</label>
            <input
              v-model="form.postal_code"
              type="text"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Area (sqm)</label>
            <input
              v-model.number="form.area_sqm"
              type="number"
              step="0.01"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Latitude</label>
            <input
              v-model.number="form.latitude"
              type="number"
              step="any"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              placeholder="-6.2088"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Longitude</label>
            <input
              v-model.number="form.longitude"
              type="number"
              step="any"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              placeholder="106.8456"
            />
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Notes</label>
          <textarea
            v-model="form.notes"
            rows="2"
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
  location: Object,
  companyId: String
});

const emit = defineEmits(['close', 'saved']);

const editMode = ref(false);
const loading = ref(false);

const form = ref({
  location_name: '',
  address: '',
  city: '',
  province: '',
  postal_code: '',
  latitude: null,
  longitude: null,
  area_sqm: null,
  notes: ''
});

watch(() => props.location, (newLocation) => {
  if (newLocation && newLocation.id) {
    editMode.value = true;
    form.value = { ...newLocation };
  } else {
    editMode.value = false;
    if (!props.isOpen) {
      resetForm();
    }
  }
});

watch(() => props.isOpen, (isOpen) => {
  if (!isOpen) {
    resetForm();
    editMode.value = false;
  }
});

const resetForm = () => {
  form.value = {
    location_name: '',
    address: '',
    city: '',
    province: '',
    postal_code: '',
    latitude: null,
    longitude: null,
    area_sqm: null,
    notes: ''
  };
};

const handleSubmit = async () => {
  loading.value = true;
  try {
    const data = {
      ...form.value,
      company_id: props.companyId
    };

    if (editMode.value) {
      await rentalApi.updateLocation(props.location.id, data);
    } else {
      await rentalApi.createLocation(data);
    }

    emit('saved');
    emit('close');
  } catch (error) {
    console.error('Failed to save location:', error);
    alert('Failed to save location: ' + (error.response?.data?.error || error.message));
  } finally {
    loading.value = false;
  }
};
</script>
