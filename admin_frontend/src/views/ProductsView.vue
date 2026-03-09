<template>
  <div class="max-w-6xl mx-auto space-y-6">
    <PageHeader
      eyebrow="Product Catalog"
      icon="bi bi-box-seam-fill"
      title="Standard products and default pricing"
      subtitle="Manage product masters used for COGS and operational calculations."
      :badges="headerBadges"
    />

    <TableShell>
      <template #toolbar>
       <div class="px-6 py-4 border-b flex justify-between items-center surface-header">
        <div class="flex items-center gap-3">
          <TextInput
            v-model="searchQuery"
            placeholder="Search products..."
            leading-icon="bi bi-search"
            class="w-64"
          />
          <SelectInput
            v-model="selectedCompanyFilter"
            :options="companyOptions"
            placeholder="All Companies"
            class="min-w-[220px]"
            @update:model-value="fetchData"
          />
        </div>
        <button @click="openAddModal" class="btn-primary gap-2">
          <i class="bi bi-plus-lg me-1"></i> Add Product
        </button>
      </div>
      </template>

        <table class="min-w-full table-compact">
          <thead>
            <tr>
              <th class="px-6 py-3 text-left">SKU / Code</th>
              <th class="px-6 py-3 text-left">Product Name</th>
              <th class="px-6 py-3 text-left">Category</th>
              <th class="px-6 py-3 text-right">Default Price</th>
              <th class="px-6 py-3 text-center">Mapping</th>
              <th class="px-6 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y" style="border-color: var(--color-border)">
             <tr v-if="store.isLoading || companyStore.isLoading">
                 <td colspan="6" class="text-center py-8">
                     <span class="spinner-border w-6 h-6" style="color: var(--color-primary)" role="status"></span>
                 </td>
             </tr>
             <tr v-else-if="filteredProducts.length === 0">
                 <td colspan="6" class="text-center py-8 text-muted">
                    <i class="bi bi-inbox text-3xl mb-2 block"></i>
                    No products found
                </td>
             </tr>
             <tr v-for="p in filteredProducts" :key="p.id" class="surface-row">
                <td class="px-6 py-4 text-sm text-muted mono">{{ p.code || '-' }}</td>
                <td class="px-6 py-4 text-sm font-medium text-theme">{{ p.name }}</td>
                <td class="px-6 py-4 text-sm text-muted">
                    <span v-if="p.category" class="product-category">{{ p.category }}</span>
                    <span v-else>-</span>
                </td>
                <td class="px-6 py-4 text-sm text-right font-medium text-theme mono">
                    {{ p.default_currency }} {{ formatNumber(p.default_price) }}
                </td>
                <td class="px-6 py-4 text-xs text-center text-muted">
                    {{ getCompanyName(p.company_id) || 'Global' }}
                </td>
                <td class="px-6 py-4 text-right text-sm font-medium">
                  <button @click="openEditModal(p)" class="action-link action-link--primary me-3" title="Edit">
                    <i class="bi bi-pencil-square"></i>
                  </button>
                  <button @click="deleteProduct(p.id)" class="action-link action-link--danger" title="Delete">
                    <i class="bi bi-trash3"></i>
                  </button>
                </td>
             </tr>
          </tbody>
        </table>
    </TableShell>

    <ProductFormModal 
        v-if="showModal"
        :isOpen="showModal" 
        :productToEdit="selectedProduct"
        @close="showModal = false"
        @saved="onSaved"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useProductStore } from '../stores/products';
import { useCompanyStore } from '../stores/companies';
import ProductFormModal from '../components/products/ProductFormModal.vue';
import PageHeader from '../components/ui/PageHeader.vue';
import SelectInput from '../components/ui/SelectInput.vue';
import TableShell from '../components/ui/TableShell.vue';
import TextInput from '../components/ui/TextInput.vue';

const store = useProductStore();
const companyStore = useCompanyStore();

const showModal = ref(false);
const selectedProduct = ref(null);
const searchQuery = ref('');
const selectedCompanyFilter = ref('');
const headerBadges = [
    { icon: 'bi bi-tags', label: 'SKU-aware' },
    { icon: 'bi bi-cash-stack', label: 'Default pricing' }
];

const companyOptions = computed(() => (
    (companyStore.companies || []).map(c => ({ value: c.id, label: c.name }))
));

const formatNumber = (num) => {
    return Number(num).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

const getCompanyName = (companyId) => {
    if (!companyId) return null;
    const comp = companyStore.companies.find(c => c.id === companyId);
    return comp ? comp.short_name || comp.name : null;
};

const fetchData = async () => {
    await store.fetchProducts(selectedCompanyFilter.value || null);
};

onMounted(async () => {
    if (companyStore.companies.length === 0) {
        await companyStore.fetchCompanies();
    }
    await fetchData();
});

const filteredProducts = computed(() => {
    let result = store.products;
    if (searchQuery.value) {
        const query = searchQuery.value.toLowerCase();
        result = result.filter(p => 
            p.name.toLowerCase().includes(query) || 
            (p.code && p.code.toLowerCase().includes(query)) ||
            (p.category && p.category.toLowerCase().includes(query))
        );
    }
    return result;
});

const openAddModal = () => {
    selectedProduct.value = { company_id: selectedCompanyFilter.value || null }; // pre-fill company
    showModal.value = true;
};

const openEditModal = (product) => {
    selectedProduct.value = { ...product };
    showModal.value = true;
};

const deleteProduct = async (id) => {
    if(confirm("Are you sure you want to delete this product?")) {
        await store.deleteProduct(id, selectedCompanyFilter.value || null);
    }
};

const onSaved = () => {
    showModal.value = false;
    fetchData();
};
</script>

<style scoped>
.surface-header {
  border-color: var(--color-border);
  background: var(--color-surface-muted);
}

.surface-row {
  transition: background-color 160ms ease;
}

.surface-row:hover {
  background: rgba(15, 118, 110, 0.05);
}

.product-category {
  @apply rounded-md px-2 py-1 text-xs;
  background: var(--color-surface-muted);
  color: var(--color-text-muted);
}

.action-link {
  transition: color 160ms ease;
}

.action-link--primary {
  color: var(--color-primary);
}

.action-link--danger {
  color: var(--color-danger);
}
</style>
