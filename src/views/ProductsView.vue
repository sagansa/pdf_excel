<template>
  <div class="max-w-6xl mx-auto space-y-6">
    <!-- Header -->
    <div class="flex justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
      <div class="flex gap-4 items-center">
        <div class="w-12 h-12 bg-indigo-50 text-indigo-600 rounded-xl flex items-center justify-center text-xl shadow-inner">
          <i class="bi bi-box-seam"></i>
        </div>
        <div>
          <h1 class="text-2xl font-bold font-display text-gray-900 tracking-tight">Products Catalog</h1>
          <p class="text-sm text-gray-500 mt-1">Manage standard products and default prices for COGS calculations</p>
        </div>
      </div>
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden flex flex-col">
       <div class="px-6 py-4 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
        <div class="flex items-center gap-3">
          <div class="relative">
             <i class="bi bi-search absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"></i>
             <input type="text" v-model="searchQuery" placeholder="Search products..." class="input-base pl-9 w-64 text-sm bg-white" />
          </div>
          <!-- Global Company Filter -->
          <div class="relative">
             <select v-model="selectedCompanyFilter" class="input-base text-sm bg-white" @change="fetchData">
                 <option :value="''">All Companies</option>
                 <option v-for="c in companyStore.companies" :key="c.id" :value="c.id">{{ c.name }}</option>
             </select>
          </div>
        </div>
        <button @click="openAddModal" class="btn-primary !bg-green-600 hover:!bg-green-700">
          <i class="bi bi-plus-lg me-1"></i> Add Product
        </button>
      </div>

      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">SKU / Code</th>
              <th class="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Product Name</th>
              <th class="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Category</th>
              <th class="px-6 py-3 text-right text-xs font-bold text-gray-500 uppercase tracking-wider">Default Price</th>
              <th class="px-6 py-3 text-center text-xs font-bold text-gray-500 uppercase tracking-wider">Mapping</th>
              <th class="px-6 py-3 text-right text-xs font-bold text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-100">
             <tr v-if="store.isLoading || companyStore.isLoading">
                 <td colspan="6" class="text-center py-8">
                     <span class="spinner-border text-indigo-500 w-6 h-6" role="status"></span>
                 </td>
             </tr>
             <tr v-else-if="filteredProducts.length === 0">
                 <td colspan="6" class="text-center py-8 text-gray-400">
                    <i class="bi bi-inbox text-3xl mb-2 block"></i>
                    No products found
                </td>
             </tr>
             <tr v-for="p in filteredProducts" :key="p.id" class="hover:bg-gray-50">
                <td class="px-6 py-4 text-sm text-gray-600 font-mono">{{ p.code || '-' }}</td>
                <td class="px-6 py-4 text-sm font-medium text-gray-900">{{ p.name }}</td>
                <td class="px-6 py-4 text-sm text-gray-500">
                    <span v-if="p.category" class="px-2 py-1 bg-gray-100 text-gray-600 rounded-md text-xs">{{ p.category }}</span>
                    <span v-else>-</span>
                </td>
                <td class="px-6 py-4 text-sm text-right font-medium text-gray-700">
                    {{ p.default_currency }} {{ formatNumber(p.default_price) }}
                </td>
                <td class="px-6 py-4 text-xs text-center text-gray-500">
                    {{ getCompanyName(p.company_id) || 'Global' }}
                </td>
                <td class="px-6 py-4 text-right text-sm font-medium">
                  <button @click="openEditModal(p)" class="text-indigo-600 hover:text-indigo-900 me-3" title="Edit">
                    <i class="bi bi-pencil-square"></i>
                  </button>
                  <button @click="deleteProduct(p.id)" class="text-red-600 hover:text-red-900" title="Delete">
                    <i class="bi bi-trash3"></i>
                  </button>
                </td>
             </tr>
          </tbody>
        </table>
      </div>
    </div>

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

const store = useProductStore();
const companyStore = useCompanyStore();

const showModal = ref(false);
const selectedProduct = ref(null);
const searchQuery = ref('');
const selectedCompanyFilter = ref('');

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
