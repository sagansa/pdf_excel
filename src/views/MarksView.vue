<template>
  <div class="max-w-6xl mx-auto space-y-6">
    <div class="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden flex flex-col">
       <div class="px-6 py-4 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
        <div>
            <h3 class="text-lg font-bold text-gray-900">Manage Reporting Marks</h3>
            <p class="text-xs text-gray-500">Define marks for transaction categorization</p>
        </div>
        <div class="flex items-center gap-2">
          <div class="flex items-center bg-gray-100 rounded-xl p-1 gap-1 border border-gray-200 shadow-sm">
            <button 
              @click="fixExpenseMappings" 
              :disabled="isFixing"
              class="px-3 py-1.5 text-[10px] font-bold bg-white text-gray-700 hover:text-amber-600 rounded-lg transition-all flex items-center gap-1.5 shadow-sm border border-gray-100"
              title="Fix EXPENSE mappings (CREDIT -> DEBIT)"
            >
              <i class="bi" :class="isFixing && currentFixType === 'EXPENSE' ? 'bi-arrow-repeat animate-spin' : 'bi-wrench-adjustable text-amber-500'"></i>
              <span>Fix Expenses</span>
            </button>
            <button 
              @click="fixRevenueMappings" 
              :disabled="isFixing"
              class="px-3 py-1.5 text-[10px] font-bold bg-white text-gray-700 hover:text-indigo-600 rounded-lg transition-all flex items-center gap-1.5 shadow-sm border border-gray-100"
              title="Fix REVENUE mappings (DEBIT -> CREDIT)"
            >
              <i class="bi" :class="isFixing && currentFixType === 'REVENUE' ? 'bi-arrow-repeat animate-spin' : 'bi-wrench-adjustable text-indigo-500'"></i>
              <span>Fix Revenues</span>
            </button>
          </div>
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
              <th class="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Tax Report</th>
              <th class="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">COA Mappings</th>
              <th class="px-6 py-3 text-right text-xs font-bold text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-100">
             <tr v-if="store.isLoading">
                 <td colspan="4" class="text-center py-8">
                     <span class="spinner-border text-indigo-500 w-6 h-6" role="status"></span>
                 </td>
             </tr>
             <tr v-else-if="store.marks.length === 0">
                 <td colspan="4" class="text-center py-8 text-gray-400">No marks found</td>
             </tr>
             <tr v-for="m in store.sortedMarks" :key="m.id" class="hover:bg-gray-50">
                <td class="px-6 py-4 text-sm text-gray-900">{{ m.internal_report }}</td>
                <td class="px-6 py-4 text-sm text-gray-500">{{ m.personal_use }}</td>
                <td class="px-6 py-4 text-sm text-gray-500">{{ m.tax_report }}</td>
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
        @saved="showModal = false"
    />

    <CoaMappingModal
        :isOpen="showMappingModal"
        :mark="selectedMarkForMapping"
        @close="showMappingModal = false"
        @updated="handleMappingUpdated"
    />

    <FixMappingsModal
        :isOpen="showFixModal"
        :isLoading="isFixing"
        :isSuccess="fixSuccess"
        :results="fixResults"
        :fixType="currentFixType"
        @close="handleFixModalClose"
        @confirm="runFixMappings"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useMarksStore } from '../stores/marks';
import MarkFormModal from '../components/marks/MarkFormModal.vue';
import CoaMappingModal from '../components/marks/CoaMappingModal.vue';
import FixMappingsModal from '../components/marks/FixMappingsModal.vue';
import axios from 'axios';

const store = useMarksStore();
const showModal = ref(false);
const selectedMark = ref(null);
const showMappingModal = ref(false);
const selectedMarkForMapping = ref(null);
const isFixing = ref(false);
const showFixModal = ref(false);
const fixSuccess = ref(false);
const fixResults = ref({ fixed_count: 0, mappings: [] });
const currentFixType = ref('EXPENSE');

onMounted(() => {
    store.fetchMarks();
});

const openAddModal = () => {
    selectedMark.value = null;
    showModal.value = true;
};

const openEditModal = (mark) => {
    selectedMark.value = mark;
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

const deleteMark = async (id) => {
    if(confirm("Are you sure you want to delete this mark?")) {
        await store.deleteMark(id);
    }
};

const fixExpenseMappings = () => {
    currentFixType.value = 'EXPENSE';
    fixSuccess.value = false;
    fixResults.value = { fixed_count: 0, mappings: [] };
    showFixModal.value = true;
};

const fixRevenueMappings = () => {
    currentFixType.value = 'REVENUE';
    fixSuccess.value = false;
    fixResults.value = { fixed_count: 0, mappings: [] };
    showFixModal.value = true;
};

const handleFixModalClose = () => {
    showFixModal.value = false;
};

const runFixMappings = async () => {
    isFixing.value = true;
    try {
        const endpoint = currentFixType.value === 'EXPENSE' 
            ? '/api/mark-coa-mappings/fix-expense-mappings' 
            : '/api/mark-coa-mappings/fix-revenue-mappings';
            
        const response = await axios.post(endpoint);
        fixResults.value = response.data;
        fixSuccess.value = true;
        
        await store.fetchMarks();
    } catch (error) {
        alert('❌ Failed to fix mappings: ' + (error.response?.data?.error || error.message));
        showFixModal.value = false;
    } finally {
        isFixing.value = false;
    }
};
</script>
