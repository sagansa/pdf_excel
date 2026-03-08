<template>
  <div class="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 space-y-5">
    <div class="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-3">
      <div>
        <h3 class="text-lg font-bold text-gray-900">Remaining Storage Monitor</h3>
        <p class="text-xs text-gray-500">
          Based on `stock_monitorings` + latest `remaining storage` stock cards (all stores)
        </p>
      </div>
      <div class="flex items-center gap-2">
        <input
          v-model="selectedDate"
          type="date"
          class="px-3 py-2 border border-gray-200 rounded-lg text-xs focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
        />
        <button
          type="button"
          class="px-3 py-2 text-xs font-semibold border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50"
          :disabled="isLoading"
          @click="loadData"
        >
          <i class="bi bi-arrow-clockwise mr-1"></i> Reload
        </button>
      </div>
    </div>

    <div v-if="isLoading" class="grid grid-cols-2 md:grid-cols-4 gap-3 animate-pulse">
      <div v-for="i in 4" :key="i" class="h-20 rounded-xl bg-gray-100"></div>
    </div>

    <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-xs text-red-700">
      {{ error }}
    </div>

    <template v-else>
      <div class="grid grid-cols-2 md:grid-cols-6 gap-3">
        <div class="rounded-xl border border-gray-200 bg-gray-50 px-3 py-3">
          <div class="text-[10px] uppercase font-semibold text-gray-500">Monitored</div>
          <div class="text-lg font-bold text-gray-900">{{ summary.total_monitored }}</div>
        </div>
        <div class="rounded-xl border border-red-200 bg-red-50 px-3 py-3">
          <div class="text-[10px] uppercase font-semibold text-red-600">Low</div>
          <div class="text-lg font-bold text-red-700">{{ summary.low_count }}</div>
        </div>
        <div class="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-3">
          <div class="text-[10px] uppercase font-semibold text-emerald-600">Safe</div>
          <div class="text-lg font-bold text-emerald-700">{{ summary.safe_count }}</div>
        </div>
        <div class="rounded-xl border border-amber-200 bg-amber-50 px-3 py-3">
          <div class="text-[10px] uppercase font-semibold text-amber-600">No Data</div>
          <div class="text-lg font-bold text-amber-700">{{ summary.missing_count }}</div>
        </div>
        <div class="rounded-xl border border-indigo-200 bg-indigo-50 px-3 py-3">
          <div class="text-[10px] uppercase font-semibold text-indigo-600">As Of</div>
          <div class="text-sm font-bold text-indigo-700">{{ summary.as_of_date || '-' }}</div>
        </div>
        <div class="rounded-xl border border-slate-200 bg-slate-50 px-3 py-3">
          <div class="text-[10px] uppercase font-semibold text-slate-600">No Report Store</div>
          <div class="text-lg font-bold text-slate-700">{{ summary.missing_report_store_count || 0 }}</div>
        </div>
      </div>

      <div
        v-if="selectedDate"
        class="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3"
      >
        <div class="text-xs font-semibold text-amber-800">
          Store belum laporan tanggal {{ selectedDate }}
        </div>
        <div class="text-xs text-amber-700 mt-1">
          <span v-if="missingReportStores.length === 0">Semua store sudah laporan.</span>
          <span v-else>{{ missingReportStores.map((item) => item.store_name).join(', ') }}</span>
        </div>
      </div>

      <div class="overflow-x-auto border border-gray-200 rounded-xl">
        <table class="min-w-full text-xs">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-3 py-2 text-left font-semibold text-gray-500 uppercase">Monitoring</th>
              <th class="px-3 py-2 text-left font-semibold text-gray-500 uppercase">Product</th>
              <th class="px-3 py-2 text-right font-semibold text-gray-500 uppercase">Total Stock</th>
              <th class="px-3 py-2 text-right font-semibold text-gray-500 uppercase">Qty Low</th>
              <th class="px-3 py-2 text-left font-semibold text-gray-500 uppercase">Status</th>
              <th class="px-3 py-2 text-left font-semibold text-gray-500 uppercase">Tanggal</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-if="items.length === 0">
              <td colspan="6" class="px-3 py-8 text-center text-gray-400">No monitoring data</td>
            </tr>
            <tr v-for="item in items" :key="`${item.monitoring_id}`" class="hover:bg-gray-50">
              <td class="px-3 py-2">
                <div class="font-semibold text-gray-800">{{ item.monitoring_name || '-' }}</div>
                <div class="text-[11px] text-gray-500">ID: {{ item.monitoring_id }}</div>
              </td>
              <td class="px-3 py-2">
                <div
                  v-if="Array.isArray(item.product_details) && item.product_details.length > 0"
                  class="space-y-1"
                >
                  <div
                    v-for="product in item.product_details.slice(0, 3)"
                    :key="`${item.monitoring_id}-${product.product_id || product.product_name}`"
                    class="text-[11px] text-gray-700"
                  >
                    {{ product.product_name || `Product ${product.product_id || '-'}` }}
                    ({{ formatNumber(product.quantity) }} x {{ formatNumber(product.coefficient) }})
                  </div>
                  <div
                    v-if="item.product_details.length > 3"
                    class="text-[10px] text-gray-400"
                  >
                    +{{ item.product_details.length - 3 }} more
                  </div>
                </div>
                <div v-else class="text-[11px] text-gray-400">-</div>
              </td>
              <td class="px-3 py-2 text-right font-semibold text-gray-800">
                {{ formatNumber(item.total_stock) }} {{ item.unit_name || '' }}
              </td>
              <td class="px-3 py-2 text-right">{{ formatNumber(item.quantity_low) }} {{ item.unit_name || '' }}</td>
              <td class="px-3 py-2">
                <span class="px-2 py-1 rounded-full text-[10px] font-semibold" :class="statusClass(item.status)">
                  {{ statusLabel(item.status) }}
                </span>
              </td>
              <td class="px-3 py-2">{{ item.latest_stock_card_date || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue';
import { historyApi } from '../../api';

const isLoading = ref(false);
const error = ref('');
const items = ref([]);
const missingReportStores = ref([]);
const yesterdayLocal = () => {
  const now = new Date();
  now.setDate(now.getDate() - 1);
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};
const selectedDate = ref(yesterdayLocal());
const summary = ref({
  total_monitored: 0,
  low_count: 0,
  safe_count: 0,
  missing_count: 0,
  as_of_date: null,
  missing_report_store_count: 0
});

const formatNumber = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '-';
  return new Intl.NumberFormat('id-ID', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2
  }).format(Number(value));
};

const statusClass = (status) => {
  if (status === 'low') return 'bg-red-100 text-red-700';
  if (status === 'ok') return 'bg-emerald-100 text-emerald-700';
  return 'bg-amber-100 text-amber-700';
};

const statusLabel = (status) => {
  if (status === 'low') return 'LOW STOCK';
  if (status === 'ok') return 'NORMAL';
  return 'NO DATA';
};

const loadData = async () => {
  isLoading.value = true;
  error.value = '';
  try {
    const params = { limit: 12 };
    if (selectedDate.value) params.date = selectedDate.value;
    const response = await historyApi.getDashboardRemainingStorage(params);
    const data = response.data || {};
    items.value = Array.isArray(data.items) ? data.items : [];
    missingReportStores.value = Array.isArray(data.missing_report_stores) ? data.missing_report_stores : [];
    summary.value = {
      ...summary.value,
      ...(data.summary || {})
    };
  } catch (err) {
    console.error('Failed to load remaining storage dashboard:', err);
    error.value = err.response?.data?.error || 'Failed to load remaining storage dashboard';
  } finally {
    isLoading.value = false;
  }
};

watch(selectedDate, async () => {
  await loadData();
});

onMounted(async () => {
  await loadData();
});
</script>
