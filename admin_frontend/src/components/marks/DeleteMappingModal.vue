<template>
  <div v-if="show" class="fixed inset-0 z-[60] flex items-center justify-center bg-gray-900/50 backdrop-blur-sm px-4">
    <div class="bg-white rounded-2xl shadow-2xl border border-gray-200 w-full max-w-md overflow-hidden animate-in fade-in zoom-in duration-200 dark:bg-[color:var(--color-surface)] dark:border-[color:var(--color-border)] dark:text-[color:var(--color-text)]">
      <!-- Header -->
      <div class="px-6 py-4 border-b border-gray-100 flex justify-between items-center bg-gray-50/50 dark:bg-[color:var(--color-surface-muted)] dark:border-[color:var(--color-border)]">
        <h3 class="text-sm font-bold text-gray-900 flex items-center gap-2 dark:text-[color:var(--color-text)]">
          <i class="bi bi-exclamation-triangle text-amber-500"></i>
          Remove COA Mapping
        </h3>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 transition-colors dark:text-[color:var(--color-text-muted)] dark:hover:text-[color:var(--color-text)]">
          <i class="bi bi-x-lg"></i>
        </button>
      </div>

      <!-- Content -->
      <div class="p-6 space-y-4">
        <div class="text-sm text-gray-600 dark:text-[color:var(--color-text-muted)]">
          Are you sure you want to remove this COA mapping?
        </div>
        
        <div class="bg-gray-50 rounded-xl p-4 border border-gray-100 space-y-2 dark:bg-[color:var(--color-surface-muted)] dark:border-[color:var(--color-border)]">
          <div class="flex items-center gap-2">
            <span class="font-mono text-sm font-semibold text-gray-900 dark:text-[color:var(--color-text)]">{{ mapping?.code }}</span>
            <span class="text-sm text-gray-600 dark:text-[color:var(--color-text-muted)]">{{ mapping?.name }}</span>
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
              :class="mapping?.mapping_type === 'DEBIT' ? 'bg-blue-100 text-blue-800 dark:bg-[color:var(--color-surface)] dark:text-[color:var(--color-text)]' : 'bg-green-100 text-green-800 dark:bg-[color:var(--color-surface)] dark:text-[color:var(--color-text)]'"
            >
              {{ mapping?.mapping_type }}
            </span>
          </div>
          <p v-if="mapping?.notes" class="text-xs text-gray-500 mt-2 italic dark:text-[color:var(--color-text-muted)]">
            "{{ mapping.notes }}"
          </p>
        </div>

        <p class="text-[10px] text-amber-600 italic bg-amber-50 p-2 rounded-lg border border-amber-100 dark:text-amber-200 dark:bg-amber-500/10 dark:border-amber-500/30">
          <i class="bi bi-info-circle mr-1"></i>
          This will unlink the COA from this mark. Transactions will need to be re-mapped.
        </p>
      </div>

      <!-- Footer -->
      <div class="px-6 py-4 bg-gray-50/50 border-t border-gray-100 flex gap-3 dark:bg-[color:var(--color-surface-muted)] dark:border-[color:var(--color-border)]">
        <button 
          @click="$emit('close')" 
          class="flex-1 px-4 py-2 text-xs font-bold text-gray-700 bg-white border border-gray-200 rounded-xl hover:bg-gray-50 transition-all shadow-sm dark:bg-[color:var(--color-surface)] dark:text-[color:var(--color-text)] dark:border-[color:var(--color-border)] dark:hover:bg-[color:var(--color-surface-muted)]"
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
    ASSET: 'bg-green-100 text-green-800 dark:bg-emerald-500/20 dark:text-emerald-200',
    LIABILITY: 'bg-red-100 text-red-800 dark:bg-red-500/20 dark:text-red-200',
    EQUITY: 'bg-blue-100 text-blue-800 dark:bg-blue-500/20 dark:text-blue-200',
    REVENUE: 'bg-purple-100 text-purple-800 dark:bg-purple-500/20 dark:text-purple-200',
    EXPENSE: 'bg-orange-100 text-orange-800 dark:bg-orange-500/20 dark:text-orange-200'
  };
  return classes[category] || 'bg-gray-100 text-gray-800 dark:bg-slate-500/20 dark:text-slate-200';
};
</script>
