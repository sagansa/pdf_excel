<template>
  <div class="bg-white p-4 rounded-2xl shadow-sm border border-gray-200 grid grid-cols-2 md:grid-cols-4 lg:grid-cols-9 gap-4 items-end">
    <!-- Year -->
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

    <!-- Bank -->
    <div class="space-y-1">
        <label class="label-base text-[10px]">Bank</label>
        <select class="input-base !py-1.5 !text-xs"
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

    <!-- Type -->
    <div class="space-y-1">
        <label class="label-base text-[10px]">Type</label>
        <select class="input-base !py-1.5 !text-xs"
             :value="store.filters.dbCr"
             @change="store.setFilter('dbCr', $event.target.value)"
        >
            <option value="">All Types</option>
            <option value="DB">Debit (DB)</option>
            <option value="CR">Credit (CR)</option>
        </select>
    </div>

    <!-- Min Amount -->
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

    <!-- Max Amount -->
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

    <!-- Mark Status -->
    <div class="space-y-1">
        <label class="label-base text-[10px]">Mark Status</label>
        <MultiSelect 
            :model-value="store.filters.markStatus"
            :options="markOptions"
            placeholder="All Marks"
            @update:model-value="store.setFilter('markStatus', $event)"
        />
    </div>

    <!-- Company -->
    <div class="space-y-1">
        <label class="label-base text-[10px]">Company</label>
        <select class="input-base !py-1.5 !text-xs"
             :value="store.filters.company"
             @change="store.setFilter('company', $event.target.value)"
        >
            <option value="">All Companies</option>
            <option v-for="c in store.companies" :key="c.id" :value="c.id">
                {{ c.name }} {{ c.short_name ? `(${c.short_name})` : '' }}
            </option>
        </select>
    </div>

    <!-- Search -->
    <div class="space-y-1">
      <label class="label-base text-[10px]">Search</label>
      <div class="relative">
        <span class="absolute inset-y-0 left-0 pl-2 flex items-center text-gray-400">
          <i class="bi bi-search text-[10px]"></i>
        </span>
        <input 
            type="text" 
            placeholder="Search..." 
            class="input-base !py-1.5 !pl-7 !text-xs"
            :value="store.filters.search"
            @input="store.setFilter('search', $event.target.value)"
        >
      </div>
    </div>
    
    <!-- Reset -->
    <div class="flex items-end">
      <button class="w-full btn-secondary !py-2 !text-xs" @click="store.resetFilters">
        <i class="bi bi-x-circle me-1"></i> Reset
      </button>
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
        { id: 'unmarked', label: 'Unmarked Only' }
    ];
    
    store.sortedMarks.forEach(m => {
        options.push({
            id: m.id.toString(),
            label: m.personal_use
        });
    });
    
    return options;
});
</script>
