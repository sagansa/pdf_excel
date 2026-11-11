<template>
  <div class="mapping-group">
    <div class="mapping-group__head">
      <span class="mapping-group__label">{{ label }}</span>
      <span class="mapping-group__count">{{ mappings.length }}</span>
    </div>

    <ul v-if="mappings.length" class="mapping-group__list">
      <li v-for="mapping in mappings" :key="`${mapping.coa_id || mapping.code}-${mapping.type}`" class="mapping-row">
        <span class="mapping-row__code">{{ mapping.code }}</span>
        <span class="mapping-row__name" :title="mapping.name">{{ mapping.name }}</span>
        <span class="mapping-row__side" :class="mapping.type === 'DEBIT' ? 'mapping-row__side--db' : 'mapping-row__side--cr'">
          {{ mapping.type === 'DEBIT' ? 'DB' : 'CR' }}
        </span>
      </li>
    </ul>

    <div v-else class="mapping-group__empty">
      <i class="bi bi-exclamation-circle"></i>
      <span>Belum di-mapping</span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  label: {
    type: String,
    required: true
  },
  mappings: {
    type: Array,
    default: () => []
  }
});
</script>

<style scoped>
.mapping-group {
  min-width: 0;
}

.mapping-group__head {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 7px;
}

.mapping-group__label {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--color-text-muted);
}

.mapping-group__count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 999px;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
  color: var(--color-text-muted);
}

.mapping-group__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.mapping-row {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 5px 8px;
  border-radius: 10px;
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
}

.mapping-row__code {
  font-family: var(--font-mono);
  font-size: 11.5px;
  font-weight: 600;
  color: var(--color-text);
  flex-shrink: 0;
}

.mapping-row__name {
  font-size: 11.5px;
  color: var(--color-text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
}

.mapping-row__side {
  margin-left: auto;
  flex-shrink: 0;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 6px;
}

.mapping-row__side--db {
  background: color-mix(in srgb, var(--color-primary) 13%, transparent);
  color: var(--color-primary);
}

.mapping-row__side--cr {
  background: color-mix(in srgb, var(--color-success) 13%, transparent);
  color: var(--color-success);
}

.mapping-group__empty {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 9px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
  background: color-mix(in srgb, var(--color-warning) 12%, transparent);
  color: var(--color-warning);
}

.mapping-group__empty i {
  font-size: 12px;
}
</style>
