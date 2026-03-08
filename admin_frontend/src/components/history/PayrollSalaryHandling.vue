<template>
  <div class="space-y-6">
    <div class="bg-white rounded-xl border border-gray-200 p-5">
      <h3 class="text-lg font-semibold text-gray-900">Payroll Components & Employee Breakdown</h3>
      <p class="text-sm text-gray-500 mt-1">
        Tandai komponen gaji dari menu Mark. Master employee dikelola dari Settings, lalu di sini tiap transaksi dipetakan ke employee untuk rekap bulanan.
      </p>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 p-4">
      <div class="space-y-4">
        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
          <div class="bg-indigo-50 border border-indigo-100 rounded-lg px-3 py-2">
            <div class="text-xs uppercase font-semibold text-indigo-600">Transactions</div>
            <div class="text-lg font-bold text-indigo-900">{{ transactionsSummary.total_transactions }}</div>
          </div>
          <div class="bg-emerald-50 border border-emerald-100 rounded-lg px-3 py-2">
            <div class="text-xs uppercase font-semibold text-emerald-600">Assigned</div>
            <div class="text-lg font-bold text-emerald-900">{{ transactionsSummary.assigned_transactions }}</div>
          </div>
          <div class="bg-amber-50 border border-amber-100 rounded-lg px-3 py-2">
            <div class="text-xs uppercase font-semibold text-amber-700">Unassigned</div>
            <div class="text-lg font-bold text-amber-900">{{ Math.max(0, transactionsSummary.total_transactions - transactionsSummary.assigned_transactions) }}</div>
          </div>
          <div class="bg-sky-50 border border-sky-100 rounded-lg px-3 py-2">
            <div class="text-xs uppercase font-semibold text-sky-700">Total Amount</div>
            <div class="text-lg font-bold text-sky-900">{{ formatCurrency(transactionsSummary.total_amount) }}</div>
          </div>
        </div>

        <div class="rounded-lg border border-gray-200 bg-gray-50/70 p-3">
          <div class="flex flex-wrap items-center justify-between gap-2 mb-3">
            <h4 class="text-xs font-semibold uppercase tracking-wide text-gray-600">Filter Data</h4>
            <span class="text-xs text-gray-500">{{ filteredTransactions.length }}/{{ transactions.length }} rows</span>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-12 gap-2">
            <div class="xl:col-span-2">
              <div class="text-[11px] font-medium text-gray-600 mb-1">Periode</div>
              <select
                v-model="selectedMonth"
                class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              >
                <option v-for="m in monthOptions" :key="m.value" :value="m.value">{{ m.label }}</option>
              </select>
            </div>

            <div class="xl:col-span-4">
              <div class="text-[11px] font-medium text-gray-600 mb-1">Search</div>
              <input
                v-model="search"
                @keyup.enter="loadData"
                type="text"
                placeholder="Search transaction..."
                class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              />
            </div>

            <div class="xl:col-span-3">
              <div class="text-[11px] font-medium text-gray-600 mb-1">Employee</div>
              <MultiSelect
                v-model="selectedEmployeeIds"
                :options="employeeFilterOptions"
                placeholder="Filter employee..."
              />
            </div>

            <div class="xl:col-span-3">
              <div class="text-[11px] font-medium text-gray-600 mb-1">Component (Mark)</div>
              <MultiSelect
                v-model="selectedComponentNames"
                :options="componentFilterOptions"
                placeholder="Filter component (mark)..."
              />
            </div>

            <div class="xl:col-span-2">
              <div class="text-[11px] font-medium text-gray-600 mb-1">Min Amount</div>
              <input
                v-model="amountMin"
                type="text"
                placeholder="Min amount"
                class="w-full px-3 py-2 text-xs border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              />
            </div>

            <div class="xl:col-span-2">
              <div class="text-[11px] font-medium text-gray-600 mb-1">Max Amount</div>
              <input
                v-model="amountMax"
                type="text"
                placeholder="Max amount"
                class="w-full px-3 py-2 text-xs border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              />
            </div>

            <div class="xl:col-span-8 flex flex-wrap items-end gap-2">
              <button
                @click="loadData"
                class="px-3 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700"
              >
                Refresh
              </button>
              <button
                @click="clearLocalFilters"
                class="px-3 py-2 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-100"
              >
                Clear Filters
              </button>
            </div>
          </div>
        </div>

        <div class="rounded-lg border border-emerald-100 bg-emerald-50/50 p-3">
          <div class="flex flex-wrap items-center gap-2">
            <span class="text-xs font-semibold text-gray-700">
              {{ selectedTransactionCount }} selected
            </span>
            <select
              v-model="bulkAssignUserId"
              class="w-full sm:w-72 px-3 py-2 text-xs border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              :disabled="selectedTransactionCount === 0 || loadingUsers || isBulkAssigning"
            >
              <option value="">-- Select employee for selected transactions --</option>
              <option value="__unassigned__">-- Unassigned --</option>
              <option v-for="user in employeeUsers" :key="`bulk-${user.id}`" :value="user.id">{{ user.name }}</option>
            </select>
            <button
              @click="bulkAssignSelectedUser"
              class="px-3 py-2 text-xs font-medium text-white bg-emerald-600 rounded-lg hover:bg-emerald-700 disabled:opacity-60"
              :disabled="selectedTransactionCount === 0 || !bulkAssignUserId || isBulkAssigning"
            >
              {{ isBulkAssigning ? 'Assigning...' : 'Assign Selected' }}
            </button>
            <button
              @click="clearSelection"
              class="px-3 py-2 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-100 disabled:opacity-60"
              :disabled="selectedTransactionCount === 0 || isBulkAssigning"
            >
              Clear Selection
            </button>
          </div>
        </div>
      </div>

      <div
        v-if="pageMessage"
        class="mt-3 px-3 py-2 rounded-lg border border-amber-200 bg-amber-50 text-xs text-amber-700"
      >
        {{ pageMessage }}
      </div>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div class="px-4 py-3 border-b border-gray-200 bg-gray-50">
        <h4 class="text-sm font-semibold text-gray-800">Salary Component Transactions</h4>
      </div>
      <div class="max-h-[520px] overflow-auto">
        <table class="min-w-full divide-y divide-gray-200 text-sm">
          <thead class="bg-white sticky top-0">
            <tr>
              <th class="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase w-10">
                <input
                  ref="selectAllCheckbox"
                  type="checkbox"
                  class="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                  :checked="allFilteredSelected"
                  :disabled="filteredTransactions.length === 0 || isBulkAssigning"
                  @change="toggleSelectAllFiltered($event.target.checked)"
                />
              </th>
              <th class="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">
                <button @click="toggleSort('txn_date')" class="inline-flex items-center gap-1 hover:text-gray-700">
                  Date / Description
                  <i :class="getSortIcon('txn_date')"></i>
                </button>
              </th>
              <th class="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">
                <button @click="toggleSort('component_name')" class="inline-flex items-center gap-1 hover:text-gray-700">
                  Component (Mark)
                  <i :class="getSortIcon('component_name')"></i>
                </button>
              </th>
              <th class="px-4 py-2 text-right text-xs font-semibold text-gray-500 uppercase">Amount</th>
              <th class="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Payroll Month</th>
              <th class="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Employee (Sagansa)</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-if="loadingTransactions">
              <td colspan="6" class="px-4 py-6 text-center text-gray-500">Loading payroll transactions...</td>
            </tr>
            <tr v-else-if="filteredTransactions.length === 0">
              <td colspan="6" class="px-4 py-6 text-center text-gray-500">
                No salary component transactions for current filter
              </td>
            </tr>
            <tr v-for="txn in filteredTransactions" :key="txn.id" class="hover:bg-gray-50">
              <td class="px-4 py-3">
                <input
                  type="checkbox"
                  class="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                  :checked="selectedTransactionIdSet.has(String(txn.id))"
                  :disabled="isBulkAssigning"
                  @change="toggleSelectTxn(txn.id, $event.target.checked)"
                />
              </td>
              <td class="px-4 py-3">
                <div class="font-medium text-gray-900">{{ formatDate(txn.txn_date) }}</div>
                <div class="text-xs text-gray-600 whitespace-normal break-words">{{ txn.description || '-' }}</div>
              </td>
              <td class="px-4 py-3 text-gray-700">{{ txn.component_name || '-' }}</td>
              <td class="px-4 py-3 text-right font-medium text-gray-900">{{ formatCurrency(txn.amount) }}</td>
              <td class="px-4 py-3">
                <div class="flex items-center gap-2">
                  <input
                    type="month"
                    :value="getTxnPayrollMonthValue(txn)"
                    @change="updateTxnPayrollMonth(txn, $event.target.value)"
                    class="w-36 px-2 py-1.5 text-xs border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    :disabled="savingTxnId === txn.id || savingPeriodTxnId === txn.id || isBulkAssigning"
                  />
                  <button
                    @click="resetTxnPayrollMonth(txn)"
                    class="px-2 py-1 text-[11px] font-medium text-gray-600 bg-gray-100 rounded hover:bg-gray-200 disabled:opacity-60"
                    :disabled="!txn.payroll_period_month || savingPeriodTxnId === txn.id || isBulkAssigning"
                    title="Reset ke bulan transaksi"
                  >
                    Default
                  </button>
                </div>
                <div v-if="savingPeriodTxnId === txn.id" class="text-[11px] text-gray-500 mt-1">Saving period...</div>
              </td>
              <td class="px-4 py-3">
                <div class="flex items-center gap-2">
                  <select
                    :value="txn.sagansa_user_id || ''"
                    @change="assignUser(txn, $event.target.value)"
                    class="w-full px-3 py-1.5 text-xs border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    :disabled="savingTxnId === txn.id || loadingUsers"
                  >
                    <option value="">-- Unassigned --</option>
                    <option
                      v-if="txn.sagansa_user_id && !isEmployeeUser(txn.sagansa_user_id)"
                      :value="txn.sagansa_user_id"
                    >
                      {{ txn.sagansa_user_name || txn.sagansa_user_id }} (Non-employee)
                    </option>
                    <option v-for="user in employeeUsers" :key="user.id" :value="user.id">{{ user.name }}</option>
                  </select>
                  <span v-if="savingTxnId === txn.id" class="text-xs text-gray-500">Saving...</span>
                </div>
                <div v-if="txn.sagansa_user_id && !isEmployeeUser(txn.sagansa_user_id)" class="text-[11px] text-amber-700 mt-1">
                  Current assignee belum ditandai employee
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div class="px-4 py-3 border-b border-gray-200 bg-gray-50">
        <h4 class="text-sm font-semibold text-gray-800">Monthly Payroll Summary</h4>
      </div>
      <div class="p-4 border-b border-gray-100 bg-white">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div class="bg-gray-50 border border-gray-200 rounded-lg px-3 py-2">
            <div class="text-xs uppercase font-semibold text-gray-500">Employees</div>
            <div class="text-base font-bold text-gray-900">{{ displayMonthlySummary.employee_count }}</div>
          </div>
          <div class="bg-gray-50 border border-gray-200 rounded-lg px-3 py-2">
            <div class="text-xs uppercase font-semibold text-gray-500">Transactions</div>
            <div class="text-base font-bold text-gray-900">{{ displayMonthlySummary.total_transactions }}</div>
          </div>
          <div class="bg-gray-50 border border-gray-200 rounded-lg px-3 py-2">
            <div class="text-xs uppercase font-semibold text-gray-500">Total Payroll</div>
            <div class="text-base font-bold text-gray-900">{{ formatCurrency(displayMonthlySummary.total_salary_amount) }}</div>
          </div>
        </div>
      </div>
      <div class="max-h-[480px] overflow-auto">
        <table class="min-w-full divide-y divide-gray-200 text-sm">
          <thead class="bg-white sticky top-0">
            <tr>
              <th class="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Employee</th>
              <th class="px-4 py-2 text-right text-xs font-semibold text-gray-500 uppercase">Transactions</th>
              <th class="px-4 py-2 text-right text-xs font-semibold text-gray-500 uppercase">Total Salary</th>
              <th class="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Component Breakdown</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-if="loadingSummary">
              <td colspan="4" class="px-4 py-6 text-center text-gray-500">Loading payroll summary...</td>
            </tr>
            <tr v-else-if="displaySummaryRows.length === 0">
              <td colspan="4" class="px-4 py-6 text-center text-gray-500">No payroll summary for selected period</td>
            </tr>
            <tr v-for="row in displaySummaryRows" :key="summaryRowKey(row)" class="hover:bg-gray-50">
              <td class="px-4 py-3">
                <div class="font-medium text-gray-900">{{ row.sagansa_user_name || 'Unassigned' }}</div>
                <div class="text-xs text-gray-500">{{ row.sagansa_user_id || '-' }}</div>
              </td>
              <td class="px-4 py-3 text-right text-gray-700">{{ row.transaction_count }}</td>
              <td class="px-4 py-3 text-right font-semibold text-gray-900">{{ formatCurrency(row.total_amount) }}</td>
              <td class="px-4 py-3">
                <div v-if="!row.components || row.components.length === 0" class="text-xs text-gray-500">-</div>
                <div v-else class="flex flex-wrap gap-1">
                  <span
                    v-for="component in row.components"
                    :key="`${row.sagansa_user_id || 'unassigned'}-${component.component_name}`"
                    class="inline-flex items-center px-2 py-1 rounded-full text-[11px] font-medium bg-indigo-50 text-indigo-700 border border-indigo-100"
                  >
                    {{ component.component_name }}: {{ formatCurrency(component.amount) }}
                  </span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { filterApi, historyApi } from '../../api';
import MultiSelect from '../ui/MultiSelect.vue';

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

const users = ref([]);
const transactions = ref([]);
const summaryRows = ref([]);
const monthlySummary = ref({
  year: new Date().getFullYear(),
  month: new Date().getMonth() + 1,
  employee_count: 0,
  total_transactions: 0,
  total_salary_amount: 0
});
const transactionsSummary = ref({
  total_transactions: 0,
  assigned_transactions: 0,
  total_amount: 0
});

const selectedMonth = ref(new Date().getMonth() + 1);
const search = ref('');
const selectedEmployeeIds = ref([]);
const selectedComponentNames = ref([]);
const amountMin = ref('');
const amountMax = ref('');
const sortField = ref('txn_date');
const sortDirection = ref('desc');
const selectedTransactionIds = ref([]);
const bulkAssignUserId = ref('');
const pageMessage = ref('');
const loadingUsers = ref(false);
const loadingTransactions = ref(false);
const loadingSummary = ref(false);
const savingTxnId = ref(null);
const savingPeriodTxnId = ref(null);
const isBulkAssigning = ref(false);
const selectAllCheckbox = ref(null);
const isFilterLoaded = ref(false);
const FILTER_VIEW_NAME = 'payroll_salary_handling';
let saveFilterTimer = null;

const normalizedYear = computed(() => {
  const parsed = Number(props.year);
  if (Number.isFinite(parsed) && parsed > 1900 && parsed < 3000) return parsed;
  return new Date().getFullYear();
});

const monthOptions = computed(() => {
  return [
    { value: '', label: 'Semua Bulan (Setahun)' },
    ...Array.from({ length: 12 }, (_, idx) => {
      const month = idx + 1;
      return {
        value: month,
        label: new Date(2000, idx, 1).toLocaleDateString('en-US', { month: 'long' })
      };
    })
  ];
});

const employeeUsers = computed(() => users.value.filter((user) => Boolean(user.is_employee)));

const employeeUserIdSet = computed(() => {
  return new Set(employeeUsers.value.map((user) => String(user.id || '').trim()).filter(Boolean));
});

const normalizeComponentName = (value) => {
  const normalized = String(value || '').trim();
  return normalized || '(Unnamed Salary Component)';
};

const employeeFilterOptions = computed(() => {
  const options = [{
    id: '__unassigned__',
    label: 'Unassigned'
  }];
  for (const user of employeeUsers.value) {
    options.push({
      id: String(user.id),
      label: user.name || String(user.id)
    });
  }
  return options;
});

const componentFilterOptions = computed(() => {
  const names = new Set();

  for (const txn of transactions.value) {
    names.add(normalizeComponentName(txn.component_name));
  }

  for (const row of summaryRows.value) {
    for (const component of (row.components || [])) {
      names.add(normalizeComponentName(component.component_name));
    }
  }

  return Array.from(names)
    .sort((a, b) => a.localeCompare(b, 'id'))
    .map((name) => ({
      id: name,
      label: name
    }));
});

const componentFilterSet = computed(() => {
  return new Set(selectedComponentNames.value.map((name) => normalizeComponentName(name)));
});

const componentFilteredTransactions = computed(() => {
  if (componentFilterSet.value.size === 0) return [...transactions.value];
  return transactions.value.filter((txn) => componentFilterSet.value.has(normalizeComponentName(txn.component_name)));
});

const parsedAmountMin = computed(() => {
  const normalized = String(amountMin.value || '').replace(/[^\d.-]/g, '');
  if (!normalized) return null;
  const value = Number(normalized);
  return Number.isFinite(value) ? value : null;
});

const parsedAmountMax = computed(() => {
  const normalized = String(amountMax.value || '').replace(/[^\d.-]/g, '');
  if (!normalized) return null;
  const value = Number(normalized);
  return Number.isFinite(value) ? value : null;
});

const filteredTransactions = computed(() => {
  let rows = [...componentFilteredTransactions.value];

  if (selectedEmployeeIds.value.length > 0) {
    const selectedSet = new Set(selectedEmployeeIds.value.map((id) => String(id)));
    rows = rows.filter((txn) => {
      const key = txn.sagansa_user_id ? String(txn.sagansa_user_id) : '__unassigned__';
      return selectedSet.has(key);
    });
  }

  if (parsedAmountMin.value !== null) {
    rows = rows.filter((txn) => Number(txn.amount || 0) >= parsedAmountMin.value);
  }

  if (parsedAmountMax.value !== null) {
    rows = rows.filter((txn) => Number(txn.amount || 0) <= parsedAmountMax.value);
  }

  rows.sort((a, b) => {
    let comparison = 0;
    if (sortField.value === 'component_name') {
      const aValue = String(a.component_name || '').toLowerCase();
      const bValue = String(b.component_name || '').toLowerCase();
      comparison = aValue.localeCompare(bValue, 'id');
    } else {
      const aDate = Date.parse(a.txn_date || '') || 0;
      const bDate = Date.parse(b.txn_date || '') || 0;
      comparison = aDate - bDate;
    }
    return sortDirection.value === 'asc' ? comparison : -comparison;
  });

  return rows;
});

const displaySummaryRows = computed(() => {
  if (componentFilterSet.value.size === 0) return summaryRows.value;

  const grouped = new Map();
  for (const txn of componentFilteredTransactions.value) {
    const userId = String(txn.sagansa_user_id || '').trim() || null;
    const userName = txn.sagansa_user_name || userId || 'Unassigned';
    const groupKey = userId ? `u:${userId}` : `u:unassigned:${userName}`;
    const componentName = normalizeComponentName(txn.component_name);
    const amount = Math.abs(Number(txn.amount || 0));

    if (!grouped.has(groupKey)) {
      grouped.set(groupKey, {
        sagansa_user_id: userId,
        sagansa_user_name: userName,
        total_amount: 0,
        transaction_count: 0,
        components_map: new Map()
      });
    }

    const row = grouped.get(groupKey);
    row.total_amount += amount;
    row.transaction_count += 1;
    row.components_map.set(componentName, (row.components_map.get(componentName) || 0) + amount);
  }

  return Array.from(grouped.values())
    .map((row) => ({
      sagansa_user_id: row.sagansa_user_id,
      sagansa_user_name: row.sagansa_user_name,
      total_amount: row.total_amount,
      transaction_count: row.transaction_count,
      components: Array.from(row.components_map.entries())
        .map(([componentName, amount]) => ({ component_name: componentName, amount }))
        .sort((a, b) => Number(b.amount || 0) - Number(a.amount || 0))
    }))
    .sort((a, b) => Number(b.total_amount || 0) - Number(a.total_amount || 0));
});

const displayMonthlySummary = computed(() => {
  if (componentFilterSet.value.size === 0) return monthlySummary.value;

  const totalAmount = componentFilteredTransactions.value.reduce(
    (sum, txn) => sum + Math.abs(Number(txn.amount || 0)),
    0
  );

  return {
    year: Number(monthlySummary.value?.year || normalizedYear.value),
    month: monthlySummary.value?.month ?? (selectedMonth.value === '' ? null : Number(selectedMonth.value)),
    employee_count: displaySummaryRows.value.length,
    total_transactions: componentFilteredTransactions.value.length,
    total_salary_amount: totalAmount
  };
});

const selectedTransactionIdSet = computed(() => new Set(selectedTransactionIds.value.map((id) => String(id))));

const selectedTransactionCount = computed(() => selectedTransactionIds.value.length);

const allFilteredSelected = computed(() => {
  if (filteredTransactions.value.length === 0) return false;
  return filteredTransactions.value.every((txn) => selectedTransactionIdSet.value.has(String(txn.id)));
});

const someFilteredSelected = computed(() => {
  if (filteredTransactions.value.length === 0) return false;
  const anySelected = filteredTransactions.value.some((txn) => selectedTransactionIdSet.value.has(String(txn.id)));
  return anySelected && !allFilteredSelected.value;
});

const formatCurrency = (amount) => {
  const val = Number(amount || 0);
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    minimumFractionDigits: 0
  }).format(val);
};

const formatDate = (dateStr) => {
  if (!dateStr) return '-';
  const d = new Date(dateStr);
  if (Number.isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString('id-ID', { year: 'numeric', month: 'short', day: 'numeric' });
};

const toYearMonth = (value) => {
  if (!value) return '';
  const str = String(value);
  if (/^\d{4}-\d{2}$/.test(str)) return str;
  if (/^\d{4}-\d{2}-\d{2}/.test(str)) return str.slice(0, 7);
  const d = new Date(str);
  if (!Number.isNaN(d.getTime())) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    return `${y}-${m}`;
  }
  return str.slice(0, 7);
};

const isEmployeeUser = (userId) => {
  const normalized = String(userId || '').trim();
  if (!normalized) return false;
  return employeeUserIdSet.value.has(normalized);
};

const getTxnPayrollMonthValue = (txn) => {
  if (!txn) return '';
  const monthFromOverride = toYearMonth(txn.payroll_period_month);
  if (monthFromOverride) return monthFromOverride;
  return toYearMonth(txn.txn_date);
};

const summaryRowKey = (row) => {
  const userId = String(row?.sagansa_user_id || '').trim();
  if (userId) return `u:${userId}`;
  return `u:unassigned:${String(row?.sagansa_user_name || 'Unassigned').trim() || 'Unassigned'}`;
};

const clearLocalFilters = () => {
  selectedEmployeeIds.value = [];
  selectedComponentNames.value = [];
  amountMin.value = '';
  amountMax.value = '';
};

const clearSelection = () => {
  selectedTransactionIds.value = [];
};

const toggleSort = (field) => {
  if (sortField.value === field) {
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc';
    return;
  }
  sortField.value = field;
  sortDirection.value = field === 'txn_date' ? 'desc' : 'asc';
};

const getSortIcon = (field) => {
  if (sortField.value !== field) return 'bi bi-arrow-down-up text-[10px] text-gray-400';
  return sortDirection.value === 'asc'
    ? 'bi bi-sort-up text-[10px] text-indigo-600'
    : 'bi bi-sort-down text-[10px] text-indigo-600';
};

const toggleSelectTxn = (txnId, checked) => {
  const key = String(txnId || '').trim();
  if (!key) return;
  const current = new Set(selectedTransactionIds.value.map((id) => String(id)));
  if (checked) {
    current.add(key);
  } else {
    current.delete(key);
  }
  selectedTransactionIds.value = Array.from(current);
};

const toggleSelectAllFiltered = (checked) => {
  const current = new Set(selectedTransactionIds.value.map((id) => String(id)));
  if (checked) {
    for (const txn of filteredTransactions.value) {
      current.add(String(txn.id));
    }
  } else {
    for (const txn of filteredTransactions.value) {
      current.delete(String(txn.id));
    }
  }
  selectedTransactionIds.value = Array.from(current);
};

const saveUiFilters = async () => {
  if (!isFilterLoaded.value) return;
  try {
    const normalizedSelectedMonth = selectedMonth.value === '' ? '' : Number(selectedMonth.value || '');
    await filterApi.saveFilters(FILTER_VIEW_NAME, {
      selectedMonth: Number.isFinite(normalizedSelectedMonth) ? normalizedSelectedMonth : '',
      search: String(search.value || ''),
      selectedEmployeeIds: selectedEmployeeIds.value.map((id) => String(id)),
      selectedComponentNames: selectedComponentNames.value.map((name) => String(name)),
      amountMin: String(amountMin.value || ''),
      amountMax: String(amountMax.value || ''),
      sortField: String(sortField.value || 'txn_date'),
      sortDirection: String(sortDirection.value || 'desc')
    });
  } catch (error) {
    console.error('Failed to save payroll filters:', error);
  }
};

const scheduleSaveUiFilters = () => {
  if (!isFilterLoaded.value) return;
  if (saveFilterTimer) clearTimeout(saveFilterTimer);
  saveFilterTimer = setTimeout(() => {
    saveUiFilters();
  }, 250);
};

const loadUiFilters = async () => {
  try {
    const response = await filterApi.getFilters(FILTER_VIEW_NAME);
    const filters = response?.data?.filters || {};
    if (Object.keys(filters).length > 0) {
      if (filters.selectedMonth === '' || filters.selectedMonth === null || filters.selectedMonth === undefined) {
        selectedMonth.value = '';
      } else {
        const month = Number(filters.selectedMonth);
        if (Number.isFinite(month) && month >= 1 && month <= 12) {
          selectedMonth.value = month;
        }
      }
      if (Array.isArray(filters.selectedEmployeeIds)) {
        selectedEmployeeIds.value = filters.selectedEmployeeIds.map((id) => String(id));
      }
      if (Array.isArray(filters.selectedComponentNames)) {
        selectedComponentNames.value = filters.selectedComponentNames.map((name) => String(name));
      }
      if (filters.search !== undefined) search.value = String(filters.search || '');
      if (filters.amountMin !== undefined) amountMin.value = String(filters.amountMin || '');
      if (filters.amountMax !== undefined) amountMax.value = String(filters.amountMax || '');
      if (filters.sortField === 'txn_date' || filters.sortField === 'component_name') {
        sortField.value = filters.sortField;
      }
      if (filters.sortDirection === 'asc' || filters.sortDirection === 'desc') {
        sortDirection.value = filters.sortDirection;
      }
    }
  } catch (error) {
    console.error('Failed to load payroll filters:', error);
  } finally {
    isFilterLoaded.value = true;
  }
};

const loadUsers = async () => {
  loadingUsers.value = true;
  try {
    const response = await historyApi.getPayrollUsers('', true);
    users.value = (response.data.users || []).map((user) => ({
      ...user,
      is_employee: Boolean(user.is_employee)
    }));
    if (users.value.length === 0 && !pageMessage.value) {
      pageMessage.value = 'Belum ada employee yang ditandai di Settings > Payroll Employee.';
    }
  } catch (error) {
    console.error('Failed to load Sagansa users:', error);
    users.value = [];
    pageMessage.value = error.response?.data?.error || 'Failed to load Sagansa users';
  } finally {
    loadingUsers.value = false;
  }
};

const loadTransactions = async () => {
  loadingTransactions.value = true;
  pageMessage.value = '';
  try {
    const response = await historyApi.getPayrollTransactions(
      props.companyId,
      normalizedYear.value,
      selectedMonth.value,
      search.value
    );
    transactions.value = response.data.transactions || [];
    transactionsSummary.value = response.data.summary || {
      total_transactions: transactions.value.length,
      assigned_transactions: transactions.value.filter((txn) => txn.sagansa_user_id).length,
      total_amount: transactions.value.reduce((acc, txn) => acc + Number(txn.amount || 0), 0)
    };
    if (response.data.message) pageMessage.value = response.data.message;
    if (!response.data.message && transactions.value.length === 0) {
      const periodLabel = selectedMonth.value === '' ? `Year ${normalizedYear.value} (Semua Bulan)` : `Year ${normalizedYear.value}, Month ${selectedMonth.value}`;
      pageMessage.value = `Tidak ada Salary Component Transactions untuk filter saat ini (${periodLabel}).`;
    }
  } catch (error) {
    console.error('Failed to load payroll transactions:', error);
    transactions.value = [];
    transactionsSummary.value = { total_transactions: 0, assigned_transactions: 0, total_amount: 0 };
    pageMessage.value = error.response?.data?.error || 'Failed to load payroll transactions';
  } finally {
    loadingTransactions.value = false;
  }
};

const loadSummary = async () => {
  loadingSummary.value = true;
  try {
    const response = await historyApi.getPayrollMonthlySummary(
      props.companyId,
      normalizedYear.value,
      selectedMonth.value
    );
    summaryRows.value = response.data.rows || [];
    monthlySummary.value = response.data.summary || {
      year: normalizedYear.value,
      month: selectedMonth.value,
      employee_count: 0,
      total_transactions: 0,
      total_salary_amount: 0
    };
    if (!pageMessage.value && response.data.message) pageMessage.value = response.data.message;
  } catch (error) {
    console.error('Failed to load payroll summary:', error);
    summaryRows.value = [];
    monthlySummary.value = {
      year: normalizedYear.value,
      month: selectedMonth.value,
      employee_count: 0,
      total_transactions: 0,
      total_salary_amount: 0
    };
    pageMessage.value = error.response?.data?.error || 'Failed to load payroll summary';
  } finally {
    loadingSummary.value = false;
  }
};

const loadData = async () => {
  await Promise.all([loadTransactions(), loadSummary()]);
};

const assignUser = async (txn, userIdRaw) => {
  if (!txn) return;
  const userId = userIdRaw || null;
  if (userId && !isEmployeeUser(userId)) {
    alert('User belum ditandai sebagai employee. Tandai dulu di Employee Master.');
    return;
  }
  savingTxnId.value = txn.id;
  try {
    const response = await historyApi.assignPayrollUser(txn.id, userId);
    txn.sagansa_user_id = response.data.sagansa_user_id || null;
    txn.sagansa_user_name = response.data.sagansa_user_name || null;
    await loadSummary();
    transactionsSummary.value.assigned_transactions = transactions.value.filter((row) => row.sagansa_user_id).length;
  } catch (error) {
    console.error('Failed to assign payroll user:', error);
    alert('Failed to assign user: ' + (error.response?.data?.error || error.message));
    await loadTransactions();
  } finally {
    savingTxnId.value = null;
  }
};

const updateTxnPayrollMonth = async (txn, monthValue) => {
  if (!txn?.id) return;
  const selectedMonthValue = String(monthValue || '').trim();
  if (!selectedMonthValue) return;

  const txnMonth = toYearMonth(txn.txn_date);
  const payloadMonth = selectedMonthValue === txnMonth ? null : selectedMonthValue;

  savingPeriodTxnId.value = txn.id;
  try {
    await historyApi.updatePayrollPeriodMonth(txn.id, payloadMonth);
    await Promise.all([loadTransactions(), loadSummary()]);
    pageMessage.value = payloadMonth
      ? `Payroll month transaksi berhasil diubah ke ${selectedMonthValue}.`
      : 'Payroll month transaksi direset mengikuti bulan transaksi.';
  } catch (error) {
    console.error('Failed to update payroll month:', error);
    alert('Failed to update payroll month: ' + (error.response?.data?.error || error.message));
    await loadTransactions();
  } finally {
    savingPeriodTxnId.value = null;
  }
};

const resetTxnPayrollMonth = async (txn) => {
  if (!txn?.id) return;
  savingPeriodTxnId.value = txn.id;
  try {
    await historyApi.updatePayrollPeriodMonth(txn.id, null);
    await Promise.all([loadTransactions(), loadSummary()]);
    pageMessage.value = 'Payroll month transaksi direset mengikuti bulan transaksi.';
  } catch (error) {
    console.error('Failed to reset payroll month:', error);
    alert('Failed to reset payroll month: ' + (error.response?.data?.error || error.message));
    await loadTransactions();
  } finally {
    savingPeriodTxnId.value = null;
  }
};

const bulkAssignSelectedUser = async () => {
  if (selectedTransactionIds.value.length === 0) return;
  if (!bulkAssignUserId.value) return;

  const targetUserId = bulkAssignUserId.value === '__unassigned__' ? null : bulkAssignUserId.value;
  if (targetUserId && !isEmployeeUser(targetUserId)) {
    alert('User belum ditandai sebagai employee. Tandai dulu di Settings > Payroll Employee.');
    return;
  }

  isBulkAssigning.value = true;
  try {
    const response = await historyApi.bulkAssignPayrollUser(selectedTransactionIds.value, targetUserId);
    await Promise.all([loadTransactions(), loadSummary()]);
    clearSelection();
    const updatedCount = Number(response?.data?.updated_count || 0);
    pageMessage.value = `${updatedCount} transaction(s) berhasil di-assign ke ${response?.data?.sagansa_user_name || 'Unassigned'}.`;
  } catch (error) {
    console.error('Failed to bulk assign payroll user:', error);
    alert('Failed to bulk assign user: ' + (error.response?.data?.error || error.message));
  } finally {
    isBulkAssigning.value = false;
  }
};

onMounted(async () => {
  await loadUiFilters();
  await loadUsers();
  await loadData();
});

watch(
  () => [props.companyId, normalizedYear.value, selectedMonth.value],
  () => {
    loadData();
  }
);

watch(employeeFilterOptions, (options) => {
  const validIds = new Set(options.map((option) => String(option.id)));
  selectedEmployeeIds.value = selectedEmployeeIds.value.filter((id) => validIds.has(String(id)));
});

watch(componentFilterOptions, (options) => {
  const validNames = new Set(options.map((option) => String(option.id)));
  selectedComponentNames.value = selectedComponentNames.value.filter((name) => validNames.has(String(name)));
});

watch(filteredTransactions, (rows) => {
  const visibleIds = new Set(rows.map((row) => String(row.id)));
  selectedTransactionIds.value = selectedTransactionIds.value.filter((id) => visibleIds.has(String(id)));
});

watch(
  () => [
    selectedMonth.value,
    search.value,
    selectedEmployeeIds.value.join('|'),
    selectedComponentNames.value.join('|'),
    amountMin.value,
    amountMax.value,
    sortField.value,
    sortDirection.value
  ],
  () => {
    scheduleSaveUiFilters();
  }
);

watch(
  () => [allFilteredSelected.value, someFilteredSelected.value, filteredTransactions.value.length],
  () => {
    if (!selectAllCheckbox.value) return;
    selectAllCheckbox.value.indeterminate = someFilteredSelected.value;
  }
);

onUnmounted(() => {
  if (saveFilterTimer) {
    clearTimeout(saveFilterTimer);
    saveFilterTimer = null;
  }
});
</script>
