<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
    @click.self="$emit('close')"
  >
    <div class="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
      <!-- Header -->
      <div class="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <h2 class="text-xl font-bold text-gray-900">
          {{ coa ? 'Edit Account' : 'Create New Account' }}
        </h2>
        <button
          @click="$emit('close')"
          class="text-gray-400 hover:text-gray-600 transition-colors"
        >
          <i class="bi bi-x-lg text-xl"></i>
        </button>
      </div>

      <!-- Form -->
      <form @submit.prevent="handleSubmit" class="p-6 space-y-4">
        <!-- Code -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            Account Code <span class="text-red-500">*</span>
          </label>
          <input
            v-model="formData.code"
            type="text"
            required
            placeholder="e.g., 1-1000"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
          <p class="text-xs text-gray-500 mt-1 flex items-center gap-1">
             <i class="bi bi-info-circle"></i>
             <span>{{ codeHelpText }}</span>
          </p>
        </div>

        <!-- Name -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            Account Name <span class="text-red-500">*</span>
          </label>
          <input
            v-model="formData.name"
            type="text"
            required
            placeholder="e.g., Kas"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>

        <!-- Category -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            Category <span class="text-red-500">*</span>
          </label>
          <select
            v-model="formData.category"
            required
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="">Select category...</option>
            <option value="ASSET">Asset (starts with 1)</option>
            <option value="LIABILITY">Liability (starts with 2)</option>
            <option value="EQUITY">Equity (starts with 3)</option>
            <option value="REVENUE">Revenue (starts with 4)</option>
            <option value="EXPENSE">Expense (starts with 5)</option>
          </select>
        </div>

        <!-- Subcategory -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            Subcategory
          </label>
          <input
            v-model="formData.subcategory"
            type="text"
            placeholder="e.g., Current Assets"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>

        <!-- Description -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            Description
          </label>
          <textarea
            v-model="formData.description"
            rows="3"
            placeholder="Brief description of this account..."
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          ></textarea>
        </div>

        <!-- Active Status -->
        <div class="flex items-center gap-2">
          <input
            v-model="formData.is_active"
            type="checkbox"
            id="is_active"
            class="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
          />
          <label for="is_active" class="text-sm text-gray-700">
            Active (uncheck to deactivate this account)
          </label>
        </div>

        <!-- Actions -->
        <div class="flex items-center justify-end gap-3 pt-4 border-t border-gray-200">
          <button
            type="button"
            @click="$emit('close')"
            class="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            :disabled="isSaving"
            class="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <span v-if="isSaving" class="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-white"></span>
            <span>{{ coa ? 'Update' : 'Create' }}</span>
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue';

const props = defineProps({
  isOpen: {
    type: Boolean,
    required: true
  },
  coa: {
    type: Object,
    default: null
  }
});

const emit = defineEmits(['close', 'save']);

const isSaving = ref(false);
const formData = ref({
  code: '',
  name: '',
  category: '',
  subcategory: '',
  description: '',
  is_active: true
});

const codeHelpText = computed(() => {
  const categoryMap = {
    'ASSET': '1-XXXX',
    'LIABILITY': '2-XXXX',
    'EQUITY': '3-XXXX',
    'REVENUE': '4-XXXX',
    'EXPENSE': '5-XXXX'
  };
  
  const prefix = categoryMap[formData.value.category];
  if (prefix) {
    return `Format: ${prefix} (e.g., ${prefix.replace('XXXX', '1000')})`;
  }
  return 'Select a category to see recommended format';
});

// Watch for coa prop changes to populate form
watch(() => props.coa, (newCoa) => {
  if (newCoa) {
    formData.value = {
      code: newCoa.code || '',
      name: newCoa.name || '',
      category: newCoa.category || '',
      subcategory: newCoa.subcategory || '',
      description: newCoa.description || '',
      is_active: newCoa.is_active !== false
    };
  } else {
    // Reset form for new entry
    formData.value = {
      code: '',
      name: '',
      category: '',
      subcategory: '',
      description: '',
      is_active: true
    };
  }
}, { immediate: true });

const handleSubmit = async () => {
  isSaving.value = true;
  try {
    await emit('save', formData.value);
  } finally {
    isSaving.value = false;
  }
};
</script>
