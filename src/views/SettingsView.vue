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
              @click="activeTab = 'payroll'"
              class="px-6 py-3 text-sm font-medium border-b-2 transition-colors"
              :class="activeTab === 'payroll'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'"
            >
              <i class="bi bi-people mr-2"></i>
              Payroll Employee
            </button>
            <button
              @click="activeTab = 'initialCapital'"
              class="px-6 py-3 text-sm font-medium border-b-2 transition-colors"
              :class="activeTab === 'initialCapital'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'"
            >
              <i class="bi bi-coins mr-2"></i>
              Initial Capital
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

      <!-- Settings Content -->
      <div v-if="activeTab === 'payroll'">
        <payroll-employee-settings />
      </div>
      <div v-else-if="activeTab === 'amortization'">
        <amortization-settings />
      </div>
      <div v-else-if="activeTab === 'initialCapital'">
        <initial-capital-settings :company-id="companyId" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import AmortizationSettings from '../components/settings/AmortizationSettings.vue';
import PayrollEmployeeSettings from '../components/settings/PayrollEmployeeSettings.vue';
import InitialCapitalSettings from '../components/settings/InitialCapitalSettings.vue';

const activeTab = ref('amortization');
const companyId = ref('');

onMounted(() => {
  // Load company ID from localStorage
  const storedCompanyId = localStorage.getItem('selectedCompanyId');
  console.log('SettingsView mounted - stored companyId:', storedCompanyId);
  if (storedCompanyId && storedCompanyId !== 'null' && storedCompanyId !== 'undefined') {
    companyId.value = storedCompanyId;
  } else {
    // Fallback: try to get from URL
    const urlParams = new URLSearchParams(window.location.search);
    companyId.value = urlParams.get('company_id') || '';
  }
  console.log('SettingsView - final companyId:', companyId.value);
});
</script>
