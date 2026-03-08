<template>
  <div class="space-y-4">
    <!-- Header -->
    <div class="flex justify-between items-center">
      <div>
        <h3 class="text-lg font-bold text-gray-900">Rental Locations</h3>
        <p class="text-xs text-gray-500 mt-1">Manage rental locations for your properties</p>
      </div>
      <button
        @click="openCreateModal"
        class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors"
      >
        <i class="bi bi-plus-lg mr-2"></i>
        Add Location
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="flex justify-center py-12">
      <div class="spinner-border w-8 h-8 text-indigo-600 border-2"></div>
    </div>

    <!-- Empty State -->
    <div v-else-if="!locations.length" class="text-center py-12">
      <div class="w-16 h-16 bg-indigo-50 text-indigo-600 rounded-full flex items-center justify-center mx-auto mb-4">
        <i class="bi bi-geo-alt text-3xl"></i>
      </div>
      <h4 class="text-lg font-bold text-gray-900">No Locations Found</h4>
      <p class="text-gray-500 text-sm mt-1">Create your first rental location</p>
      <button @click="openCreateModal" class="btn-primary mt-4">Create First Location</button>
    </div>

    <!-- Locations Table -->
    <div v-else class="overflow-x-auto">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Address</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">City</th>
            <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr v-for="location in locations" :key="location.id" class="hover:bg-gray-50">
            <td class="px-6 py-4 whitespace-nowrap">
              <div class="text-sm font-bold text-gray-900">{{ location.location_name || location.name }}</div>
            </td>
            <td class="px-6 py-4">
              <div class="text-sm text-gray-500 max-w-md truncate">{{ location.address }}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              <div class="text-sm text-gray-500">{{ location.city || '-' }}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-right">
              <button
                @click="openEditModal(location)"
                class="text-indigo-600 hover:text-indigo-900 mr-3"
              >
                <i class="bi bi-pencil-square"></i>
              </button>
              <button
                @click="confirmDelete(location)"
                class="text-red-600 hover:text-red-900"
              >
                <i class="bi bi-trash"></i>
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Add/Edit Modal -->
    <LocationFormModal
      :is-open="showFormModal"
      :location-id="selectedLocationId"
      :company-id="companyId"
      @close="closeFormModal"
      @saved="onSaved"
    />

    <!-- Delete Confirm -->
    <ConfirmModal
      :is-open="showDeleteConfirm"
      title="Delete Location"
      message="Are you sure you want to delete this location? This action cannot be undone."
      confirm-text="Delete Location"
      variant="danger"
      :loading="isDeleting"
      @close="showDeleteConfirm = false"
      @confirm="executeDelete"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import { rentalApi } from '../../api';
import ConfirmModal from '../ui/ConfirmModal.vue';
import LocationFormModal from './LocationFormModal.vue';

const props = defineProps({
  companyId: String
});

const locations = ref([]);
const isLoading = ref(false);
const showFormModal = ref(false);
const selectedLocationId = ref(null);
const showDeleteConfirm = ref(false);
const locationToDelete = ref(null);
const isDeleting = ref(false);

const loadLocations = async () => {
  if (!props.companyId) {
    console.warn('No companyId provided');
    return;
  }
  isLoading.value = true;
  try {
    console.log('Loading locations for company:', props.companyId);
    const response = await rentalApi.getLocations(props.companyId);
    console.log('Locations response:', response.data);
    locations.value = response.data.locations || [];
  } catch (err) {
    console.error('Failed to load locations:', err);
    alert('Failed to load locations: ' + err.message);
  } finally {
    isLoading.value = false;
  }
};

onMounted(() => {
  loadLocations();
});

watch(() => props.companyId, () => {
  loadLocations();
});

const openCreateModal = () => {
  selectedLocationId.value = null;
  showFormModal.value = true;
};

const openEditModal = (location) => {
  selectedLocationId.value = location.id;
  showFormModal.value = true;
};

const closeFormModal = () => {
  showFormModal.value = false;
  selectedLocationId.value = null;
};

const onSaved = () => {
  loadLocations();
  closeFormModal();
};

const confirmDelete = (location) => {
  locationToDelete.value = location;
  showDeleteConfirm.value = true;
};

const executeDelete = async () => {
  if (!locationToDelete.value) return;
  isDeleting.value = true;
  try {
    await rentalApi.deleteLocation(locationToDelete.value.id);
    showDeleteConfirm.value = false;
    locationToDelete.value = null;
    loadLocations();
  } catch (err) {
    alert('Failed to delete: ' + err.message);
  } finally {
    isDeleting.value = false;
  }
};
</script>
