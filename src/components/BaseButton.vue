<template>
  <button
    :class="[
      'transition-colors duration-200 rounded-md py-2 flex items-center justify-center',
      active
        ? 'text-black bg-white border border-black hover:bg-blue-700 hover:text-white hover:border-blue-700'
        : 'text-white bg-black hover:bg-blue-700 hover:border-blue-700',
      disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
    ]"
    :disabled="disabled"
    @click="$emit('click', $event)"
  >
    <slot></slot>
  </button>
</template>

<script setup>
defineProps({
  /**
   * Controls the active state of the button
   */
  active: {
    type: Boolean,
    default: false
  },
  /**
   * Controls the disabled state of the button
   */
  disabled: {
    type: Boolean,
    default: false
  }
})

defineEmits(['click'])
</script>