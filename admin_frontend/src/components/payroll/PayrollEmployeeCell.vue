<template>
  <td
    :class="[
      'px-4 py-3',
      sticky ? 'sticky left-0 z-10' : '',
      bg === 'muted' ? 'bg-surface-muted' : 'bg-surface'
    ]"
    :style="sticky ? { minWidth } : null"
  >
    <button
      v-if="expandable"
      type="button"
      class="w-full flex items-center justify-between gap-2 text-left"
      @click="$emit('toggle')"
    >
      <div class="min-w-0">
        <div class="font-semibold text-theme truncate">{{ displayName }}</div>
        <div class="text-[11px] text-muted truncate mono">{{ employeeId || '-' }}</div>
      </div>
      <i
        :class="expanded ? 'bi bi-chevron-up' : 'bi bi-chevron-down'"
        class="text-xs text-muted shrink-0"
        aria-hidden="true"
      ></i>
    </button>
    <div v-else class="min-w-0">
      <div class="font-semibold text-theme truncate">{{ displayName }}</div>
      <div class="text-[11px] text-muted truncate mono">{{ employeeId || '-' }}</div>
    </div>
  </td>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  name: {
    type: String,
    default: ''
  },
  employeeId: {
    type: [String, Number],
    default: ''
  },
  expandable: {
    type: Boolean,
    default: false
  },
  expanded: {
    type: Boolean,
    default: false
  },
  // Sticky cells need an opaque background or scrolled content bleeds through.
  sticky: {
    type: Boolean,
    default: false
  },
  bg: {
    type: String,
    default: 'surface'
  },
  minWidth: {
    type: String,
    default: '260px'
  }
});

defineEmits(['toggle']);

const displayName = computed(() => props.name || 'Unassigned');
</script>
