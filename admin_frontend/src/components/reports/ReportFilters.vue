<template>
  <SectionCard body-class="p-4">
    <div class="mb-3 flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
      <div>
        <h3 class="text-sm font-semibold text-theme">Report Filters</h3>
        <p class="mt-1 text-xs text-muted">Set company, period, and report mode before generating reports.</p>
      </div>
      <span class="stat-pill !px-2.5 !py-1 text-[10px]">Auto refresh enabled</span>
    </div>

    <div class="grid grid-cols-1 gap-4 md:grid-cols-6">
      <FormField label="Report Type" label-class="!text-xs">
        <SelectInput
          :model-value="modelValue.reportType || 'real'"
          :options="reportTypeOptions"
          size="md"
          @update:model-value="handleReportTypeChange"
        />
      </FormField>

      <FormField label="Year" label-class="!text-xs">
        <SelectInput
          :model-value="modelValue.year || currentYear"
          :options="yearOptions"
          size="md"
          @update:model-value="handleYearChange"
        />
      </FormField>

      <FormField label="Period: Start" label-class="!text-xs">
        <TextInput
          :model-value="modelValue.startDate"
          type="date"
          size="md"
          @update:model-value="updateFilter('startDate', $event)"
        />
      </FormField>

      <FormField label="Period: End" label-class="!text-xs">
        <TextInput
          :model-value="modelValue.endDate"
          type="date"
          size="md"
          @update:model-value="updateFilter('endDate', $event)"
        />
      </FormField>

      <FormField label="As of Date" label-class="!text-xs">
        <TextInput
          :model-value="modelValue.asOfDate"
          type="date"
          size="md"
          @update:model-value="updateFilter('asOfDate', $event)"
        />
      </FormField>

      <FormField label="Company" label-class="!text-xs">
        <SelectInput
          :model-value="modelValue.companyId"
          :options="companyOptions"
          placeholder="All Companies"
          size="md"
          @update:model-value="updateFilter('companyId', $event)"
        />
      </FormField>
    </div>
  </SectionCard>
</template>

<script setup>
import { computed } from 'vue';
import FormField from '../ui/FormField.vue';
import SectionCard from '../ui/SectionCard.vue';
import SelectInput from '../ui/SelectInput.vue';
import TextInput from '../ui/TextInput.vue';

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

const currentYear = new Date().getFullYear();

const reportTypeOptions = [
  { value: 'real', label: 'Real' },
  { value: 'coretax', label: 'Coretax' }
];

const yearOptions = computed(() => {
  const fromTransactions = (props.availableYears || [])
    .map((year) => parseInt(year, 10))
    .filter((year) => !Number.isNaN(year))
    .sort((a, b) => b - a);

  const normalizedYears = fromTransactions.length > 0 ? fromTransactions : [currentYear];
  return normalizedYears.map((year) => ({
    value: String(year),
    label: String(year)
  }));
});

const companyOptions = computed(() => (
  (props.companies || []).map((company) => ({
    value: company.id,
    label: company.name
  }))
));

const updateFilter = (key, value) => {
  emit('update:modelValue', {
    ...props.modelValue,
    [key]: value || null
  });
};

const handleReportTypeChange = (value) => {
  emit('update:modelValue', {
    ...props.modelValue,
    reportType: value || 'real'
  });
};

const handleYearChange = (year) => {
  const selectedYear = String(year);
  emit('update:modelValue', {
    ...props.modelValue,
    year: selectedYear,
    startDate: `${selectedYear}-01-01`,
    endDate: `${selectedYear}-12-31`,
    asOfDate: `${selectedYear}-12-31`
  });
};
</script>
