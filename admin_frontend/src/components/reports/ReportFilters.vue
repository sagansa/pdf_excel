<template>
  <div class="reports-filters">
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

    <div class="reports-filters__status" role="status" aria-live="polite">
      <span v-if="isLoading" class="reports-filters__status-item text-primary">
        <i class="bi bi-arrow-repeat reports-filters__spinner" aria-hidden="true"></i>
        Updating…
      </span>
      <span v-else class="reports-filters__status-item text-muted">
        <i class="bi bi-lightning-charge-fill" aria-hidden="true"></i>
        Auto refresh
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import FormField from '../ui/FormField.vue';
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

<style scoped>
.reports-filters {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 12px 16px;
}

.reports-filters > :deep(.field-stack) {
  flex: 1 1 132px;
  min-width: 122px;
  max-width: 200px;
}

.reports-filters > :deep(.field-stack:last-of-type) {
  flex: 1 1 160px;
  min-width: 150px;
  max-width: 230px;
}

.reports-filters__status {
  margin-left: auto;
  padding-bottom: 8px;
  flex: 0 0 auto;
}

.reports-filters__status-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  white-space: nowrap;
}

.reports-filters__spinner {
  animation: reports-filters-spin 1s linear infinite;
}

@keyframes reports-filters-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@media (prefers-reduced-motion: reduce) {
  .reports-filters__spinner {
    animation: none;
  }
}

@media (max-width: 720px) {
  .reports-filters > :deep(.field-stack),
  .reports-filters > :deep(.field-stack:last-of-type) {
    flex: 1 1 100%;
    max-width: none;
  }

  .reports-filters__status {
    margin-left: 0;
    padding-bottom: 0;
  }
}
</style>
