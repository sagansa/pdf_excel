<template>
  <div class="space-y-4">
    <div class="bg-white rounded-2xl border border-gray-200 p-4 md:p-5">
      <form class="grid grid-cols-1 md:grid-cols-6 gap-3 items-end" @submit.prevent="applyFilters">
        <div>
          <label class="block text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-1">Date</label>
          <input
            v-model="dateFilter"
            type="date"
            class="w-full px-3 py-2 border border-gray-200 rounded-lg text-xs focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
        </div>
        <div>
          <label class="block text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-1">Store</label>
          <select
            v-model="selectedStoreId"
            class="w-full px-3 py-2 border border-gray-200 rounded-lg text-xs focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="">All Stores</option>
            <option
              v-for="option in storeOptions"
              :key="option.store_id || option.store_name"
              :value="option.store_id || ''"
            >
              {{ option.store_name }}
            </option>
          </select>
        </div>
        <div>
          <label class="block text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-1">Per Page</label>
          <select
            v-model.number="perPage"
            class="w-full px-3 py-2 border border-gray-200 rounded-lg text-xs focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option :value="10">10</option>
            <option :value="15">15</option>
            <option :value="25">25</option>
            <option :value="50">50</option>
            <option :value="100">100</option>
          </select>
        </div>
        <div class="md:col-span-3 flex gap-2">
          <button
            type="submit"
            class="px-3 py-2 text-xs font-semibold bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50"
            :disabled="isLoading"
          >
            <i class="bi bi-funnel mr-1"></i> Apply
          </button>
          <button
            type="button"
            class="px-3 py-2 text-xs font-semibold border border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
            @click="loadRows"
            :disabled="isLoading"
          >
            <i class="bi bi-arrow-clockwise mr-1"></i> Reload
          </button>
        </div>
      </form>
      <p v-if="isPartialResult" class="mt-2 text-[10px] text-amber-700">
        Menampilkan data terbaru (mode cepat). Gunakan filter untuk mempersempit pencarian.
      </p>

      <details class="mt-3 border border-dashed border-gray-200 rounded-lg p-3">
        <summary class="text-xs font-semibold text-gray-600 cursor-pointer">API Override (optional)</summary>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-2 mt-3">
          <input
            v-model="apiUrlOverride"
            type="text"
            placeholder="API URL override"
            class="px-3 py-2 border border-gray-200 rounded-lg text-xs focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
          <input
            v-model="tokenOverride"
            type="password"
            placeholder="Token override"
            class="px-3 py-2 border border-gray-200 rounded-lg text-xs focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
        </div>
        <p class="text-[10px] text-gray-500 mt-2">
          Jika kosong, backend akan memakai env `SAGANSA_REMAINING_STORAGE_API_URL` dan `SAGANSA_REMAINING_STORAGE_TOKEN`.
        </p>
      </details>
    </div>

    <div v-if="error" class="p-3 rounded-lg border border-red-200 bg-red-50 text-red-700 text-xs">
      {{ error }}
    </div>

    <div class="bg-white rounded-2xl border border-gray-200 overflow-hidden">
      <div class="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
        <div class="text-sm font-semibold text-gray-800">Remaining Storages</div>
        <div class="text-xs text-gray-500">
          {{ rows.length }} rows • page {{ page }} / {{ lastPage }} • total {{ total }}
        </div>
      </div>

      <div class="overflow-x-auto">
        <table class="min-w-full text-xs">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-3 py-2 text-left font-semibold text-gray-500 uppercase">Date</th>
              <th class="px-3 py-2 text-left font-semibold text-gray-500 uppercase">Store</th>
              <th class="px-3 py-2 text-left font-semibold text-gray-500 uppercase">User</th>
              <th class="px-3 py-2 text-left font-semibold text-gray-500 uppercase">Description</th>
              <th class="px-3 py-2 text-right font-semibold text-gray-500 uppercase">Details</th>
              <th class="px-3 py-2 text-right font-semibold text-gray-500 uppercase">Total Qty</th>
              <th class="px-3 py-2 text-right font-semibold text-gray-500 uppercase">Action</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-if="isLoading">
              <td colspan="7" class="px-3 py-8 text-center text-gray-400">Loading remaining storages...</td>
            </tr>
            <tr v-else-if="rows.length === 0">
              <td colspan="7" class="px-3 py-8 text-center text-gray-400">No remaining storage data</td>
            </tr>
            <template v-for="(row, idx) in rows" :key="row.id || `${row.date || 'row'}-${idx}`">
              <tr class="hover:bg-gray-50">
                <td class="px-3 py-2 whitespace-nowrap">{{ formatDate(row.date) }}</td>
                <td class="px-3 py-2">{{ row.store_name || '-' }}</td>
                <td class="px-3 py-2">{{ row.user_name || '-' }}</td>
                <td class="px-3 py-2">{{ row.description || '-' }}</td>
                <td class="px-3 py-2 text-right">{{ row.detail_count || 0 }}</td>
                <td class="px-3 py-2 text-right">{{ formatNumber(row.total_quantity) }}</td>
                <td class="px-3 py-2 text-right">
                  <button
                    type="button"
                    class="px-2 py-1 text-[11px] font-semibold border border-gray-200 rounded-md hover:bg-gray-50"
                    :disabled="Boolean(detailLoadingKeys[buildRowKey(row, idx)])"
                    @click="toggleDetails(row, idx)"
                  >
                    {{ Boolean(detailLoadingKeys[buildRowKey(row, idx)]) ? 'Loading...' : (isExpanded(row, idx) ? 'Hide' : 'Detail') }}
                  </button>
                </td>
              </tr>
              <tr v-if="isExpanded(row, idx)" class="bg-gray-50">
                <td colspan="7" class="px-3 py-3">
                  <div v-if="Boolean(detailLoadingKeys[buildRowKey(row, idx)])" class="text-[11px] text-gray-500">
                    Loading detail items...
                  </div>
                  <div v-else-if="(row.details || []).length === 0" class="text-[11px] text-gray-500">
                    No detail items.
                  </div>
                  <div v-else class="overflow-x-auto">
                    <table class="min-w-full text-[11px] border border-gray-200 rounded-md bg-white">
                      <thead class="bg-gray-100">
                        <tr>
                          <th class="px-2 py-1.5 text-left font-semibold text-gray-500 uppercase">Product</th>
                          <th class="px-2 py-1.5 text-left font-semibold text-gray-500 uppercase">Unit</th>
                          <th class="px-2 py-1.5 text-right font-semibold text-gray-500 uppercase">Quantity</th>
                        </tr>
                      </thead>
                      <tbody class="divide-y divide-gray-100">
                        <tr
                          v-for="(detail, detailIdx) in row.details"
                          :key="detail.id || `${detail.product_id || 'item'}-${detailIdx}`"
                        >
                          <td class="px-2 py-1.5">{{ detail.product_name || detail.product_id || '-' }}</td>
                          <td class="px-2 py-1.5">{{ detail.unit_name || detail.unit_id || '-' }}</td>
                          <td class="px-2 py-1.5 text-right">{{ formatNumber(detail.quantity) }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>

      <div class="px-4 py-3 border-t border-gray-100 flex items-center justify-end gap-2">
        <button
          class="px-3 py-1.5 text-xs font-medium border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50"
          :disabled="isLoading || page <= 1"
          @click="goToPreviousPage"
        >
          Prev
        </button>
        <button
          class="px-3 py-1.5 text-xs font-medium border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50"
          :disabled="isLoading || page >= lastPage"
          @click="goToNextPage"
        >
          Next
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue';
import { historyApi } from '../../api';

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

const formatDate = (value) => {
  if (!value) return '-';
  return String(value).slice(0, 10);
};

const formatNumber = (value) => {
  const parsed = Number(value || 0);
  if (!Number.isFinite(parsed)) return '0';
  return parsed.toLocaleString('en-US', { maximumFractionDigits: 2 });
};

const buildListParams = () => {
  const params = {
    page: page.value,
    per_page: perPage.value,
    recent_only: 1,
    scan_pages: 4
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

const buildRowKey = (row, idx) => {
  return String(row?.id || `${row?.date || 'row'}-${idx}`);
};

const isExpanded = (row, idx) => {
  return Boolean(expandedKeys.value[buildRowKey(row, idx)]);
};

const toggleDetails = async (row, idx) => {
  const key = buildRowKey(row, idx);
  const currentlyExpanded = Boolean(expandedKeys.value[key]);
  if (currentlyExpanded) {
    expandedKeys.value = {
      ...expandedKeys.value,
      [key]: false
    };
    return;
  }

  expandedKeys.value = {
    ...expandedKeys.value,
    [key]: true
  };

  if (row?._detailsLoaded || !row?.id) {
    return;
  }

  detailLoadingKeys.value = {
    ...detailLoadingKeys.value,
    [key]: true
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
      [key]: false
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
      ? [...incomingRows].sort((a, b) => {
          const left = String(a?.date || '');
          const right = String(b?.date || '');
          if (left === right) return Number(b?.id || 0) - Number(a?.id || 0);
          return left < right ? 1 : -1;
        }).map((item) => ({
          ...item,
          details: Array.isArray(item?.details) ? item.details : [],
          _detailsLoaded: false
        }))
      : [];
    expandedKeys.value = {};
    detailLoadingKeys.value = {};

    const pagination = data.pagination || {};
    page.value = Number(pagination.page || page.value) || 1;
    perPage.value = Number(pagination.per_page || perPage.value) || 15;
    total.value = Number(pagination.total || rows.value.length) || 0;
    const computedLastPage = Number(pagination.last_page) || Math.max(1, Math.ceil(total.value / Math.max(1, perPage.value)));
    lastPage.value = Math.max(1, computedLastPage);
    const incomingStoreOptions = Array.isArray(data.store_options) ? data.store_options : [];
    storeOptions.value = incomingStoreOptions;
    if (selectedStoreId.value && !storeOptions.value.some((item) => String(item.store_id || '') === String(selectedStoreId.value))) {
      selectedStoreId.value = '';
    }
    isPartialResult.value = Boolean(data?.meta?.partial_result);

    if (typeof window !== 'undefined' && tokenOverride.value.trim()) {
      window.localStorage.setItem('remaining_storage_token', tokenOverride.value.trim());
    }
  } catch (err) {
    console.error('Failed to load remaining storages:', err);
    error.value = err.response?.data?.error || 'Failed to load remaining storages';
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
