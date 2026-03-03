<template>
  <div class="space-y-4">
    <div class="bg-white rounded-2xl border border-gray-200 p-4 md:p-5">
      <div class="flex flex-col lg:flex-row lg:items-end gap-3">
        <div class="w-full lg:w-28">
          <label class="block text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-1">Year</label>
          <input
            :value="selectedYear"
            type="number"
            class="w-full px-3 py-2 border border-gray-200 rounded-lg text-xs focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            disabled
          >
        </div>

        <div class="w-full lg:w-40">
          <label class="block text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-1">Month</label>
          <select
            v-model="month"
            class="w-full px-3 py-2 border border-gray-200 rounded-lg text-xs focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="">All Months</option>
            <option v-for="option in monthOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </div>

        <form class="flex-1 flex items-center gap-2" @submit.prevent="loadPresences">
          <div class="relative flex-1">
            <span class="absolute inset-y-0 left-0 pl-2.5 flex items-center text-gray-400">
              <i class="bi bi-search text-[10px]"></i>
            </span>
            <input
              v-model="search"
              type="text"
              placeholder="Search employee, user id, status..."
              class="w-full pl-8 pr-3 py-2 border border-gray-200 rounded-lg text-xs focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            >
          </div>
          <button
            type="submit"
            class="px-3 py-2 text-xs font-semibold border border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
            :disabled="isLoading"
          >
            Apply
          </button>
        </form>

        <div class="flex items-center gap-2">
          <button
            class="px-3 py-2 text-xs font-semibold border border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
            @click="loadPresences"
            :disabled="isLoading"
          >
            <i class="bi bi-arrow-clockwise mr-1"></i> Reload
          </button>
          <button
            class="px-3 py-2 text-xs font-semibold bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50"
            @click="syncPresences"
            :disabled="isSyncing"
          >
            <i class="bi bi-cloud-download mr-1"></i> {{ isSyncing ? 'Syncing...' : 'Sync API' }}
          </button>
        </div>
      </div>

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
          Jika kosong, backend akan memakai env `SAGANSA_PRESENCE_API_URL` dan `SAGANSA_PRESENCE_TOKEN`.
        </p>
        <p class="text-[10px] text-gray-500 mt-1">
          Tombol Sync memanggil endpoint lokal `/api/payroll/presences/sync`, lalu backend akan request ke URL API ini.
        </p>
      </details>
    </div>

    <div v-if="message" class="p-3 rounded-lg border border-emerald-200 bg-emerald-50 text-emerald-700 text-xs">
      {{ message }}
    </div>
    <div v-if="error" class="p-3 rounded-lg border border-red-200 bg-red-50 text-red-700 text-xs">
      {{ error }}
    </div>

    <div class="bg-white rounded-2xl border border-gray-200 overflow-hidden">
      <div class="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
        <div class="text-sm font-semibold text-gray-800">Payroll Presences</div>
        <div class="text-xs text-gray-500">{{ rows.length }} rows</div>
      </div>

      <div class="overflow-x-auto">
        <table class="min-w-full text-xs">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-3 py-2 text-left font-semibold text-gray-500 uppercase">Creator</th>
              <th class="px-3 py-2 text-left font-semibold text-gray-500 uppercase">Store</th>
              <th class="px-3 py-2 text-left font-semibold text-gray-500 uppercase">Shift</th>
              <th class="px-3 py-2 text-left font-semibold text-gray-500 uppercase">Check In</th>
              <th class="px-3 py-2 text-left font-semibold text-gray-500 uppercase">Check Out</th>
              <th class="px-3 py-2 text-left font-semibold text-gray-500 uppercase">Created</th>
              <th class="px-3 py-2 text-left font-semibold text-gray-500 uppercase">Updated</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-if="isLoading">
              <td colspan="7" class="px-3 py-8 text-center text-gray-400">Loading presences...</td>
            </tr>
            <tr v-else-if="rows.length === 0">
              <td colspan="7" class="px-3 py-8 text-center text-gray-400">No presence data</td>
            </tr>
            <tr
              v-for="(row, idx) in rows"
              :key="row.id || `${displayCreator(row)}-${displayCheckIn(row)}-${idx}`"
              class="hover:bg-gray-50"
            >
              <td class="px-3 py-2">{{ displayCreator(row) || '-' }}</td>
              <td class="px-3 py-2">{{ displayStore(row) || '-' }}</td>
              <td class="px-3 py-2">
                <div class="font-semibold text-gray-800">{{ displayShiftName(row) || '-' }}</div>
                <div class="text-[11px] text-gray-500">{{ displayShiftStart(row) || '-' }} - {{ displayShiftEnd(row) || '-' }} ({{ displayShiftDuration(row) || 0 }}h)</div>
              </td>
              <td class="px-3 py-2 whitespace-nowrap">{{ formatDateTime(displayCheckIn(row)) }}</td>
              <td class="px-3 py-2 whitespace-nowrap">{{ formatDateTime(displayCheckOut(row)) }}</td>
              <td class="px-3 py-2 whitespace-nowrap">{{ formatDateTime(displayCreatedAt(row)) }}</td>
              <td class="px-3 py-2 whitespace-nowrap">{{ formatDateTime(displayUpdatedAt(row)) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { historyApi } from '../../api';

const props = defineProps({
  companyId: {
    type: String,
    default: ''
  },
  year: {
    type: [String, Number],
    default: ''
  }
});

const rows = ref([]);
const isLoading = ref(false);
const isSyncing = ref(false);
const error = ref('');
const message = ref('');
const month = ref('');
const search = ref('');
const apiUrlOverride = ref('https://superadmin.sagansa.id/api/presences');
const tokenOverride = ref('1928|DvkiyXPhc5ixN0kx71TU6dai9jxaK0kIqvh5ggyJ81f4bc25');

const selectedYear = computed(() => {
  const parsed = Number(props.year);
  if (Number.isFinite(parsed) && parsed > 1900) return parsed;
  return new Date().getFullYear();
});

const monthOptions = [
  { value: 1, label: 'January' },
  { value: 2, label: 'February' },
  { value: 3, label: 'March' },
  { value: 4, label: 'April' },
  { value: 5, label: 'May' },
  { value: 6, label: 'June' },
  { value: 7, label: 'July' },
  { value: 8, label: 'August' },
  { value: 9, label: 'September' },
  { value: 10, label: 'October' },
  { value: 11, label: 'November' },
  { value: 12, label: 'December' }
];

const formatDateTime = (value) => {
  if (!value) return '-';
  return String(value).replace('T', ' ').slice(0, 19);
};

const parseRawPayload = (rawPayload) => {
  if (!rawPayload) return {};
  if (typeof rawPayload === 'object' && rawPayload !== null) return rawPayload;
  if (typeof rawPayload === 'string') {
    try {
      const parsed = JSON.parse(rawPayload);
      if (parsed && typeof parsed === 'object') return parsed;
    } catch (e) {
      return {};
    }
  }
  return {};
};

const normalizePresenceRow = (item = {}) => {
  const raw = parseRawPayload(item.raw_payload);
  const shiftDuration = Number(
    item.shift_duration
    ?? item.shift_duration_hours
    ?? raw.shift_duration
    ?? raw.shift_duration_hours
    ?? raw.shift_hours
    ?? 0
  ) || 0;

  return {
    ...item,
    creator: item.creator || item.creator_name || item.user_name || item.name || raw.creator || raw.creator_name || raw.user_name || raw.name || '',
    store: item.store || item.store_name || item.branch || item.location || raw.store || raw.store_name || raw.branch || raw.location || '',
    shift_name: item.shift_name || item.shift || raw.shift_name || raw.shift || '',
    shift_start_time: item.shift_start_time || item.shift_start || raw.shift_start_time || raw.shift_start || '',
    shift_end_time: item.shift_end_time || item.shift_end || raw.shift_end_time || raw.shift_end || '',
    shift_duration: shiftDuration,
    check_in: item.check_in || item.check_in_at || item.clock_in || raw.check_in || raw.check_in_at || raw.clock_in || raw.in_time || '',
    check_out: item.check_out || item.check_out_at || item.clock_out || raw.check_out || raw.check_out_at || raw.clock_out || raw.out_time || '',
    created_at: item.created_at || item.source_created_at || raw.created_at || raw.inserted_at || '',
    updated_at: item.updated_at || item.source_updated_at || raw.updated_at || raw.modified_at || raw.last_updated_at || ''
  };
};

const displayCreator = (row) => row?.creator || row?.creator_name || row?.user_name || row?.name || '';
const displayStore = (row) => row?.store || row?.store_name || row?.branch || row?.location || '';
const displayShiftName = (row) => row?.shift_name || row?.shift || '';
const displayShiftStart = (row) => row?.shift_start_time || row?.shift_start || '';
const displayShiftEnd = (row) => row?.shift_end_time || row?.shift_end || '';
const displayShiftDuration = (row) => Number(row?.shift_duration || row?.shift_duration_hours || row?.work_hours || 0);
const displayCheckIn = (row) => row?.check_in || row?.check_in_at || row?.clock_in || '';
const displayCheckOut = (row) => row?.check_out || row?.check_out_at || row?.clock_out || '';
const displayCreatedAt = (row) => row?.created_at || row?.source_created_at || '';
const displayUpdatedAt = (row) => row?.updated_at || row?.source_updated_at || '';

const loadPresences = async () => {
  isLoading.value = true;
  error.value = '';
  message.value = '';
  try {
    const response = await historyApi.getPayrollPresences({
      company_id: props.companyId || undefined,
      year: selectedYear.value,
      month: month.value || undefined,
      search: search.value || undefined,
      limit: 500
    });
    const rawRows = response.data?.data || response.data?.presences || [];
    rows.value = rawRows.map(normalizePresenceRow);
  } catch (err) {
    console.error('Failed to load payroll presences:', err);
    error.value = err.response?.data?.error || 'Failed to load payroll presences';
  } finally {
    isLoading.value = false;
  }
};

const syncPresences = async () => {
  isSyncing.value = true;
  error.value = '';
  message.value = '';
  try {
    const payload = {
      company_id: props.companyId || undefined,
      year: selectedYear.value,
      month: month.value || undefined
    };
    if (apiUrlOverride.value.trim()) payload.api_url = apiUrlOverride.value.trim();
    if (tokenOverride.value.trim()) payload.token = tokenOverride.value.trim();
    if (typeof window !== 'undefined' && tokenOverride.value.trim()) {
      window.localStorage.setItem('payroll_presence_token', tokenOverride.value.trim());
    }

    const response = await historyApi.syncPayrollPresences(payload);
    const data = response.data || {};
    message.value = `Synced ${data.fetched || 0} records (inserted ${data.inserted || 0}, updated ${data.updated || 0}, skipped ${data.skipped || 0}).`;
    await loadPresences();
  } catch (err) {
    console.error('Failed to sync payroll presences:', err);
    error.value = err.response?.data?.error || 'Failed to sync payroll presences';
  } finally {
    isSyncing.value = false;
  }
};

watch(() => [props.companyId, props.year], () => {
  loadPresences();
});

onMounted(() => {
  if (typeof window !== 'undefined') {
    const cachedToken = window.localStorage.getItem('payroll_presence_token') || '';
    if (cachedToken) tokenOverride.value = cachedToken;
  }
  loadPresences();
});
</script>
