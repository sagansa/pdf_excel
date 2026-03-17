<template>
  <div class="surface-card p-6 space-y-5">
    <div class="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-3">
      <div>
        <h3 class="text-lg font-bold text-theme">Stock Comparison</h3>
        <p class="text-xs text-muted">
          Compare sales vs stock changes between two dates
        </p>
      </div>
      <div class="flex items-center gap-2">
        <div class="flex items-center gap-2">
          <input
            v-model="fromDate"
            type="date"
            class="input-base !w-auto !px-3 !py-2 !text-xs"
            placeholder="From"
          />
          <span class="text-muted">→</span>
          <input
            v-model="toDate"
            type="date"
            class="input-base !w-auto !px-3 !py-2 !text-xs"
            placeholder="To"
          />
        </div>
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
      <div class="grid grid-cols-2 md:grid-cols-5 gap-3">
        <div class="metric-card metric-card--primary">
          <div class="metric-label metric-label--primary">Total Sales Qty</div>
          <div class="metric-value metric-value--primary">{{ formatNumber(summary.total_sales_quantity) }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Stock From</div>
          <div class="metric-value">{{ formatNumber(summary.stock_from_quantity) }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Stock To</div>
          <div class="metric-value">{{ formatNumber(summary.stock_to_quantity) }}</div>
        </div>
        <div class="metric-card metric-card--warning">
          <div class="metric-label metric-label--warning">Total Variance</div>
          <div class="metric-value metric-value--warning">{{ formatNumber(summary.total_variance) }}</div>
        </div>
        <div class="metric-card metric-card--info">
          <div class="metric-label metric-label--info">Period</div>
          <div class="text-xs font-bold" :style="{ color: 'var(--color-info)' }">{{ summary.period_display }}</div>
        </div>
      </div>

      <div class="flex items-center gap-4 text-xs">
        <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full" style="background: rgba(22, 101, 52, 0.10); color: var(--color-success);">
          <i class="bi bi-check-circle-fill"></i>
          Balanced: {{ summary.balanced_items }}
        </span>
        <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full" style="background: rgba(180, 83, 9, 0.12); color: var(--color-warning);">
          <i class="bi bi-exclamation-triangle-fill"></i>
          Over Sold: {{ summary.over_sold_items }}
        </span>
        <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full" style="background: rgba(185, 28, 28, 0.10); color: var(--color-danger);">
          <i class="bi bi-x-circle-fill"></i>
          Under Sold: {{ summary.under_sold_items }}
        </span>
      </div>

      <div class="overflow-x-auto rounded-2xl storage-table-shell">
        <table class="min-w-full text-xs">
          <thead class="storage-table-head">
            <tr>
              <th class="px-3 py-2 text-left font-semibold uppercase text-muted">#</th>
              <th class="px-3 py-2 text-left font-semibold uppercase text-muted">Stock Monitoring</th>
              <th class="px-3 py-2 text-right font-semibold uppercase text-muted">Sales Qty</th>
              <th class="px-3 py-2 text-right font-semibold uppercase text-muted">Stock From</th>
              <th class="px-3 py-2 text-right font-semibold uppercase text-muted">Stock To</th>
              <th class="px-3 py-2 text-right font-semibold uppercase text-muted">Change</th>
              <th class="px-3 py-2 text-right font-semibold uppercase text-muted">Variance</th>
              <th class="px-3 py-2 text-center font-semibold uppercase text-muted">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y" style="border-color: var(--color-border)">
            <tr v-if="items.length === 0">
              <td colspan="8" class="px-3 py-8 text-center text-muted">No data for this period</td>
            </tr>
            <tr v-for="(item, index) in items" :key="item.stock_monitoring_id" class="storage-row">
              <td class="px-3 py-2 text-center text-muted mono">{{ index + 1 }}</td>
              <td class="px-3 py-2">
                <div class="font-semibold text-theme">{{ item.stock_monitoring_name }}</div>
              </td>
              <td class="px-3 py-2 text-right font-semibold text-theme mono">
                {{ formatNumber(item.sales_quantity) }}
              </td>
              <td class="px-3 py-2 text-right mono">
                {{ formatNumber(item.stock_from_quantity) }}
              </td>
              <td class="px-3 py-2 text-right mono">
                {{ formatNumber(item.stock_to_quantity) }}
              </td>
              <td class="px-3 py-2 text-right mono" :class="item.stock_change >= 0 ? 'text-success' : 'text-danger'">
                {{ item.stock_change >= 0 ? '+' : '' }}{{ formatNumber(item.stock_change) }}
              </td>
              <td class="px-3 py-2 text-right mono" :class="item.variance >= 0 ? 'text-warning' : 'text-danger'">
                {{ item.variance >= 0 ? '+' : '' }}{{ formatNumber(item.variance) }}
              </td>
              <td class="px-3 py-2 text-center">
                <span class="status-badge" :class="getStatusClass(item.status)">
                  {{ item.status }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="storage-note rounded-2xl px-4 py-3 text-xs" style="background: rgba(15, 118, 110, 0.05); border: 1px solid var(--color-border);">
        <i class="bi bi-info-circle mr-2"></i>
        <strong>Note:</strong> Sales from {{ toDate }}. Stock snapshots from {{ fromDate }} and {{ toDate }}.
      </div>
    </template>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue';

// Use backend proxy instead of direct API call to avoid CORS issues
const API_BASE_URL = 'http://localhost:5001/api';

const isLoading = ref(false);
const error = ref('');
const items = ref([]);

const getDefaultDates = () => {
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  return {
    fromDate: yesterday.toISOString().split('T')[0],  // Yesterday
    toDate: today.toISOString().split('T')[0]         // Today
  };
};

const defaultDates = getDefaultDates();
const fromDate = ref(defaultDates.fromDate);
const toDate = ref(defaultDates.toDate);

const summary = ref({
  total_sales_quantity: 0,
  stock_from_quantity: 0,
  stock_to_quantity: 0,
  total_variance: 0,
  period_display: '',
  balanced_items: 0,
  over_sold_items: 0,
  under_sold_items: 0
});

const formatNumber = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '-';
  return new Intl.NumberFormat('id-ID', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(Number(value));
};

const getStatusClass = (status) => {
  switch (status) {
    case 'balanced': return 'status-badge--success';
    case 'over_sold': return 'status-badge--warning';
    case 'under_sold': return 'status-badge--danger';
    default: return '';
  }
};

const loadData = async () => {
  isLoading.value = true;
  error.value = '';
  try {
    // Use backend proxy which handles authentication
    const url = `${API_BASE_URL}/stock-comparison?from_date=${fromDate.value}&to_date=${toDate.value}`;
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
    }
    
    const data = await response.json();
    items.value = Array.isArray(data.data) ? data.data : [];
    
    const s = data.summary || {};
    summary.value = {
      total_sales_quantity: s.sales?.total_quantity || 0,
      stock_from_quantity: s.stock?.from_quantity || 0,
      stock_to_quantity: s.stock?.to_quantity || 0,
      total_variance: s.total_variance || 0,
      period_display: `${fromDate.value} → ${toDate.value}`,
      balanced_items: s.balanced_items || 0,
      over_sold_items: s.over_sold_items || 0,
      under_sold_items: s.under_sold_items || 0
    };
  } catch (err) {
    console.error('Failed to load stock comparison:', err);
    error.value = err.message || 'Failed to load stock comparison';
  } finally {
    isLoading.value = false;
  }
};

watch([fromDate, toDate], async () => {
  await loadData();
});

onMounted(async () => {
  await loadData();
});
</script>

<style scoped>
.storage-skeleton { background: var(--color-surface-muted); }
.storage-error { background: rgba(185, 28, 28, 0.08); border: 1px solid rgba(185, 28, 28, 0.18); color: var(--color-danger); }
.metric-card { @apply rounded-2xl px-3 py-3; background: var(--color-surface-muted); border: 1px solid var(--color-border); }
.metric-card--primary { background: rgba(15, 118, 110, 0.08); border-color: rgba(15, 118, 110, 0.18); }
.metric-card--warning { background: rgba(180, 83, 9, 0.08); border-color: rgba(180, 83, 9, 0.18); }
.metric-card--info { background: rgba(29, 78, 216, 0.08); border-color: rgba(29, 78, 216, 0.18); }
.metric-label { @apply text-[10px] uppercase font-semibold; color: var(--color-text-muted); }
.metric-label--primary { color: var(--color-primary); }
.metric-label--warning { color: var(--color-warning); }
.metric-label--info { color: #1d4ed8; }
.metric-value { @apply text-lg font-bold; font-family: var(--font-mono); color: var(--color-text); }
.metric-value--primary { color: var(--color-primary); }
.metric-value--warning { color: var(--color-warning); }
.storage-note { background: rgba(180, 83, 9, 0.08); border: 1px solid rgba(180, 83, 9, 0.18); }
.storage-table-shell { border: 1px solid var(--color-border); }
.storage-table-head { background: var(--color-surface-muted); }
.storage-row { transition: background-color 160ms ease; }
.storage-row:hover { background: rgba(15, 118, 110, 0.05); }
.status-badge { @apply inline-flex items-center rounded-full px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.12em]; }
.status-badge--success { background: rgba(22, 101, 52, 0.10); color: var(--color-success); }
.status-badge--warning { background: rgba(180, 83, 9, 0.12); color: var(--color-warning); }
.status-badge--danger { background: rgba(185, 28, 28, 0.10); color: var(--color-danger); }
</style>
