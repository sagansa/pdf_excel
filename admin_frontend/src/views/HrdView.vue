<template>
  <div class="space-y-4">
    <PageHeader
      title="HRD Presences"
      subtitle="Pantau kehadiran karyawan hasil sync dari API presence Sagansa — filter per perusahaan dan periode, lalu tarik data terbaru."
    >
      <template #actions>
        <template v-if="activeTab === 'presences'">
          <button
            type="button"
            class="btn-secondary flex items-center gap-2 py-2"
            :disabled="panelLoading"
            @click="reloadPresences"
          >
            <i class="bi bi-arrow-clockwise" :class="{ 'animate-spin': panelLoading }" aria-hidden="true"></i>
            <span>Reload</span>
          </button>
          <button
            type="button"
            class="btn-primary flex items-center gap-2 py-2"
            :disabled="panelSyncing"
            @click="syncPresences"
          >
            <i class="bi" :class="panelSyncing ? 'bi-arrow-repeat animate-spin' : 'bi-cloud-download'" aria-hidden="true"></i>
            <span>{{ panelSyncing ? 'Syncing…' : 'Sync API' }}</span>
          </button>
        </template>
      </template>
    </PageHeader>

    <SegmentedControl v-model="activeTab" :options="hrdTabs">
      <template #option="{ option }">
        <i :class="option.icon" class="mr-1.5" aria-hidden="true"></i>
        <span>{{ option.label }}</span>
      </template>
    </SegmentedControl>

    <PresencesPanel v-if="activeTab === 'presences'" ref="presencesPanel" />

    <SectionCard v-else body-class="px-6 py-12">
      <div class="hrd-tab-empty">
        <i class="bi hrd-tab-empty__icon" :class="activeTabMeta.icon" aria-hidden="true"></i>
        <p class="hrd-tab-empty__title">{{ activeTabMeta.label }}</p>
        <p class="hrd-tab-empty__hint">{{ activeTabMeta.hint }}</p>
      </div>
    </SectionCard>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';
import PageHeader from '../components/ui/PageHeader.vue';
import PresencesPanel from '../components/hrd/PresencesPanel.vue';
import SectionCard from '../components/ui/SectionCard.vue';
import SegmentedControl from '../components/ui/SegmentedControl.vue';

const activeTab = ref('presences');
const presencesPanel = ref(null);

const hrdTabs = [
  { id: 'presences', label: 'Presences', icon: 'bi-calendar-check', hint: '' },
  { id: 'employees', label: 'Employees', icon: 'bi-people', hint: 'Modul data karyawan akan tersedia di sini.' },
  { id: 'requests', label: 'Requests', icon: 'bi-file-earmark-text', hint: 'Modul pengajuan (cuti, izin, lembur) akan tersedia di sini.' }
];

const activeTabMeta = computed(() => {
  return hrdTabs.find((tab) => tab.id === activeTab.value) || hrdTabs[0];
});

const panelLoading = computed(() => presencesPanel.value?.isLoading ?? false);
const panelSyncing = computed(() => presencesPanel.value?.isSyncing ?? false);

const reloadPresences = () => presencesPanel.value?.reload();
const syncPresences = () => presencesPanel.value?.sync();
</script>

<style scoped>
.hrd-tab-empty {
  text-align: center;
  color: var(--color-text-muted);
}

.hrd-tab-empty__icon {
  display: block;
  font-size: 26px;
  margin: 0 auto 10px;
  color: var(--color-border-strong);
}

.hrd-tab-empty__title {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
  color: var(--color-text);
}

.hrd-tab-empty__hint {
  margin: 4px 0 0;
  font-size: 12px;
}
</style>
