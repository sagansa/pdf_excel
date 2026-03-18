<template>
  <span 
    class="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border shadow-sm transition-all duration-200 inline-flex items-center justify-center min-w-[60px]"
    :class="variantClasses"
  >
    <slot>{{ label }}</slot>
  </span>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  label: String,
  variant: {
    type: String,
    default: 'primary',
    validator: (value) => ['primary', 'success', 'danger', 'warning', 'info', 'indigo', 'muted'].includes(value)
  }
});

const variantClasses = computed(() => {
  const base = {
    primary: 'bg-primary/10 text-primary border-primary/20 hover:bg-primary/15',
    success: 'bg-success/10 text-success border-success/20 hover:bg-success/15',
    danger: 'bg-danger/10 text-danger border-danger/20 hover:bg-danger/15',
    warning: 'bg-warning/10 text-warning border-warning/20 hover:bg-warning/15',
    info: 'bg-info/10 text-info border-info/20 hover:bg-info/15',
    indigo: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20 hover:bg-indigo-500/15',
    muted: 'bg-surface-muted text-muted border-border hover:bg-border/20'
  };
  return base[props.variant] || base.primary;
});
</script>
