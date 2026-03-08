<template>
  <BaseModal :isOpen="isOpen" @close="close">
    <template #title>Assign Mark</template>

    <div class="p-6 space-y-4">
      <p class="text-sm text-gray-500">Select a predefined mark category for this transaction:</p>
      
      <div v-if="loading" class="text-center py-4">
          <span class="spinner-border w-6 h-6 text-indigo-500"></span>
      </div>
      
      <div v-else class="space-y-2 max-h-[300px] overflow-y-auto">
          <div 
            v-for="mark in sortedMarks" 
            :key="mark.id"
            @click="selectMark(mark)"
            class="p-3 rounded-xl border cursor-pointer transition-all hover:bg-indigo-50 hover:border-indigo-200"
            :class="selectedMarkId === mark.id ? 'bg-indigo-50 border-indigo-500 ring-1 ring-indigo-500' : 'border-gray-200'"
          >
              <div class="flex justify-between items-center mb-1">
                  <span class="text-xs font-bold text-gray-500 uppercase">Internal</span>
                  <span v-if="selectedMarkId === mark.id" class="text-indigo-600"><i class="bi bi-check-circle-fill"></i></span>
              </div>
              <p class="text-sm font-medium text-gray-900 mb-2">{{ mark.internal_report }}</p>
               
               <div class="grid grid-cols-2 gap-2 text-xs text-gray-500">
                   <div>
                       <span class="uppercase text-[10px] font-bold">Personal</span>
                       <p>{{ mark.personal_use || '-' }}</p>
                   </div>
                   <div>
                       <span class="uppercase text-[10px] font-bold">Tax</span>
                       <p>{{ mark.tax_report || '-' }}</p>
                   </div>
               </div>
          </div>
      </div>

      <div v-if="error" class="text-sm text-red-600 bg-red-50 p-2 rounded">
          {{ error }}
      </div>
    </div>

    <template #footer>
      <button @click="close" class="btn-secondary">Cancel</button>
      <button 
        @click="handleSubmit" 
        class="btn-primary shadow-lg shadow-indigo-100"
        :disabled="submitting || !selectedMarkId"
      >
        <span v-if="submitting" class="spinner-border w-4 h-4 me-2"></span>
        Apply Mark
      </button>
    </template>
  </BaseModal>
</template>

<script setup>
import { ref, watch, computed } from 'vue';
import BaseModal from '../ui/BaseModal.vue';
import { useMarksStore } from '../../stores/marks';

const props = defineProps({
  isOpen: Boolean,
  transaction: Object
});

const emit = defineEmits(['close', 'assigned']);
const store = useMarksStore();

const loading = ref(false);
const submitting = ref(false);
const selectedMarkId = ref(null);
const error = ref(null);

watch(() => props.isOpen, async (newVal) => {
    if (newVal) {
        selectedMarkId.value = props.transaction?.mark_id || null;
        loading.value = true;
        try {
            await store.fetchMarks();
        } finally {
            loading.value = false;
        }
    }
});

const sortedMarks = computed(() => store.sortedMarks);

const selectMark = (mark) => {
    selectedMarkId.value = mark.id;
};

const close = () => {
    error.value = null;
    emit('close');
};

const handleSubmit = async () => {
    if (!selectedMarkId.value) return;
    
    submitting.value = true;
    error.value = null;

    try {
        await store.assignMark(props.transaction.id, selectedMarkId.value);
        emit('assigned'); // Parent should refresh data
        close();
    } catch (err) {
        error.value = err.response?.data?.error || err.message;
    } finally {
        submitting.value = false;
    }
};
</script>
