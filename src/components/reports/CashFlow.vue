<template>
  <div class="space-y-6">
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-2xl font-bold text-gray-900">Cash Flow</h2>
          <p class="text-sm text-gray-500 mt-1">Laporan Arus Kas</p>
        </div>
        <div v-if="hasData" class="text-right">
          <p class="text-xs text-gray-500">Period</p>
          <p class="text-sm font-semibold text-gray-900">
            {{ formatDate(data.period.start_date) }} - {{ formatDate(data.period.end_date) }}
          </p>
        </div>
      </div>
    </div>

    <div v-if="!hasData" class="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
      <i class="bi bi-cash-stack text-6xl text-gray-300"></i>
      <p class="text-gray-500 mt-4 text-lg font-medium">No Report Generated</p>
      <p class="text-gray-400 text-sm mt-2">Select a date range and click "Generate Report" to view cash flow</p>
    </div>

    <div v-else class="space-y-6">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div class="bg-gradient-to-br from-sky-50 to-sky-100 rounded-lg shadow-sm border border-sky-200 p-6">
          <p class="text-xs font-medium text-sky-600 uppercase">Opening Cash</p>
          <p class="text-2xl font-bold text-sky-900 mt-1">{{ formatCurrency(data.summary.opening_cash) }}</p>
        </div>
        <div class="bg-gradient-to-br from-indigo-50 to-indigo-100 rounded-lg shadow-sm border border-indigo-200 p-6">
          <p class="text-xs font-medium text-indigo-600 uppercase">Net Change</p>
          <p class="text-2xl font-bold text-indigo-900 mt-1">{{ formatCurrency(data.summary.net_change) }}</p>
        </div>
        <div class="bg-gradient-to-br from-emerald-50 to-emerald-100 rounded-lg shadow-sm border border-emerald-200 p-6">
          <p class="text-xs font-medium text-emerald-600 uppercase">Closing Cash</p>
          <p class="text-2xl font-bold text-emerald-900 mt-1">{{ formatCurrency(data.summary.closing_cash) }}</p>
        </div>
      </div>

      <div v-if="Math.abs(Number(data.summary.reconciliation_difference || 0)) > 0.01" class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <div class="flex items-center gap-2">
          <i class="bi bi-exclamation-triangle text-yellow-600"></i>
          <p class="text-sm text-yellow-800">
            Reconciliation difference: {{ formatCurrency(data.summary.reconciliation_difference) }}
          </p>
        </div>
      </div>

      <div v-for="sectionKey in data.section_order" :key="sectionKey" class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div class="px-6 py-3 border-b border-gray-200 bg-gray-50">
          <div class="flex items-center justify-between">
            <h3 class="text-sm font-bold text-gray-900 uppercase">{{ getSection(sectionKey).name }}</h3>
            <div class="text-xs text-gray-600">
              In: <span class="font-semibold text-emerald-700">{{ formatCurrency(getSection(sectionKey).inflow_total) }}</span>
              |
              Out: <span class="font-semibold text-red-700">{{ formatCurrency(getSection(sectionKey).outflow_total) }}</span>
              |
              Net: <span class="font-semibold text-indigo-700">{{ formatCurrency(getSection(sectionKey).net_cash) }}</span>
            </div>
          </div>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full">
            <thead class="bg-gray-50 border-b border-gray-200">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Description</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Mark</th>
                <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Inflow</th>
                <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Outflow</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              <tr v-if="getSection(sectionKey).items.length === 0">
                <td colspan="5" class="px-6 py-8 text-center text-gray-400 text-sm">No transactions</td>
              </tr>
              <tr v-for="item in getSection(sectionKey).items" :key="item.id" class="hover:bg-gray-50">
                <td class="px-6 py-3 text-sm text-gray-700">{{ formatDate(item.txn_date) }}</td>
                <td class="px-6 py-3 text-sm text-gray-900">{{ item.description || '-' }}</td>
                <td class="px-6 py-3 text-sm text-gray-500">{{ item.mark_name || '-' }}</td>
                <td class="px-6 py-3 text-sm text-right font-semibold text-emerald-700">
                  {{ item.signed_amount > 0 ? formatCurrency(item.signed_amount) : '-' }}
                </td>
                <td class="px-6 py-3 text-sm text-right font-semibold text-red-700">
                  {{ item.signed_amount < 0 ? formatCurrency(Math.abs(item.signed_amount)) : '-' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  data: {
    type: Object,
    default: null
  }
});

const hasData = computed(() => {
  return Boolean(props.data && props.data.period && props.data.sections && props.data.summary);
});

const formatCurrency = (amount) => {
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    minimumFractionDigits: 0
  }).format(Number(amount || 0));
};

const formatDate = (value) => {
  if (!value) return '-';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString('id-ID', { year: 'numeric', month: 'short', day: 'numeric' });
};

const getSection = (key) => {
  return props.data?.sections?.[key] || {
    name: key,
    inflow_total: 0,
    outflow_total: 0,
    net_cash: 0,
    items: []
  };
};
</script>
