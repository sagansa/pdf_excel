<template>
  <div class="relative">
    <select
      v-bind="$attrs"
      :value="modelValue"
      :disabled="disabled"
      :class="selectClasses"
      @change="$emit('update:modelValue', $event.target.value)"
    >
      <option
        v-if="placeholder"
        value=""
      >
        {{ placeholder }}
      </option>
      <option
        v-for="option in options"
        :key="getOptionValue(option)"
        :value="getOptionValue(option)"
      >
        {{ getOptionLabel(option) }}
      </option>
    </select>

    <span class="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3 text-muted">
      <i class="bi bi-chevron-down text-[10px]"></i>
    </span>
  </div>
</template>

<script setup>
import { computed } from 'vue';

defineOptions({
  inheritAttrs: false
});

const props = defineProps({
  modelValue: {
    type: [String, Number],
    default: ''
  },
  options: {
    type: Array,
    default: () => []
  },
  placeholder: {
    type: String,
    default: ''
  },
  labelKey: {
    type: String,
    default: 'label'
  },
  valueKey: {
    type: String,
    default: 'value'
  },
  disabled: {
    type: Boolean,
    default: false
  },
  size: {
    type: String,
    default: 'md'
  }
});

defineEmits(['update:modelValue']);

const getOptionLabel = (option) => {
  if (typeof option === 'string' || typeof option === 'number') return option;
  return option?.[props.labelKey] ?? option?.label ?? option?.name ?? '';
};

const getOptionValue = (option) => {
  if (typeof option === 'string' || typeof option === 'number') return option;
  return option?.[props.valueKey] ?? option?.value ?? option?.id ?? '';
};

const selectClasses = computed(() => {
  const sizeClass = props.size === 'sm'
    ? 'py-1.5 text-xs'
    : 'py-2 text-sm';

  return [
    'input-base appearance-none pr-9',
    sizeClass
  ];
});
</script>
