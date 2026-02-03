<template>
  <BaseModal :isOpen="isOpen" @close="close">
    <template #title>{{ title }}</template>
    
    <div class="p-6">
      <div class="flex items-center gap-4">
        <div 
          class="w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0"
          :class="variant === 'danger' ? 'bg-red-50 text-red-600' : 'bg-indigo-50 text-indigo-600'"
        >
          <i class="bi" :class="variant === 'danger' ? 'bi-exclamation-triangle-fill' : 'bi-info-circle-fill'" style="font-size: 1.5rem;"></i>
        </div>
        <div>
          <p class="text-sm text-gray-600 leading-relaxed">{{ message }}</p>
        </div>
      </div>
    </div>

    <template #footer>
      <button @click="close" class="btn-secondary" :disabled="loading">Cancel</button>
      <button 
        @click="confirm" 
        :disabled="loading"
        class="flex items-center px-4 py-2 rounded-xl font-bold transition-all duration-200 shadow-sm"
        :class="variant === 'danger' 
          ? 'bg-red-600 text-white hover:bg-red-700 shadow-red-100' 
          : 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-indigo-100'"
      >
        <span v-if="loading" class="spinner-border spinner-border-sm me-2" role="status"></span>
        {{ confirmText }}
      </button>
    </template>
  </BaseModal>
</template>

<script setup>
import BaseModal from './BaseModal.vue';

const props = defineProps({
  isOpen: Boolean,
  title: {
    type: String,
    default: 'Are you sure?'
  },
  message: {
    type: String,
    default: 'This action cannot be undone.'
  },
  confirmText: {
    type: String,
    default: 'Confirm'
  },
  loading: {
    type: Boolean,
    default: false
  },
  variant: {
    type: String,
    default: 'danger',
    validator: (val) => ['danger', 'primary'].includes(val)
  }
});

const emit = defineEmits(['close', 'confirm']);

const close = () => emit('close');
const confirm = () => emit('confirm');
</script>
