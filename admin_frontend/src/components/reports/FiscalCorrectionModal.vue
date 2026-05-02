<template>
  <BaseModal :isOpen="isOpen" @close="$emit('close')" size="lg">
    <template #title>
      <div class="flex items-center gap-2 text-theme">
        <div class="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
          <i class="bi bi-calculator text-primary"></i>
        </div>
        <span>Manual Fiscal Correction</span>
      </div>
    </template>

    <div class="p-6 space-y-6">
      <form @submit.prevent="handleSubmit" class="space-y-5">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
          <!-- COA Selection -->
          <div class="space-y-1.5 md:col-span-2">
            <label class="text-[10px] font-bold text-muted uppercase tracking-[0.2em] ml-1">
              Account (COA) <span class="text-danger">*</span>
            </label>
            <select
              v-model="formData.coa_id"
              required
              class="input-base w-full appearance-none"
            >
              <option value="" disabled>Select account to correct...</option>
              <option v-for="coa in coaList" :key="coa.id" :value="coa.id">
                {{ coa.code }} - {{ coa.name }}
              </option>
            </select>
          </div>

          <!-- Type Selection -->
          <div class="space-y-1.5">
            <label class="text-[10px] font-bold text-muted uppercase tracking-[0.2em] ml-1">
              Correction Type <span class="text-danger">*</span>
            </label>
            <select
              v-model="formData.correction_type"
              required
              class="input-base w-full appearance-none"
            >
              <option value="POSITIVE">Positive Correction (Adds to Net Income)</option>
              <option value="NEGATIVE">Negative Correction (Reduces Net Income)</option>
            </select>
          </div>

          <!-- Amount -->
          <div class="space-y-1.5">
            <label class="text-[10px] font-bold text-muted uppercase tracking-[0.2em] ml-1">
              Amount <span class="text-danger">*</span>
            </label>
            <input
              v-model.number="formData.amount"
              type="number"
              min="0"
              step="0.01"
              required
              placeholder="e.g., 500000"
              class="input-base w-full"
            />
          </div>
        </div>

        <!-- Reason -->
        <div class="space-y-1.5">
          <label class="text-[10px] font-bold text-muted uppercase tracking-[0.2em] ml-1">
            Reason / Description
          </label>
          <textarea
            v-model="formData.reason"
            rows="3"
            placeholder="e.g., Biaya entertainment tanpa daftar nominatif"
            class="input-base w-full resize-none min-h-[100px]"
          ></textarea>
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
          <span>Add Correction</span>
        </button>
      </div>
    </template>
  </BaseModal>
</template>

<script setup>
import { ref, watch } from 'vue';
import BaseModal from '../ui/BaseModal.vue';
import { useCoaStore } from '../../stores/coa';

const props = defineProps({
  isOpen: {
    type: Boolean,
    required: true
  },
  periodDate: {
    type: String,
    required: true
  }
});

const emit = defineEmits(['close', 'save']);
const coaStore = useCoaStore();

const isSaving = ref(false);
const formData = ref({
  coa_id: '',
  correction_type: 'POSITIVE',
  amount: 0,
  reason: ''
});

const coaList = ref([]);

watch(() => props.isOpen, async (newVal) => {
  if (newVal) {
    formData.value = {
      coa_id: '',
      correction_type: 'POSITIVE',
      amount: 0,
      reason: ''
    };
    if (coaStore.coaList.length === 0) {
      await coaStore.fetchCoa();
    }
    // Filter to expense and revenue accounts only
    coaList.value = coaStore.coaList.filter(c => ['EXPENSE', 'REVENUE'].includes(c.category));
  }
}, { immediate: true });

const handleSubmit = async () => {
  if (!formData.value.coa_id || !formData.value.amount || formData.value.amount <= 0) {
    alert("Please fill in all required fields correctly.");
    return;
  }
  
  isSaving.value = true;
  try {
    const payload = {
      ...formData.value,
      period_date: props.periodDate,
      company_id: localStorage.getItem('company_id') || ''
    };
    await emit('save', payload);
  } finally {
    isSaving.value = false;
  }
};
</script>
