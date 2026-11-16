<template>
  <div class="space-y-6">
    <PageHeader
      eyebrow="Configuration"
      icon="bi bi-sliders"
      title="System settings and operational configuration"
      subtitle="Kelola konfigurasi amortisasi, payroll, modal awal, dan kontrak rental dari satu workspace."
      :badges="headerBadges"
    />

    <!-- Main Content -->
    <div class="space-y-6">
      <!-- Settings Tabs -->
      <SectionCard body-class="p-3">
        <PillTabs v-model="activeTab" :tabs="settingsTabs" />
      </SectionCard>

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
      <div v-else-if="activeTab === 'rentalContracts'">
        <rental-contract-settings :company-id="companyId" />
      </div>
      <div v-else-if="activeTab === 'reports'">
        <report-details-settings :company-id="companyId" />
      </div>
      <div v-else-if="activeTab === 'apiKeys'">
        <credentials-settings />
      </div>
      <div v-else-if="activeTab === 'general'">
        <general-settings />
      </div>
      <div v-else-if="activeTab === 'ai'">
        <ai-settings @go-to-api-keys="activeTab = 'apiKeys'" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import AmortizationSettings from '../components/settings/AmortizationSettings.vue';
import PayrollEmployeeSettings from '../components/settings/PayrollEmployeeSettings.vue';
import InitialCapitalSettings from '../components/settings/InitialCapitalSettings.vue';
import RentalContractSettings from '../components/settings/RentalContractSettings.vue';
import ReportDetailsSettings from '../components/settings/ReportDetailsSettings.vue';
import AiSettings from '../components/settings/AiSettings.vue';
import CredentialsSettings from '../components/settings/CredentialsSettings.vue';
import GeneralSettings from '../components/settings/GeneralSettings.vue';
import PageHeader from '../components/ui/PageHeader.vue';
import SectionCard from '../components/ui/SectionCard.vue';
import PillTabs from '../components/ui/PillTabs.vue';

const activeTab = ref('amortization');
const settingsTabs = [
  { key: 'amortization', label: 'Amortization', icon: 'bi bi-calculator' },
  { key: 'payroll', label: 'Payroll Employee', icon: 'bi bi-people' },
  { key: 'initialCapital', label: 'Initial Capital', icon: 'bi bi-coins' },
  { key: 'rentalContracts', label: 'Rental Contracts', icon: 'bi bi-house-door' },
  { key: 'reports', label: 'Report Details', icon: 'bi bi-file-earmark-pdf' },
  { key: 'apiKeys', label: 'API Keys', icon: 'bi bi-key-fill' },
  { key: 'general', label: 'General', icon: 'bi bi-gear' },
  { key: 'ai', label: 'AI', icon: 'bi bi-cpu' }
];
const companyId = ref('');
const headerBadges = [
  { icon: 'bi bi-gear', label: 'System config' },
  { icon: 'bi bi-building-gear', label: 'Company-aware' }
];

onMounted(() => {
  // Load company ID from localStorage
  const storedCompanyId = localStorage.getItem('selectedCompanyId');
  if (storedCompanyId && storedCompanyId !== 'null' && storedCompanyId !== 'undefined') {
    companyId.value = storedCompanyId;
  } else {
    // Fallback: try to get from URL
    const urlParams = new URLSearchParams(window.location.search);
    companyId.value = urlParams.get('company_id') || '';
  }
});
</script>

<style scoped>
</style>
