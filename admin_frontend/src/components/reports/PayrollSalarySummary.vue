<template>
  <div class="space-y-6">
    <SectionCard body-class="p-6">
      <div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h2 class="text-2xl font-bold text-theme">Payroll Salary Summary</h2>
          <p class="text-sm text-muted mt-1">Ringkasan gaji per bulan, employee, dan mark</p>
        </div>
        <div class="text-xs text-muted">
          <div>Period: {{ formatDate(data?.period?.start_date) }} - {{ formatDate(data?.period?.end_date) }}</div>
          <div v-if="data?.message" class="text-danger mt-1">{{ data.message }}</div>
        </div>
      </div>
    </SectionCard>

    <StatCard
      label="Total Payroll"
      :value="formatCurrency(grandTotal)"
      variant="primary"
    />

    <SectionCard v-if="!hasData" body-class="p-10 text-center">
      <i class="bi bi-people text-5xl text-muted opacity-50"></i>
      <p class="text-theme mt-3 font-medium">No payroll salary summary</p>
      <p class="text-xs text-muted mt-1">Pastikan periode, company filter, dan konfigurasi salary component sudah sesuai.</p>
    </SectionCard>

    <SectionCard v-else body-class="p-0 overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm min-w-[980px]">
          <thead class="border-b border-border">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-semibold text-muted uppercase sticky left-0 bg-surface-muted z-10 min-w-[260px]">
                Employee / Mark
              </th>
              <th
                v-for="month in monthColumns"
                :key="`month-header-${month.month_key}`"
                class="px-4 py-3 text-right text-xs font-semibold text-muted uppercase whitespace-nowrap"
              >
                {{ month.month_label }}
              </th>
              <th class="px-4 py-3 text-right text-xs font-semibold text-theme uppercase whitespace-nowrap bg-primary/5">
                Total
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border">
            <template v-for="employee in employeeRows" :key="employee.key">
              <tr class="hover:bg-hover active:bg-hover/80 transition-colors">
                <PayrollEmployeeCell
                  :name="employee.name"
                  :employee-id="employee.id"
                  expandable
                  :expanded="isExpanded(employee.key)"
                  sticky
                  @toggle="toggleExpanded(employee.key)"
                />
                <td
                  v-for="month in monthColumns"
                  :key="`employee-${employee.key}-${month.month_key}`"
                  class="px-4 py-3 text-right font-medium text-theme whitespace-nowrap bg-surface transition-colors"
                >
                  {{ formatCurrency(employee.monthly[month.month_key] || 0) }}
                </td>
                <td class="px-4 py-3 text-right font-bold text-primary whitespace-nowrap bg-primary/5 transition-colors">
                  {{ formatCurrency(employee.total) }}
                </td>
              </tr>
              <tr
                v-for="component in isExpanded(employee.key) ? employee.components : []"
                :key="`component-${employee.key}-${component.mark_name}`"
                class="bg-surface-muted"
              >
                <td class="px-6 py-2 min-w-[260px] sticky left-0 bg-surface-muted z-10">
                  <span class="inline-flex items-center">
                    <PayrollComponentChip :name="component.mark_name" />
                  </span>
                </td>
                <td
                  v-for="month in monthColumns"
                  :key="`component-${employee.key}-${component.mark_name}-${month.month_key}`"
                  class="px-4 py-2 text-right text-muted whitespace-nowrap"
                >
                  {{ formatCurrency(component.monthly[month.month_key] || 0) }}
                </td>
                <td class="px-4 py-2 text-right font-semibold text-theme whitespace-nowrap bg-primary/5">
                  {{ formatCurrency(component.total) }}
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </SectionCard>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import SectionCard from '../ui/SectionCard.vue';
import StatCard from '../ui/StatCard.vue';
import PayrollEmployeeCell from '../payroll/PayrollEmployeeCell.vue';
import PayrollComponentChip from '../payroll/PayrollComponentChip.vue';

const props = defineProps({
  data: {
    type: Object,
    default: null
  }
});

const expandedEmployees = ref([]);

const monthColumns = computed(() => {
  if (!Array.isArray(props.data?.months)) return [];
  const months = props.data.months;
  // The period (with its year) is already shown in the card header, so the
  // year is dropped from month headers unless the range crosses years.
  const years = new Set(months.map((month) => String(month.month_key || '').slice(0, 4)));
  const singleYear = years.size <= 1;
  return months.map((month) => {
    const key = String(month.month_key || '');
    const parts = key.split('-');
    let label = month.month_label || key;
    if (singleYear && parts.length === 2) {
      const date = new Date(Number(parts[0]), Number(parts[1]) - 1, 1);
      if (!Number.isNaN(date.getTime())) label = date.toLocaleString('en-US', { month: 'long' });
    }
    return {
      month_key: month.month_key,
      month_label: label
    };
  });
});

const employeeRows = computed(() => {
  const map = new Map();
  const months = Array.isArray(props.data?.months) ? props.data.months : [];

  for (const month of months) {
    const monthKey = month.month_key;
    const rows = Array.isArray(month.rows) ? month.rows : [];
    for (const row of rows) {
      const userId = row.sagansa_user_id || null;
      const userName = row.sagansa_user_name || userId || 'Unassigned';
      const employeeKey = userId ? `u:${userId}` : `u:unassigned:${userName}`;
      const markName = row.mark_name || '(Unnamed Salary Component)';
      const amount = Number(row.total_amount || 0);

      if (!map.has(employeeKey)) {
        map.set(employeeKey, {
          key: employeeKey,
          id: userId,
          name: userName,
          monthly: {},
          total: 0,
          componentsMap: new Map()
        });
      }

      const employee = map.get(employeeKey);
      employee.monthly[monthKey] = (employee.monthly[monthKey] || 0) + amount;
      employee.total += amount;

      if (!employee.componentsMap.has(markName)) {
        employee.componentsMap.set(markName, {
          mark_name: markName,
          monthly: {},
          total: 0
        });
      }
      const component = employee.componentsMap.get(markName);
      component.monthly[monthKey] = (component.monthly[monthKey] || 0) + amount;
      component.total += amount;
    }
  }

  return Array.from(map.values())
    .map((employee) => ({
      ...employee,
      components: Array.from(employee.componentsMap.values()).sort((a, b) => a.mark_name.localeCompare(b.mark_name, 'id'))
    }))
    .sort((a, b) => a.name.localeCompare(b.name, 'id'));
});

const hasData = computed(() => employeeRows.value.length > 0);
const grandTotal = computed(() => employeeRows.value.reduce((sum, row) => sum + Number(row.total || 0), 0));

const formatCurrency = (value) => {
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(Number(value || 0));
};

const formatDate = (value) => {
  if (!value) return '-';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString('id-ID', { year: 'numeric', month: 'short', day: 'numeric' });
};

const isExpanded = (key) => expandedEmployees.value.includes(key);

const toggleExpanded = (key) => {
  if (!key) return;
  if (isExpanded(key)) {
    expandedEmployees.value = expandedEmployees.value.filter((item) => item !== key);
    return;
  }
  expandedEmployees.value = [...expandedEmployees.value, key];
};

watch(employeeRows, (rows) => {
  const valid = new Set(rows.map((row) => row.key));
  expandedEmployees.value = expandedEmployees.value.filter((key) => valid.has(key));
});
</script>
