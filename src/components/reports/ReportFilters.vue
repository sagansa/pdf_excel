<template>
  <div class="space-y-4">
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
      <h3 class="text-sm font-semibold text-gray-700 mb-3">Report Filters</h3>
      
      <div class="grid grid-cols-1 md:grid-cols-5 gap-4">
        <!-- Year Selection -->
        <div>
          <label class="block text-xs font-medium text-gray-700 mb-1">
            Year
          </label>
          <select
            :value="modelValue.year"
            @change="handleYearChange($event.target.value)"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option v-for="y in availableYears" :key="y" :value="y">{{ y }}</option>
          </select>
        </div>

        <!-- Start Date -->
        <div>
          <label class="block text-xs font-medium text-gray-700 mb-1">
            Start Date <span class="text-red-500">*</span>
          </label>
          <input
            :value="modelValue.startDate"
            @input="updateFilter('startDate', $event.target.value)"
            type="date"
            required
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>

        <!-- End Date -->
        <div>
          <label class="block text-xs font-medium text-gray-700 mb-1">
            End Date <span class="text-red-500">*</span>
          </label>
          <input
            :value="modelValue.endDate"
            @input="updateFilter('endDate', $event.target.value)"
            type="date"
            required
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>

        <!-- Company Filter -->
        <div>
          <label class="block text-xs font-medium text-gray-700 mb-1">
            Company
          </label>
          <select
            :value="modelValue.companyId"
            @change="updateFilter('companyId', $event.target.value)"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="">All Companies</option>
            <option
              v-for="company in companies"
              :key="company.id"
              :value="company.id"
            >
              {{ company.name }}
            </option>
          </select>
        </div>

        <!-- Generate Button -->
        <div class="flex items-end">
          <button
            @click="$emit('generate')"
            :disabled="!isValid || isLoading"
            class="w-full px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            <span v-if="isLoading" class="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-white"></span>
            <i v-else class="bi bi-bar-chart-fill"></i>
            <span>{{ isLoading ? 'Generating...' : 'Generate' }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  modelValue: {
    type: Object,
    required: true
  },
  companies: {
    type: Array,
    default: () => []
  },
  isLoading: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['update:modelValue', 'generate']);

const availableYears = [2024, 2025, 2026];

const isValid = computed(() => {
  return props.modelValue.startDate && props.modelValue.endDate;
});

const updateFilter = (key, value) => {
  emit('update:modelValue', {
    ...props.modelValue,
    [key]: value || null
  });
};

const handleYearChange = (year) => {
  const startDate = `${year}-01-01`;
  const endDate = `${year}-12-31`;
  
  emit('update:modelValue', {
    ...props.modelValue,
    year: year,
    startDate: startDate,
    endDate: endDate
  });
};
</script>
