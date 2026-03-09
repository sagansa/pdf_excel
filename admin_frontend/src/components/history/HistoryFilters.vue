<template>
  <SectionCard body-class="p-4 md:p-5">
    <div class="grid grid-cols-1 gap-3 mb-4 xl:grid-cols-[minmax(0,1.5fr)_minmax(220px,0.9fr)_minmax(260px,1fr)_auto] xl:items-end">
      <FormField label="Search" label-class="text-[10px]">
        <TextInput
          :model-value="store.filters.search"
          placeholder="Description, amount, mark, COA, source file..."
          leading-icon="bi bi-search text-[10px]"
          size="sm"
          @update:model-value="store.setFilter('search', $event)"
        />
      </FormField>

      <FormField label="Mark Status" label-class="text-[10px]">
        <MultiSelect
          :key="`mark-filter-${store.filterResetToken}`"
          :model-value="store.filters.markStatus"
          :options="markOptions"
          placeholder="All mark status"
          @update:model-value="store.setFilter('markStatus', $event)"
        />
      </FormField>

      <FormField label="COA" label-class="text-[10px]">
        <MultiSelect
          :key="`coa-filter-${store.filterResetToken}`"
          :model-value="store.filters.coaIds"
          :options="store.coaOptions"
          placeholder="All accounts"
          @update:model-value="store.setFilter('coaIds', $event)"
        />
      </FormField>

      <div class="flex items-center gap-2 xl:justify-end">
        <div class="stat-pill !rounded-xl !px-2.5 !py-1 text-[10px]">
          {{ activeFilterCount }} active filters
        </div>
        <button class="btn-secondary !py-2 !text-xs whitespace-nowrap" @click="resetAllFilters">
          <i class="bi bi-x-circle me-1"></i> Reset Filters
        </button>
      </div>
    </div>

    <div class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
      <FormField label="Year" label-class="text-[10px]">
        <SelectInput
          :model-value="store.filters.year"
          :options="yearOptions"
          placeholder="All Years"
          size="sm"
          @update:model-value="store.setFilter('year', $event)"
        />
      </FormField>

      <FormField label="Start Date" label-class="text-[10px]">
        <TextInput
          :model-value="store.filters.dateStart"
          type="date"
          size="sm"
          @update:model-value="store.setFilter('dateStart', $event)"
        />
      </FormField>

      <FormField label="End Date" label-class="text-[10px]">
        <TextInput
          :model-value="store.filters.dateEnd"
          type="date"
          size="sm"
          @update:model-value="store.setFilter('dateEnd', $event)"
        />
      </FormField>

      <FormField label="Company" label-class="text-[10px]">
        <SelectInput
          :model-value="store.filters.company"
          :options="companyOptions"
          placeholder="All Companies"
          size="sm"
          @update:model-value="store.setFilter('company', $event)"
        />
      </FormField>

      <FormField label="Bank" label-class="text-[10px]">
        <SelectInput
          :model-value="store.filters.bank"
          :options="bankOptions"
          placeholder="All Banks"
          size="sm"
          @update:model-value="store.setFilter('bank', $event)"
        />
      </FormField>

      <FormField label="Type" label-class="text-[10px]">
        <SelectInput
          :model-value="store.filters.dbCr"
          :options="typeOptions"
          placeholder="All Types"
          size="sm"
          @update:model-value="store.setFilter('dbCr', $event)"
        />
      </FormField>

      <FormField label="Min Amount" label-class="text-[10px]">
        <TextInput
          :model-value="store.filters.amountMin"
          type="number"
          placeholder="Min..."
          size="sm"
          @update:model-value="store.setFilter('amountMin', $event)"
        />
      </FormField>

      <FormField label="Max Amount" label-class="text-[10px]">
        <TextInput
          :model-value="store.filters.amountMax"
          type="number"
          placeholder="Max..."
          size="sm"
          @update:model-value="store.setFilter('amountMax', $event)"
        />
      </FormField>
    </div>
  </SectionCard>
</template>

<script setup>
import { computed } from 'vue';
import { useHistoryStore } from '../../stores/history';
import FormField from '../ui/FormField.vue';
import MultiSelect from '../ui/MultiSelect.vue';
import SectionCard from '../ui/SectionCard.vue';
import SelectInput from '../ui/SelectInput.vue';
import TextInput from '../ui/TextInput.vue';

const store = useHistoryStore();

const bankOptions = [
  { value: 'BCA', label: 'BCA' },
  { value: 'BCA_CC', label: 'BCA CC' },
  { value: 'MANDIRI', label: 'Mandiri' },
  { value: 'MANDIRI_CC', label: 'Mandiri CC' },
  { value: 'DBS', label: 'DBS' },
  { value: 'BRI', label: 'BRI' },
  { value: 'SAQU', label: 'SAQU' },
  { value: 'BLU', label: 'BLU' }
];

const typeOptions = [
  { value: 'DB', label: 'Debit (DB)' },
  { value: 'CR', label: 'Credit (CR)' }
];

const yearOptions = computed(() => (
  (store.availableYears || []).map(year => ({ value: year, label: year }))
));

const companyOptions = computed(() => (
  (store.companies || []).map(company => ({
    value: company.id,
    label: `${company.name}${company.short_name ? ` (${company.short_name})` : ''}`
  }))
));

const markOptions = computed(() => {
  const options = [
    { id: 'marked', label: 'Marked Only' },
    { id: 'unmarked', label: 'Unmarked Only' },
    { id: 'multi_marked', label: 'Multi Marked (Split Parent)' },
    { id: 'missing_mark', label: 'Deleted Mark / Missing Mark' },
    { id: 'separator-1', type: 'separator' }
  ];

  store.sortedMarks.forEach(m => {
    options.push({
      id: m.id.toString(),
      label: m.internal_report || m.personal_use || m.tax_report || 'Unnamed Mark'
    });
  });

  return options;
});

const activeFilterCount = computed(() => {
  const f = store.filters;
  let count = 0;
  if (f.year) count += 1;
  if (f.dateStart) count += 1;
  if (f.dateEnd) count += 1;
  if (f.company) count += 1;
  if (f.bank) count += 1;
  if (f.dbCr) count += 1;
  if (f.amountMin !== null && f.amountMin !== '') count += 1;
  if (f.amountMax !== null && f.amountMax !== '') count += 1;
  if (f.markStatus.length > 0) count += 1;
  if (f.coaIds.length > 0) count += 1;
  if (f.search) count += 1;
  return count;
});

const resetAllFilters = () => {
  store.resetFilters();
};
</script>
