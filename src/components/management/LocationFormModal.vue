<template>
  <div v-if="isOpen" class="fixed inset-0 z-[100] flex items-center justify-center overflow-y-auto overflow-x-hidden bg-black/50 backdrop-blur-sm p-4" @click.self="$emit('close')">
    <div class="relative w-full max-w-2xl bg-white rounded-2xl shadow-2xl flex flex-col max-h-[90vh]">
      <!-- Header -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100 bg-gray-50/80 rounded-t-2xl shrink-0">
        <div>
          <h3 class="text-xl font-bold text-gray-900">{{ locationId ? 'Edit Location' : 'Add New Location' }}</h3>
          <p class="text-xs text-gray-500 mt-0.5">Manage rental property locations</p>
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
            <h4 class="font-bold text-sm">Error saving location</h4>
            <p class="text-xs">{{ error }}</p>
          </div>
        </div>

        <div>
          <label class="block text-sm font-bold text-gray-700 mb-2">Location Name *</label>
          <input
            v-model="form.name"
            type="text"
            required
            class="w-full px-4 py-2 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
            placeholder="e.g., Ruko Permata Hijau"
          />
        </div>

        <div>
          <label class="block text-sm font-bold text-gray-700 mb-2">Address *</label>
          <textarea
            v-model="form.address"
            required
            rows="3"
            class="w-full px-4 py-2 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
            placeholder="Full address"
          ></textarea>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-bold text-gray-700 mb-2">City</label>
            <input
              v-model="form.city"
              type="text"
              class="w-full px-4 py-2 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
            />
          </div>
          <div>
            <label class="block text-sm font-bold text-gray-700 mb-2">Province</label>
            <input
              v-model="form.province"
              type="text"
              class="w-full px-4 py-2 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
            />
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-bold text-gray-700 mb-2">Postal Code</label>
            <input
              v-model="form.postal_code"
              type="text"
              class="w-full px-4 py-2 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
            />
          </div>
          <div>
            <label class="block text-sm font-bold text-gray-700 mb-2">Area (sqm)</label>
            <input
              v-model.number="form.area_sqm"
              type="number"
              step="0.01"
              class="w-full px-4 py-2 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
            />
          </div>
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
          {{ isSaving ? 'Saving...' : 'Save Location' }}
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
  locationId: String,
  companyId: String
});

const emit = defineEmits(['close', 'saved']);

const form = ref({
  name: '',
  address: '',
  city: '',
  province: '',
  postal_code: '',
  area_sqm: null,
  notes: ''
});

const isSaving = ref(false);
const error = ref('');

const init = async () => {
  error.value = '';
  form.value = {
    name: '',
    address: '',
    city: '',
    province: '',
    postal_code: '',
    area_sqm: null,
    notes: ''
  };

  if (props.locationId) {
    try {
      const response = await rentalApi.getLocations(props.companyId);
      const locations = response.data.locations || [];
      const location = locations.find(l => l.id === props.locationId);
      console.log('Editing location:', location);
      if (location) {
        form.value = {
          name: location.name || location.location_name || '',
          address: location.address,
          city: location.city || '',
          province: location.province || '',
          postal_code: location.postal_code || '',
          area_sqm: location.area_sqm || null,
          notes: location.notes || ''
        };
      } else {
        error.value = 'Location not found';
      }
    } catch (e) {
      console.error('Failed to load location details:', e);
      error.value = 'Failed to load location details: ' + (e.response?.data?.error || e.message);
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
    location_name: form.value.name,
    address: form.value.address,
    city: form.value.city,
    province: form.value.province,
    postal_code: form.value.postal_code,
    area_sqm: form.value.area_sqm,
    notes: form.value.notes
  };

  try {
    if (props.locationId) {
      await rentalApi.updateLocation(props.locationId, payload);
    } else {
      await rentalApi.createLocation({
        ...payload,
        company_id: props.companyId
      });
    }
    emit('saved');
  } catch (e) {
    console.error('Error saving location:', e);
    error.value = e.response?.data?.error || e.message || 'Failed to save location';
  } finally {
    isSaving.value = false;
  }
};
</script>
