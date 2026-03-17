<template>
  <div class="max-w-6xl mx-auto space-y-6">
    <PageHeader
      eyebrow="Reporting Marks"
      icon="bi bi-tags-fill"
      title="Transaction classification rules"
      subtitle="Definisikan mark untuk kategorisasi transaksi dan mapping COA."
      :badges="headerBadges"
    />

    <TableShell>
      <template #toolbar>
       <div class="marks-toolbar">
        <div class="marks-toolbar__meta">
          <div class="marks-toolbar__icon">
            <i class="bi bi-tags-fill"></i>
          </div>
          <div class="min-w-0">
            <div class="flex flex-wrap items-center gap-2">
              <h3 class="text-xl font-bold text-theme">Manage Reporting Marks</h3>
              <span class="stat-pill !px-2.5 !py-1 text-[10px]">
                {{ totalMarks }} marks
              </span>
              <span class="stat-pill !px-2.5 !py-1 text-[10px]">
                {{ unmappedCount }} unmapped
              </span>
            </div>
            <p class="mt-2 max-w-2xl text-sm text-muted">
              Define marks for transaction categorization, keep mapping coverage visible, and jump straight into COA maintenance without leaving the table.
            </p>
          </div>
        </div>
        <div class="marks-toolbar__actions">
          <button @click="openAddModal" class="btn-primary gap-2">
            <i class="bi bi-plus-lg"></i>
            <span>Add New Mark</span>
          </button>
        </div>
      </div>
      </template>

         <table class="min-w-full table-compact">
           <thead>
             <tr>
               <th class="px-6 py-3 text-left">Internal Report</th>
               <th class="px-6 py-3 text-left">
                 <div class="flex items-center gap-1">
                   <span>Personal Use</span>
                   <i class="bi bi-sort-alpha-down" style="color: var(--color-primary)"></i>
                 </div>
               </th>
               <th class="px-6 py-3 text-center">Coretax?</th>
               <th class="px-6 py-3 text-center">Aset?</th>
               <th class="px-6 py-3 text-center">Jasa?</th>
               <th class="px-6 py-3 text-center">Salary?</th>
               <th class="px-6 py-3 text-center">Sewa Tempat?</th>
               <th class="px-6 py-3 text-left">COA Mappings</th>
               <th class="px-6 py-3 text-right">Actions</th>
             </tr>
           </thead>
           <tbody class="divide-y" style="border-color: var(--color-border)">
              <tr v-if="store.isLoading">
                  <td colspan="9" class="text-center py-8">
                      <span class="spinner-border w-6 h-6" style="color: var(--color-primary)" role="status"></span>
                  </td>
              </tr>
              <tr v-else-if="store.marks.length === 0">
                  <td colspan="9" class="text-center py-8 text-muted">No marks found</td>
              </tr>
              <tr v-for="m in store.sortedMarks" :key="m.id" :class="{'mark-row--highlight': m.is_asset || m.is_service || m.is_salary_component || m.is_rental}" class="mark-row">
                 <td class="px-6 py-4 text-sm text-theme">{{ m.internal_report }}</td>
                 <td class="px-6 py-4 text-sm text-muted">
                   <span :class="{'font-semibold': m.is_asset || m.is_salary_component}" :style="m.is_asset || m.is_salary_component ? 'color: var(--color-primary)' : ''">{{ m.personal_use }}</span>
                 </td>
                 <td class="px-6 py-4 text-center">
                   <button
                     @click="toggleMarkFlag(m, 'is_coretax')"
                     :disabled="isToggleLoading(m.id, 'is_coretax')"
                     class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium transition-colors disabled:opacity-60"
                     :class="m.is_coretax ? 'bg-cyan-100 text-cyan-800 hover:bg-cyan-200' : 'mark-flag-off'"
                   >
                     <i v-if="isToggleLoading(m.id, 'is_coretax')" class="bi bi-arrow-repeat animate-spin mr-1"></i>
                     <i v-else :class="m.is_coretax ? 'bi bi-check-circle-fill mr-1' : 'bi bi-dash-circle mr-1'"></i>
                     {{ m.is_coretax ? 'Ya' : 'Tidak' }}
                   </button>
                 </td>
                 <td class="px-6 py-4 text-center">
                   <button
                     @click="toggleMarkFlag(m, 'is_asset')"
                     :disabled="isToggleLoading(m.id, 'is_asset')"
                     class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium transition-colors disabled:opacity-60"
                     :class="m.is_asset ? 'bg-green-100 text-green-800 hover:bg-green-200' : 'mark-flag-off'"
                   >
                     <i v-if="isToggleLoading(m.id, 'is_asset')" class="bi bi-arrow-repeat animate-spin mr-1"></i>
                     <i v-else :class="m.is_asset ? 'bi bi-check-circle-fill mr-1' : 'bi bi-dash-circle mr-1'"></i>
                     {{ m.is_asset ? 'Aset' : 'Bukan' }}
                   </button>
                 </td>
                 <td class="px-6 py-4 text-center">
                   <button
                     @click="toggleMarkFlag(m, 'is_service')"
                     :disabled="isToggleLoading(m.id, 'is_service')"
                     class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium transition-colors disabled:opacity-60"
                     :class="m.is_service ? 'bg-amber-100 text-amber-800 hover:bg-amber-200' : 'mark-flag-off'"
                   >
                     <i v-if="isToggleLoading(m.id, 'is_service')" class="bi bi-arrow-repeat animate-spin mr-1"></i>
                     <i v-else :class="m.is_service ? 'bi bi-check-circle-fill mr-1' : 'bi bi-dash-circle mr-1'"></i>
                     {{ m.is_service ? 'Jasa' : 'Bukan' }}
                   </button>
                 </td>
                 <td class="px-6 py-4 text-center">
                   <button
                     @click="toggleMarkFlag(m, 'is_salary_component')"
                     :disabled="isToggleLoading(m.id, 'is_salary_component')"
                     class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium transition-colors disabled:opacity-60"
                     :class="m.is_salary_component ? 'bg-emerald-100 text-emerald-800 hover:bg-emerald-200' : 'mark-flag-off'"
                   >
                     <i v-if="isToggleLoading(m.id, 'is_salary_component')" class="bi bi-arrow-repeat animate-spin mr-1"></i>
                     <i v-else :class="m.is_salary_component ? 'bi bi-check-circle-fill mr-1' : 'bi bi-dash-circle mr-1'"></i>
                     {{ m.is_salary_component ? 'Salary' : 'Bukan' }}
                   </button>
                 </td>
                 <td class="px-6 py-4 text-center">
                   <button
                     @click="toggleMarkFlag(m, 'is_rental')"
                     :disabled="isToggleLoading(m.id, 'is_rental')"
                     class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium transition-colors disabled:opacity-60"
                     :class="m.is_rental ? 'bg-blue-100 text-blue-800 hover:bg-blue-200' : 'mark-flag-off'"
                   >
                     <i v-if="isToggleLoading(m.id, 'is_rental')" class="bi bi-arrow-repeat animate-spin mr-1"></i>
                     <i v-else :class="m.is_rental ? 'bi bi-check-circle-fill mr-1' : 'bi bi-dash-circle mr-1'"></i>
                     {{ m.is_rental ? 'Sewa' : 'Bukan' }}
                   </button>
                 </td>
                 <td class="px-6 py-4">
                   <div class="flex flex-col gap-2 mb-2">
                     <div>
                       <div class="text-[9px] font-semibold uppercase text-muted">Real</div>
                       <div v-if="getRealMappings(m).length > 0" class="flex flex-col gap-1 mt-1">
                         <div
                           v-for="mapping in getRealMappings(m)"
                           :key="`real-${mapping.coa_id || mapping.code}-${mapping.type}`"
                           class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium"
                           :class="mapping.type === 'DEBIT' ? 'bg-blue-50 text-blue-700 border border-blue-100' : 'bg-emerald-50 text-emerald-700 border border-emerald-100'"
                         >
                           <span class="font-mono mr-1">{{ mapping.code }}</span>
                           <span class="mr-1 text-[9px] truncate max-w-[120px]" :title="mapping.name">{{ mapping.name }}</span>
                           <span>({{ mapping.type === 'DEBIT' ? 'DB' : 'CR' }})</span>
                         </div>
                       </div>
                       <div v-else class="mt-1">
                         <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-amber-50 text-amber-700 border border-amber-100">
                           <i class="bi bi-exclamation-circle me-1"></i> Not Mapped
                         </span>
                       </div>
                     </div>
                     <div>
                       <div class="text-[9px] font-semibold uppercase text-muted">Coretax</div>
                       <div v-if="getCoretaxMappings(m).length > 0" class="flex flex-col gap-1 mt-1">
                         <div
                           v-for="mapping in getCoretaxMappings(m)"
                           :key="`coretax-${mapping.coa_id || mapping.code}-${mapping.type}`"
                           class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium"
                           :class="mapping.type === 'DEBIT' ? 'bg-blue-50 text-blue-700 border border-blue-100' : 'bg-emerald-50 text-emerald-700 border border-emerald-100'"
                         >
                           <span class="font-mono mr-1">{{ mapping.code }}</span>
                           <span class="mr-1 text-[9px] truncate max-w-[120px]" :title="mapping.name">{{ mapping.name }}</span>
                           <span>({{ mapping.type === 'DEBIT' ? 'DB' : 'CR' }})</span>
                         </div>
                       </div>
                       <div v-else class="mt-1">
                         <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-cyan-50 text-cyan-700 border border-cyan-100">
                           <i class="bi bi-exclamation-circle me-1"></i> Not Mapped
                         </span>
                       </div>
                     </div>
                   </div>
                   <button
                     @click="openMappingModal(m)"
                     class="mark-mapping-button"
                   >
                     <i class="bi bi-link-45deg"></i>
                     <span>Manage COA</span>
                   </button>
                 </td>
                 <td class="px-6 py-4 text-right text-sm font-medium">
                   <button @click="openEditModal(m)" class="action-link action-link--primary me-3">
                     <i class="bi bi-pencil-square"></i>
                   </button>
                   <button @click="deleteMark(m.id)" class="action-link action-link--danger">
                     <i class="bi bi-trash3"></i>
                   </button>
                 </td>
              </tr>
           </tbody>
         </table>
    </TableShell>

    <MarkFormModal 
        :isOpen="showModal" 
        :markToEdit="selectedMark"
        @close="showModal = false"
        @saved="handleMarkSaved"
    />

    <CoaMappingModal
        :isOpen="showMappingModal"
        :mark="selectedMarkForMapping"
        @close="showMappingModal = false"
        @updated="handleMappingUpdated"
    />
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';
import { useMarksStore } from '../stores/marks';
import MarkFormModal from '../components/marks/MarkFormModal.vue';
import CoaMappingModal from '../components/marks/CoaMappingModal.vue';
import PageHeader from '../components/ui/PageHeader.vue';
import TableShell from '../components/ui/TableShell.vue';

const store = useMarksStore();
const showModal = ref(false);
const selectedMark = ref(null);
const showMappingModal = ref(false);
const selectedMarkForMapping = ref(null);
const togglingFlags = ref({});
const totalMarks = computed(() => store.sortedMarks.length);
const getRealMappings = (mark) => {
  if (Array.isArray(mark?.mappings_real)) return mark.mappings_real;
  if (Array.isArray(mark?.mappings)) {
    return mark.mappings.filter((mapping) => (
      String(mapping?.report_type || 'real').trim().toLowerCase() === 'real'
    ));
  }
  return [];
};

const getCoretaxMappings = (mark) => (
  Array.isArray(mark?.mappings_coretax)
    ? mark.mappings_coretax
    : (Array.isArray(mark?.mappings)
        ? mark.mappings.filter((mapping) => (
          String(mapping?.report_type || '').trim().toLowerCase() === 'coretax'
        ))
        : [])
);

const unmappedCount = computed(() => (
    (store.sortedMarks || []).filter(mark => (
      getRealMappings(mark).length === 0 && getCoretaxMappings(mark).length === 0
    )).length
));
const headerBadges = [
    { icon: 'bi bi-link-45deg', label: 'COA mapping' },
    { icon: 'bi bi-funnel', label: 'Reporting flags' }
];

store.fetchMarks();

const getToggleKey = (markId, flagKey) => `${markId}:${flagKey}`;

const isToggleLoading = (markId, flagKey) => {
    return Boolean(togglingFlags.value[getToggleKey(markId, flagKey)]);
};

const toggleMarkFlag = async (mark, flagKey) => {
    const toggleKey = getToggleKey(mark.id, flagKey);
    if (togglingFlags.value[toggleKey]) return;

    togglingFlags.value = { ...togglingFlags.value, [toggleKey]: true };
    try {
        await store.updateMarkFlag(mark.id, flagKey, !Boolean(mark[flagKey]));
    } catch (error) {
        alert('Gagal update status mark: ' + (error.response?.data?.error || error.message));
    } finally {
        const nextState = { ...togglingFlags.value };
        delete nextState[toggleKey];
        togglingFlags.value = nextState;
    }
};

const openAddModal = () => {
    selectedMark.value = null;
    showModal.value = true;
};

const openEditModal = async (mark) => {
    // First refresh the marks data to ensure we have the latest from database
    await store.fetchMarks();
    // Then get the fresh mark data from the refreshed store
    const freshMark = store.marks.find(m => m.id === mark.id);
    selectedMark.value = freshMark;
    showModal.value = true;
};

const openMappingModal = (mark) => {
    selectedMarkForMapping.value = mark;
    showMappingModal.value = true;
};

const handleMappingUpdated = async () => {
    // Refresh marks to show new mappings
    await store.fetchMarks();
    console.log('Mapping updated successfully');
};

const handleMarkSaved = async () => {
    // Refresh marks to show updated data
    await store.fetchMarks();
    showModal.value = false;
    console.log('Mark saved successfully');
};

const deleteMark = async (id) => {
    if(confirm("Are you sure you want to delete this mark?")) {
        await store.deleteMark(id);
    }
};
</script>

<style scoped>
.surface-header {
  border-color: var(--color-border);
  background: var(--color-surface-muted);
}

.marks-toolbar {
  @apply flex w-full flex-col gap-4 lg:flex-row lg:items-center lg:justify-between;
}

.marks-toolbar__meta {
  @apply flex items-start gap-4;
}

.marks-toolbar__icon {
  @apply flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl text-lg;
  background:
    linear-gradient(135deg, rgba(45, 182, 163, 0.18), rgba(15, 118, 110, 0.08)),
    var(--color-surface-muted);
  border: 1px solid var(--color-border);
  color: var(--color-primary);
  box-shadow: var(--shadow-soft);
}

.marks-toolbar__actions {
  @apply flex shrink-0 items-center lg:ml-auto;
}

.marks-toolbar__actions .btn-primary {
  @apply min-h-[44px] px-5;
}

.mark-row {
  transition: background-color 160ms ease;
}

.mark-row:hover {
  background: rgba(15, 118, 110, 0.05);
}

.mark-row--highlight {
  background: rgba(15, 118, 110, 0.06);
}

.mark-flag-off {
  background: var(--color-surface-muted);
  color: var(--color-text-muted);
}

.mark-mapping-button {
  @apply flex w-full items-center justify-center gap-1 rounded px-2 py-1 text-[10px] transition-colors;
  background: rgba(15, 118, 110, 0.10);
  color: var(--color-primary);
}

.mark-mapping-button:hover {
  background: rgba(15, 118, 110, 0.16);
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
