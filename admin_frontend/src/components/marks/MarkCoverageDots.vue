<template>
  <div class="coverage-dots">
    <span v-for="group in groups" :key="group.label" class="coverage-dots__group" :title="group.title">
      <span class="coverage-dots__label">{{ group.label }}</span>
      <span class="coverage-dots__track" aria-hidden="true">
        <template v-if="group.count > 0">
          <span v-for="dot in Math.min(group.count, 3)" :key="dot" class="coverage-dot coverage-dot--filled"></span>
          <span v-if="group.count > 3" class="coverage-dots__more">+{{ group.count - 3 }}</span>
        </template>
        <span v-else class="coverage-dot coverage-dot--missing"></span>
      </span>
    </span>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  realCount: {
    type: Number,
    default: 0
  },
  coretaxCount: {
    type: Number,
    default: 0
  }
});

const groups = computed(() => [
  { label: 'Real', count: props.realCount, title: `Mapping Real: ${props.realCount}` },
  { label: 'Coretax', count: props.coretaxCount, title: `Mapping Coretax: ${props.coretaxCount}` }
]);
</script>

<style scoped>
.coverage-dots {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.coverage-dots__group {
  display: inline-flex;
  align-items: center;
  gap: 7px;
}

.coverage-dots__label {
  width: 56px;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--color-text-muted);
}

.coverage-dots__track {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.coverage-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
}

.coverage-dot--filled {
  background: var(--color-primary);
}

.coverage-dot--missing {
  background: transparent;
  border: 1.5px solid color-mix(in srgb, var(--color-warning) 70%, transparent);
}

.coverage-dots__more {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-text-muted);
}
</style>
