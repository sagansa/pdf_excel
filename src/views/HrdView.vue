<template>
  <div class="w-full px-6 space-y-5">
    <div class="bg-white/95 backdrop-blur border-b border-gray-200 -mx-6 -mt-6 px-6 py-4 mb-5 sticky top-0 z-40 shadow-sm flex items-center justify-between">
      <h3 class="text-xl font-bold text-gray-900">HRD</h3>
      <p class="text-[10px] text-gray-500 uppercase tracking-widest mt-0.5">Presence monitoring and sync</p>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 p-4">
      <div class="flex flex-col md:flex-row gap-3 items-end">
        <div class="flex-1">
          <label class="block text-xs font-semibold text-gray-500 mb-1">Company</label>
          <select
            v-model="filters.companyId"
            class="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
          >
            <option value="">All Companies</option>
            <option v-for="c in companyStore.companies" :key="c.id" :value="c.id">
              {{ c.name }}
            </option>
          </select>
        </div>
        <div class="w-full md:w-40">
          <label class="block text-xs font-semibold text-gray-500 mb-1">Year</label>
          <input
            v-model.number="filters.year"
            type="number"
            min="2000"
            max="2100"
            class="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
          >
        </div>
      </div>
    </div>

    <PayrollPresencesTable
      :key="`hrd-presences-${filters.companyId || 'all'}-${filters.year}`"
      :company-id="filters.companyId"
      :year="filters.year"
    />
  </div>
</template>

<script setup>
import { onMounted, reactive } from 'vue';
import { useCompanyStore } from '../stores/companies';
import PayrollPresencesTable from '../components/history/PayrollPresencesTable.vue';

const companyStore = useCompanyStore();
const filters = reactive({
  companyId: '',
  year: new Date().getFullYear()
});

onMounted(async () => {
  await companyStore.fetchCompanies();
});
</script>
