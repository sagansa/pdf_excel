<template>
  <div v-if="isOpen" class="fixed inset-0 z-[60] flex items-center justify-center bg-gray-900/50 backdrop-blur-sm px-4">
    <div class="bg-white rounded-2xl shadow-2xl border border-gray-200 w-full max-w-lg overflow-hidden animate-in fade-in zoom-in duration-200">
      <!-- Header -->
      <div class="px-6 py-4 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
        <h3 class="text-sm font-bold text-gray-900 flex items-center gap-2">
          <i class="bi bi-wrench-adjustable text-amber-500"></i>
          {{ isSuccess ? 'Mapping Fix Results' : 'Confirm Auto-Fix' }}
        </h3>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 transition-colors">
          <i class="bi bi-x-lg"></i>
        </button>
      </div>

      <!-- Content: Confirmation -->
      <div v-if="!isSuccess" class="p-6 space-y-4">
        <div class="text-sm text-gray-600">
          This tool will automatically correct transaction mappings based on COA categories.
        </div>
        
        <div class="bg-amber-50 rounded-xl p-4 border border-amber-100 space-y-3">
          <p class="text-xs font-semibold text-amber-800 flex items-center gap-2">
            <i class="bi bi-info-circle"></i>
            How it works:
          </p>
          <ul class="text-[11px] text-amber-700 space-y-1 ml-1 list-disc list-inside">
            <li>Finds all mappings where COA is <strong>EXPENSE (5xxx)</strong> but type is <strong>CREDIT</strong></li>
            <li>Changes them to <strong>DEBIT</strong> so they appear positive in reports</li>
            <li v-if="fixType === 'REVENUE'">Finds all mappings where COA is <strong>REVENUE (4xxx)</strong> but type is <strong>DEBIT</strong></li>
            <li v-if="fixType === 'REVENUE'">Changes them to <strong>CREDIT</strong></li>
          </ul>
        </div>

        <p class="text-[11px] text-gray-500 italic">
          Transactions already correctly mapped will not be affected. After fixing, please refresh your Financial Reports.
        </p>
      </div>

      <!-- Content: Success Results -->
      <div v-else class="p-6 space-y-4">
        <div class="flex flex-col items-center text-center space-y-2 mb-4">
          <div class="w-12 h-12 bg-green-100 text-green-600 rounded-full flex items-center justify-center text-2xl mb-2">
            <i class="bi bi-check-circle-fill"></i>
          </div>
          <h4 class="font-bold text-gray-900">
            {{ results.fixed_count > 0 ? 'Fixes Applied Successfully!' : 'No Fixes Needed' }}
          </h4>
          <p class="text-xs text-gray-500">
            {{ results.fixed_count > 0 
                ? `Successfully updated ${results.fixed_count} mapping(s).` 
                : 'All your mappings are already follow the correct DEBIT/CREDIT rules.' }}
          </p>
        </div>

        <div v-if="results.fixed_count > 0" class="bg-gray-50 rounded-xl p-4 border border-gray-100 max-h-48 overflow-y-auto">
          <div v-for="m in results.mappings" :key="m.id" class="text-[10px] py-1 border-b border-gray-200 last:border-0 flex justify-between">
            <span class="font-medium text-gray-700 truncate mr-2">{{ m.mark }}</span>
            <span class="font-mono text-gray-500 shrink-0">{{ m.coa_code }} ({{ m.old_type }} → {{ m.new_type }})</span>
          </div>
        </div>

        <div class="bg-blue-50 p-3 rounded-lg border border-blue-100 text-[10px] text-blue-700">
          <i class="bi bi-lightbulb mr-1"></i>
          <strong>Tip:</strong> Refresh the Financial Reports page to see the updated balances.
        </div>
      </div>

      <!-- Footer -->
      <div class="px-6 py-4 bg-gray-50/50 border-t border-gray-100 flex gap-3">
        <template v-if="!isSuccess">
          <button 
            @click="$emit('close')" 
            class="flex-1 px-4 py-2 text-xs font-bold text-gray-700 bg-white border border-gray-200 rounded-xl hover:bg-gray-50 transition-all shadow-sm"
          >
            Cancel
          </button>
          <button 
            @click="$emit('confirm')" 
            :disabled="isLoading"
            class="flex-1 px-4 py-2 text-xs font-bold text-white bg-amber-600 rounded-xl hover:bg-amber-700 transition-all shadow-sm shadow-amber-100 flex items-center justify-center gap-2 disabled:opacity-50"
          >
            <span v-if="isLoading" class="spinner-border spinner-border-sm w-3 h-3"></span>
            <span>Run Auto-Fix</span>
          </button>
        </template>
        <template v-else>
          <button 
            @click="$emit('close')" 
            class="w-full px-4 py-2 text-xs font-bold text-white bg-indigo-600 rounded-xl hover:bg-indigo-700 transition-all shadow-sm"
          >
            Done
          </button>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  isOpen: Boolean,
  isLoading: Boolean,
  isSuccess: Boolean,
  results: {
    type: Object,
    default: () => ({ fixed_count: 0, mappings: [] })
  },
  fixType: {
    type: String,
    default: 'EXPENSE'
  }
});

defineEmits(['close', 'confirm']);
</script>
