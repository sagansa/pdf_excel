<template>
  <div class="space-y-4">
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
      <StatCard
        label="Records"
        :value="rows.length"
        subtext="baris dimuat · limit 500"
        icon="bi bi-journal-text"
        wrapper-class="border-border"
      />
      <StatCard
        label="Employees"
        :value="uniqueEmployees"
        subtext="karyawan unik terdata"
        icon="bi bi-people"
        wrapper-class="border-border"
      />
      <StatCard
        label="Period"
        :value="periodRange"
        subtext="rentang tanggal check-in"
        icon="bi bi-calendar3"
        wrapper-class="border-border"
      />
    </div>

    <TableShell>
      <template #toolbar>
        <div class="hrd-toolbar-wrap">
          <div class="hrd-toolbar">
            <div class="hrd-toolbar__filters">
              <div class="hrd-toolbar__field">
                <label class="hrd-toolbar__label" for="hrd-filter-company">Company</label>
                <SelectInput
                  id="hrd-filter-company"
                  v-model="companyId"
                  :options="companyOptions"
                  placeholder="All Companies"
                  size="sm"
                  class="hrd-toolbar__company"
                />
              </div>
              <div class="hrd-toolbar__field">
                <label class="hrd-toolbar__label" for="hrd-filter-year">Year</label>
                <SelectInput
                  id="hrd-filter-year"
                  v-model="year"
                  :options="yearOptions"
                  size="sm"
                  class="hrd-toolbar__year"
                />
              </div>
              <div class="hrd-toolbar__field">
                <label class="hrd-toolbar__label" for="hrd-filter-month">Month</label>
                <SelectInput
                  id="hrd-filter-month"
                  v-model="month"
                  :options="monthOptions"
                  placeholder="All Months"
                  size="sm"
                  class="hrd-toolbar__month"
                />
              </div>
              <div class="hrd-toolbar__field">
                <label class="hrd-toolbar__label" for="hrd-filter-search">Search</label>
                <div class="hrd-toolbar__search">
                  <i class="bi bi-search" aria-hidden="true"></i>
                  <TextInput
                    id="hrd-filter-search"
                    v-model="search"
                    placeholder="Cari karyawan, status…"
                    size="sm"
                  />
                </div>
              </div>
            </div>
            <span class="hrd-toolbar__total" role="status">{{ rows.length }} of 500 records</span>
          </div>

          <div class="hrd-override">
            <button
              type="button"
              class="hrd-override__toggle"
              :aria-expanded="showOverride"
              @click="showOverride = !showOverride"
            >
              <i class="bi bi-sliders" aria-hidden="true"></i>
              <span>API override</span>
              <i
                class="bi bi-chevron-down hrd-override__chevron"
                :class="{ 'hrd-override__chevron--open': showOverride }"
                aria-hidden="true"
              ></i>
            </button>
            <div v-show="showOverride" class="hrd-override__body">
              <div class="hrd-override__grid">
                <FormField label="API URL">
                  <TextInput
                    v-model="apiUrlOverride"
                    placeholder="https://…/api/presences"
                    size="sm"
                  />
                </FormField>
                <FormField label="Token">
                  <TextInput
                    v-model="tokenOverride"
                    type="password"
                    placeholder="Token (opsional)"
                    size="sm"
                  />
                </FormField>
              </div>
              <p class="hrd-override__hint">
                Kosongkan untuk memakai env <code>SAGANSA_PRESENCE_API_URL</code> /
                <code>SAGANSA_PRESENCE_TOKEN</code> di backend. Sync memanggil
                <code>/api/payroll/presences/sync</code> lokal, lalu backend menarik data dari URL ini.
              </p>
            </div>
          </div>
        </div>
      </template>

      <table class="min-w-full hrd-table">
        <thead class="hrd-table-head">
          <tr>
            <th scope="col" class="hrd-th">Employee</th>
            <th scope="col" class="hrd-th">Shift</th>
            <th scope="col" class="hrd-th">Check In</th>
            <th scope="col" class="hrd-th">Check Out</th>
            <th scope="col" class="hrd-th hrd-th--meta">Created</th>
            <th scope="col" class="hrd-th hrd-th--meta">Updated</th>
          </tr>
        </thead>
        <tbody class="hrd-tbody">
          <tr v-if="isLoading">
            <td colspan="6" class="hrd-state">
              <span class="spinner-border h-8 w-8" style="color: var(--color-primary)" role="status"></span>
              <p class="hrd-state__title">Loading presences…</p>
            </td>
          </tr>
          <tr v-else-if="rows.length === 0">
            <td colspan="6" class="hrd-state">
              <i class="bi bi-calendar-x hrd-state__icon" aria-hidden="true"></i>
              <p class="hrd-state__title">No presence data</p>
              <p class="hrd-state__hint">Ubah filter atau periode, atau jalankan Sync API untuk menarik data terbaru.</p>
            </td>
          </tr>
          <tr
            v-for="(row, idx) in rows"
            :key="row.id || `${displayCreator(row)}-${displayCheckIn(row)}-${idx}`"
          >
            <td class="hrd-td hrd-td--employee">
              <div class="hrd-employee" :title="displayCreator(row) || undefined">
                <span class="hrd-employee__name">{{ displayCreator(row) || '(tanpa nama)' }}</span>
                <span class="hrd-employee__store">{{ displayStore(row) || '—' }}</span>
              </div>
            </td>
            <td class="hrd-td hrd-td--shift">
              <span class="hrd-shift__name">{{ displayShiftName(row) || '—' }}</span>
              <span class="hrd-shift__time mono">
                {{ displayShiftStart(row) || '—' }}–{{ displayShiftEnd(row) || '—' }} · {{ displayShiftDuration(row) }}h
              </span>
            </td>
            <td class="hrd-td hrd-td--mono" :title="displayCheckIn(row) || undefined">
              {{ formatDateTime(displayCheckIn(row)) }}
            </td>
            <td class="hrd-td hrd-td--mono" :title="displayCheckOut(row) || undefined">
              <span v-if="displayCheckOut(row)" >{{ formatDateTime(displayCheckOut(row)) }}</span>
              <span v-else class="hrd-td--pending" title="Check-out belum tercatat">—</span>
            </td>
            <td class="hrd-td hrd-td--mono hrd-td--meta hrd-td--muted" :title="displayCreatedAt(row) || undefined">
              {{ formatDateTime(displayCreatedAt(row)) }}
            </td>
            <td class="hrd-td hrd-td--mono hrd-td--meta hrd-td--muted" :title="displayUpdatedAt(row) || undefined">
              {{ formatDateTime(displayUpdatedAt(row)) }}
            </td>
          </tr>
        </tbody>
      </table>

      <template #footer>
        <div class="hrd-footer">
          <span>Showing <span class="mono">{{ rows.length }}</span> row{{ rows.length !== 1 ? 's' : '' }}</span>
          <span class="mono">limit 500 / request</span>
        </div>
      </template>
    </TableShell>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { historyApi } from '../../api';
import { useNotifications } from '../../composables/useNotifications';
import { useCompanyStore } from '../../stores/companies';
import FormField from '../ui/FormField.vue';
import SelectInput from '../ui/SelectInput.vue';
import StatCard from '../ui/StatCard.vue';
import TableShell from '../ui/TableShell.vue';
import TextInput from '../ui/TextInput.vue';

const companyStore = useCompanyStore();
const notifications = useNotifications();

const rows = ref([]);
const isLoading = ref(false);
const isSyncing = ref(false);
const companyId = ref('');
const year = ref(new Date().getFullYear());
const month = ref('');
const search = ref('');
const showOverride = ref(false);
const apiUrlOverride = ref('https://superadmin.sagansa.id/api/presences');
const tokenOverride = ref('');

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

const currentYear = new Date().getFullYear();
const yearOptions = computed(() => {
  const options = [];
  for (let y = currentYear + 1; y >= currentYear - 5; y -= 1) {
    options.push({ label: String(y), value: y });
  }
  return options;
});

const companyOptions = computed(() =>
  companyStore.companies.map((c) => ({ label: c.name, value: c.id }))
);

// SelectInput mengembalikan string dari <select>, jadi normalisasi ke angka.
const selectedYear = computed(() => {
  const parsed = Number(year.value);
  if (Number.isFinite(parsed) && parsed > 1900) return parsed;
  return currentYear;
});

const MONTH_SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

const formatDateShort = (value) => {
  const [y, m, d] = String(value).split('-');
  const mIndex = Number(m) - 1;
  if (!y || !d || mIndex < 0 || mIndex > 11) return value;
  return `${d} ${MONTH_SHORT[mIndex]} ${y}`;
};

const formatDateTime = (value) => {
  if (!value) return '—';
  const [date, time = ''] = String(value).replace('T', ' ').split(' ');
  return `${formatDateShort(date)} ${time.slice(0, 5)}`.trim();
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
const displayShiftStart = (row) => String(row?.shift_start_time || row?.shift_start || '').slice(0, 5);
const displayShiftEnd = (row) => String(row?.shift_end_time || row?.shift_end || '').slice(0, 5);
const displayShiftDuration = (row) => Number(row?.shift_duration || row?.shift_duration_hours || row?.work_hours || 0);
const displayCheckIn = (row) => row?.check_in || row?.check_in_at || row?.clock_in || '';
const displayCheckOut = (row) => row?.check_out || row?.check_out_at || row?.clock_out || '';
const displayCreatedAt = (row) => row?.created_at || row?.source_created_at || '';
const displayUpdatedAt = (row) => row?.updated_at || row?.source_updated_at || '';

const uniqueEmployees = computed(() => {
  const names = new Set();
  rows.value.forEach((row) => {
    const name = displayCreator(row);
    if (name) names.add(name);
  });
  return names.size;
});

const periodRange = computed(() => {
  const dates = rows.value
    .map((row) => String(displayCheckIn(row)).slice(0, 10))
    .filter(Boolean)
    .sort();
  if (!dates.length) return '—';
  const first = dates[0];
  const last = dates[dates.length - 1];
  return first === last ? formatDateShort(first) : `${formatDateShort(first)} – ${formatDateShort(last)}`;
});

const loadPresences = async () => {
  isLoading.value = true;
  try {
    const response = await historyApi.getPayrollPresences({
      company_id: companyId.value || undefined,
      year: selectedYear.value,
      month: month.value || undefined,
      search: search.value || undefined,
      limit: 500
    });
    const rawRows = response.data?.data || response.data?.presences || [];
    rows.value = rawRows.map(normalizePresenceRow);
  } catch (err) {
    console.error('Failed to load payroll presences:', err);
    notifications.error(err.response?.data?.error || 'Failed to load payroll presences');
  } finally {
    isLoading.value = false;
  }
};

const syncPresences = async () => {
  isSyncing.value = true;
  try {
    const payload = {
      company_id: companyId.value || undefined,
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
    notifications.success(
      `Synced ${data.fetched || 0} records (inserted ${data.inserted || 0}, updated ${data.updated || 0}, skipped ${data.skipped || 0}).`,
      { title: 'Sync API' }
    );
    await loadPresences();
  } catch (err) {
    console.error('Failed to sync payroll presences:', err);
    notifications.error(err.response?.data?.error || 'Failed to sync payroll presences');
  } finally {
    isSyncing.value = false;
  }
};

let searchTimer = null;
watch(search, () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    loadPresences();
  }, 450);
});
onBeforeUnmount(() => clearTimeout(searchTimer));

watch([companyId, month, selectedYear], () => {
  loadPresences();
});

onMounted(async () => {
  if (typeof window !== 'undefined') {
    const cachedToken = window.localStorage.getItem('payroll_presence_token') || '';
    if (cachedToken) tokenOverride.value = cachedToken;
  }
  await companyStore.fetchCompanies();
  loadPresences();
});

defineExpose({
  reload: loadPresences,
  sync: syncPresences,
  isLoading,
  isSyncing
});
</script>

<style scoped>
.hrd-toolbar-wrap {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
}

.hrd-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 16px;
}

.hrd-toolbar__filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}

.hrd-toolbar__field {
  display: flex;
  align-items: center;
  gap: 8px;
}

.hrd-toolbar__label {
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-text-muted);
}

.hrd-toolbar__company {
  width: 170px;
}

.hrd-toolbar__year {
  width: 100px;
}

.hrd-toolbar__month {
  width: 140px;
}

.hrd-toolbar__search {
  position: relative;
  width: 220px;
}

.hrd-toolbar__search > i {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 11px;
  color: var(--color-text-muted);
  pointer-events: none;
}

.hrd-toolbar__search :deep(input) {
  padding-left: 28px;
}

.hrd-toolbar__total {
  font: 500 12px var(--font-mono);
  color: var(--color-text-muted);
  white-space: nowrap;
}

.hrd-override__toggle {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 5px 10px;
  border: 1px solid transparent;
  border-radius: 8px;
  background: none;
  font: 600 11.5px var(--font-sans);
  color: var(--color-text-muted);
  cursor: pointer;
  transition: color 140ms ease, background-color 140ms ease, border-color 140ms ease;
}

.hrd-override__toggle:hover {
  color: var(--color-text);
  background: var(--color-surface-muted);
  border-color: var(--color-border);
}

.hrd-override__toggle:focus-visible {
  outline: 2px solid var(--color-primary-ring);
  outline-offset: 1px;
}

.hrd-override__chevron {
  font-size: 10px;
  transition: transform 160ms ease;
}

.hrd-override__chevron--open {
  transform: rotate(180deg);
}

.hrd-override__body {
  padding: 0 16px 12px;
  border-left: 1px solid var(--color-border);
  margin-left: 10px;
}

.hrd-override__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 12px;
  max-width: 640px;
}

.hrd-override__hint {
  margin: 10px 0 0;
  font-size: 11px;
  line-height: 1.5;
  color: var(--color-text-muted);
}

.hrd-override__hint code {
  font-family: var(--font-mono);
  font-size: 10.5px;
  padding: 1px 5px;
  border-radius: 5px;
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
}

.hrd-table-head {
  background: var(--color-surface-muted);
}

.hrd-th {
  padding: 10px;
  text-align: left;
  font-size: 10.5px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-text-muted);
  border-bottom: 1px solid var(--color-border-strong);
  white-space: nowrap;
}

.hrd-tbody tr {
  transition: background-color 160ms ease;
}

.hrd-td {
  height: 46px;
  padding: 0 10px;
  border-bottom: 1px solid var(--color-border);
  font-size: 13px;
  color: var(--color-text);
  white-space: nowrap;
  vertical-align: middle;
}

.hrd-tbody tr:last-child .hrd-td {
  border-bottom: none;
}

.hrd-tbody tr:hover .hrd-td {
  background: color-mix(in srgb, var(--color-primary) 4%, transparent);
}

.hrd-td--employee {
  min-width: 180px;
}

.hrd-employee {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.hrd-employee__name {
  font-weight: 600;
  font-size: 12.5px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.hrd-employee__store {
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  color: var(--color-text-muted);
}

.hrd-td--shift {
  min-width: 170px;
}

.hrd-td--shift > span {
  display: block;
}

.hrd-shift__name {
  font-weight: 600;
  font-size: 12.5px;
}

.hrd-shift__time {
  font-size: 11px;
  color: var(--color-text-muted);
}

.hrd-td--mono {
  font-family: var(--font-mono);
  font-size: 12px;
}

.hrd-td--muted {
  color: var(--color-text-muted);
  font-size: 11px;
}

.hrd-td--pending {
  color: var(--color-warning);
  font-weight: 700;
}

.hrd-state {
  padding: 44px 16px;
  text-align: center;
  color: var(--color-text-muted);
}

.hrd-state__icon {
  display: block;
  font-size: 26px;
  margin: 0 auto 10px;
  color: var(--color-border-strong);
}

.hrd-state__title {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
  color: var(--color-text);
}

.hrd-state__hint {
  margin: 4px 0 0;
  font-size: 12px;
}

.hrd-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  font-size: 12px;
  color: var(--color-text-muted);
}

@media (max-width: 1200px) {
  .hrd-td--meta,
  .hrd-th--meta {
    display: none;
  }
}

@media (max-width: 900px) {
  .hrd-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .hrd-toolbar__total {
    align-self: flex-end;
  }
}
</style>
