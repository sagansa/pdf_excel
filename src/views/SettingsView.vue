<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50/30">
    <!-- Header -->
    <div class="bg-white border-b border-gray-200 sticky top-0 z-10 shadow-sm">
      <div class="max-w-7xl mx-auto px-6 py-4">
        <div class="flex items-center justify-between">
          <div>
            <h1 class="text-2xl font-bold text-gray-900">Settings</h1>
            <p class="text-sm text-gray-500 mt-1">Pengaturan Sistem & Konfigurasi</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="max-w-7xl mx-auto px-6 py-6">
      <!-- Settings Tabs -->
      <div class="bg-white rounded-lg shadow-sm border border-gray-200 mb-6">
        <div class="border-b border-gray-200">
          <nav class="flex -mb-px">
            <button
              @click="activeTab = 'amortization'"
              class="px-6 py-3 text-sm font-medium border-b-2 transition-colors"
              :class="activeTab === 'amortization' 
                ? 'border-indigo-600 text-indigo-600' 
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'"
            >
              <i class="bi bi-calculator mr-2"></i>
              Amortization
            </button>
            <button
              @click="activeTab = 'prepaid'"
              class="px-6 py-3 text-sm font-medium border-b-2 transition-colors"
              :class="activeTab === 'prepaid' 
                ? 'border-indigo-600 text-indigo-600' 
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'"
            >
              <i class="bi bi-house-door mr-2"></i>
              Rent & Prepaid
            </button>
            <button
              @click="activeTab = 'general'"
              disabled
              class="px-6 py-3 text-sm font-medium border-b-2 border-transparent text-gray-400 cursor-not-allowed"
            >
              <i class="bi bi-gear mr-2"></i>
              General
              <span class="ml-2 text-xs bg-gray-100 px-2 py-0.5 rounded">Coming Soon</span>
            </button>
          </nav>
        </div>
      </div>

      <!-- Company Selector -->
      <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
        <label class="block text-sm font-semibold text-gray-700 mb-2">Select Company</label>
        <div class="flex gap-4">
          <select 
            v-model="selectedCompanyId"
            class="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all"
          >
            <option value="">Select a company...</option>
            <option v-for="company in companies" :key="company.id" :value="company.id">
              {{ company.name }}
            </option>
          </select>
        </div>
      </div>

      <!-- Settings Content -->
      <div v-if="selectedCompanyId">
        <AmortizationSettings 
          v-if="activeTab === 'amortization'"
          :company-id="selectedCompanyId"
        />
        <PrepaidSettings 
          v-if="activeTab === 'prepaid'"
          :company-id="selectedCompanyId"
        />
      </div>
      <div v-else class="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
        <i class="bi bi-building text-6xl text-gray-300"></i>
        <p class="text-gray-500 mt-4 text-lg font-medium">No Company Selected</p>
        <p class="text-gray-400 text-sm mt-2">Please select a company to configure settings</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useCompanyStore } from '../stores/companies';
import AmortizationSettings from '../components/settings/AmortizationSettings.vue';
import PrepaidSettings from '../components/settings/PrepaidSettings.vue';

const companyStore = useCompanyStore();

const activeTab = ref('amortization');
const selectedCompanyId = ref('');
const companies = ref([]);

onMounted(async () => {
  await companyStore.fetchCompanies();
  companies.value = companyStore.companies;
});
</script>
