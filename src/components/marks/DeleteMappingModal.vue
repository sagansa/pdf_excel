<template>
  <div v-if="show" class="fixed inset-0 z-[60] flex items-center justify-center bg-gray-900/50 backdrop-blur-sm px-4">
    <div class="bg-white rounded-2xl shadow-2xl border border-gray-200 w-full max-w-md overflow-hidden animate-in fade-in zoom-in duration-200">
      <!-- Header -->
      <div class="px-6 py-4 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
        <h3 class="text-sm font-bold text-gray-900 flex items-center gap-2">
          <i class="bi bi-exclamation-triangle text-amber-500"></i>
          Remove COA Mapping
        </h3>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 transition-colors">
          <i class="bi bi-x-lg"></i>
        </button>
      </div>

      <!-- Content -->
      <div class="p-6 space-y-4">
        <div class="text-sm text-gray-600">
          Are you sure you want to remove this COA mapping?
        </div>
        
        <div class="bg-gray-50 rounded-xl p-4 border border-gray-100 space-y-2">
          <div class="flex items-center gap-2">
            <span class="font-mono text-sm font-semibold text-gray-900">{{ mapping?.code }}</span>
            <span class="text-sm text-gray-600">{{ mapping?.name }}</span>
          </div>
          <div class="flex items-center gap-2">
            <span
              class="px-2 py-0.5 text-xs font-medium rounded-full"
              :class="getCategoryClass(mapping?.category)"
            >
              {{ mapping?.category }}
            </span>
            <span
              class="px-2 py-0.5 text-xs font-medium rounded-full"
              :class="mapping?.mapping_type === 'DEBIT' ? 'bg-blue-100 text-blue-800' : 'bg-green-100 text-green-800'"
            >
              {{ mapping?.mapping_type }}
            </span>
          </div>
          <p v-if="mapping?.notes" class="text-xs text-gray-500 mt-2 italic">
            "{{ mapping.notes }}"
          </p>
        </div>

        <p class="text-[10px] text-amber-600 italic bg-amber-50 p-2 rounded-lg border border-amber-100">
          <i class="bi bi-info-circle mr-1"></i>
          This will unlink the COA from this mark. Transactions will need to be re-mapped.
        </p>
      </div>

      <!-- Footer -->
      <div class="px-6 py-4 bg-gray-50/50 border-t border-gray-100 flex gap-3">
        <button 
          @click="$emit('close')" 
          class="flex-1 px-4 py-2 text-xs font-bold text-gray-700 bg-white border border-gray-200 rounded-xl hover:bg-gray-50 transition-all shadow-sm"
        >
          Cancel
        </button>
        <button 
          @click="$emit('confirm')" 
          :disabled="isDeleting"
          class="flex-1 px-4 py-2 text-xs font-bold text-white bg-red-600 rounded-xl hover:bg-red-700 transition-all shadow-sm shadow-red-100 flex items-center justify-center gap-2 disabled:opacity-50"
        >
          <span v-if="isDeleting" class="spinner-border spinner-border-sm w-3 h-3"></span>
          <span>Remove Mapping</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  show: Boolean,
  mapping: Object,
  isDeleting: Boolean
});

defineEmits(['close', 'confirm']);

const getCategoryClass = (category) => {
  const classes = {
    ASSET: 'bg-green-100 text-green-800',
    LIABILITY: 'bg-red-100 text-red-800',
    EQUITY: 'bg-blue-100 text-blue-800',
    REVENUE: 'bg-purple-100 text-purple-800',
    EXPENSE: 'bg-orange-100 text-orange-800'
  };
  return classes[category] || 'bg-gray-100 text-gray-800';
};
</script>
