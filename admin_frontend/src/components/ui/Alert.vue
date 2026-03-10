<template>
  <div :class="['rounded-2xl px-4 py-3 border flex items-start gap-3', variantClass]">
    <div v-if="showIcon" :class="['mt-0.5', iconClass]">
      <slot name="icon">
        <i :class="computedIcon"></i>
      </slot>
    </div>
    <div class="flex-1">
      <div v-if="title || $slots.title" :class="['text-xs font-bold mb-1', titleClass]">
        <slot name="title">{{ title }}</slot>
      </div>
      <div v-if="message || $slots.message" :class="['text-[10px] leading-tight', messageClass]">
        <slot name="message">{{ message }}</slot>
      </div>
      <div v-if="$slots.actions" class="mt-2 flex items-center gap-2">
        <slot name="actions"></slot>
      </div>
    </div>
    <button
      v-if="dismissible"
      @click="$emit('dismiss')"
      :class="['shrink-0 -mr-1 -mt-1 p-1 rounded-lg transition-colors', dismissClass]"
    >
      <i class="bi bi-x-lg text-[10px]"></i>
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  variant: {
    type: String,
    default: 'info',
    validator: (value) => ['info', 'success', 'warning', 'danger', 'error'].includes(value)
  },
  title: {
    type: String,
    default: ''
  },
  message: {
    type: String,
    default: ''
  },
  icon: {
    type: String,
    default: ''
  },
  showIcon: {
    type: Boolean,
    default: true
  },
  dismissible: {
    type: Boolean,
    default: false
  }
});

defineEmits(['dismiss']);

const variantStyles = {
  info: {
    wrapper: 'bg-surface-muted border-border',
    icon: 'text-muted',
    title: 'text-theme',
    message: 'text-muted',
    dismiss: 'text-muted hover:text-theme hover:bg-surface-muted'
  },
  success: {
    wrapper: 'border',
    icon: 'text-success',
    title: 'text-theme',
    message: 'text-muted',
    dismiss: 'text-muted hover:text-theme hover:bg-surface-muted'
  },
  warning: {
    wrapper: 'border',
    icon: 'text-warning',
    title: 'text-theme',
    message: 'text-muted',
    dismiss: 'text-muted hover:text-theme hover:bg-surface-muted'
  },
  danger: {
    wrapper: 'border',
    icon: 'text-danger',
    title: 'text-theme',
    message: 'text-muted',
    dismiss: 'text-muted hover:text-theme hover:bg-surface-muted'
  },
  error: {
    wrapper: 'border',
    icon: 'text-danger',
    title: 'text-theme',
    message: 'text-muted',
    dismiss: 'text-muted hover:text-theme hover:bg-surface-muted'
  }
};

const variantClass = computed(() => {
  const style = variantStyles[props.variant] || variantStyles.info;
  return style.wrapper;
});

const iconClass = computed(() => {
  const style = variantStyles[props.variant] || variantStyles.info;
  return style.icon;
});

const titleClass = computed(() => {
  const style = variantStyles[props.variant] || variantStyles.info;
  return style.title;
});

const messageClass = computed(() => {
  const style = variantStyles[props.variant] || variantStyles.info;
  return style.message;
});

const dismissClass = computed(() => {
  const style = variantStyles[props.variant] || variantStyles.info;
  return style.dismiss;
});

const iconMap = {
  info: 'bi-info-circle-fill',
  success: 'bi-check-circle-fill',
  warning: 'bi-exclamation-triangle-fill',
  danger: 'bi-exclamation-circle-fill',
  error: 'bi-x-circle-fill'
};

const computedIcon = computed(() => {
  return props.icon || iconMap[props.variant] || iconMap.info;
});
</script>

<style scoped>
/* Success variant inline styles */
</style>
