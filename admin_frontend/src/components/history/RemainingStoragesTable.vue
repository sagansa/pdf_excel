<template>
  <div class="space-y-5">
    <SectionCard
      title="Remaining Storage Filters"
      subtitle="Filter snapshot storage cards by date, store, and page size."
      body-class="p-4 md:p-5"
    >
      <div class="grid grid-cols-1 gap-3 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)_180px_auto] xl:items-end">
        <FormField label="Date" label-class="text-[10px]">
          <TextInput
            v-model="dateFilter"
            type="date"
            size="sm"
          />
        </FormField>

        <FormField label="Store" label-class="text-[10px]">
          <SelectInput
            v-model="selectedStoreId"
            :options="storeSelectOptions"
            placeholder="All Stores"
            size="sm"
          />
        </FormField>

        <FormField label="Per Page" label-class="text-[10px]">
          <SelectInput
            :model-value="String(perPage)"
            :options="perPageOptions"
            size="sm"
            @update:model-value="perPage = Number($event || 15)"
          />
        </FormField>

        <div class="flex flex-wrap items-center gap-2 xl:justify-end">
          <StatCard
            :value="total"
            label="total rows"
            wrapper-class="!rounded-xl !px-2.5 !py-1"
            label-class="!text-[10px] !font-medium"
            value-class="!text-xs"
          />
          <Button
            variant="primary"
            size="md"
            icon="bi bi-funnel"
            :loading="isLoading"
            @click="applyFilters"
          >
            Apply
          </Button>
          <Button
            variant="secondary"
            size="md"
            icon="bi bi-arrow-clockwise"
            :loading="isLoading"
            @click="loadRows"
          >
            Reload
          </Button>
        </div>
      </div>

      <div class="mt-4 flex flex-wrap items-center gap-2" v-if="isPartialResult || error">
        <Alert
          v-if="isPartialResult"
          variant="warning"
          message="Fast mode active, only recent pages scanned"
          icon="bi bi-lightning-charge-fill"
          wrapper-class="!py-2"
          :show-icon="true"
        />

        <Alert
          v-if="error"
          variant="danger"
          :message="error"
          icon="bi bi-exclamation-octagon-fill"
          wrapper-class="!py-2"
          :show-icon="true"
        />
      </div>

      <details class="remaining-debug">
        <summary class="remaining-debug__summary">
          Debug Override
        </summary>

        <div class="grid grid-cols-1 gap-3 pt-3 md:grid-cols-2">
          <FormField
            label="API URL Override"
            label-class="text-[10px]"
            hint="If blank, backend env is used."
          >
            <TextInput
              v-model="apiUrlOverride"
              size="sm"
              placeholder="http://127.0.0.1:8000/api/remaining-storages"
            />
          </FormField>

          <FormField
            label="Token Override"
            label-class="text-[10px]"
            hint="Use only for local debugging."
          >
            <TextInput
              v-model="tokenOverride"
              type="password"
              size="sm"
              placeholder="Bearer token"
            />
          </FormField>
        </div>
      </details>
    </SectionCard>

    <div class="overflow-hidden rounded-2xl border border-border">
      <div class="bg-surface-muted border-b border-border px-4 py-3">
        <div class="flex items-center justify-between">
          <div>
            <h3 class="text-sm font-semibold text-theme">Remaining Storage Snapshots</h3>
            <p class="mt-1 text-xs text-muted">
              {{ rows.length }} rows on this page, page {{ page }} of {{ lastPage }}
            </p>
          </div>
          <StatCard
            :value="rows.length"
            label="visible"
            wrapper-class="!rounded-xl !px-2.5 !py-1"
            label-class="!text-[10px] !font-medium"
            value-class="!text-xs"
          />
        </div>
      </div>

      <table class="min-w-full text-sm">
        <thead class="bg-surface-muted border-b border-border">
          <tr>
            <th class="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.18em] text-muted min-w-[112px]">Date</th>
            <th class="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.18em] text-muted min-w-[180px]">Store</th>
            <th class="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.18em] text-muted min-w-[160px]">User</th>
            <th class="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.18em] text-muted min-w-[260px]">Description</th>
            <th class="px-4 py-3 text-right text-[11px] font-semibold uppercase tracking-[0.18em] text-muted w-[96px]">Lines</th>
            <th class="px-4 py-3 text-right text-[11px] font-semibold uppercase tracking-[0.18em] text-muted w-[120px]">Total Qty</th>
            <th class="px-4 py-3 text-right text-[11px] font-semibold uppercase tracking-[0.18em] text-muted w-[96px]">Action</th>
          </tr>
        </thead>

        <tbody class="divide-y" style="border-color: var(--color-border)">
          <tr v-if="isLoading">
            <td colspan="7" class="px-6 py-12 text-center">
              <div class="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl text-lg" style="background: var(--color-surface-muted); color: var(--color-text-muted);">
                <i class="bi bi-arrow-repeat spin"></i>
              </div>
              <p class="text-sm font-semibold text-theme">Loading remaining storages</p>
              <p class="mt-1 text-xs text-muted">Fetching the latest storage snapshots.</p>
            </td>
          </tr>

          <tr v-else-if="rows.length === 0">
            <td colspan="7" class="px-6 py-12 text-center">
              <div class="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl text-lg" style="background: var(--color-surface-muted); color: var(--color-text-muted);">
                <i class="bi bi-inboxes"></i>
              </div>
              <p class="text-sm font-semibold text-theme">No remaining storage data</p>
              <p class="mt-1 text-xs text-muted">Try adjusting the date or store filter.</p>
            </td>
          </tr>

          <template v-for="(row, idx) in rows" :key="row.id || `${row.date || 'row'}-${idx}`">
            <tr class="transition-colors hover:bg-surface-muted/50">
              <td class="px-4 py-3 align-top text-sm text-theme whitespace-nowrap">
                <span class="rounded-lg px-2.5 py-1 text-xs font-semibold" style="background: rgba(15, 118, 110, 0.10); color: var(--color-primary);">
                  {{ formatDate(row.date) }}
                </span>
              </td>
              <td class="px-4 py-3 align-top text-sm">
                <div class="flex flex-col gap-1">
                  <span class="leading-tight text-theme">{{ row.store_name || '-' }}</span>
                  <span class="text-[11px] text-muted">Store snapshot</span>
                </div>
              </td>
              <td class="px-4 py-3 align-top text-sm text-theme">
                {{ row.user_name || '-' }}
              </td>
              <td class="px-4 py-3 align-top text-sm">
                <div class="flex flex-col gap-1">
                  <span class="leading-tight text-theme">{{ row.description || '-' }}</span>
                  <span class="text-[11px] text-muted">ID {{ row.id || '-' }}</span>
                </div>
              </td>
              <td class="px-4 py-3 align-top text-right text-sm">
                <span class="inline-flex min-w-[34px] items-center justify-center rounded-lg px-2 py-1 text-xs font-semibold" style="background: color-mix(in srgb, var(--color-surface-muted) 65%, black 35%); color: var(--color-text);">
                  {{ row.detail_count || 0 }}
                </span>
              </td>
              <td class="px-4 py-3 align-top text-right text-sm font-semibold text-theme">
                {{ formatNumber(row.total_quantity) }}
              </td>
              <td class="px-4 py-3 align-top text-right text-sm">
                <Button
                  variant="secondary"
                  size="sm"
                  :loading="Boolean(detailLoadingKeys[buildRowKey(row, idx)])"
                  @click="toggleDetails(row, idx)"
                >
                  {{ Boolean(detailLoadingKeys[buildRowKey(row, idx)]) ? 'Loading' : (isExpanded(row, idx) ? 'Hide' : 'Detail') }}
                </Button>
              </td>
            </tr>

            <tr v-if="isExpanded(row, idx)" class="bg-surface-muted/60">
              <td colspan="7" class="p-4 md:p-5">
                <div class="overflow-hidden rounded-2xl border border-border" style="background: var(--color-surface);">
                  <div class="border-b px-4 py-3" style="background: color-mix(in srgb, var(--color-surface-muted) 78%, black 22%); border-color: var(--color-border);">
                    <div class="flex items-center justify-between">
                      <div>
                        <h4 class="text-sm font-semibold text-theme">Detail Items</h4>
                        <p class="mt-1 text-xs text-muted">
                          {{ row.store_name || 'Unknown Store' }} • {{ formatDate(row.date) }}
                        </p>
                      </div>
                      <StatCard
                        :value="row.detail_count || 0"
                        label="items"
                        wrapper-class="!rounded-xl !px-2.5 !py-1"
                        label-class="!text-[10px] !font-medium"
                        value-class="!text-xs"
                      />
                    </div>
                  </div>

                  <div
                    v-if="Boolean(detailLoadingKeys[buildRowKey(row, idx)])"
                    class="px-4 py-8 text-center text-xs text-muted"
                  >
                    Loading detail items...
                  </div>

                  <div
                    v-else-if="(row.details || []).length === 0"
                    class="px-4 py-8 text-center text-xs text-muted"
                  >
                    No detail items.
                  </div>

                  <div v-else class="overflow-x-auto">
                    <table class="min-w-full text-xs">
                      <thead class="bg-surface-muted border-b border-border">
                        <tr>
                          <th class="px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-[0.16em] text-muted min-w-[240px]">Product</th>
                          <th class="px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-[0.16em] text-muted min-w-[120px]">Unit</th>
                          <th class="px-4 py-2.5 text-right text-[10px] font-semibold uppercase tracking-[0.16em] text-muted w-[120px]">Quantity</th>
                        </tr>
                      </thead>
                      <tbody class="divide-y" style="border-color: var(--color-border)">
                        <tr
                          v-for="(detail, detailIdx) in row.details"
                          :key="detail.id || `${detail.product_id || 'item'}-${detailIdx}`"
                          class="transition-colors hover:bg-surface-muted/30"
                        >
                          <td class="px-4 py-2.5 text-sm text-theme">
                            {{ detail.product_name || detail.product_id || '-' }}
                          </td>
                          <td class="px-4 py-2.5 text-sm text-theme">
                            {{ detail.unit_name || detail.unit_id || '-' }}
                          </td>
                          <td class="px-4 py-2.5 text-right text-sm font-semibold text-theme">
                            {{ formatNumber(detail.quantity) }}
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>

      <div class="bg-surface-muted border-t border-border px-4 py-3">
        <div class="flex items-center justify-between gap-3">
          <span class="text-xs text-muted">
            Showing page {{ page }} of {{ lastPage }}
          </span>

          <div class="flex items-center gap-2">
            <Button
              variant="secondary"
              size="md"
              :disabled="isLoading || page <= 1"
              @click="goToPreviousPage"
            >
              Prev
            </Button>
            <Button
              variant="secondary"
              size="md"
              :disabled="isLoading || page >= lastPage"
              @click="goToNextPage"
            >
              Next
            </Button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { historyApi } from '../../api';
import FormField from '../ui/FormField.vue';
import SectionCard from '../ui/SectionCard.vue';
import SelectInput from '../ui/SelectInput.vue';
import TextInput from '../ui/TextInput.vue';
import StatCard from '../ui/StatCard.vue';
import Button from '../ui/Button.vue';
import Alert from '../ui/Alert.vue';

const rows = ref([]);
const isLoading = ref(false);
const error = ref('');
const page = ref(1);
const perPage = ref(15);
const total = ref(0);
const lastPage = ref(1);
const dateFilter = ref('');
const selectedStoreId = ref('');
const storeOptions = ref([]);
const apiUrlOverride = ref('https://superadmin.sagansa.id/api/remaining-storages');
const tokenOverride = ref('');
const expandedKeys = ref({});
const detailLoadingKeys = ref({});
const isPartialResult = ref(false);

const perPageOptions = [
  { value: '10', label: '10 rows' },
  { value: '15', label: '15 rows' },
  { value: '25', label: '25 rows' },
  { value: '50', label: '50 rows' },
  { value: '100', label: '100 rows' },
];

const storeSelectOptions = computed(() => [
  { value: '', label: 'All Stores' },
  ...(storeOptions.value || []).map((option) => ({
    value: option.store_id || '',
    label: option.store_name,
  })),
]);

const formatDate = (value) => {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value).slice(0, 10);
  return date.toLocaleDateString('id-ID', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
};

const formatNumber = (value) => {
  const parsed = Number(value || 0);
  if (!Number.isFinite(parsed)) return '0';
  return parsed.toLocaleString('id-ID', { maximumFractionDigits: 2 });
};

const buildListParams = () => {
  const params = {
    page: page.value,
    per_page: perPage.value,
    recent_only: 1,
    scan_pages: 4,
  };
  if (dateFilter.value) params.date = dateFilter.value;
  if (selectedStoreId.value) params.store_id = selectedStoreId.value;
  if (apiUrlOverride.value.trim()) params.api_url = apiUrlOverride.value.trim();
  if (tokenOverride.value.trim()) params.token = tokenOverride.value.trim();
  return params;
};

const buildDetailParams = () => {
  const params = {};
  if (apiUrlOverride.value.trim()) params.api_url = apiUrlOverride.value.trim();
  if (tokenOverride.value.trim()) params.token = tokenOverride.value.trim();
  return params;
};

const buildRowKey = (row, idx) => String(row?.id || `${row?.date || 'row'}-${idx}`);

const isExpanded = (row, idx) => Boolean(expandedKeys.value[buildRowKey(row, idx)]);

const toggleDetails = async (row, idx) => {
  const key = buildRowKey(row, idx);
  const currentlyExpanded = Boolean(expandedKeys.value[key]);

  if (currentlyExpanded) {
    expandedKeys.value = {
      ...expandedKeys.value,
      [key]: false,
    };
    return;
  }

  expandedKeys.value = {
    ...expandedKeys.value,
    [key]: true,
  };

  if (row?._detailsLoaded || !row?.id) {
    return;
  }

  detailLoadingKeys.value = {
    ...detailLoadingKeys.value,
    [key]: true,
  };

  try {
    const response = await historyApi.getRemainingStorageDetails(row.id, buildDetailParams());
    const detailData = response?.data?.data || {};
    row.details = Array.isArray(detailData.details) ? detailData.details : [];
    row.detail_count = Number(detailData.detail_count || row.details.length) || 0;
    row.total_quantity = Number(detailData.total_quantity || 0) || 0;
    row.description = detailData.description || row.description || '';
    row.store_name = detailData.store_name || row.store_name || '';
    row.user_name = detailData.user_name || row.user_name || '';
    row._detailsLoaded = true;
  } catch (err) {
    console.error('Failed to load remaining storage details:', err);
  } finally {
    detailLoadingKeys.value = {
      ...detailLoadingKeys.value,
      [key]: false,
    };
  }
};

const loadRows = async () => {
  isLoading.value = true;
  error.value = '';

  try {
    const response = await historyApi.getRemainingStorages(buildListParams());
    const data = response.data || {};
    const incomingRows = data.data || data.remaining_storages || [];

    rows.value = Array.isArray(incomingRows)
      ? [...incomingRows]
        .sort((a, b) => {
          const left = String(a?.date || '');
          const right = String(b?.date || '');
          if (left === right) return Number(b?.id || 0) - Number(a?.id || 0);
          return left < right ? 1 : -1;
        })
        .map((item) => ({
          ...item,
          details: Array.isArray(item?.details) ? item.details : [],
          _detailsLoaded: false,
        }))
      : [];

    expandedKeys.value = {};
    detailLoadingKeys.value = {};

    const pagination = data.pagination || {};
    page.value = Number(pagination.page || page.value) || 1;
    perPage.value = Number(pagination.per_page || perPage.value) || 15;
    total.value = Number(pagination.total || rows.value.length) || 0;
    lastPage.value = Math.max(
      1,
      Number(pagination.last_page) || Math.ceil(total.value / Math.max(1, perPage.value))
    );

    const incomingStoreOptions = Array.isArray(data.store_options) ? data.store_options : [];
    storeOptions.value = incomingStoreOptions;

    if (
      selectedStoreId.value &&
      !storeOptions.value.some((item) => String(item.store_id || '') === String(selectedStoreId.value))
    ) {
      selectedStoreId.value = '';
    }

    isPartialResult.value = Boolean(data?.meta?.partial_result);

    if (typeof window !== 'undefined' && tokenOverride.value.trim()) {
      window.localStorage.setItem('remaining_storage_token', tokenOverride.value.trim());
    }
  } catch (err) {
    console.error('Failed to load remaining storages:', {
      message: err?.message,
      status: err?.response?.status,
      data: err?.response?.data,
      url: err?.config?.url,
      params: err?.config?.params,
    });

    const backendError = err?.response?.data?.error;
    const backendCode = err?.response?.data?.code;
    error.value = backendError
      ? `${backendError}${backendCode ? ` (${backendCode})` : ''}`
      : 'Failed to load remaining storages';
  } finally {
    isLoading.value = false;
  }
};

const applyFilters = async () => {
  page.value = 1;
  await loadRows();
};

const goToPreviousPage = async () => {
  if (page.value <= 1) return;
  page.value -= 1;
  await loadRows();
};

const goToNextPage = async () => {
  if (page.value >= lastPage.value) return;
  page.value += 1;
  await loadRows();
};

onMounted(async () => {
  if (typeof window !== 'undefined') {
    const cachedToken = window.localStorage.getItem('remaining_storage_token') || '';
    if (cachedToken) tokenOverride.value = cachedToken;
  }
  await loadRows();
});
</script>

<style scoped>
.spin {
  animation: spin 1s linear infinite;
}

.remaining-debug {
  @apply mt-4 rounded-2xl border p-3;
  border-color: var(--color-border);
  background: color-mix(in srgb, var(--color-surface-muted) 74%, transparent 26%);
}

.remaining-debug__summary {
  @apply cursor-pointer text-xs font-semibold;
  color: var(--color-text-muted);
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
