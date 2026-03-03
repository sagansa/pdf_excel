<template>
  <div class="bg-white p-4 md:p-5 rounded-2xl shadow-sm border border-gray-200">
    <div class="flex flex-col lg:flex-row lg:items-end gap-3 mb-4">
      <div class="flex-1">
        <label class="label-base text-[10px]">Search</label>
        <div class="relative mt-1">
          <span class="absolute inset-y-0 left-0 pl-2.5 flex items-center text-gray-400">
            <i class="bi bi-search text-[10px]"></i>
          </span>
          <input
            type="text"
            placeholder="Description, amount, mark, COA, source file..."
            class="input-base !py-2 !pl-8 !text-xs"
            :value="store.filters.search"
            @input="store.setFilter('search', $event.target.value)"
          >
        </div>
      </div>

      <div class="flex items-center gap-2">
        <div class="text-[10px] font-semibold text-gray-500 px-2 py-1 rounded-md bg-gray-100 border border-gray-200">
          {{ activeFilterCount }} active filters
        </div>
        <button class="btn-secondary !py-2 !text-xs whitespace-nowrap" @click="resetAllFilters">
          <i class="bi bi-x-circle me-1"></i> Reset Filters
        </button>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
      <div class="space-y-1">
        <label class="label-base text-[10px]">Year</label>
        <select
          class="input-base !py-1.5 !text-xs"
          :value="store.filters.year"
          @change="store.setFilter('year', $event.target.value)"
        >
          <option value="">All Years</option>
          <option v-for="y in store.availableYears" :key="y" :value="y">{{ y }}</option>
        </select>
      </div>

      <div class="space-y-1">
        <label class="label-base text-[10px]">Start Date</label>
        <input
          type="date"
          class="input-base !py-1.5 !text-xs"
          :value="store.filters.dateStart"
          @input="store.setFilter('dateStart', $event.target.value)"
        >
      </div>

      <div class="space-y-1">
        <label class="label-base text-[10px]">End Date</label>
        <input
          type="date"
          class="input-base !py-1.5 !text-xs"
          :value="store.filters.dateEnd"
          @input="store.setFilter('dateEnd', $event.target.value)"
        >
      </div>

      <div class="space-y-1">
        <label class="label-base text-[10px]">Company</label>
        <select
          class="input-base !py-1.5 !text-xs"
          :value="store.filters.company"
          @change="store.setFilter('company', $event.target.value)"
        >
          <option value="">All Companies</option>
          <option v-for="c in store.companies" :key="c.id" :value="c.id">
            {{ c.name }} {{ c.short_name ? `(${c.short_name})` : '' }}
          </option>
        </select>
      </div>

      <div class="space-y-1">
        <label class="label-base text-[10px]">Bank</label>
        <select
          class="input-base !py-1.5 !text-xs"
          :value="store.filters.bank"
          @change="store.setFilter('bank', $event.target.value)"
        >
          <option value="">All Banks</option>
          <option value="BCA">BCA</option>
          <option value="BCA_CC">BCA CC</option>
          <option value="MANDIRI">Mandiri</option>
          <option value="MANDIRI_CC">Mandiri CC</option>
          <option value="DBS">DBS</option>
          <option value="BRI">BRI</option>
          <option value="SAQU">SAQU</option>
          <option value="BLU">BLU</option>
        </select>
      </div>

      <div class="space-y-1">
        <label class="label-base text-[10px]">Type</label>
        <select
          class="input-base !py-1.5 !text-xs"
          :value="store.filters.dbCr"
          @change="store.setFilter('dbCr', $event.target.value)"
        >
          <option value="">All Types</option>
          <option value="DB">Debit (DB)</option>
          <option value="CR">Credit (CR)</option>
        </select>
      </div>

      <div class="space-y-1">
        <label class="label-base text-[10px]">Min Amount</label>
        <input
          type="number"
          placeholder="Min..."
          class="input-base !py-1.5 !text-xs"
          :value="store.filters.amountMin"
          @input="store.setFilter('amountMin', $event.target.value)"
        >
      </div>

      <div class="space-y-1">
        <label class="label-base text-[10px]">Max Amount</label>
        <input
          type="number"
          placeholder="Max..."
          class="input-base !py-1.5 !text-xs"
          :value="store.filters.amountMax"
          @input="store.setFilter('amountMax', $event.target.value)"
        >
      </div>

      <div class="space-y-1 md:col-span-2">
        <label class="label-base text-[10px]">Mark Status</label>
        <MultiSelect
          :key="`mark-filter-${store.filterResetToken}`"
          :model-value="store.filters.markStatus"
          :options="markOptions"
          placeholder="All mark status"
          @update:model-value="store.setFilter('markStatus', $event)"
        />
      </div>

      <div class="space-y-1 md:col-span-2">
        <label class="label-base text-[10px]">COA</label>
        <MultiSelect
          :key="`coa-filter-${store.filterResetToken}`"
          :model-value="store.filters.coaIds"
          :options="store.coaOptions"
          placeholder="All accounts"
          @update:model-value="store.setFilter('coaIds', $event)"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useHistoryStore } from '../../stores/history';
import MultiSelect from '../ui/MultiSelect.vue';

const store = useHistoryStore();

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
