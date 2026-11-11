<template>
  <BaseModal :isOpen="show" size="md" @close="$emit('close')">
    <template #title>
      <span class="delete-title">
        <i class="bi bi-exclamation-triangle delete-title__icon" aria-hidden="true"></i>
        Remove COA Mapping
      </span>
    </template>

    <!-- Content -->
    <div class="p-6 space-y-4">
      <div class="text-sm text-muted">
        Are you sure you want to remove this COA mapping?
      </div>

      <div class="mapping-summary">
        <div class="flex items-center gap-2">
          <span class="mono text-sm font-semibold text-theme">{{ mapping?.code }}</span>
          <span class="text-sm text-muted">{{ mapping?.name }}</span>
        </div>
        <div class="flex items-center gap-2">
          <span class="badge" :class="`badge--cat-${categoryTone(mapping?.category)}`">
            {{ mapping?.category }}
          </span>
          <span class="badge" :class="mapping?.mapping_type === 'DEBIT' ? 'badge--db' : 'badge--cr'">
            {{ mapping?.mapping_type }}
          </span>
        </div>
        <p v-if="mapping?.notes" class="text-xs text-muted mt-2 italic">
          "{{ mapping.notes }}"
        </p>
      </div>

      <p class="delete-note">
        <i class="bi bi-info-circle mr-1"></i>
        This will unlink the COA from this mark. Transactions will need to be re-mapped.
      </p>
    </div>

    <!-- Footer -->
    <template #footer>
      <button @click="$emit('close')" class="btn-secondary flex-1">Cancel</button>
      <button
        @click="$emit('confirm')"
        :disabled="isDeleting"
        class="btn-danger flex-1"
      >
        <span v-if="isDeleting" class="spinner-border spinner-border-sm w-3 h-3 me-2"></span>
        <span>Remove Mapping</span>
      </button>
    </template>
  </BaseModal>
</template>

<script setup>
import BaseModal from '../ui/BaseModal.vue';

defineProps({
  show: Boolean,
  mapping: Object,
  isDeleting: Boolean
});

defineEmits(['close', 'confirm']);

const CATEGORY_TONES = {
  ASSET: 'success',
  LIABILITY: 'danger',
  EQUITY: 'primary',
  REVENUE: 'revenue',
  EXPENSE: 'warning'
};

const categoryTone = (category) => CATEGORY_TONES[category] || 'neutral';
</script>

<style scoped>
.delete-title {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.delete-title__icon {
  color: var(--color-warning);
}

.mapping-summary {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 16px;
  border-radius: 12px;
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
}

.delete-note {
  font-size: 11px;
  font-style: italic;
  padding: 8px 10px;
  border-radius: 10px;
  background: color-mix(in srgb, var(--color-warning) 10%, transparent);
  border: 1px solid color-mix(in srgb, var(--color-warning) 25%, transparent);
  color: var(--color-warning);
}

.badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.03em;
  white-space: nowrap;
}

.badge--neutral {
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border);
  color: var(--color-text-muted);
}

.badge--primary {
  background: color-mix(in srgb, var(--color-primary) 12%, transparent);
  color: var(--color-primary);
}

.badge--success {
  background: color-mix(in srgb, var(--color-success) 12%, transparent);
  color: var(--color-success);
}

.badge--warning {
  background: color-mix(in srgb, var(--color-warning) 13%, transparent);
  color: var(--color-warning);
}

.badge--danger {
  background: color-mix(in srgb, var(--color-danger) 12%, transparent);
  color: var(--color-danger);
}

.badge--revenue {
  --badge-accent: #7c3aed;
  background: color-mix(in srgb, var(--badge-accent) 11%, transparent);
  color: var(--badge-accent);
}

html.dark .badge--revenue {
  --badge-accent: #c4b5fd;
}

.badge--db {
  background: color-mix(in srgb, var(--color-primary) 12%, transparent);
  color: var(--color-primary);
}

.badge--cr {
  background: color-mix(in srgb, var(--color-success) 12%, transparent);
  color: var(--color-success);
}
</style>
