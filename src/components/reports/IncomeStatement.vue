<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-2xl font-bold text-gray-900">Income Statement</h2>
          <p class="text-sm text-gray-500 mt-1">Laporan Laba Rugi</p>
        </div>
        <div v-if="hasData" class="text-right">
          <p class="text-xs text-gray-500">Period</p>
          <p class="text-sm font-semibold text-gray-900">
            {{ formatDate(data.period.start_date) }} - {{ formatDate(data.period.end_date) }}
          </p>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-if="!hasData" class="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
      <i class="bi bi-file-earmark-bar-graph text-6xl text-gray-300"></i>
      <p class="text-gray-500 mt-4 text-lg font-medium">No Report Generated</p>
      <p class="text-gray-400 text-sm mt-2">Select a date range and click "Generate Report" to view the income statement</p>
    </div>

    <!-- Report Content -->
    <div v-else class="space-y-6">
      <!-- Summary Cards -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div class="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg shadow-sm border border-purple-200 p-6">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-xs font-medium text-purple-600 uppercase">Total Revenue</p>
              <p class="text-2xl font-bold text-purple-900 mt-1">{{ formatCurrency(data.total_revenue) }}</p>
            </div>
            <div class="w-12 h-12 rounded-full bg-purple-200 flex items-center justify-center">
              <i class="bi bi-graph-up-arrow text-purple-700 text-xl"></i>
            </div>
          </div>
        </div>

        <div class="bg-gradient-to-br from-orange-50 to-orange-100 rounded-lg shadow-sm border border-orange-200 p-6">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-xs font-medium text-orange-600 uppercase">Total Expenses</p>
              <p class="text-2xl font-bold text-orange-900 mt-1">{{ formatCurrency(data.total_expenses) }}</p>
            </div>
            <div class="w-12 h-12 rounded-full bg-orange-200 flex items-center justify-center">
              <i class="bi bi-graph-down-arrow text-orange-700 text-xl"></i>
            </div>
          </div>
        </div>

        <div class="bg-gradient-to-br from-green-50 to-green-100 rounded-lg shadow-sm border border-green-200 p-6">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-xs font-medium text-green-600 uppercase">Net Income</p>
              <p class="text-2xl font-bold text-green-900 mt-1">{{ formatCurrency(data.net_income) }}</p>
            </div>
            <div class="w-12 h-12 rounded-full bg-green-200 flex items-center justify-center">
              <i class="bi bi-cash-coin text-green-700 text-xl"></i>
            </div>
          </div>
        </div>
      </div>

      <!-- Revenue Section -->
      <div class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div class="bg-purple-50 border-b border-purple-100 px-6 py-3">
          <h3 class="text-sm font-bold text-purple-900 uppercase">Revenue (Pendapatan)</h3>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full">
            <thead class="bg-gray-50 border-b border-gray-200">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Code</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Account Name</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Subcategory</th>
                <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Amount</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              <tr v-if="data.revenue.length === 0">
                <td colspan="4" class="px-6 py-8 text-center text-gray-400 text-sm">No revenue entries</td>
              </tr>
              <tr v-for="item in data.revenue" :key="item.code" class="hover:bg-gray-50">
                <td class="px-6 py-3 text-sm font-mono font-semibold text-gray-900">{{ item.code }}</td>
                <td class="px-6 py-3 text-sm text-gray-900">{{ item.name }}</td>
                <td class="px-6 py-3 text-sm text-gray-500">{{ item.subcategory || '-' }}</td>
                <td class="px-6 py-3 text-sm text-right font-semibold text-purple-700">{{ formatCurrency(item.amount) }}</td>
              </tr>
              <tr class="bg-purple-50 font-bold">
                <td colspan="3" class="px-6 py-3 text-sm text-purple-900">Total Revenue</td>
                <td class="px-6 py-3 text-sm text-right text-purple-900">{{ formatCurrency(data.total_revenue) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <!-- HPP Section -->
      <div v-if="data.cogs_breakdown" class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div class="bg-blue-50 border-b border-blue-100 px-6 py-3">
          <h3 class="text-sm font-bold text-blue-900 uppercase">Beban Pokok Penjualan (HPP)</h3>
        </div>
        <div class="p-6">
          <div class="max-w-2xl mx-auto space-y-3">
            <div class="flex justify-between text-sm">
              <span class="text-gray-600">Persediaan Barang Dagangan - Awal {{ data.cogs_breakdown.year }}</span>
              <span class="font-medium text-gray-900">{{ formatCurrency(data.cogs_breakdown.beginning_inventory) }}</span>
            </div>
            <div class="flex justify-between text-sm">
              <span class="text-gray-600">Pembelian (Net)</span>
              <span class="font-medium text-gray-900">{{ formatCurrency(data.cogs_breakdown.purchases) }}</span>
            </div>
            <!-- Detailed Other COGS -->
            <div v-for="item in data.cogs_breakdown.other_cogs_items" :key="item.code" class="flex justify-between text-sm">
              <span class="text-gray-600">{{ item.name }} ({{ item.code }})</span>
              <span class="font-medium text-gray-900">{{ formatCurrency(item.amount) }}</span>
            </div>
            
            <div class="pt-2 border-t border-gray-100 flex justify-between text-sm font-bold">
              <span class="text-gray-700">Barang Tersedia Untuk Dijual</span>
              <span class="text-gray-900">{{ formatCurrency(data.cogs_breakdown.beginning_inventory + data.cogs_breakdown.purchases + data.cogs_breakdown.total_other_cogs) }}</span>
            </div>
            <div class="flex justify-between text-sm text-red-600 italic">
              <span>Persediaan Barang Dagangan - Akhir {{ data.cogs_breakdown.year }}</span>
              <span>- {{ formatCurrency(data.cogs_breakdown.ending_inventory) }}</span>
            </div>
            <div class="pt-3 border-t-2 border-slate-200 flex justify-between text-base font-black">
              <span class="text-blue-900 uppercase tracking-wider">Total Harga Pokok Penjualan</span>
              <span class="text-blue-900">{{ formatCurrency(data.cogs_breakdown.total_cogs) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Expenses Section -->
      <div class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div class="bg-orange-50 border-b border-orange-100 px-6 py-3">
          <h3 class="text-sm font-bold text-orange-900 uppercase">Expenses (Beban)</h3>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full">
            <thead class="bg-gray-50 border-b border-gray-200">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Code</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Account Name</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Subcategory</th>
                <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Amount</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              <tr v-if="data.expenses.length === 0">
                <td colspan="4" class="px-6 py-8 text-center text-gray-400 text-sm">No expense entries</td>
              </tr>
              <tr v-for="item in data.expenses" :key="item.code" class="hover:bg-gray-50">
                <td class="px-6 py-3 text-sm font-mono font-semibold text-gray-900">{{ item.code }}</td>
                <td class="px-6 py-3 text-sm text-gray-900">{{ item.name }}</td>
                <td class="px-6 py-3 text-sm text-gray-500">{{ item.subcategory || '-' }}</td>
                <td class="px-6 py-3 text-sm text-right font-semibold text-orange-700">{{ formatCurrency(item.amount) }}</td>
              </tr>
              <tr class="bg-orange-50 font-bold">
                <td colspan="3" class="px-6 py-3 text-sm text-orange-900">Total Expenses</td>
                <td class="px-6 py-3 text-sm text-right text-orange-900">{{ formatCurrency(data.total_expenses) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Net Income Summary -->
      <div class="bg-gradient-to-r from-green-600 to-green-700 rounded-lg shadow-lg p-6 text-white">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm font-medium opacity-90">Net Income / (Loss)</p>
            <p class="text-xs opacity-75 mt-1">Laba / (Rugi) Bersih</p>
          </div>
          <div class="text-right">
            <p class="text-3xl font-bold">{{ formatCurrency(data.net_income) }}</p>
            <p class="text-xs opacity-75 mt-1">
              {{ data.net_income >= 0 ? 'Profit' : 'Loss' }}
            </p>
          </div>
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

const hasData = computed(() => props.data !== null);

const formatDate = (dateStr) => {
  if (!dateStr) return '-';
  const date = new Date(dateStr);
  return date.toLocaleDateString('id-ID', { 
    year: 'numeric', 
    month: 'long', 
    day: 'numeric' 
  });
};

const formatCurrency = (amount) => {
  if (amount === null || amount === undefined) return 'Rp 0';
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(amount);
};
</script>
