<template>
  <div class="space-y-6">
    <!-- Header with Filters -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div class="flex items-center justify-between mb-4">
        <div>
          <h2 class="text-2xl font-bold text-gray-900">Locations & Stores</h2>
          <p class="text-sm text-gray-500 mt-1">Manage rental locations and stores</p>
        </div>
      </div>
      
      <!-- Filters -->
      <div class="flex gap-4 items-end">
        <div class="flex-1">
          <label class="block text-sm font-medium text-gray-700 mb-1">Company</label>
          <select
            v-model="selectedCompanyId"
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="">-- Select Company --</option>
            <option v-for="company in companies" :key="company.id" :value="company.id">
              {{ company.name }}
            </option>
          </select>
        </div>
      </div>
    </div>

    <!-- Tabs -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      <div class="border-b border-gray-200">
        <nav class="flex gap-4 px-6" aria-label="Tabs">
          <button
            @click="activeTab = 'locations'"
            :class="[
              activeTab === 'locations'
                ? 'border-indigo-500 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
              'whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors'
            ]"
          >
            <i class="bi bi-geo-alt mr-2"></i>
            Locations
          </button>
          <button
            @click="activeTab = 'stores'"
            :class="[
              activeTab === 'stores'
                ? 'border-indigo-500 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
              'whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors'
            ]"
          >
            <i class="bi bi-shop mr-2"></i>
            Stores
          </button>
        </nav>
      </div>

      <!-- Tab Content -->
      <div class="p-6">
        <LocationsTab v-if="activeTab === 'locations'" :company-id="selectedCompanyId" />
        <StoresTab v-if="activeTab === 'stores'" :company-id="selectedCompanyId" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { companyApi } from '../api';
import LocationsTab from '../components/management/LocationsTab.vue';
import StoresTab from '../components/management/StoresTab.vue';

const companies = ref([]);
const selectedCompanyId = ref('');

const loadCompanies = async () => {
  try {
    const response = await companyApi.getCompanies();
    companies.value = response.data.companies || [];
    // Auto-select first company if available
    if (companies.value.length > 0) {
      selectedCompanyId.value = companies.value[0].id;
    }
  } catch (err) {
    console.error('Failed to load companies:', err);
  }
};

onMounted(() => {
  loadCompanies();
});

const activeTab = ref('locations');
</script>
