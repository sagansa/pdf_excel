<template>
  <BaseModal :isOpen="isOpen" @close="close" size="md">
    <template #title>
      <div class="flex items-center gap-3">
        <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <i class="bi bi-stack text-xl"></i>
        </div>
        <div>
          <h3 class="text-lg font-bold">Bulk Actions</h3>
          <p class="text-xs text-muted font-medium uppercase tracking-wider">
            Applying changes to {{ selectedCount }} transactions
          </p>
        </div>
      </div>
    </template>

    <div class="p-6 space-y-6">
      <!-- Section: Company Assignment -->
      <div class="space-y-3">
        <label class="flex items-center gap-2 text-sm font-bold text-theme">
          <i class="bi bi-building text-primary"></i>
          Assign Company
        </label>
        <div class="grid grid-cols-1 gap-2">
            <button
                v-for="company in companies"
                :key="company.id"
                @click="tempCompanyId = company.id"
                class="flex items-center justify-between p-3 rounded-xl border transition-all text-left"
                :class="tempCompanyId === company.id 
                    ? 'border-primary bg-primary/5 ring-1 ring-primary' 
                    : 'border-border hover:bg-surface-muted'"
            >
                <div class="flex items-center gap-3">
                  <div class="w-8 h-8 rounded-lg bg-surface-muted flex items-center justify-center text-xs font-bold text-muted uppercase">
                    {{ company.short_name || company.name.substring(0, 2) }}
                  </div>
                  <span class="text-sm font-medium">{{ company.name }}</span>
                </div>
                <i v-if="tempCompanyId === company.id" class="bi bi-check-circle-fill text-primary"></i>
            </button>
            <button
                @click="tempCompanyId = 'none'"
                class="flex items-center justify-between p-3 rounded-xl border transition-all text-left"
                :class="tempCompanyId === 'none' 
                    ? 'border-primary bg-primary/5 ring-1 ring-primary' 
                    : 'border-border hover:bg-surface-muted'"
            >
                <span class="text-sm font-medium italic text-muted">-- No Company (Unassign) --</span>
                <i v-if="tempCompanyId === 'none'" class="bi bi-check-circle-fill text-primary"></i>
            </button>
        </div>
      </div>

      <div class="h-px bg-border/50"></div>

      <!-- Section: Mark Assignment -->
      <div class="space-y-3">
        <label class="flex items-center gap-2 text-sm font-bold text-theme">
          <i class="bi bi-bookmark-star text-primary"></i>
          Assign Mark
        </label>
        <div class="max-h-[300px] overflow-y-auto space-y-2 pr-1 custom-scrollbar">
            <div
                v-for="mark in sortedMarks"
                :key="mark.id"
                @click="tempMarkId = mark.id"
                class="p-3 rounded-xl border cursor-pointer transition-all group"
                :class="tempMarkId === mark.id 
                    ? 'border-primary bg-primary/5 ring-1 ring-primary' 
                    : 'border-border hover:bg-surface-muted'"
            >
                <div class="flex justify-between items-start mb-1">
                   <p class="text-sm font-bold">{{ mark.internal_report }}</p>
                   <i v-if="tempMarkId === mark.id" class="bi bi-check-circle-fill text-primary"></i>
                </div>
                <div class="flex gap-4 text-[10px] text-muted font-medium">
                    <div v-if="mark.personal_use" class="flex items-center gap-1">
                        <span class="uppercase font-bold text-[9px] text-primary/70">Personal:</span>
                        {{ mark.personal_use }}
                    </div>
                    <div v-if="mark.tax_report" class="flex items-center gap-1">
                        <span class="uppercase font-bold text-[9px] text-primary/70">Tax:</span>
                        {{ mark.tax_report }}
                    </div>
                </div>
            </div>
             <button
                @click="tempMarkId = 'none'"
                class="w-full flex items-center justify-between p-3 rounded-xl border transition-all text-left"
                :class="tempMarkId === 'none' 
                    ? 'border-primary bg-primary/5 ring-1 ring-primary' 
                    : 'border-border hover:bg-surface-muted'"
            >
                <span class="text-sm font-medium italic text-muted">-- Unmark --</span>
                <i v-if="tempMarkId === 'none'" class="bi bi-check-circle-fill text-primary"></i>
            </button>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="flex items-center justify-between w-full h-full">
        <button @click="close" class="btn-secondary">Cancel</button>
        <div class="flex gap-3">
             <button 
                @click="handleApply" 
                class="btn-primary"
                :disabled="loading || (!tempCompanyId && !tempMarkId)"
             >
                <span v-if="loading" class="spinner-border w-4 h-4 me-2"></span>
                Apply Changes
             </button>
        </div>
      </div>
    </template>
  </BaseModal>
</template>

<script setup>
import { ref, watch } from 'vue';
import BaseModal from '../ui/BaseModal.vue';

const props = defineProps({
  isOpen: Boolean,
  selectedCount: Number,
  companies: {
    type: Array,
    default: () => []
  },
  sortedMarks: {
    type: Array,
    default: () => []
  },
  loading: Boolean
});

const emit = defineEmits(['close', 'apply']);

const tempCompanyId = ref(null);
const tempMarkId = ref(null);

watch(() => props.isOpen, (newVal) => {
    if (newVal) {
        tempCompanyId.value = null;
        tempMarkId.value = null;
    }
});

const close = () => {
  emit('close');
};

const handleApply = () => {
  emit('apply', {
      companyId: tempCompanyId.value,
      markId: tempMarkId.value
  });
};
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  @apply bg-transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: var(--color-border);
  border-radius: 9999px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: var(--color-border-strong);
}
</style>
