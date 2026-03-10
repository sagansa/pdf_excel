<template>
  <div class="space-y-1.5">
    <!-- Label -->
    <div v-if="label || $slots.label" class="flex justify-between text-[10px]">
      <slot name="label">
        <span class="font-bold text-muted uppercase tracking-widest">{{ label }}</span>
      </slot>
      <slot name="label-extra">
        <span v-if="showValue" :class="['font-bold font-mono', valueColorClass]">
          {{ currentValue }} / {{ maxValue }}
        </span>
      </slot>
    </div>

    <!-- Progress Bar -->
    <div class="relative h-2 w-full bg-surface-muted rounded-full overflow-hidden shadow-inner">
      <!-- Success/Primary segment -->
      <div
        class="h-full transition-all duration-300 ease-in-out"
        :class="isOver ? 'bg-danger' : barColorClass"
        :style="{ width: `${Math.min(percentage, 100)}%` }"
      ></div>
      <!-- Over segment -->
      <div
        v-if="isOver"
        class="h-full bg-danger"
        :style="{ width: `${Math.min(percentage - 100, 100)}%` }"
      ></div>
    </div>

    <!-- Footer Info -->
    <div v-if="showFooter" class="flex justify-between items-center text-[10px]">
      <span :class="[isOver ? 'text-danger font-bold' : 'text-primary font-bold']">
        {{ percentage.toFixed(0) }}%
      </span>
      <slot name="footer-extra">
        <span v-if="hasRemaining" :class="isOver ? 'text-danger' : 'text-warning'">
          {{ isOver ? 'Over:' : 'Rem:' }} {{ formatValue(remaining) }}
        </span>
        <span v-else class="text-success font-bold flex items-center gap-1">
          <i class="bi bi-check-circle-fill text-[9px]"></i> OK
        </span>
      </slot>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  label: {
    type: String,
    default: ''
  },
  currentValue: {
    type: [String, Number],
    default: 0
  },
  maxValue: {
    type: [String, Number],
    default: 100
  },
  showValue: {
    type: Boolean,
    default: true
  },
  showFooter: {
    type: Boolean,
    default: true
  },
  barColor: {
    type: String,
    default: 'primary',
    validator: (value) => ['primary', 'success', 'warning', 'danger'].includes(value)
  },
  formatFn: {
    type: Function,
    default: null
  }
});

const numericCurrent = computed(() => {
  const val = typeof props.currentValue === 'string' 
    ? parseFloat(props.currentValue) 
    : props.currentValue;
  return isNaN(val) ? 0 : val;
});

const numericMax = computed(() => {
  const val = typeof props.maxValue === 'string' 
    ? parseFloat(props.maxValue) 
    : props.maxValue;
  return isNaN(val) ? 100 : val;
});

const percentage = computed(() => {
  if (numericMax.value === 0) return 0;
  return (numericCurrent.value / numericMax.value) * 100;
});

const isOver = computed(() => percentage.value > 100);

const remaining = computed(() => numericMax.value - numericCurrent.value);

const hasRemaining = computed(() => Math.abs(remaining.value) > 0.01);

const barColorClass = computed(() => {
  const colorMap = {
    primary: 'bg-primary',
    success: 'bg-success',
    warning: 'bg-warning',
    danger: 'bg-danger'
  };
  return colorMap[props.barColor] || 'bg-primary';
});

const valueColorClass = computed(() => {
  return isOver.value ? 'text-danger' : 'text-primary';
});

const formatValue = (val) => {
  if (props.formatFn) return props.formatFn(val);
  return Math.abs(val).toLocaleString('id-ID', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2
  });
};
</script>
