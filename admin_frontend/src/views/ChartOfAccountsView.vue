<template>
  <div class="space-y-6">
    <PageHeader
      eyebrow="Chart of Accounts"
      icon="bi bi-journal-richtext"
      title="Financial account registry"
      subtitle="Kelola akun aset, liabilitas, ekuitas, revenue, dan expense dari satu register."
    >
      <template #actions>
        <button
          @click="showCreateModal = true"
          class="btn-primary gap-2"
        >
          <i class="bi bi-plus-circle"></i>
          <span>Tambah Akun</span>
        </button>
      </template>
    </PageHeader>

    <!-- Main Content -->
    <div class="space-y-6">
      <!-- Stats Cards -->
      <div class="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
        <StatCard icon="bi bi-cash-stack" label="Assets" :value="coaByCategory.ASSET.length" tone="success" />
        <StatCard icon="bi bi-credit-card" label="Liabilities" :value="coaByCategory.LIABILITY.length" tone="danger" />
        <StatCard icon="bi bi-bank" label="Equity" :value="coaByCategory.EQUITY.length" tone="info" />
        <StatCard icon="bi bi-graph-up-arrow" label="Revenue" :value="coaByCategory.REVENUE.length" tone="accent" />
        <StatCard icon="bi bi-graph-down-arrow" label="Expenses" :value="coaByCategory.EXPENSE.length" tone="warning" />
      </div>

      <!-- Filter & Search -->
      <SectionCard content-class="mb-6" body-class="p-4">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <FormField label="Category" label-class="!text-xs">
            <SelectInput
              v-model="filterCategory"
              :options="categoryOptions"
              placeholder="All Categories"
            />
          </FormField>
          <FormField label="Search" label-class="!text-xs" wrapper-class="md:col-span-2">
            <TextInput
              v-model="searchQuery"
              placeholder="Search by code or name..."
              leading-icon="bi bi-search"
            />
          </FormField>
        </div>
      </SectionCard>

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
import FormField from '../components/ui/FormField.vue';
import PageHeader from '../components/ui/PageHeader.vue';
import SectionCard from '../components/ui/SectionCard.vue';
import SelectInput from '../components/ui/SelectInput.vue';
import StatCard from '../components/ui/StatCard.vue';
import TextInput from '../components/ui/TextInput.vue';

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
const categoryOptions = [
  { value: 'ASSET', label: 'Asset' },
  { value: 'LIABILITY', label: 'Liability' },
  { value: 'EQUITY', label: 'Equity' },
  { value: 'REVENUE', label: 'Revenue' },
  { value: 'EXPENSE', label: 'Expense' }
];

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
