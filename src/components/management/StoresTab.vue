<template>
  <div class="space-y-4">
    <!-- Header -->
    <div class="flex justify-between items-center">
      <div>
        <h3 class="text-lg font-bold text-gray-900">Rental Stores</h3>
        <p class="text-xs text-gray-500 mt-1">Manage rental stores and outlets</p>
      </div>
      <button
        @click="openCreateModal"
        class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors"
      >
        <i class="bi bi-plus-lg mr-2"></i>
        Add Store
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="flex justify-center py-12">
      <div class="spinner-border w-8 h-8 text-indigo-600 border-2"></div>
    </div>

    <!-- Empty State -->
    <div v-else-if="!stores.length" class="text-center py-12">
      <div class="w-16 h-16 bg-indigo-50 text-indigo-600 rounded-full flex items-center justify-center mx-auto mb-4">
        <i class="bi bi-shop text-3xl"></i>
      </div>
      <h4 class="text-lg font-bold text-gray-900">No Stores Found</h4>
      <p class="text-gray-500 text-sm mt-1">Create your first store</p>
      <button @click="openCreateModal" class="btn-primary mt-4">Create First Store</button>
    </div>

    <!-- Stores Table -->
    <div v-else class="overflow-x-auto">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Store Name</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Store Code</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
            <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr v-for="store in stores" :key="store.id" class="hover:bg-gray-50">
            <td class="px-6 py-4 whitespace-nowrap">
              <div class="text-sm font-bold text-gray-900">{{ store.store_name || store.name }}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              <div class="text-sm text-gray-500">{{ store.store_code || '-' }}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              <span class="px-2 py-1 text-xs font-medium rounded-full" 
                    :class="store.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'">
                {{ store.status || 'active' }}
              </span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-right">
              <button
                @click="openEditModal(store)"
                class="text-indigo-600 hover:text-indigo-900 mr-3"
              >
                <i class="bi bi-pencil-square"></i>
              </button>
              <button
                @click="confirmDelete(store)"
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
    <StoreFormModal
      :is-open="showFormModal"
      :store-id="selectedStoreId"
      :company-id="companyId"
      @close="closeFormModal"
      @saved="onSaved"
    />

    <!-- Delete Confirm -->
    <ConfirmModal
      :is-open="showDeleteConfirm"
      title="Delete Store"
      message="Are you sure you want to delete this store? This action cannot be undone."
      confirm-text="Delete Store"
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
import StoreFormModal from './StoreFormModal.vue';

const props = defineProps({
  companyId: String
});

const stores = ref([]);
const isLoading = ref(false);
const showFormModal = ref(false);
const selectedStoreId = ref(null);
const showDeleteConfirm = ref(false);
const storeToDelete = ref(null);
const isDeleting = ref(false);

const loadStores = async () => {
  if (!props.companyId) {
    console.warn('No companyId provided');
    return;
  }
  isLoading.value = true;
  try {
    console.log('Loading stores for company:', props.companyId);
    const response = await rentalApi.getStores(props.companyId);
    console.log('Stores response:', response.data);
    stores.value = response.data.stores || [];
  } catch (err) {
    console.error('Failed to load stores:', err);
    alert('Failed to load stores: ' + err.message);
  } finally {
    isLoading.value = false;
  }
};

onMounted(() => {
  loadStores();
});

watch(() => props.companyId, () => {
  loadStores();
});

const openCreateModal = () => {
  selectedStoreId.value = null;
  showFormModal.value = true;
};

const openEditModal = (store) => {
  selectedStoreId.value = store.id;
  showFormModal.value = true;
};

const closeFormModal = () => {
  showFormModal.value = false;
  selectedStoreId.value = null;
};

const onSaved = () => {
  loadStores();
  closeFormModal();
};

const confirmDelete = (store) => {
  storeToDelete.value = store;
  showDeleteConfirm.value = true;
};

const executeDelete = async () => {
  if (!storeToDelete.value) return;
  isDeleting.value = true;
  try {
    await rentalApi.deleteStore(storeToDelete.value.id);
    showDeleteConfirm.value = false;
    storeToDelete.value = null;
    loadStores();
  } catch (err) {
    alert('Failed to delete: ' + err.message);
  } finally {
    isDeleting.value = false;
  }
};
</script>
