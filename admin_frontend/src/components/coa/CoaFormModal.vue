<template>
  <BaseModal :isOpen="isOpen" @close="$emit('close')" size="lg">
    <template #title>
      <div class="flex items-center gap-2 text-theme">
        <div class="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
          <i class="bi bi-diagram-3 text-primary"></i>
        </div>
        <span>{{ coa ? 'Edit Account' : 'Create New Account' }}</span>
      </div>
    </template>

    <div class="p-6 space-y-6">
      <form @submit.prevent="handleSubmit" class="space-y-5">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
          <!-- Code -->
          <div class="space-y-1.5">
            <label class="text-[10px] font-bold text-muted uppercase tracking-[0.2em] ml-1">
              Account Code <span class="text-danger">*</span>
            </label>
            <input
              v-model="formData.code"
              type="text"
              required
              placeholder="e.g., 1-1000"
              class="input-base w-full"
            />
            <p class="text-[10px] text-muted mt-1 flex items-center gap-1 ml-1 font-medium italic">
               <i class="bi bi-info-circle"></i>
               <span>{{ codeHelpText }}</span>
            </p>
          </div>

          <!-- Name -->
          <div class="space-y-1.5">
            <label class="text-[10px] font-bold text-muted uppercase tracking-[0.2em] ml-1">
              Account Name <span class="text-danger">*</span>
            </label>
            <input
              v-model="formData.name"
              type="text"
              required
              placeholder="e.g., Kas"
              class="input-base w-full"
            />
          </div>

          <!-- Category -->
          <div class="space-y-1.5">
            <label class="text-[10px] font-bold text-muted uppercase tracking-[0.2em] ml-1">
              Main Category <span class="text-danger">*</span>
            </label>
            <select
              v-model="formData.category"
              required
              class="input-base w-full appearance-none"
            >
              <option value="" disabled>Select category...</option>
              <option value="ASSET">Asset (starts with 1)</option>
              <option value="LIABILITY">Liability (starts with 2)</option>
              <option value="EQUITY">Equity (starts with 3)</option>
              <option value="REVENUE">Revenue (starts with 4)</option>
              <option value="EXPENSE">Expense (starts with 5)</option>
            </select>
          </div>

          <!-- Fiscal Category -->
          <div class="space-y-1.5">
            <div class="flex items-center gap-2 ml-1">
              <label class="text-[10px] font-bold text-muted uppercase tracking-[0.2em]">
                Fiscal Category
              </label>
              <FiscalCategoryBadge :category="formData.fiscal_category" />
            </div>
            <select
              v-model="formData.fiscal_category"
              class="input-base w-full appearance-none"
            >
              <option value="DEDUCTIBLE">Deductible (Normal)</option>
              <option value="NON_DEDUCTIBLE_PERMANENT">Non-Deductible (Permanent)</option>
              <option value="NON_DEDUCTIBLE_TEMPORARY">Non-Deductible (Temporary)</option>
              <option value="NON_TAXABLE_INCOME">Non-Taxable Income</option>
            </select>
          </div>
        </div>

        <!-- Subcategory -->
        <div class="space-y-1.5">
          <label class="text-[10px] font-bold text-muted uppercase tracking-[0.2em] ml-1">
            Subcategory
          </label>
          <input
            v-model="formData.subcategory"
            type="text"
            placeholder="e.g., Current Assets"
            class="input-base w-full"
          />
        </div>

        <!-- Description -->
        <div class="space-y-1.5">
          <label class="text-[10px] font-bold text-muted uppercase tracking-[0.2em] ml-1">
            Description
          </label>
          <textarea
            v-model="formData.description"
            rows="3"
            placeholder="Brief description of this account..."
            class="input-base w-full resize-none min-h-[100px]"
          ></textarea>
        </div>

        <!-- Active Status -->
        <div class="flex items-center gap-3 p-3 rounded-xl bg-surface-muted border border-border">
          <input
            v-model="formData.is_active"
            type="checkbox"
            id="is_active_coa"
            class="w-4 h-4 text-primary bg-surface border-border rounded focus:ring-primary"
          />
          <label for="is_active_coa" class="text-xs font-bold text-theme cursor-pointer select-none">
            Active Status <span class="text-[10px] text-muted font-normal ml-2">(Uncheck to deactivate this account)</span>
          </label>
        </div>
      </form>
    </div>

    <template #footer>
      <div class="flex items-center justify-end gap-3 w-full">
        <button
          type="button"
          @click="$emit('close')"
          class="btn-secondary !text-xs !py-2 h-[38px] px-6"
        >
          Cancel
        </button>
        <button
          @click="handleSubmit"
          :disabled="isSaving"
          class="btn-primary !text-xs !py-2 h-[38px] px-8 flex items-center gap-2"
        >
          <span v-if="isSaving" class="inline-block animate-spin rounded-full h-3 w-3 border-b-2 border-white"></span>
          <span>{{ coa ? 'Update Account' : 'Create Account' }}</span>
        </button>
      </div>
    </template>
  </BaseModal>
</template>

<script setup>
import { ref, watch, computed } from 'vue';
import BaseModal from '../ui/BaseModal.vue';
import FiscalCategoryBadge from '../ui/FiscalCategoryBadge.vue';

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
  fiscal_category: 'DEDUCTIBLE',
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
      fiscal_category: newCoa.fiscal_category || 'DEDUCTIBLE',
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
      fiscal_category: 'DEDUCTIBLE',
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
