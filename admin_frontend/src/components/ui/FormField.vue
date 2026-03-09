<template>
  <div :class="['field-stack', wrapperClass]">
    <label v-if="label" :class="['label-base', labelClass]">
      {{ label }}
    </label>

    <slot />

    <p v-if="hint" :class="['field-hint', hintClass]">
      {{ hint }}
    </p>
  </div>
</template>

<script setup>
defineProps({
  label: {
    type: String,
    default: ''
  },
  hint: {
    type: String,
    default: ''
  },
  wrapperClass: {
    type: String,
    default: ''
  },
  labelClass: {
    type: String,
    default: ''
  },
  hintClass: {
    type: String,
    default: ''
  }
});
</script>
