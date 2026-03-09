<template>
  <div class="toast-viewport" aria-live="polite" aria-atomic="true">
    <TransitionGroup name="toast">
      <div
        v-for="notification in notifications"
        :key="notification.id"
        class="toast-card"
        :class="`toast-card--${notification.type}`"
      >
        <div class="toast-card__icon">
          <i :class="iconClass(notification.type)"></i>
        </div>

        <div class="toast-card__body">
          <p class="toast-card__title">{{ notification.title }}</p>
          <p v-if="notification.message" class="toast-card__message">
            {{ notification.message }}
          </p>
        </div>

        <button
          type="button"
          class="toast-card__close"
          aria-label="Dismiss notification"
          @click="remove(notification.id)"
        >
          <i class="bi bi-x-lg"></i>
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup>
import { useNotifications } from '../../composables/useNotifications';

const { notifications, remove } = useNotifications();

const iconClass = (type) => {
  if (type === 'success') return 'bi bi-check-circle-fill';
  if (type === 'error') return 'bi bi-exclamation-octagon-fill';
  return 'bi bi-info-circle-fill';
};
</script>

<style scoped>
.toast-viewport {
  @apply pointer-events-none fixed right-4 top-4 z-[120] flex w-[min(360px,calc(100vw-2rem))] flex-col gap-3;
}

.toast-enter-active,
.toast-leave-active {
  transition: all 180ms ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.98);
}

.toast-card {
  @apply pointer-events-auto flex items-start gap-3 rounded-2xl px-4 py-3 shadow-lg backdrop-blur;
  background: color-mix(in srgb, var(--color-panel) 94%, transparent 6%);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-card);
}

.toast-card--success {
  border-color: color-mix(in srgb, var(--color-success) 36%, var(--color-border));
}

.toast-card--error {
  border-color: color-mix(in srgb, var(--color-danger) 36%, var(--color-border));
}

.toast-card__icon {
  @apply mt-0.5 text-base;
  color: var(--color-primary);
}

.toast-card--success .toast-card__icon {
  color: var(--color-success);
}

.toast-card--error .toast-card__icon {
  color: var(--color-danger);
}

.toast-card__body {
  @apply min-w-0 flex-1;
}

.toast-card__title {
  @apply text-sm font-semibold;
  color: var(--color-text);
}

.toast-card__message {
  @apply mt-1 text-xs leading-5;
  color: var(--color-text-muted);
}

.toast-card__close {
  @apply inline-flex h-7 w-7 items-center justify-center rounded-full transition-colors;
  color: var(--color-text-muted);
}

.toast-card__close:hover {
  background: color-mix(in srgb, var(--color-surface-raised) 80%, transparent 20%);
  color: var(--color-text);
}
</style>
