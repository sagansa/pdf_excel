<template>
  <div class="surface-card p-6 space-y-5">
    <div class="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-3">
      <div>
        <h3 class="text-lg font-bold text-theme">Remaining Storage Monitor</h3>
        <p class="text-xs text-muted">
          Based on local `stock_monitorings` thresholds and remote `remaining-storages` snapshots
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
      <div class="grid grid-cols-2 md:grid-cols-6 gap-3">
        <div class="metric-card">
          <div class="metric-label">Monitored</div>
          <div class="metric-value">{{ summary.total_monitored }}</div>
        </div>
        <div class="metric-card metric-card--danger">
          <div class="metric-label metric-label--danger">Low</div>
          <div class="metric-value metric-value--danger">{{ summary.low_count }}</div>
        </div>
        <div class="metric-card metric-card--success">
          <div class="metric-label metric-label--success">Safe</div>
          <div class="metric-value metric-value--success">{{ summary.safe_count }}</div>
        </div>
        <div class="metric-card metric-card--warning">
          <div class="metric-label metric-label--warning">No Data</div>
          <div class="metric-value metric-value--warning">{{ summary.missing_count }}</div>
        </div>
        <div class="metric-card metric-card--primary">
          <div class="metric-label metric-label--primary">As Of</div>
          <div class="text-sm font-bold mono" style="color: var(--color-primary)">{{ summary.as_of_date || '-' }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">No Report Store</div>
          <div class="metric-value">{{ summary.missing_report_store_count || 0 }}</div>
        </div>
      </div>

      <div
        v-if="selectedDate"
        class="storage-note rounded-2xl px-4 py-3"
      >
        <div class="text-xs font-semibold" style="color: var(--color-warning)">
          Store belum laporan tanggal {{ selectedDate }}
        </div>
        <div class="text-xs mt-1" style="color: var(--color-warning)">
          <span v-if="missingReportStores.length === 0">Semua store sudah laporan.</span>
          <span v-else>{{ missingReportStores.map((item) => item.store_name).join(', ') }}</span>
        </div>
      </div>

      <div class="overflow-x-auto rounded-2xl storage-table-shell">
        <table class="min-w-full text-xs">
          <thead class="storage-table-head">
            <tr>
              <th class="px-3 py-2 text-left font-semibold uppercase text-muted">Monitoring</th>
              <th class="px-3 py-2 text-left font-semibold uppercase text-muted">Product</th>
              <th class="px-3 py-2 text-right font-semibold uppercase text-muted">Total Stock</th>
              <th class="px-3 py-2 text-right font-semibold uppercase text-muted">Qty Low</th>
              <th class="px-3 py-2 text-left font-semibold uppercase text-muted">Status</th>
              <th class="px-3 py-2 text-left font-semibold uppercase text-muted">Tanggal</th>
            </tr>
          </thead>
          <tbody class="divide-y" style="border-color: var(--color-border)">
            <tr v-if="items.length === 0">
              <td colspan="6" class="px-3 py-8 text-center text-muted">No monitoring data</td>
            </tr>
            <tr v-for="item in items" :key="`${item.monitoring_id}`" class="storage-row">
              <td class="px-3 py-2">
                <div class="font-semibold text-theme">{{ item.monitoring_name || '-' }}</div>
                <div class="text-[11px] text-muted">ID: {{ item.monitoring_id }}</div>
              </td>
              <td class="px-3 py-2">
                <div
                  v-if="Array.isArray(item.product_details) && item.product_details.length > 0"
                  class="space-y-1"
                >
                  <div
                    v-for="product in item.product_details.slice(0, 3)"
                    :key="`${item.monitoring_id}-${product.product_id || product.product_name}`"
                    class="text-[11px] text-theme"
                  >
                    {{ product.product_name || `Product ${product.product_id || '-'}` }}
                    ({{ formatNumber(product.quantity) }} x {{ formatNumber(product.coefficient) }})
                  </div>
                  <div
                    v-if="item.product_details.length > 3"
                    class="text-[10px] text-muted"
                  >
                    +{{ item.product_details.length - 3 }} more
                  </div>
                </div>
                <div v-else class="text-[11px] text-muted">-</div>
              </td>
              <td class="px-3 py-2 text-right font-semibold text-theme mono">
                {{ formatNumber(item.total_stock) }} {{ item.unit_name || '' }}
              </td>
              <td class="px-3 py-2 text-right mono">{{ formatNumber(item.quantity_low) }} {{ item.unit_name || '' }}</td>
              <td class="px-3 py-2">
                <span class="px-2 py-1 rounded-full text-[10px] font-semibold" :class="statusClass(item.status)">
                  {{ statusLabel(item.status) }}
                </span>
              </td>
              <td class="px-3 py-2 mono">{{ item.latest_stock_card_date || '-' }}</td>
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
  if (status === 'low') return 'status-badge status-badge--danger';
  if (status === 'ok') return 'status-badge status-badge--success';
  return 'status-badge status-badge--warning';
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
