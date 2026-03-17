<template>
  <div class="workspace-container">
    <div class="workspace-header">
      <div class="workspace-header__content">
        <h2 class="workspace-title">{{ title }}</h2>
        <p v-if="subtitle" class="workspace-subtitle">{{ subtitle }}</p>
      </div>
      <div class="workspace-header__actions">
        <slot name="header-actions"></slot>
      </div>
    </div>

    <div v-if="hasFilters" class="workspace-filters">
      <slot name="filters"></slot>
    </div>

    <div class="workspace-toolbar">
      <div class="workspace-toolbar__left">
        <slot name="toolbar-left">
          <div v-if="totalItems !== null" class="workspace-stats">
            <span class="workspace-stat">
              <span class="workspace-stat__label">Total:</span>
              <span class="workspace-stat__value">{{ formatNumber(totalItems) }}</span>
            </span>
          </div>
        </slot>
      </div>
      <div class="workspace-toolbar__right">
        <slot name="toolbar-right">
          <button type="button" class="btn-secondary !px-3 !py-2 !text-xs" :disabled="isLoading" @click="$emit('refresh')">
            <i class="bi bi-arrow-clockwise mr-1"></i> Refresh
          </button>
        </slot>
      </div>
    </div>

    <div class="workspace-content">
      <div v-if="isLoading" class="workspace-loading">
        <div class="workspace-loading__spinner"></div>
        <p class="workspace-loading__text">Loading...</p>
      </div>

      <div v-else-if="error" class="workspace-error">
        <i class="bi bi-exclamation-triangle-fill workspace-error__icon"></i>
        <p class="workspace-error__text">{{ error }}</p>
        <button v-if="onRetry" type="button" class="btn-primary !mt-3" @click="onRetry">Retry</button>
      </div>

      <div v-else-if="isEmpty" class="workspace-empty">
        <i class="bi bi-inbox workspace-empty__icon"></i>
        <h3 class="workspace-empty__title">{{ emptyTitle || 'No Data' }}</h3>
        <p class="workspace-empty__text">{{ emptyText || 'No items to display' }}</p>
        <slot name="empty-actions"></slot>
      </div>

      <template v-else><slot></slot></template>
    </div>

    <div v-if="hasFooter" class="workspace-footer">
      <slot name="footer"></slot>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  isLoading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  totalItems: { type: Number, default: null },
  isEmpty: { type: Boolean, default: false },
  emptyTitle: { type: String, default: '' },
  emptyText: { type: String, default: '' },
  hasFilters: { type: Boolean, default: false },
  hasFooter: { type: Boolean, default: false },
  onRetry: { type: Function, default: null }
});

defineEmits(['refresh']);

const formatNumber = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '-';
  return new Intl.NumberFormat('id-ID', { minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(Number(value));
};
</script>

<style scoped>
.workspace-container { @apply space-y-4; }
.workspace-header { @apply flex items-start justify-between gap-4; background: var(--color-surface); border-radius: 12px; padding: 1.5rem; border: 1px solid var(--color-border); }
.workspace-header__content { @apply flex-1; }
.workspace-title { @apply text-xl font-bold mb-1; color: var(--color-text); }
.workspace-subtitle { @apply text-xs; color: var(--color-text-muted); }
.workspace-header__actions { @apply flex items-center gap-2; }
.workspace-filters { @apply surface-card p-4; border-radius: 12px; }
.workspace-toolbar { @apply flex items-center justify-between; background: var(--color-surface); border-radius: 12px; padding: 1rem 1.5rem; border: 1px solid var(--color-border); }
.workspace-toolbar__left, .workspace-toolbar__right { @apply flex items-center gap-3; }
.workspace-stats { @apply flex items-center gap-4; }
.workspace-stat { @apply flex items-center gap-2 text-xs; }
.workspace-stat__label { @apply uppercase font-semibold; color: var(--color-text-muted); }
.workspace-stat__value { @apply font-bold; font-family: var(--font-mono); color: var(--color-text); }
.workspace-stat__value--primary { color: var(--color-primary); }
.workspace-content { @apply relative; min-height: 400px; }
.workspace-loading { @apply flex flex-col items-center justify-center h-full; background: var(--color-surface); border-radius: 12px; border: 1px solid var(--color-border); }
.workspace-loading__spinner { @apply w-12 h-12 rounded-full; border: 3px solid var(--color-border); border-top-color: var(--color-primary); animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.workspace-loading__text { @apply mt-4 text-sm; color: var(--color-text-muted); }
.workspace-error { @apply flex flex-col items-center justify-center h-full; background: rgba(185, 28, 28, 0.05); border: 1px solid rgba(185, 28, 28, 0.18); border-radius: 12px; padding: 3rem; }
.workspace-error__icon { @apply text-4xl mb-3; color: var(--color-danger); }
.workspace-error__text { @apply text-sm text-center; color: var(--color-danger); }
.workspace-empty { @apply flex flex-col items-center justify-center h-full; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 12px; padding: 3rem; }
.workspace-empty__icon { @apply text-5xl mb-4; color: var(--color-text-muted); }
.workspace-empty__title { @apply text-lg font-bold mb-2; color: var(--color-text); }
.workspace-empty__text { @apply text-sm text-center max-w-md; color: var(--color-text-muted); }
.workspace-footer { @apply surface-card p-4; border-radius: 12px; border: 1px solid var(--color-border); }
</style>
