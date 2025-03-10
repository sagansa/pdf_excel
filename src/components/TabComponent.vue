<template>
  <div>
    <!-- Mobile view with dropdown select -->
    <div class="sm:hidden">
      <MobileSelect
        :model-value="modelValue"
        @update:modelValue="$emit('update:modelValue', $event)"
        :options="tabs.map(tab => ({ label: tab.name, value: tab.value }))"
        aria-label="Select a tab"
      />
    </div>
    
    <!-- Desktop view with horizontal tabs -->
    <div class="hidden sm:block">
      <nav class="flex space-x-4" aria-label="Tabs">
        <BaseButton 
          v-for="tab in tabs" 
          :key="tab.name"
          @click="$emit('update:modelValue', tab.value)"
          :active="tab.value === modelValue"
          :aria-current="tab.value === modelValue ? 'page' : undefined"
        >
          <i v-if="tab.icon" :class="tab.icon + ' me-2'"></i>
          {{ tab.name }}
        </BaseButton>
      </nav>
    </div>
  </div>
</template>

<script setup>
import BaseButton from './BaseButton.vue'
import MobileSelect from './MobileSelect.vue'
defineProps({
  /**
   * Array of tab objects with name, value, and optional icon
   * Example: [{ name: 'BCA', value: 'bca', icon: 'bi bi-bank' }]
   */
  tabs: {
    type: Array,
    required: true,
    validator: (tabs) => tabs.every(tab => tab.name && tab.value !== undefined)
  },
  
  /**
   * Current selected tab value (v-model)
   */
  modelValue: {
    type: [String, Number],
    required: true
  }
})

const emit = defineEmits(['update:modelValue'])

</script>

<style scoped>
/* The component uses Tailwind classes by default */
</style>