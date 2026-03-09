<template>
  <section class="page-header">
    <div>
      <slot name="eyebrow">
        <span v-if="eyebrow" class="page-header__eyebrow">
          <i v-if="icon" :class="icon"></i>
          {{ eyebrow }}
        </span>
      </slot>

      <h1 class="page-header__title">{{ title }}</h1>
      <p v-if="subtitle" class="page-header__subtitle">{{ subtitle }}</p>
    </div>

    <div v-if="$slots.actions || badges.length" class="flex flex-wrap gap-2">
      <slot name="actions">
        <span v-for="badge in badges" :key="badge.label" class="stat-pill">
          <i v-if="badge.icon" :class="badge.icon"></i>
          {{ badge.label }}
        </span>
      </slot>
    </div>
  </section>
</template>

<script setup>
defineProps({
  eyebrow: {
    type: String,
    default: ''
  },
  icon: {
    type: String,
    default: ''
  },
  title: {
    type: String,
    required: true
  },
  subtitle: {
    type: String,
    default: ''
  },
  badges: {
    type: Array,
    default: () => []
  }
});
</script>
