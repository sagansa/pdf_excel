<template>
  <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-[10.5px] font-bold bg-primary/10 text-primary border border-primary/20">
    {{ name }}<template v-if="value">: <span class="mono">{{ value }}</span></template>
  </span>
</template>

<script setup>
defineProps({
  name: {
    type: String,
    required: true
  },
  // Preformatted amount; omit for a name-only chip.
  value: {
    type: String,
    default: ''
  }
});
</script>
