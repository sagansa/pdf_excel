<template>
  <section :class="['section-card', contentClass]">
    <div v-if="title || subtitle || $slots.header || $slots.actions" class="section-card__header">
      <slot name="header">
        <div>
          <h3 v-if="title" class="section-card__title">{{ title }}</h3>
          <p v-if="subtitle" class="section-card__subtitle">{{ subtitle }}</p>
        </div>
      </slot>

      <div v-if="$slots.actions">
        <slot name="actions" />
      </div>
    </div>

    <div :class="bodyClass">
      <slot />
    </div>
  </section>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    default: ''
  },
  subtitle: {
    type: String,
    default: ''
  },
  contentClass: {
    type: String,
    default: ''
  },
  bodyClass: {
    type: String,
    default: ''
  }
});
</script>
