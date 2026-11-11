<template>
  <button
    type="button"
    role="switch"
    :aria-checked="modelValue ? 'true' : 'false'"
    :disabled="loading"
    class="flag-switch"
    :class="{ 'flag-switch--on': modelValue }"
    @click="toggle"
  >
    <span class="flag-switch__track" aria-hidden="true">
      <i v-if="loading" class="bi bi-arrow-repeat flag-switch__spinner"></i>
      <span v-else class="flag-switch__knob"></span>
    </span>
    <span class="flag-switch__label">{{ label }}</span>
  </button>
</template>

<script setup>
const props = defineProps({
  label: {
    type: String,
    required: true
  },
  modelValue: {
    type: Boolean,
    default: false
  },
  loading: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['update:modelValue']);

const toggle = () => {
  if (!props.loading) {
    emit('update:modelValue', !props.modelValue);
  }
};
</script>

<style scoped>
.flag-switch {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: none;
  background: transparent;
  padding: 2px 0;
  cursor: pointer;
  font: inherit;
}

.flag-switch:disabled {
  cursor: wait;
  opacity: 0.7;
}

.flag-switch:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 3px;
  border-radius: 999px;
}

.flag-switch__track {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: flex-start;
  width: 34px;
  height: 19px;
  border-radius: 999px;
  background: var(--color-border);
  transition: background-color 180ms ease;
  flex-shrink: 0;
}

.flag-switch--on .flag-switch__track {
  background: var(--color-primary);
  justify-content: flex-end;
}

.flag-switch__knob {
  width: 13px;
  height: 13px;
  margin: 3px;
  border-radius: 999px;
  background: #ffffff;
  box-shadow: 0 1px 2px rgba(31, 41, 55, 0.35);
}

.flag-switch__spinner {
  width: 100%;
  text-align: center;
  font-size: 11px;
  color: #ffffff;
  animation: flag-switch-spin 900ms linear infinite;
}

@keyframes flag-switch-spin {
  to {
    transform: rotate(360deg);
  }
}

.flag-switch__label {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-muted);
  transition: color 180ms ease;
}

.flag-switch--on .flag-switch__label {
  color: var(--color-text);
}

@media (prefers-reduced-motion: reduce) {
  .flag-switch__track,
  .flag-switch__label {
    transition: none;
  }
}
</style>
