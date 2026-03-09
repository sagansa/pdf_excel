<template>
  <div class="max-w-4xl mx-auto space-y-6">
    <PageHeader
      eyebrow="Company Directory"
      icon="bi bi-buildings-fill"
      title="Manage registered companies"
      subtitle="Tambah, edit, dan tinjau entitas perusahaan yang dipakai untuk mapping dan reporting."
      :badges="headerBadges"
    />

    <TableShell>
      <template #toolbar>
       <div class="px-6 py-4 border-b flex justify-between items-center surface-header">
        <div>
            <h3 class="text-lg font-bold text-theme">Manage Companies</h3>
            <p class="text-xs text-muted">Add or edit company entities</p>
        </div>
        <button @click="openAddModal" class="btn-primary gap-2">
          <i class="bi bi-plus-lg me-1"></i> Add Company
        </button>
      </div>
      </template>

        <table class="min-w-full table-compact">
          <thead>
            <tr>
              <th class="px-6 py-3 text-left">Company Name</th>
              <th class="px-6 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y" style="border-color: var(--color-border)">
             <tr v-if="store.isLoading">
                 <td colspan="2" class="text-center py-8">
                     <span class="spinner-border w-6 h-6" style="color: var(--color-primary)" role="status"></span>
                 </td>
             </tr>
             <tr v-else-if="store.companies.length === 0">
                 <td colspan="2" class="text-center py-8 text-muted">No companies found</td>
             </tr>
             <tr v-for="c in store.companies" :key="c.id" class="surface-row">
                <td class="px-6 py-4 text-sm font-medium text-theme">
                    {{ c.name }} 
                    <span v-if="c.short_name" class="ml-2 text-xs text-muted font-normal">[{{ c.short_name }}]</span>
                </td>
                <td class="px-6 py-4 text-right text-sm font-medium">
                  <button @click="openEditModal(c)" class="action-link action-link--primary me-3">
                    <i class="bi bi-pencil-square"></i>
                  </button>
                  <button @click="deleteCompany(c.id)" class="action-link action-link--danger">
                    <i class="bi bi-trash3"></i>
                  </button>
                </td>
             </tr>
          </tbody>
        </table>
    </TableShell>

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
import PageHeader from '../components/ui/PageHeader.vue';
import TableShell from '../components/ui/TableShell.vue';

const store = useCompanyStore();
const showModal = ref(false);
const selectedCompany = ref(null);
const headerBadges = [{ icon: 'bi bi-diagram-3', label: 'Master data' }];

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
