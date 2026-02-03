<template>
  <div class="max-w-4xl mx-auto space-y-6">
    <div class="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden flex flex-col">
       <div class="px-6 py-4 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
        <div>
            <h3 class="text-lg font-bold text-gray-900">Manage Companies</h3>
            <p class="text-xs text-gray-500">Add or edit company entities</p>
        </div>
        <button @click="openAddModal" class="btn-primary !bg-green-600 hover:!bg-green-700">
          <i class="bi bi-plus-lg me-1"></i> Add Company
        </button>
      </div>

      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Company Name</th>
              <th class="px-6 py-3 text-right text-xs font-bold text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-100">
             <tr v-if="store.isLoading">
                 <td colspan="2" class="text-center py-8">
                     <span class="spinner-border text-indigo-500 w-6 h-6" role="status"></span>
                 </td>
             </tr>
             <tr v-else-if="store.companies.length === 0">
                 <td colspan="2" class="text-center py-8 text-gray-400">No companies found</td>
             </tr>
             <tr v-for="c in store.companies" :key="c.id" class="hover:bg-gray-50">
                <td class="px-6 py-4 text-sm font-medium text-gray-900">
                    {{ c.name }} 
                    <span v-if="c.short_name" class="ml-2 text-xs text-gray-400 font-normal">[{{ c.short_name }}]</span>
                </td>
                <td class="px-6 py-4 text-right text-sm font-medium">
                  <button @click="openEditModal(c)" class="text-indigo-600 hover:text-indigo-900 me-3">
                    <i class="bi bi-pencil-square"></i>
                  </button>
                  <button @click="deleteCompany(c.id)" class="text-red-600 hover:text-red-900">
                    <i class="bi bi-trash3"></i>
                  </button>
                </td>
             </tr>
          </tbody>
        </table>
      </div>
    </div>

    <CompanyFormModal 
        :isOpen="showModal" 
        :companyToEdit="selectedCompany"
        @close="showModal = false"
        @saved="showModal = false"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useCompanyStore } from '../stores/companies';
import CompanyFormModal from '../components/companies/CompanyFormModal.vue';

const store = useCompanyStore();
const showModal = ref(false);
const selectedCompany = ref(null);

onMounted(() => {
    store.fetchCompanies();
});

const openAddModal = () => {
    selectedCompany.value = null;
    showModal.value = true;
};

const openEditModal = (company) => {
    selectedCompany.value = company;
    showModal.value = true;
};

const deleteCompany = async (id) => {
    if(confirm("Are you sure you want to delete this company?")) {
        await store.deleteCompany(id);
    }
};
</script>
