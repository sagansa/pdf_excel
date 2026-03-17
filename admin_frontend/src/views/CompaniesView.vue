<template>
  <div class="max-w-4xl mx-auto space-y-6">
    <PageHeader
      eyebrow="Company Management"
      icon="bi bi-buildings-fill"
      title="Company Directory"
      subtitle="Manage your business entities, abbreviations, and organizational identifiers for tracking."
      :badges="headerBadges"
    />

    <SectionCard>
      <template #header>
        <div class="flex items-center justify-between w-full">
          <div>
            <h3 class="text-lg font-bold text-theme">Entities</h3>
            <p class="text-xs text-muted">A list of all registered business units</p>
          </div>
          <button @click="openAddModal" class="btn-primary px-5 py-2.5">
            <i class="bi bi-plus-lg mr-2"></i>
            Add Company
          </button>
        </div>
      </template>

      <div v-if="store.isLoading" class="flex flex-col items-center justify-center py-20">
        <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-primary"></div>
        <p class="mt-4 text-muted text-sm font-medium">Loading companies...</p>
      </div>

      <div v-else-if="store.companies.length === 0" class="flex flex-col items-center justify-center py-20 text-center">
        <div class="w-20 h-20 rounded-full bg-surface-muted flex items-center justify-center mb-4">
          <i class="bi bi-building text-3xl text-muted/50"></i>
        </div>
        <h4 class="text-lg font-semibold text-theme">No Companies Found</h4>
        <p class="text-sm text-muted max-w-xs mt-1">Start by adding your first business entity to begin mapping transactions.</p>
        <button @click="openAddModal" class="btn-secondary mt-6">
          <i class="bi bi-plus-lg mr-2"></i> Register New Entity
        </button>
      </div>

      <DataList v-else :items="store.companies">
        <template #default="{ item: company }">
          <div class="px-6 py-4 flex items-center justify-between group">
            <div class="flex items-center gap-4">
              <div class="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary font-bold transition-transform group-hover:scale-110">
                {{ company.short_name ? company.short_name.substring(0, 2).toUpperCase() : company.name.substring(0, 2).toUpperCase() }}
              </div>
              <div>
                <h4 class="text-sm font-bold text-theme leading-tight">{{ company.name }}</h4>
                <div class="flex items-center gap-2 mt-1">
                  <span v-if="company.short_name" class="text-[10px] font-bold uppercase tracking-wider text-muted bg-surface-muted px-1.5 py-0.5 rounded border border-border/50">
                    {{ company.short_name }}
                  </span>
                  <span class="text-[10px] text-muted-strong">ID: {{ company.id.split('-')[0] }}...</span>
                </div>
              </div>
            </div>

            <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <button 
                @click="openEditModal(company)" 
                class="w-9 h-9 flex items-center justify-center rounded-lg text-muted hover:text-primary hover:bg-primary/10 transition-colors"
                title="Edit Details"
              >
                <i class="bi bi-pencil-square"></i>
              </button>
              <button 
                @click="confirmDelete(company)" 
                class="w-9 h-9 flex items-center justify-center rounded-lg text-muted hover:text-danger hover:bg-danger/10 transition-colors"
                title="Delete Entity"
              >
                <i class="bi bi-trash3"></i>
              </button>
            </div>
          </div>
        </template>
      </DataList>
    </SectionCard>

    <!-- Modals -->
    <CompanyFormModal 
        :isOpen="showModal" 
        :companyToEdit="selectedCompany"
        @close="showModal = false"
        @saved="showModal = false"
    />

    <ConfirmModal
      :isOpen="showDeleteConfirm"
      title="Delete Entity"
      :message="`Are you sure you want to permanentely delete '${companyToDelete?.name}'? This will affect all associated data.`"
      confirmText="Delete Permanently"
      variant="danger"
      :loading="deleting"
      @close="showDeleteConfirm = false"
      @confirm="executeDelete"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useCompanyStore } from '../stores/companies';
import CompanyFormModal from '../components/companies/CompanyFormModal.vue';
import PageHeader from '../components/ui/PageHeader.vue';
import SectionCard from '../components/ui/SectionCard.vue';
import DataList from '../components/ui/DataList.vue';
import ConfirmModal from '../components/ui/ConfirmModal.vue';

const store = useCompanyStore();
const showModal = ref(false);
const selectedCompany = ref(null);
const headerBadges = [{ icon: 'bi bi-diagram-3', label: 'Master Data' }];

const showDeleteConfirm = ref(false);
const companyToDelete = ref(null);
const deleting = ref(false);

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

const confirmDelete = (company) => {
    companyToDelete.value = company;
    showDeleteConfirm.value = true;
};

const executeDelete = async () => {
    if (!companyToDelete.value) return;
    
    deleting.value = true;
    try {
        await store.deleteCompany(companyToDelete.value.id);
        showDeleteConfirm.value = false;
        companyToDelete.value = null;
    } finally {
        deleting.value = false;
    }
};
</script>

<style scoped>
/* DataList dividers are handled by the component */
</style>
