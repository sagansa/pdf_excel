<template>
  <div class="trait-chips">
    <span
      v-for="chip in chips"
      :key="chip.key"
      class="trait-chip"
      :class="`trait-chip--${chip.tone}`"
    >{{ chip.label }}</span>
    <span v-if="fiscalLabel" class="trait-chip trait-chip--fiscal">{{ fiscalLabel }}</span>
    <span v-else-if="showFiscalInherit" class="trait-chip trait-chip--inherit">Inherit COA</span>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  mark: {
    type: Object,
    required: true
  },
  showFiscalInherit: {
    type: Boolean,
    default: false
  }
});

const TRAITS = [
  { key: 'is_coretax', label: 'Coretax', tone: 'coretax' },
  { key: 'is_salary_component', label: 'Gaji', tone: 'gaji' },
  { key: 'is_rental', label: 'Sewa', tone: 'sewa' },
  { key: 'is_asset', label: 'Aset', tone: 'aset' },
  { key: 'is_service', label: 'Jasa', tone: 'jasa' }
];

const FISCAL_LABELS = {
  DEDUCTIBLE: 'Deductible',
  NON_DEDUCTIBLE_PERMANENT: 'Non-Deductible',
  NON_DEDUCTIBLE_TEMPORARY: 'Non-Deductible (Temp)'
};

const chips = computed(() => TRAITS.filter((t) => Boolean(props.mark[t.key])));

const fiscalLabel = computed(() => {
  const value = props.mark?.fiscal_category;
  return value ? (FISCAL_LABELS[value] || value) : '';
});
</script>

<style scoped>
.trait-chips {
  --chip-sewa: #2563eb;
  --chip-aset: #7c3aed;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
}

.trait-chip {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.02em;
  line-height: 1.45;
  white-space: nowrap;
}

.trait-chip--coretax {
  background: color-mix(in srgb, var(--color-primary) 13%, transparent);
  color: var(--color-primary);
}

.trait-chip--gaji {
  background: color-mix(in srgb, var(--color-success) 13%, transparent);
  color: var(--color-success);
}

.trait-chip--jasa {
  background: color-mix(in srgb, var(--color-warning) 15%, transparent);
  color: var(--color-warning);
}

.trait-chip--sewa {
  background: color-mix(in srgb, var(--chip-sewa) 11%, transparent);
  color: var(--chip-sewa);
}

.trait-chip--aset {
  background: color-mix(in srgb, var(--chip-aset) 11%, transparent);
  color: var(--chip-aset);
}

.trait-chip--fiscal {
  background: color-mix(in srgb, var(--color-success) 10%, transparent);
  border: 1px solid color-mix(in srgb, var(--color-success) 26%, transparent);
  color: var(--color-success);
  text-transform: uppercase;
  font-size: 10.5px;
  letter-spacing: 0.06em;
}

.trait-chip--inherit {
  background: transparent;
  border: 1px dashed var(--color-border-strong);
  color: var(--color-text-muted);
  font-weight: 500;
  font-style: italic;
}

html.dark .trait-chips {
  --chip-sewa: #93c5fd;
  --chip-aset: #c4b5fd;
}
</style>
