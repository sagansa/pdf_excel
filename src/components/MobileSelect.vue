<template>
  <div class="grid grid-cols-1">
    <select 
      :aria-label="ariaLabel" 
      class="col-start-1 row-start-1 w-full appearance-none rounded-md bg-gray-800 py-2 pr-8 pl-3 text-base text-white outline-1 -outline-offset-1 outline-gray-600 focus:outline-2 focus:-outline-offset-2 focus:outline-indigo-400"
      :value="modelValue"
      @change="$emit('update:modelValue', $event.target.value)"
    >
      <option 
        v-for="option in options" 
        :key="option.value" 
        :value="option.value"
        class="bg-gray-800 text-white"
      >
        {{ option.label }}
      </option>
    </select>
    <svg 
      class="pointer-events-none col-start-1 row-start-1 mr-2 size-5 self-center justify-self-end fill-gray-300" 
      viewBox="0 0 20 20" 
      fill="currentColor" 
      aria-hidden="true"
    >
      <path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clip-rule="evenodd" />
    </svg>
  </div>
</template>

<script setup>
defineProps({
  /**
   * Array of option objects with label and value
   * Example: [{ label: 'BCA', value: 'bca' }]
   */
  options: {
    type: Array,
    required: true,
    validator: (options) => options.every(option => option.label && option.value !== undefined)
  },
  
  /**
   * Current selected option value (v-model)
   */
  modelValue: {
    type: [String, Number],
    required: true
  },

  /**
   * Aria label for the select element
   */
  ariaLabel: {
    type: String,
    default: 'Select an option'
  }
})

defineEmits(['update:modelValue'])
</script>