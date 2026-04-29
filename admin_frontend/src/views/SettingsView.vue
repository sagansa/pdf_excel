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
        <div class="settings-tab-wrap">
            <button
              @click="activeTab = 'amortization'"
              class="settings-tab"
              :class="{ 'settings-tab--active': activeTab === 'amortization' }"
            >
              <i class="bi bi-calculator mr-2"></i>
              Amortization
            </button>
            <button
              @click="activeTab = 'payroll'"
              class="settings-tab"
              :class="{ 'settings-tab--active': activeTab === 'payroll' }"
            >
              <i class="bi bi-people mr-2"></i>
              Payroll Employee
            </button>
            <button
              @click="activeTab = 'initialCapital'"
              class="settings-tab"
              :class="{ 'settings-tab--active': activeTab === 'initialCapital' }"
            >
              <i class="bi bi-coins mr-2"></i>
              Initial Capital
            </button>
            <button
              @click="activeTab = 'rentalContracts'"
              class="settings-tab"
              :class="{ 'settings-tab--active': activeTab === 'rentalContracts' }"
            >
              <i class="bi bi-house-door mr-2"></i>
              Rental Contracts
            </button>
            <button
              @click="activeTab = 'reports'"
              class="settings-tab"
              :class="{ 'settings-tab--active': activeTab === 'reports' }"
            >
              <i class="bi bi-file-earmark-pdf mr-2"></i>
              Report Details
            </button>
            <button
              @click="activeTab = 'general'"
              disabled
              class="settings-tab settings-tab--disabled"
            >
              <i class="bi bi-gear mr-2"></i>
              General
              <span class="ml-2 rounded-full px-2 py-0.5 text-[10px]" style="background: var(--color-surface-muted)">Coming Soon</span>
            </button>
        </div>
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
import PageHeader from '../components/ui/PageHeader.vue';
import SectionCard from '../components/ui/SectionCard.vue';

const activeTab = ref('amortization');
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
.settings-tab-wrap {
  @apply flex gap-2 overflow-x-auto;
}

.settings-tab {
  @apply inline-flex items-center whitespace-nowrap rounded-2xl px-4 py-2.5 text-sm font-medium transition-all;
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
  color: var(--color-text-muted);
}

.settings-tab:hover {
  border-color: var(--color-border-strong);
  color: var(--color-text);
}

.settings-tab--active {
  background: rgba(15, 118, 110, 0.12);
  border-color: rgba(15, 118, 110, 0.18);
  color: var(--color-primary);
  box-shadow: var(--shadow-soft);
}

.settings-tab--disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
</style>
