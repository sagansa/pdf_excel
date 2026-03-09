<template>
  <div class="space-y-8">
    <PageHeader
      eyebrow="Operations Hub"
      icon="bi bi-grid-1x2-fill"
      title="Statement operations in one place"
      subtitle="Monitor financial performance, recent data intake, and storage health from a single control surface designed for daily admin work."
      :badges="headerBadges"
    />

    <!-- Financial Summary -->
    <FinancialSummaryWidget />

    <!-- Remaining Storage Monitoring -->
    <RemainingStorageWidget />

    <!-- Quick Actions Grid -->
    <SectionCard
      title="Priority Workflows"
      subtitle="Masuk ke area kerja yang paling sering dipakai tim operasional."
      body-class="p-6 pt-0"
    >
      <div class="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
      
      <!-- Converter Card -->
      <router-link to="/converter" class="surface-card interactive-card group p-6">
        <div class="quick-action-icon quick-action-icon--primary">
           <i class="bi bi-file-earmark-medical text-2xl"></i>
        </div>
        <div class="flex items-center justify-between gap-3">
          <h3 class="font-bold text-lg text-theme group-hover:text-[var(--color-primary)] transition-colors">Converter</h3>
          <span class="stat-pill !px-2.5 !py-1">Intake</span>
        </div>
        <p class="text-sm text-muted mt-2 leading-relaxed">
          Upload PDF/CSV statements and extract transactions automatically.
        </p>
      </router-link>

      <!-- History Card -->
      <router-link to="/history" class="surface-card interactive-card group p-6">
        <div class="quick-action-icon quick-action-icon--success">
           <i class="bi bi-database-fill text-2xl"></i>
        </div>
        <div class="flex items-center justify-between gap-3">
          <h3 class="font-bold text-lg text-theme group-hover:text-[var(--color-success)] transition-colors">History & DB</h3>
          <span class="stat-pill !px-2.5 !py-1">Review</span>
        </div>
        <p class="text-sm text-muted mt-2 leading-relaxed">
          Search, filter, and manage your full transaction history.
        </p>
      </router-link>

      <!-- Companies Card -->
      <router-link to="/companies" class="surface-card interactive-card group p-6">
        <div class="quick-action-icon quick-action-icon--info">
           <i class="bi bi-building text-2xl"></i>
        </div>
        <div class="flex items-center justify-between gap-3">
          <h3 class="font-bold text-lg text-theme group-hover:text-[var(--color-primary)] transition-colors">Companies</h3>
          <span class="stat-pill !px-2.5 !py-1">Master Data</span>
        </div>
        <p class="text-sm text-muted mt-2 leading-relaxed">
          Add or edit company entities and mapping rules.
        </p>
      </router-link>

      <!-- Marks Card -->
      <router-link to="/marks" class="surface-card interactive-card group p-6">
        <div class="quick-action-icon quick-action-icon--accent">
           <i class="bi bi-tags-fill text-2xl"></i>
        </div>
        <div class="flex items-center justify-between gap-3">
          <h3 class="font-bold text-lg text-theme group-hover:text-[var(--color-accent)] transition-colors">Marks</h3>
          <span class="stat-pill !px-2.5 !py-1">Classification</span>
        </div>
        <p class="text-sm text-muted mt-2 leading-relaxed">
          Manage reporting categories for transaction tagging.
        </p>
      </router-link>
      </div>
    </SectionCard>
  </div>
</template>

<script setup>
import PageHeader from '../components/ui/PageHeader.vue';
import SectionCard from '../components/ui/SectionCard.vue';
import FinancialSummaryWidget from '../components/dashboard/FinancialSummaryWidget.vue';
import RemainingStorageWidget from '../components/dashboard/RemainingStorageWidget.vue';

const headerBadges = [
  { icon: 'bi bi-lightning-charge-fill', label: 'Fast intake' },
  { icon: 'bi bi-journal-check', label: 'Report-ready' },
  { icon: 'bi bi-cloud-check', label: 'Live backend' }
];
</script>

<style scoped>
.quick-action-icon {
  @apply mb-4 flex h-14 w-14 items-center justify-center rounded-2xl transition-transform;
}

.group:hover .quick-action-icon {
  transform: scale(1.06);
}

.quick-action-icon--primary {
  background: rgba(15, 118, 110, 0.12);
  color: var(--color-primary);
}

.quick-action-icon--success {
  background: rgba(22, 101, 52, 0.12);
  color: var(--color-success);
}

.quick-action-icon--info {
  background: rgba(29, 78, 216, 0.12);
  color: #1d4ed8;
}

.quick-action-icon--accent {
  background: rgba(180, 83, 9, 0.12);
  color: var(--color-accent);
}
</style>
