<template>
  <div class="surface-card p-6 space-y-5">
    <div class="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-3">
      <div>
        <h3 class="text-lg font-bold text-theme">Sales by Date</h3>
        <p class="text-xs text-muted">
          Daily product sales with quantity and total price
        </p>
      </div>
      <div class="flex items-center gap-2">
        <input
          v-model="selectedDate"
          type="date"
          class="input-base !w-auto !px-3 !py-2 !text-xs"
        />
        <button
          type="button"
          class="btn-secondary !px-3 !py-2 !text-xs disabled:opacity-50"
          :disabled="isLoading"
          @click="loadData"
        >
          <i class="bi bi-arrow-clockwise mr-1"></i> Reload
        </button>
      </div>
    </div>

    <div v-if="isLoading" class="grid grid-cols-2 md:grid-cols-4 gap-3 animate-pulse">
      <div v-for="i in 4" :key="i" class="h-20 rounded-2xl storage-skeleton"></div>
    </div>

    <div v-else-if="error" class="storage-error rounded-2xl px-4 py-3 text-xs">
      {{ error }}
    </div>

    <template v-else>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div class="metric-card">
          <div class="metric-label">Total Products</div>
          <div class="metric-value">{{ summary.total_products }}</div>
        </div>
        <div class="metric-card metric-card--success">
          <div class="metric-label metric-label--success">Total Quantity</div>
          <div class="metric-value metric-value--success">{{ formatNumber(summary.total_quantity) }}</div>
        </div>
        <div class="metric-card metric-card--primary">
          <div class="metric-label metric-label--primary">Total Revenue</div>
          <div class="text-sm font-bold mono" style="color: var(--color-primary)">{{ formatCurrency(summary.total_revenue) }}</div>
        </div>
        <div class="metric-card metric-card--info">
          <div class="metric-label metric-label--info">Date</div>
          <div class="text-sm font-bold mono" style="color: var(--color-info)">{{ summary.selected_date || '-' }}</div>
        </div>
      </div>

      <div class="overflow-x-auto rounded-2xl storage-table-shell">
        <table class="min-w-full text-xs">
          <thead class="storage-table-head">
            <tr>
              <th class="px-3 py-2 text-left font-semibold uppercase text-muted">#</th>
              <th class="px-3 py-2 text-left font-semibold uppercase text-muted">Product Name</th>
              <th class="px-3 py-2 text-right font-semibold uppercase text-muted">Quantity</th>
              <th class="px-3 py-2 text-right font-semibold uppercase text-muted">Unit Price</th>
              <th class="px-3 py-2 text-right font-semibold uppercase text-muted">Total Price</th>
            </tr>
          </thead>
          <tbody class="divide-y" style="border-color: var(--color-border)">
            <tr v-if="items.length === 0">
              <td colspan="5" class="px-3 py-8 text-center text-muted">No sales data for this date</td>
            </tr>
            <tr v-for="(item, index) in items" :key="`${item.stock_monitoring_name}-${index}`" class="storage-row">
              <td class="px-3 py-2 text-center text-muted mono">{{ index + 1 }}</td>
              <td class="px-3 py-2">
                <div class="font-semibold text-theme">{{ item.stock_monitoring_name || '-' }}</div>
              </td>
              <td class="px-3 py-2 text-right font-semibold text-theme mono">
                {{ formatNumber(item.quantity) }}
              </td>
              <td class="px-3 py-2 text-right mono">
                {{ formatCurrency(item.unit_price) }}
              </td>
              <td class="px-3 py-2 text-right font-semibold text-theme mono">
                {{ formatCurrency(item.total_price) }}
              </td>
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
  total_products: 0,
  total_quantity: 0,
  total_revenue: 0,
  selected_date: null
});

const formatNumber = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '-';
  return new Intl.NumberFormat('id-ID', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2
  }).format(Number(value));
};

const formatCurrency = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '-';
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(Number(value));
};

const loadData = async () => {
  isLoading.value = true;
  error.value = '';
  try {
    const params = {};
    if (selectedDate.value) params.date = selectedDate.value;
    const response = await historyApi.getDashboardSalesByDate(params);
    const data = response.data || {};
    items.value = Array.isArray(data.data) ? data.data : [];
    summary.value = {
      total_products: data.data?.length || 0,
      total_quantity: (data.data || []).reduce((sum, item) => sum + (item.quantity || 0), 0),
      total_revenue: (data.data || []).reduce((sum, item) => sum + (item.total_price || 0), 0),
      selected_date: data.date || selectedDate.value
    };
  } catch (err) {
    console.error('Failed to load sales by date dashboard:', err);
    error.value = err.response?.data?.error || 'Failed to load sales by date dashboard';
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

<style scoped>
.storage-skeleton {
  background: var(--color-surface-muted);
}

.storage-error {
  background: rgba(185, 28, 28, 0.08);
  border: 1px solid rgba(185, 28, 28, 0.18);
  color: var(--color-danger);
}

.metric-card {
  @apply rounded-2xl px-3 py-3;
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
}

.metric-card--danger {
  background: rgba(185, 28, 28, 0.08);
  border-color: rgba(185, 28, 28, 0.18);
}

.metric-card--success {
  background: rgba(22, 101, 52, 0.08);
  border-color: rgba(22, 101, 52, 0.18);
}

.metric-card--warning {
  background: rgba(180, 83, 9, 0.08);
  border-color: rgba(180, 83, 9, 0.18);
}

.metric-card--primary {
  background: rgba(15, 118, 110, 0.08);
  border-color: rgba(15, 118, 110, 0.18);
}

.metric-card--info {
  background: rgba(29, 78, 216, 0.08);
  border-color: rgba(29, 78, 216, 0.18);
}

.metric-label {
  @apply text-[10px] uppercase font-semibold;
  color: var(--color-text-muted);
}

.metric-label--danger,
.metric-value--danger {
  color: var(--color-danger);
}

.metric-label--success,
.metric-value--success {
  color: var(--color-success);
}

.metric-label--warning,
.metric-value--warning {
  color: var(--color-warning);
}

.metric-label--primary {
  color: var(--color-primary);
}

.metric-label--info {
  color: #1d4ed8;
}

.metric-value {
  @apply text-lg font-bold;
  font-family: var(--font-mono);
  color: var(--color-text);
}

.storage-note {
  background: rgba(180, 83, 9, 0.08);
  border: 1px solid rgba(180, 83, 9, 0.18);
}

.storage-table-shell {
  border: 1px solid var(--color-border);
}

.storage-table-head {
  background: var(--color-surface-muted);
}

.storage-row {
  transition: background-color 160ms ease;
}

.storage-row:hover {
  background: rgba(15, 118, 110, 0.05);
}

.status-badge {
  @apply inline-flex items-center rounded-full px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.12em];
}

.status-badge--danger {
  background: rgba(185, 28, 28, 0.10);
  color: var(--color-danger);
}

.status-badge--success {
  background: rgba(22, 101, 52, 0.10);
  color: var(--color-success);
}

.status-badge--warning {
  background: rgba(180, 83, 9, 0.12);
  color: var(--color-warning);
}
</style>
