<template>
  <div class="max-w-6xl mx-auto space-y-6">
    <div class="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden flex flex-col">
       <div class="px-6 py-4 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
        <div>
            <h3 class="text-lg font-bold text-gray-900">Manage Reporting Marks</h3>
            <p class="text-xs text-gray-500">Define marks for transaction categorization</p>
        </div>
        <div class="flex items-center gap-2">
          <button @click="openAddModal" class="btn-primary !bg-green-600 hover:!bg-green-700">
            <i class="bi bi-plus-lg me-1"></i> Add New Mark
          </button>
        </div>
      </div>

       <div class="overflow-x-auto">
         <table class="min-w-full divide-y divide-gray-200">
           <thead class="bg-gray-50">
             <tr>
               <th class="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Internal Report</th>
               <th class="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">
                 <div class="flex items-center gap-1">
                   <span>Personal Use</span>
                   <i class="bi bi-sort-alpha-down text-indigo-500"></i>
                 </div>
               </th>
               <th class="px-6 py-3 text-center text-xs font-bold text-gray-500 uppercase tracking-wider">Coretax?</th>
               <th class="px-6 py-3 text-center text-xs font-bold text-gray-500 uppercase tracking-wider">Aset?</th>
               <th class="px-6 py-3 text-center text-xs font-bold text-gray-500 uppercase tracking-wider">Jasa?</th>
               <th class="px-6 py-3 text-center text-xs font-bold text-gray-500 uppercase tracking-wider">Salary?</th>
               <th class="px-6 py-3 text-center text-xs font-bold text-gray-500 uppercase tracking-wider">Sewa Tempat?</th>
               <th class="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">COA Mappings</th>
               <th class="px-6 py-3 text-right text-xs font-bold text-gray-500 uppercase tracking-wider">Actions</th>
             </tr>
           </thead>
           <tbody class="bg-white divide-y divide-gray-100">
              <tr v-if="store.isLoading">
                  <td colspan="9" class="text-center py-8">
                      <span class="spinner-border text-indigo-500 w-6 h-6" role="status"></span>
                  </td>
              </tr>
              <tr v-else-if="store.marks.length === 0">
                  <td colspan="9" class="text-center py-8 text-gray-400">No marks found</td>
              </tr>
              <tr v-for="m in store.sortedMarks" :key="m.id" :class="{'bg-indigo-50/30': m.is_asset || m.is_service || m.is_salary_component || m.is_rental}" class="hover:bg-gray-50">
                 <td class="px-6 py-4 text-sm text-gray-900">{{ m.internal_report }}</td>
                 <td class="px-6 py-4 text-sm text-gray-500">
                   <span :class="{'font-semibold text-indigo-700': m.is_asset || m.is_salary_component}">{{ m.personal_use }}</span>
                 </td>
                 <td class="px-6 py-4 text-center">
                   <button
                     @click="toggleMarkFlag(m, 'is_coretax')"
                     :disabled="isToggleLoading(m.id, 'is_coretax')"
                     class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium transition-colors disabled:opacity-60"
                     :class="m.is_coretax ? 'bg-cyan-100 text-cyan-800 hover:bg-cyan-200' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'"
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
                     :class="m.is_asset ? 'bg-green-100 text-green-800 hover:bg-green-200' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'"
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
                     :class="m.is_service ? 'bg-amber-100 text-amber-800 hover:bg-amber-200' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'"
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
                     :class="m.is_salary_component ? 'bg-emerald-100 text-emerald-800 hover:bg-emerald-200' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'"
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
                     :class="m.is_rental ? 'bg-blue-100 text-blue-800 hover:bg-blue-200' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'"
                   >
                     <i v-if="isToggleLoading(m.id, 'is_rental')" class="bi bi-arrow-repeat animate-spin mr-1"></i>
                     <i v-else :class="m.is_rental ? 'bi bi-check-circle-fill mr-1' : 'bi bi-dash-circle mr-1'"></i>
                     {{ m.is_rental ? 'Sewa' : 'Bukan' }}
                   </button>
                 </td>
                 <td class="px-6 py-4">
                   <div class="flex flex-col gap-1 mb-2" v-if="m.mappings && m.mappings.length > 0">
                     <div
                       v-for="mapping in m.mappings"
                       :key="mapping.code"
                       class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium"
                       :class="mapping.type === 'DEBIT' ? 'bg-blue-50 text-blue-700 border border-blue-100' : 'bg-emerald-50 text-emerald-700 border border-emerald-100'"
                     >
                       <span class="font-mono mr-1">{{ mapping.code }}</span>
                       <span class="mr-1 text-[9px] truncate max-w-[120px]" :title="mapping.name">{{ mapping.name }}</span>
                       <span>({{ mapping.type === 'DEBIT' ? 'DB' : 'CR' }})</span>
                     </div>
                   </div>
                   <div v-else class="mb-2">
                     <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-amber-50 text-amber-700 border border-amber-100">
                       <i class="bi bi-exclamation-circle me-1"></i> Not Mapped
                     </span>
                   </div>
                   <button
                     @click="openMappingModal(m)"
                     class="text-[10px] px-2 py-1 bg-indigo-50 text-indigo-700 hover:bg-indigo-100 rounded transition-colors flex items-center justify-center gap-1 w-full"
                   >
                     <i class="bi bi-link-45deg"></i>
                     <span>Manage COA</span>
                   </button>
                 </td>
                 <td class="px-6 py-4 text-right text-sm font-medium">
                   <button @click="openEditModal(m)" class="text-indigo-600 hover:text-indigo-900 me-3">
                     <i class="bi bi-pencil-square"></i>
                   </button>
                   <button @click="deleteMark(m.id)" class="text-red-600 hover:text-red-900">
                     <i class="bi bi-trash3"></i>
                   </button>
                 </td>
              </tr>
           </tbody>
         </table>
       </div>
    </div>

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
import { ref } from 'vue';
import { useMarksStore } from '../stores/marks';
import MarkFormModal from '../components/marks/MarkFormModal.vue';
import CoaMappingModal from '../components/marks/CoaMappingModal.vue';

const store = useMarksStore();
const showModal = ref(false);
const selectedMark = ref(null);
const showMappingModal = ref(false);
const selectedMarkForMapping = ref(null);
const togglingFlags = ref({});

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
