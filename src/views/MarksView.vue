<template>
  <div class="max-w-6xl mx-auto space-y-6">
    <div class="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden flex flex-col">
       <div class="px-6 py-4 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
        <div>
            <h3 class="text-lg font-bold text-gray-900">Manage Reporting Marks</h3>
            <p class="text-xs text-gray-500">Define marks for transaction categorization</p>
        </div>
        <button @click="openAddModal" class="btn-primary !bg-green-600 hover:!bg-green-700">
          <i class="bi bi-plus-lg me-1"></i> Add New Mark
        </button>
      </div>

      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Internal Report</th>
              <th class="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Personal Use</th>
              <th class="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Tax Report</th>
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
             <tr v-for="m in store.marks" :key="m.id" class="hover:bg-gray-50">
                <td class="px-6 py-4 text-sm text-gray-900">{{ m.internal_report }}</td>
                <td class="px-6 py-4 text-sm text-gray-500">{{ m.personal_use }}</td>
                <td class="px-6 py-4 text-sm text-gray-500">{{ m.tax_report }}</td>
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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useMarksStore } from '../stores/marks';
import MarkFormModal from '../components/marks/MarkFormModal.vue';

const store = useMarksStore();
const showModal = ref(false);
const selectedMark = ref(null);

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

const deleteMark = async (id) => {
    if(confirm("Are you sure you want to delete this mark?")) {
        await store.deleteMark(id);
    }
};
</script>
