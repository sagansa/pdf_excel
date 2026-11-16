<template>
  <div ref="listRef" class="pill-tabs" role="tablist" @keydown="onKeydown">
    <button
      v-for="tab in tabs"
      :key="tab.key"
      :data-key="tab.key"
      type="button"
      role="tab"
      class="pill-tabs__item"
      :class="{ 'pill-tabs__item--active': tab.key === modelValue }"
      :aria-selected="tab.key === modelValue"
      :tabindex="tab.key === modelValue ? 0 : -1"
      :disabled="tab.disabled"
      @click="select(tab.key)"
    >
      <i v-if="tab.icon" :class="tab.icon" aria-hidden="true"></i>
      {{ tab.label }}
    </button>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const props = defineProps({
  tabs: {
    type: Array,
    required: true
  },
  modelValue: {
    type: String,
    default: ''
  }
});

const emit = defineEmits(['update:modelValue']);

const listRef = ref(null);

const select = (key) => {
  if (key !== props.modelValue) emit('update:modelValue', key);
};

// Roving-focus keyboard navigation (Arrow / Home / End), activation follows focus.
const onKeydown = (event) => {
  if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
  const items = Array.from(listRef.value.querySelectorAll('.pill-tabs__item')).filter((el) => !el.disabled);
  if (items.length === 0) return;

  const currentIndex = Math.max(0, items.findIndex((el) => el.classList.contains('pill-tabs__item--active')));
  let nextIndex = currentIndex;
  if (event.key === 'ArrowRight') nextIndex = (currentIndex + 1) % items.length;
  else if (event.key === 'ArrowLeft') nextIndex = (currentIndex - 1 + items.length) % items.length;
  else if (event.key === 'Home') nextIndex = 0;
  else nextIndex = items.length - 1;

  event.preventDefault();
  items[nextIndex].focus();
  emit('update:modelValue', items[nextIndex].dataset.key);
};
</script>

<style scoped>
/* Pill tab language — the app's incumbent tab voice (matches the chip/stat-pill
   vocabulary of the paper-ledger system). Place inside a padded card band. */
.pill-tabs {
  display: flex;
  gap: 8px;
  overflow-x: auto;
}

.pill-tabs__item {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
  padding: 10px 16px;
  border-radius: 16px;
  font-family: var(--font-sans);
  font-size: 14px;
  font-weight: 500;
  line-height: 1.35;
  color: var(--color-text-muted);
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
  transition: color 0.2s ease, background-color 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}

.pill-tabs__item:hover:not(:disabled):not(.pill-tabs__item--active) {
  color: var(--color-text);
  border-color: var(--color-border-strong);
}

.pill-tabs__item--active {
  color: var(--color-primary);
  background: rgba(15, 118, 110, 0.12);
  border-color: rgba(15, 118, 110, 0.18);
  box-shadow: var(--shadow-soft);
}

.pill-tabs__item:focus-visible {
  outline: 2px solid var(--color-primary-ring);
  outline-offset: 1px;
}

.pill-tabs__item:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

@media (prefers-reduced-motion: reduce) {
  .pill-tabs__item {
    transition: none;
  }
}
</style>
