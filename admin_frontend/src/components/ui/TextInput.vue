<template>
  <div class="ui-input-shell">
    <span v-if="leadingIcon || $slots.leading" class="ui-input-shell__icon">
      <slot name="leading">
        <i :class="leadingIcon"></i>
      </slot>
    </span>

    <input
      v-bind="$attrs"
      :type="type"
      :value="modelValue"
      :placeholder="placeholder"
      :disabled="disabled"
      :class="inputClasses"
      @input="$emit('update:modelValue', $event.target.value)"
    >

    <div v-if="$slots.trailing || (clearable && modelValue)" class="ui-input-shell__action">
      <slot name="trailing">
        <button
          v-if="clearable && modelValue"
          type="button"
          class="ui-clear-button"
          @click="$emit('update:modelValue', '')"
        >
          <i class="bi bi-x text-xs"></i>
        </button>
      </slot>
    </div>
  </div>
</template>

<script setup>
import { computed, useSlots } from 'vue';

const slots = useSlots();

defineOptions({
  inheritAttrs: false
});

const props = defineProps({
  modelValue: {
    type: [String, Number],
    default: ''
  },
  type: {
    type: String,
    default: 'text'
  },
  placeholder: {
    type: String,
    default: ''
  },
  leadingIcon: {
    type: String,
    default: ''
  },
  disabled: {
    type: Boolean,
    default: false
  },
  clearable: {
    type: Boolean,
    default: false
  },
  size: {
    type: String,
    default: 'md'
  }
});

defineEmits(['update:modelValue']);

const inputClasses = computed(() => {
  const sizeClass = props.size === 'sm'
    ? 'py-1.5 text-xs'
    : 'py-2 text-sm';

  const hasLeading = props.leadingIcon || !!slots.leading;

  return [
    'w-full border-none bg-transparent pr-3 outline-none focus:ring-0',
    hasLeading ? 'pl-11' : 'pl-3',
    props.clearable ? 'pr-10' : '',
    sizeClass
  ];
});
</script>
