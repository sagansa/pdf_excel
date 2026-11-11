<template>
  <div class="mapping-chips">
    <div class="mapping-chips__lens">
      <span class="mapping-chips__label">{{ label }}</span>
      <template v-if="visibleMappings.length">
        <span v-for="mapping in visibleMappings" :key="`${mapping.coa_id || mapping.code}-${mapping.type}`" class="mapping-chip">
          <span class="mapping-chip__code">{{ mapping.code }}</span>
          <span class="mapping-chip__name" :title="mapping.name">{{ mapping.name }}</span>
          <span class="mapping-chip__side" :class="mapping.type === 'DEBIT' ? 'mapping-chip__side--db' : 'mapping-chip__side--cr'">
            {{ mapping.type === 'DEBIT' ? 'DB' : 'CR' }}
          </span>
        </span>
        <span v-if="mappings.length > max" class="mapping-chips__more">+{{ mappings.length - max }}</span>
      </template>
      <span v-else class="mapping-chips__none" title="Tanpa mapping pada lensa ini">—</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  label: {
    type: String,
    required: true
  },
  mappings: {
    type: Array,
    default: () => []
  },
  max: {
    type: Number,
    default: 2
  }
});

const visibleMappings = computed(() => props.mappings.slice(0, props.max));
</script>

<style scoped>
.mapping-chips {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
}

.mapping-chips__lens {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.mapping-chips__label {
  width: 56px;
  flex-shrink: 0;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--color-text-muted);
}

.mapping-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 7px;
  border-radius: 8px;
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
  min-width: 0;
}

.mapping-chip__code {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text);
  flex-shrink: 0;
}

.mapping-chip__name {
  font-size: 11px;
  color: var(--color-text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 120px;
}

.mapping-chip__side {
  font-family: var(--font-mono);
  font-size: 10.5px;
  font-weight: 700;
  flex-shrink: 0;
}

.mapping-chip__side--db {
  color: var(--color-primary);
}

.mapping-chip__side--cr {
  color: var(--color-success);
}

.mapping-chips__more {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.mapping-chips__none {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-text-muted);
  opacity: 0.7;
}
</style>
