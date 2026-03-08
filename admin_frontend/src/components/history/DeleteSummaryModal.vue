<template>
  <div v-if="show" class="fixed inset-0 z-[60] flex items-center justify-center bg-gray-900/50 backdrop-blur-sm px-4">
    <div class="bg-white rounded-2xl shadow-2xl border border-gray-200 w-full max-w-sm overflow-hidden animate-in fade-in zoom-in duration-200">
      <!-- Header -->
      <div class="px-6 py-4 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
        <h3 class="text-sm font-bold text-gray-900 flex items-center gap-2">
          <i class="bi bi-exclamation-triangle text-amber-500"></i>
          Confirm Deletion
        </h3>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 transition-colors">
          <i class="bi bi-x-lg"></i>
        </button>
      </div>

      <!-- Content -->
      <div class="p-6 space-y-4">
        <div class="text-sm text-gray-600">
          Are you sure you want to delete all transactions from this upload?
        </div>
        
        <div class="bg-gray-50 rounded-xl p-4 border border-gray-100 space-y-2">
          <div class="flex justify-between text-[11px]">
            <span class="text-gray-400">File:</span>
            <span class="text-gray-900 font-semibold truncate max-w-[200px]" :title="item?.source_file">{{ item?.source_file }}</span>
          </div>
          <div class="flex justify-between text-[11px]">
            <span class="text-gray-400">Bank:</span>
            <span class="text-gray-900 font-medium font-mono uppercase">{{ formatBankCode(item?.bank_code) }}</span>
          </div>
          <div class="text-[10px] text-gray-500">Deletion scope: all companies in this file/bank group.</div>
          <div class="flex justify-between text-[11px] pt-1 border-t border-gray-100">
            <span class="text-gray-400">Transactions:</span>
            <span class="text-indigo-600 font-bold">{{ item?.transaction_count }}</span>
          </div>
        </div>

        <p class="text-[10px] text-red-500 italic bg-red-50 p-2 rounded-lg border border-red-100">
          <i class="bi bi-info-circle mr-1"></i>
          This action cannot be undone. All associated data will be permanently removed.
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
          :disabled="isLoading"
          class="flex-1 px-4 py-2 text-xs font-bold text-white bg-red-600 rounded-xl hover:bg-red-700 transition-all shadow-sm shadow-red-100 flex items-center justify-center gap-2 disabled:opacity-50"
        >
          <span v-if="isLoading" class="spinner-border spinner-border-sm w-3 h-3"></span>
          <span>Delete All</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  show: Boolean,
  item: Object,
  isLoading: Boolean
});

defineEmits(['close', 'confirm']);

const formatBankCode = (bankCode) => {
  const value = (bankCode || '').toString();
  if (!value) return 'UNKNOWN BANK';
  return value.replace('_CC', ' CREDIT CARD');
};
</script>
