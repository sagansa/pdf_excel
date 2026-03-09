<template>
  <section :class="['surface-card overflow-hidden flex flex-col', shellClass]">
    <div v-if="$slots.toolbar" class="table-shell__toolbar">
      <slot name="toolbar" />
    </div>

    <div :class="['table-shell__scroller', scrollerClass]">
      <slot />
    </div>

    <div v-if="$slots.footer" :class="['table-shell__footer', footerClass]">
      <slot name="footer" />
    </div>
  </section>
</template>

<script setup>
defineProps({
  shellClass: {
    type: String,
    default: ''
  },
  scrollerClass: {
    type: String,
    default: ''
  },
  footerClass: {
    type: String,
    default: ''
  }
});
</script>
