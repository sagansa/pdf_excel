<template>
  <div class="space-y-6">
    <!-- Header Controls -->
    <div class="flex justify-between items-center bg-white p-4 rounded-xl shadow-sm border border-gray-200">
      <div>
        <h3 class="text-lg font-bold text-gray-900">COGS Batches</h3>
        <p class="text-xs text-gray-500">Group multiple transactions and assign product costs</p>
      </div>
      <div>
        <button @click="openCreateModal" class="btn-primary flex items-center gap-2">
          <i class="bi bi-plus-lg"></i>
          Create New Batch
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="batchStore.isLoading && !batchStore.batches.length" class="flex justify-center p-12">
      <div class="spinner-border w-8 h-8 text-indigo-600 border-2"></div>
    </div>

    <!-- Empty State -->
    <div v-else-if="!batchStore.batches.length" class="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
      <div class="w-16 h-16 bg-indigo-50 text-indigo-600 rounded-full flex items-center justify-center mx-auto mb-4">
        <i class="bi bi-boxes text-3xl"></i>
      </div>
      <h3 class="text-lg font-bold text-gray-900">No COGS Batches Found</h3>
      <p class="text-gray-500 text-sm mt-1 max-w-sm mx-auto">
        Create a new batch by grouping multiple bank transactions and mapping them to inventory products.
      </p>
      <button @click="openCreateModal" class="btn-primary mt-6">Create First Batch</button>
    </div>

    <!-- Batches List -->
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
      <div 
        v-for="batch in batchStore.batches" 
        :key="batch.id"
        class="bg-white rounded-xl shadow-sm border border-gray-200 p-5 hover:shadow-md transition-shadow relative group"
      >
        <div class="absolute top-4 right-4 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <button @click="openEditModal(batch)" class="text-gray-400 hover:text-indigo-600 transition-colors p-1" title="Edit Batch">
            <i class="bi bi-pencil-square"></i>
          </button>
          <button @click="confirmDelete(batch)" class="text-gray-400 hover:text-red-600 transition-colors p-1" title="Delete Batch">
            <i class="bi bi-trash3"></i>
          </button>
        </div>

        <div class="mb-4 pr-16">
          <div class="flex items-center gap-2 mb-1">
            <span class="bg-indigo-100 text-indigo-700 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase">Batch</span>
            <span class="text-xs text-gray-500">{{ formatDate(batch.batch_date || batch.created_at) }}</span>
          </div>
          <h4 class="font-bold text-gray-900 truncate" :title="batch.memo">{{ batch.memo || 'Unnamed Batch' }}</h4>
        </div>

        <div class="bg-gray-50 rounded-lg p-3 space-y-3 border border-gray-100">
          <div class="flex justify-between items-center text-sm">
            <span class="text-gray-500 font-medium">Transactions</span>
            <span class="font-bold text-gray-900">{{ batch.txn_count }}</span>
          </div>
          <div class="flex justify-between items-center text-sm">
            <span class="text-gray-500 font-medium">Products Linked</span>
            <span class="font-bold text-indigo-600">{{ batch.product_count }}</span>
          </div>
          <div class="pt-3 border-t border-gray-200/60">
            <span class="text-[10px] text-gray-400 font-bold uppercase tracking-wider block mb-2">Unit Prices</span>
            <div class="space-y-1">
              <div 
                v-for="(price, idx) in batch.unit_prices" 
                :key="idx"
                class="flex justify-between items-center text-xs"
              >
                <span class="text-gray-600 truncate flex-1" :title="price.product_name">{{ price.product_name }}</span>
                <span class="font-bold text-indigo-700 whitespace-nowrap ml-2">Rp {{ formatNumber(price.unit_price) }}/unit</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal Form -->
    <HppBatchFormModal
      v-if="showFormModal"
      :is-open="showFormModal"
      :batch-id="selectedBatchId"
      :company-id="companyId"
      @close="closeFormModal"
      @saved="onBatchSaved"
    />

    <!-- Delete Confirm -->
    <ConfirmModal
      :is-open="showDeleteConfirm"
      title="Delete Batch"
      message="Are you sure you want to delete this COGS batch? The specific transactions and products will not be deleted, but they will be unlinked from each other."
      confirm-text="Delete Batch"
      variant="danger"
      :loading="isDeleting"
      @close="showDeleteConfirm = false"
      @confirm="executeDelete"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import { useHppBatchStore } from '../../stores/hppBatch';
import ConfirmModal from '../ui/ConfirmModal.vue';
import HppBatchFormModal from './HppBatchFormModal.vue';

const props = defineProps({
  companyId: String,
  year: [String, Number]
});

const batchStore = useHppBatchStore();

const showFormModal = ref(false);
const selectedBatchId = ref(null);

const showDeleteConfirm = ref(false);
const batchToDelete = ref(null);
const isDeleting = ref(false);

const loadData = async () => {
  await batchStore.fetchBatches(props.companyId);
};

onMounted(() => {
  loadData();
});

watch(() => props.companyId, () => {
  loadData();
});

const openCreateModal = () => {
  selectedBatchId.value = null;
  showFormModal.value = true;
};

const openEditModal = (batch) => {
  selectedBatchId.value = batch.id;
  showFormModal.value = true;
};

const closeFormModal = () => {
  showFormModal.value = false;
  selectedBatchId.value = null;
};

const onBatchSaved = () => {
  loadData();
  closeFormModal();
};

const confirmDelete = (batch) => {
  batchToDelete.value = batch;
  showDeleteConfirm.value = true;
};

const executeDelete = async () => {
  if (!batchToDelete.value) return;
  isDeleting.value = true;
  try {
    await batchStore.deleteBatch(batchToDelete.value.id);
    showDeleteConfirm.value = false;
    batchToDelete.value = null;
  } catch (err) {
    alert("Failed to delete: " + err.message);
  } finally {
    isDeleting.value = false;
  }
};

const formatNumber = (val) => {
  return Number(val || 0).toLocaleString('id-ID');
};

const formatDate = (dateStr) => {
  if (!dateStr) return '';
  // Handle ISO date format (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
  const date = new Date(dateStr);
  if (isNaN(date.getTime())) return dateStr.split(' ')[0]; // Fallback to original
  return date.toLocaleDateString('id-ID', { year: 'numeric', month: 'short', day: 'numeric' });
};
</script>
