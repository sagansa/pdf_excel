<template>
  <div class="relative">
    <div
      :class="[
        'inline-flex items-center gap-1 rounded-lg p-1',
        variantClass
      ]"
    >
      <button
        v-for="option in options"
        :key="getOptionValue(option)"
        @click="selectOption(option)"
        :class="[
          'px-3 py-1.5 text-xs font-medium rounded-md transition-all',
          isSelected(option) ? 'bg-white shadow-sm font-semibold' : 'text-muted hover:text-theme'
        ]"
        :disabled="option.disabled"
      >
        <slot name="option" :option="option">
          {{ getOptionLabel(option) }}
        </slot>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  modelValue: {
    type: [String, Number],
    default: ''
  },
  options: {
    type: Array,
    default: () => []
  },
  labelKey: {
    type: String,
    default: 'label'
  },
  valueKey: {
    type: String,
    default: 'value'
  },
  variant: {
    type: String,
    default: 'default',
    validator: (value) => ['default', 'primary'].includes(value)
  }
});

const emit = defineEmits(['update:modelValue', 'change']);

const variantClass = computed(() => {
  if (props.variant === 'primary') {
    return 'bg-primary/10';
  }
  return 'bg-surface-muted';
});

const getOptionLabel = (option) => {
  if (typeof option === 'string' || typeof option === 'number') return option;
  return option?.[props.labelKey] ?? option?.label ?? option?.name ?? '';
};

const getOptionValue = (option) => {
  if (typeof option === 'string' || typeof option === 'number') return option;
  return option?.[props.valueKey] ?? option?.value ?? option?.id ?? '';
};

const isSelected = (option) => {
  return props.modelValue === getOptionValue(option);
};

const selectOption = (option) => {
  const value = getOptionValue(option);
  emit('update:modelValue', value);
  emit('change', value, option);
};
</script>
