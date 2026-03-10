<template>
  <div class="relative inline-flex">
    <div
      v-if="loading"
      class="absolute inset-0 flex items-center justify-center bg-surface/80 rounded-lg z-10"
    >
      <i class="bi bi-arrow-repeat animate-spin text-lg" :class="iconColorClass"></i>
    </div>
    <button
      :type="type"
      :disabled="disabled || loading"
      :class="[
        'inline-flex items-center justify-center gap-2 font-medium rounded-lg transition-all whitespace-nowrap',
        sizeClass,
        variantClass,
        disabledClass,
        className
      ]"
      @click="$emit('click', $event)"
    >
      <i v-if="loading" class="bi bi-arrow-repeat animate-spin"></i>
      <i v-else-if="icon" :class="icon"></i>
      <slot></slot>
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  variant: {
    type: String,
    default: 'default',
    validator: (value) => ['default', 'primary', 'secondary', 'danger', 'ghost', 'outline'].includes(value)
  },
  size: {
    type: String,
    default: 'md',
    validator: (value) => ['sm', 'md', 'lg'].includes(value)
  },
  type: {
    type: String,
    default: 'button'
  },
  disabled: {
    type: Boolean,
    default: false
  },
  loading: {
    type: Boolean,
    default: false
  },
  icon: {
    type: String,
    default: ''
  },
  className: {
    type: String,
    default: ''
  }
});

defineEmits(['click']);

const sizeClass = computed(() => {
  const sizes = {
    sm: 'px-2.5 py-1.5 text-[10px]',
    md: 'px-4 py-2 text-xs',
    lg: 'px-6 py-2.5 text-sm'
  };
  return sizes[props.size] || sizes.md;
});

const variantClass = computed(() => {
  const variants = {
    default: 'btn-primary',
    primary: 'btn-primary',
    secondary: 'btn-secondary',
    danger: 'btn-danger',
    ghost: 'btn-ghost',
    outline: 'btn-outline'
  };
  return variants[props.variant] || variants.default;
});

const disabledClass = computed(() => {
  if (props.disabled || props.loading) {
    return 'opacity-50 cursor-not-allowed';
  }
  return '';
});

const iconColorClass = computed(() => {
  const colors = {
    primary: 'text-primary',
    secondary: 'text-muted',
    danger: 'text-danger',
    default: 'text-primary'
  };
  return colors[props.variant] || colors.default;
});
</script>
