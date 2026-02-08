<template>
  <div v-if="isOpen" class="fixed inset-0 z-[1050] overflow-y-auto">
    <!-- Backdrop -->
    <div class="fixed inset-0 bg-black/40 backdrop-blur-sm" @click="$emit('close')"></div>

    <!-- Modal Content -->
    <div class="flex min-h-full items-center justify-center p-4">
      <div class="relative bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden animate-fade-in-up">
        <div class="px-6 py-4 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
          <h3 class="text-lg font-bold text-gray-900">PDF Password Required</h3>
          <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 transition-colors">
            <i class="bi bi-x-lg"></i>
          </button>
        </div>

        <div class="p-6 space-y-4">
          <p class="text-sm text-gray-500">This PDF is password protected. Please enter the password to continue.</p>
          
          <div class="space-y-1">
            <div class="relative flex items-center">
              <input 
                :type="showPassword ? 'text' : 'password'" 
                v-model="password"
                @keyup.enter="handleSubmit"
                placeholder="Enter password" 
                class="input-base focus:ring-2 ring-indigo-500/20 pr-10"
              >
              <button 
                type="button" 
                class="absolute right-3 text-gray-400 hover:text-indigo-600 transition-colors"
                @click="showPassword = !showPassword"
              >
                <i class="bi" :class="showPassword ? 'bi-eye-slash' : 'bi-eye'"></i>
              </button>
            </div>
            <div v-if="error" class="text-xs text-red-600 font-medium">{{ error }}</div>
          </div>
        </div>

        <div class="px-6 py-4 border-t border-gray-100 bg-gray-50/50 flex justify-end gap-3">
          <button @click="$emit('close')" class="btn-secondary">Cancel</button>
          <button 
            @click="handleSubmit" 
            class="btn-primary shadow-lg shadow-indigo-100"
            :disabled="!password || isLoading"
          >
            <span v-if="isLoading" class="spinner-border text-white w-4 h-4 me-2" role="status"></span>
            Unlock & Convert
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue';

const props = defineProps({
  isOpen: Boolean,
  error: String,
  isLoading: Boolean
});

const emit = defineEmits(['close', 'submit']);

const password = ref('');
const showPassword = ref(false);

watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    password.value = '';
    showPassword.value = false;
  }
});

const handleSubmit = () => {
    if (password.value && !props.isLoading) {
        emit('submit', password.value);
    }
};
</script>
