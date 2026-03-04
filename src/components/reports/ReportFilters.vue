<template>
  <div class="space-y-4">
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
      <h3 class="text-sm font-semibold text-gray-700 mb-3">Report Filters</h3>
      
      <div class="grid grid-cols-1 md:grid-cols-6 gap-4">
        <!-- Report Type Selection -->
        <div>
          <label class="block text-xs font-medium text-gray-700 mb-1">
            Report Type
          </label>
          <select
            :value="modelValue.reportType || 'real'"
            @change="handleReportTypeChange($event.target.value)"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="real">Real</option>
            <option value="coretax">Coretax</option>
          </select>
        </div>

        <!-- Year Selection -->
        <div>
          <label class="block text-xs font-medium text-gray-700 mb-1">
            Year
          </label>
          <select
            :value="modelValue.year || new Date().getFullYear()"
            @change="handleYearChange($event.target.value)"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option v-for="y in availableYears" :key="y" :value="y">{{ y }}</option>
          </select>
        </div>

        <!-- Start Date -->
        <div>
          <label class="block text-xs font-medium text-gray-700 mb-1">
            Period: Start <span class="text-red-500">*</span>
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
            Period: End <span class="text-red-500">*</span>
          </label>
          <input
            :value="modelValue.endDate"
            @input="updateFilter('endDate', $event.target.value)"
            type="date"
            required
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>

        <!-- As Of Date (for Balance Sheet) -->
        <div>
          <label class="block text-xs font-medium text-gray-700 mb-1">
            As of Date <span class="text-red-500">*</span>
          </label>
          <input
            :value="modelValue.asOfDate"
            @input="updateFilter('asOfDate', $event.target.value)"
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
  availableYears: {
    type: Array,
    default: () => []
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

const emit = defineEmits(['update:modelValue']);

const availableYears = computed(() => {
  const fromTransactions = (props.availableYears || [])
    .map((year) => parseInt(year, 10))
    .filter((year) => !Number.isNaN(year))
    .sort((a, b) => b - a);

  if (fromTransactions.length > 0) {
    return fromTransactions;
  }

  return [new Date().getFullYear()];
});

const updateFilter = (key, value) => {
  emit('update:modelValue', {
    ...props.modelValue,
    [key]: value || null
  });
};

const handleReportTypeChange = (value) => {
  const reportType = value || 'real';
  emit('update:modelValue', {
    ...props.modelValue,
    reportType
  });
};

const handleYearChange = (year) => {
  const selectedYear = String(year);
  const startDate = `${selectedYear}-01-01`;
  const endDate = `${selectedYear}-12-31`;
  const asOfDate = `${selectedYear}-12-31`;
  
  const newFilters = {
    ...props.modelValue,
    year: selectedYear,
    startDate: startDate,
    endDate: endDate,
    asOfDate: asOfDate
  };

  emit('update:modelValue', newFilters);
};
</script>
