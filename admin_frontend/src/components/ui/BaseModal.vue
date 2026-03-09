<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 overflow-y-auto" aria-labelledby="modal-title" role="dialog" aria-modal="true">
    <div class="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
      
      <!-- Backdrop -->
      <div 
        class="fixed inset-0 modal-backdrop transition-opacity" 
        aria-hidden="true"
        @click="close"
      ></div>

      <span class="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>

       <!-- Modal Panel -->
       <div 
         :class="[
           'inline-block align-bottom modal-panel text-left overflow-hidden transform transition-all sm:my-8 sm:align-middle sm:w-full',
           size === 'sm' ? 'sm:max-w-sm' : '',
           size === 'md' ? 'sm:max-w-md' : '',
           size === 'lg' ? 'sm:max-w-lg' : '',
           size === 'xl' ? 'sm:max-w-7xl' : '',
           !size || size === '2xl' ? 'sm:max-w-5xl' : ''
         ]"
       >
        <div class="px-6 py-4 modal-header flex justify-between items-center">
           <h3 class="text-lg font-bold text-theme"><slot name="title"></slot></h3>
           <button @click="close" class="btn-ghost rounded-xl p-2">
             <i class="bi bi-x-lg"></i>
           </button>
        </div>
        
        <div class="modal-body">
          <slot></slot>
        </div>
        
        <div class="px-6 py-4 modal-footer flex justify-end gap-3" v-if="$slots.footer">
           <slot name="footer"></slot>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  isOpen: Boolean,
  size: {
    type: String,
    default: '2xl',
    validator: (value) => ['sm', 'md', 'lg', 'xl', '2xl'].includes(value)
  }
});

const emit = defineEmits(['close']);

const close = () => {
  emit('close');
};
</script>

<style scoped>
.modal-backdrop {
  background: rgba(15, 23, 42, 0.62);
}

.modal-panel {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card-hover);
}

.modal-header,
.modal-footer {
  background: var(--color-surface-muted);
  border-color: var(--color-border);
}

.modal-header {
  border-bottom: 1px solid var(--color-border);
}

.modal-body {
  background: var(--color-surface);
}

.modal-footer {
  border-top: 1px solid var(--color-border);
}
</style>
