<template>
  <div class="surface-card p-4">
    <div class="flex items-center gap-3">
      <div :class="['stat-card__icon', `stat-card__icon--${tone}`]">
        <i :class="icon"></i>
      </div>
      <div class="min-w-0">
        <p class="text-xs text-muted">{{ label }}</p>
        <p class="text-xl font-bold text-theme">{{ value }}</p>
        <p v-if="hint" class="mt-1 text-[11px] text-muted">{{ hint }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  icon: {
    type: String,
    required: true
  },
  label: {
    type: String,
    required: true
  },
  value: {
    type: [String, Number],
    required: true
  },
  hint: {
    type: String,
    default: ''
  },
  tone: {
    type: String,
    default: 'primary'
  }
});
</script>

<style scoped>
.stat-card__icon {
  @apply flex h-10 w-10 items-center justify-center rounded-lg text-lg;
}

.stat-card__icon--primary {
  background: rgba(15, 118, 110, 0.12);
  color: var(--color-primary);
}

.stat-card__icon--success {
  background: rgba(22, 101, 52, 0.12);
  color: var(--color-success);
}

.stat-card__icon--danger {
  background: rgba(185, 28, 28, 0.12);
  color: var(--color-danger);
}

.stat-card__icon--info {
  background: rgba(37, 99, 235, 0.12);
  color: #2563eb;
}

.stat-card__icon--accent {
  background: rgba(147, 51, 234, 0.12);
  color: #7c3aed;
}

.stat-card__icon--warning {
  background: rgba(180, 83, 9, 0.12);
  color: var(--color-warning);
}
</style>
