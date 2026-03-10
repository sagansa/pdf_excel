<template>
  <div :class="['rounded-2xl px-4 py-3 border', wrapperClass]">
    <div class="flex items-center justify-between">
      <div>
        <div :class="['text-[10px] uppercase font-semibold', labelClass]">
          {{ label }}
        </div>
        <div :class="['text-lg font-bold font-mono mt-1', valueClass]">
          <slot name="value">{{ value }}</slot>
        </div>
      </div>
      <div v-if="icon || $slots.icon" :class="['p-2 rounded-lg', iconWrapperClass]">
        <slot name="icon">
          <i :class="[icon, iconClass]"></i>
        </slot>
      </div>
    </div>
    <div v-if="subtext || $slots.subtext" :class="['text-[10px] mt-2', subtextClass]">
      <slot name="subtext">{{ subtext }}</slot>
    </div>
  </div>
</template>

<script setup>
defineProps({
  label: {
    type: String,
    default: ''
  },
  value: {
    type: [String, Number],
    default: ''
  },
  subtext: {
    type: String,
    default: ''
  },
  icon: {
    type: String,
    default: ''
  },
  variant: {
    type: String,
    default: 'default',
    validator: (value) => ['default', 'primary', 'success', 'danger', 'warning'].includes(value)
  },
  wrapperClass: {
    type: String,
    default: ''
  },
  labelClass: {
    type: String,
    default: ''
  },
  valueClass: {
    type: String,
    default: ''
  },
  iconWrapperClass: {
    type: String,
    default: ''
  },
  iconClass: {
    type: String,
    default: ''
  },
  subtextClass: {
    type: String,
    default: ''
  }
});
</script>

<style scoped>
/* Default variant uses CSS variables */
</style>
