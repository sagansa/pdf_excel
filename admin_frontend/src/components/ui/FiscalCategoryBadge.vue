<template>
  <BaseBadge :variant="config.variant" :label="config.label" />
</template>

<script setup>
import { computed } from 'vue';
import BaseBadge from './BaseBadge.vue';

const props = defineProps({
  category: {
    type: String,
    default: 'DEDUCTIBLE'
  }
});

const config = computed(() => {
  switch (props.category) {
    case 'NON_DEDUCTIBLE_PERMANENT':
      return {
        label: 'Fiscal: Non-Deductible (P)',
        variant: 'danger'
      };
    case 'NON_DEDUCTIBLE_TEMPORARY':
      return {
        label: 'Fiscal: Non-Deductible (T)',
        variant: 'warning'
      };
    case 'NON_TAXABLE_INCOME':
      return {
        label: 'Fiscal: Non-Taxable Inc.',
        variant: 'primary'
      };
    default:
      return {
        label: 'Fiscal: Deductible',
        variant: 'success'
      };
  }
});
</script>
