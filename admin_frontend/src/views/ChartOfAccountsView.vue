<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50/30">
    <!-- Header -->
    <div class="bg-white border-b border-gray-200 sticky top-0 z-10 shadow-sm">
      <div class="max-w-7xl mx-auto px-6 py-4">
        <div class="flex items-center justify-between">
          <div>
            <h1 class="text-2xl font-bold text-gray-900">Chart of Accounts</h1>
            <p class="text-sm text-gray-500 mt-1">Daftar Akun Keuangan (CoreTax 2025)</p>
          </div>
          <button
            @click="showCreateModal = true"
            class="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors flex items-center gap-2 shadow-sm"
          >
            <i class="bi bi-plus-circle"></i>
            <span>Tambah Akun</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="max-w-7xl mx-auto px-6 py-6">
      <!-- Stats Cards -->
      <div class="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center">
              <i class="bi bi-cash-stack text-green-600 text-lg"></i>
            </div>
            <div>
              <p class="text-xs text-gray-500">Assets</p>
              <p class="text-xl font-bold text-gray-900">{{ coaByCategory.ASSET.length }}</p>
            </div>
          </div>
        </div>
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-lg bg-red-100 flex items-center justify-center">
              <i class="bi bi-credit-card text-red-600 text-lg"></i>
            </div>
            <div>
              <p class="text-xs text-gray-500">Liabilities</p>
              <p class="text-xl font-bold text-gray-900">{{ coaByCategory.LIABILITY.length }}</p>
            </div>
          </div>
        </div>
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
              <i class="bi bi-bank text-blue-600 text-lg"></i>
            </div>
            <div>
              <p class="text-xs text-gray-500">Equity</p>
              <p class="text-xl font-bold text-gray-900">{{ coaByCategory.EQUITY.length }}</p>
            </div>
          </div>
        </div>
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-lg bg-purple-100 flex items-center justify-center">
              <i class="bi bi-graph-up-arrow text-purple-600 text-lg"></i>
            </div>
            <div>
              <p class="text-xs text-gray-500">Revenue</p>
              <p class="text-xl font-bold text-gray-900">{{ coaByCategory.REVENUE.length }}</p>
            </div>
          </div>
        </div>
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-lg bg-orange-100 flex items-center justify-center">
              <i class="bi bi-graph-down-arrow text-orange-600 text-lg"></i>
            </div>
            <div>
              <p class="text-xs text-gray-500">Expenses</p>
              <p class="text-xl font-bold text-gray-900">{{ coaByCategory.EXPENSE.length }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Filter & Search -->
      <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label class="block text-xs font-medium text-gray-700 mb-1">Category</label>
            <select v-model="filterCategory" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
              <option value="">All Categories</option>
              <option value="ASSET">Asset</option>
              <option value="LIABILITY">Liability</option>
              <option value="EQUITY">Equity</option>
              <option value="REVENUE">Revenue</option>
              <option value="EXPENSE">Expense</option>
            </select>
          </div>
          <div class="md:col-span-2">
            <label class="block text-xs font-medium text-gray-700 mb-1">Search</label>
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Search by code or name..."
              class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            />
          </div>
        </div>
      </div>

      <!-- COA Table -->
      <CoaTable
        :coa-list="filteredCoaList"
        :is-loading="store.isLoading"
        @edit="handleEdit"
        @delete="handleDelete"
      />
    </div>

    <!-- Create/Edit Modal -->
    <CoaFormModal
      v-if="showCreateModal || showEditModal"
      :is-open="showCreateModal || showEditModal"
      :coa="selectedCoa"
      @close="closeModal"
      @save="handleSave"
    />

    <!-- Delete Confirmation Modal -->
    <ConfirmModal
      v-if="showDeleteModal"
      :is-open="showDeleteModal"
      title="Delete Account"
      :message="`Are you sure you want to delete ${selectedCoa?.code} - ${selectedCoa?.name}?`"
      variant="danger"
      :loading="isDeleting"
      @close="showDeleteModal = false"
      @confirm="confirmDelete"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useCoaStore } from '../stores/coa';
import CoaTable from '../components/coa/CoaTable.vue';
import CoaFormModal from '../components/coa/CoaFormModal.vue';
import ConfirmModal from '../components/ui/ConfirmModal.vue';

const store = useCoaStore();

// Modal states
const showCreateModal = ref(false);
const showEditModal = ref(false);
const showDeleteModal = ref(false);
const selectedCoa = ref(null);
const isDeleting = ref(false);

// Filter states
const filterCategory = ref('');
const searchQuery = ref('');

// Computed
const coaByCategory = computed(() => store.coaByCategory);

const filteredCoaList = computed(() => {
  let list = store.coaList;

  // Filter by category
  if (filterCategory.value) {
    list = list.filter(coa => coa.category === filterCategory.value);
  }

  // Filter by search query
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase();
    list = list.filter(coa =>
      coa.code.toLowerCase().includes(query) ||
      coa.name.toLowerCase().includes(query) ||
      (coa.description && coa.description.toLowerCase().includes(query))
    );
  }

  return list;
});

// Methods
const handleEdit = (coa) => {
  selectedCoa.value = { ...coa };
  showEditModal.value = true;
};

const handleDelete = (coa) => {
  selectedCoa.value = coa;
  showDeleteModal.value = true;
};

const handleSave = async (data) => {
  try {
    if (selectedCoa.value?.id) {
      // Update existing
      await store.updateCoa(selectedCoa.value.id, data);
    } else {
      // Create new
      await store.createCoa(data);
    }
    closeModal();
  } catch (error) {
    alert(error.message);
  }
};

const confirmDelete = async () => {
  isDeleting.value = true;
  try {
    await store.deleteCoa(selectedCoa.value.id);
    showDeleteModal.value = false;
    selectedCoa.value = null;
  } catch (error) {
    alert(error.message);
  } finally {
    isDeleting.value = false;
  }
};

const closeModal = () => {
  showCreateModal.value = false;
  showEditModal.value = false;
  selectedCoa.value = null;
};

// Lifecycle
onMounted(() => {
  store.fetchCoa();
});
</script>
