<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 overflow-y-auto" aria-labelledby="modal-title" role="dialog" aria-modal="true">
    <div class="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
      
      <!-- Backdrop -->
      <div 
        class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" 
        aria-hidden="true"
        @click="close"
      ></div>

      <span class="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>

      <!-- Modal Panel -->
      <div 
        class="inline-block align-bottom bg-white rounded-2xl text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-5xl sm:w-full"
      >
        <div class="px-6 py-4 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
           <h3 class="text-lg font-bold text-gray-900"><slot name="title"></slot></h3>
           <button @click="close" class="text-gray-400 hover:text-gray-600 transition-colors">
             <i class="bi bi-x-lg"></i>
           </button>
        </div>
        
        <div class="bg-white">
          <slot></slot>
        </div>
        
        <div class="px-6 py-4 border-t border-gray-100 bg-gray-50/50 flex justify-end gap-3" v-if="$slots.footer">
           <slot name="footer"></slot>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  isOpen: Boolean
});

const emit = defineEmits(['close']);

const close = () => {
  emit('close');
};
</script>
