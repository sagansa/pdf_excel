<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-2xl font-bold text-gray-900">Income Statement</h2>
          <p class="text-sm text-gray-500 mt-1">Laporan Laba Rugi</p>
        </div>
        <div v-if="hasData" class="text-right">
          <p class="text-xs text-gray-500">Period</p>
          <p class="text-sm font-semibold text-gray-900">
            {{ formatDate(data.period.start_date) }} -
            {{ formatDate(data.period.end_date) }}
          </p>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div
      v-if="!hasData"
      class="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center"
    >
      <i class="bi bi-file-earmark-bar-graph text-6xl text-gray-300"></i>
      <p class="text-gray-500 mt-4 text-lg font-medium">No Report Generated</p>
      <p class="text-gray-400 text-sm mt-2">
        Select a date range and click "Generate Report" to view the income
        statement
      </p>
    </div>

    <!-- Report Content -->
    <div v-else class="space-y-6">
      <!-- Summary Cards -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div
          class="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg shadow-sm border border-purple-200 p-6"
        >
          <div class="flex items-center justify-between">
            <div>
              <p class="text-xs font-medium text-purple-600 uppercase">
                Total Revenue
              </p>
              <p class="text-2xl font-bold text-purple-900 mt-1">
                {{ formatCurrency(data.total_revenue) }}
              </p>
            </div>
            <div
              class="w-12 h-12 rounded-full bg-purple-200 flex items-center justify-center"
            >
              <i class="bi bi-graph-up-arrow text-purple-700 text-xl"></i>
            </div>
          </div>
        </div>

        <div
          class="bg-gradient-to-br from-orange-50 to-orange-100 rounded-lg shadow-sm border border-orange-200 p-6"
        >
          <div class="flex items-center justify-between">
            <div>
              <p class="text-xs font-medium text-orange-600 uppercase">
                Total Expenses
              </p>
              <p class="text-2xl font-bold text-orange-900 mt-1">
                {{ formatCurrency(data.total_expenses) }}
              </p>
            </div>
            <div
              class="w-12 h-12 rounded-full bg-orange-200 flex items-center justify-center"
            >
              <i class="bi bi-graph-down-arrow text-orange-700 text-xl"></i>
            </div>
          </div>
        </div>

        <div
          class="bg-gradient-to-br from-green-50 to-green-100 rounded-lg shadow-sm border border-green-200 p-6"
        >
          <div class="flex items-center justify-between">
            <div>
              <p class="text-xs font-medium text-green-600 uppercase">
                Net Income
              </p>
              <p class="text-2xl font-bold text-green-900 mt-1">
                {{ formatCurrency(data.net_income) }}
              </p>
            </div>
            <div
              class="w-12 h-12 rounded-full bg-green-200 flex items-center justify-center"
            >
              <i class="bi bi-cash-coin text-green-700 text-xl"></i>
            </div>
          </div>
        </div>
      </div>

      <!-- Revenue Section -->
      <div
        class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden"
      >
        <div class="bg-purple-50 border-b border-purple-100 px-6 py-3">
          <h3 class="text-sm font-bold text-purple-900 uppercase">
            Revenue (Pendapatan)
          </h3>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full">
            <thead class="bg-gray-50 border-b border-gray-200">
              <tr>
                <th
                  class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase"
                >
                  Code
                </th>
                <th
                  class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase"
                >
                  Account Name
                </th>
                <th
                  class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase"
                >
                  Subcategory
                </th>
                <th
                  class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase"
                >
                  Amount
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              <tr v-if="data.revenue.length === 0">
                <td
                  colspan="4"
                  class="px-6 py-8 text-center text-gray-400 text-sm"
                  >
                  No revenue entries
                </td>
              </tr>
              <tr
                v-for="item in data.revenue"
                :key="item.code"
                class="hover:bg-gray-50 group cursor-pointer"
                @click="openCoaDetail(item)"
              >
                <td
                  class="px-6 py-3 text-sm font-mono font-semibold text-gray-900"
                >
                  {{ item.code }}
                </td>
                <td class="px-6 py-3 text-sm text-gray-900">{{ item.name }}</td>
                <td class="px-6 py-3 text-sm text-gray-500">
                  {{ item.subcategory || "-" }}
                </td>
                <td
                  class="px-6 py-3 text-right text-sm font-semibold text-purple-700"
                >
                  <div class="flex items-center justify-end gap-2">
                    <span>{{ formatCurrency(item.amount) }}</span>
                    <button
                      @click.stop="copyToClipboard(item.amount)"
                      class="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-purple-600 transition-opacity"
                      title="Copy amount"
                    >
                      <i class="bi bi-clipboard text-xs"></i>
                    </button>
                  </div>
                </td>
              </tr>
              <tr class="bg-purple-50 font-bold group">
                <td colspan="3" class="px-6 py-3 text-sm text-purple-900">
                  Total Revenue
                </td>
                <td class="px-6 py-3 text-right text-purple-900">
                  <div class="flex items-center justify-end gap-2">
                    <span>{{ formatCurrency(data.total_revenue) }}</span>
                    <button
                      @click="copyToClipboard(data.total_revenue)"
                      class="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-purple-600 transition-opacity"
                      title="Copy amount"
                    >
                      <i class="bi bi-clipboard text-xs"></i>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

       <!-- COGS Section -->
       <div
         v-if="data.cogs_breakdown && data.cogs_breakdown.total_cogs > 0"
         class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden"
       >
         <div class="bg-blue-50 border-b border-blue-100 px-6 py-3">
           <h3 class="text-sm font-bold text-blue-900 uppercase">
             Cost of Goods Sold (HPP)
           </h3>
         </div>
         <div class="p-6 space-y-6">
           <!-- Inventory Summary Cards -->
           <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
             <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
               <p class="text-xs font-medium text-blue-600 uppercase mb-1">Beginning Inventory</p>
               <p class="text-lg font-bold text-blue-900">{{ formatCurrency(data.cogs_breakdown.beginning_inventory) }}</p>
             </div>
             <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
               <p class="text-xs font-medium text-blue-600 uppercase mb-1">- Ending Inventory</p>
               <p class="text-lg font-bold text-blue-900">{{ formatCurrency(data.cogs_breakdown.ending_inventory) }}</p>
             </div>
             <div class="bg-blue-100 border border-blue-200 rounded-lg p-4">
               <p class="text-xs font-medium text-blue-600 uppercase mb-1">Total COGS</p>
               <p class="text-lg font-bold text-blue-900">{{ formatCurrency(data.cogs_breakdown.total_cogs) }}</p>
             </div>
           </div>

           <!-- Purchases Breakdown Table -->
           <div v-if="data.cogs_breakdown.purchases_items && data.cogs_breakdown.purchases_items.length > 0">
             <div class="bg-blue-100 border-b border-blue-200 px-6 py-2 mb-3">
               <h4 class="text-xs font-bold text-blue-800 uppercase">
                 Purchases Breakdown
               </h4>
             </div>
             <div class="overflow-x-auto">
               <table class="w-full">
                 <thead class="bg-gray-50 border-b border-gray-200">
                   <tr>
                     <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Code</th>
                     <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Account Name</th>
                     <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Subcategory</th>
                     <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Amount</th>
                   </tr>
                 </thead>
                 <tbody class="divide-y divide-gray-100">
                   <tr
                     v-for="item in data.cogs_breakdown.purchases_items"
                     :key="item.code"
                     class="hover:bg-gray-50 group cursor-pointer"
                     @click="openCoaDetail(item)"
                   >
                     <td class="px-6 py-3 text-sm font-mono font-semibold text-gray-900">
                       {{ item.code }}
                     </td>
                     <td class="px-6 py-3 text-sm text-gray-900">{{ item.name }}</td>
                     <td class="px-6 py-3 text-sm text-gray-500">
                       {{ item.subcategory || "-" }}
                     </td>
                     <td class="px-6 py-3 text-sm text-right font-semibold text-blue-700">
                       <div class="flex items-center justify-end gap-2">
                         <span>{{ formatCurrency(item.amount) }}</span>
                         <button
                           @click.stop="copyToClipboard(item.amount)"
                           class="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-blue-600 transition-opacity"
                           title="Copy amount"
                         >
                           <i class="bi bi-clipboard text-xs"></i>
                         </button>
                         <button
                           @click.stop="openCoaDetail(item)"
                           class="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-indigo-600 transition-opacity"
                           title="View transactions"
                         >
                           <i class="bi bi-list-ul text-xs"></i>
                         </button>
                       </div>
                     </td>
                   </tr>
                   <tr class="bg-blue-50 font-bold group">
                     <td colspan="3" class="px-6 py-3 text-sm text-blue-900">
                       Total Purchases
                     </td>
                     <td class="px-6 py-3 text-sm text-right text-blue-900">
                       <div class="flex items-center justify-end gap-2">
                         <span>{{ formatCurrency(data.cogs_breakdown.purchases) }}</span>
                         <button
                           @click="copyToClipboard(data.cogs_breakdown.purchases)"
                           class="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-blue-600 transition-opacity"
                           title="Copy amount"
                         >
                           <i class="bi bi-clipboard text-xs"></i>
                         </button>
                       </div>
                     </td>
                   </tr>
                 </tbody>
               </table>
             </div>
           </div>

           <!-- Other COGS Items -->
           <div v-if="data.cogs_breakdown.other_cogs_items && data.cogs_breakdown.other_cogs_items.length > 0">
             <div class="bg-blue-100 border-b border-blue-200 px-6 py-2 mb-3">
               <h4 class="text-xs font-bold text-blue-800 uppercase">
                 Other COGS Items
               </h4>
             </div>
             <div class="overflow-x-auto">
               <table class="w-full">
                 <thead class="bg-gray-50 border-b border-gray-200">
                   <tr>
                     <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Code</th>
                     <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Account Name</th>
                     <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Subcategory</th>
                     <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Amount</th>
                   </tr>
                 </thead>
                 <tbody class="divide-y divide-gray-100">
                   <tr
                     v-for="item in data.cogs_breakdown.other_cogs_items"
                     :key="item.code"
                     class="hover:bg-gray-50 group cursor-pointer"
                     @click="openCoaDetail(item)"
                   >
                     <td class="px-6 py-3 text-sm font-mono font-semibold text-gray-900">
                       {{ item.code }}
                     </td>
                     <td class="px-6 py-3 text-sm text-gray-900">{{ item.name }}</td>
                     <td class="px-6 py-3 text-sm text-gray-500">
                       {{ item.subcategory || "-" }}
                     </td>
                     <td class="px-6 py-3 text-sm text-right font-semibold text-blue-700">
                       <div class="flex items-center justify-end gap-2">
                         <span>{{ formatCurrency(item.amount) }}</span>
                         <button
                           @click.stop="copyToClipboard(item.amount)"
                           class="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-blue-600 transition-opacity"
                           title="Copy amount"
                         >
                           <i class="bi bi-clipboard text-xs"></i>
                         </button>
                         <button
                           @click.stop="openCoaDetail(item)"
                           class="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-indigo-600 transition-opacity"
                           title="View transactions"
                         >
                           <i class="bi bi-list-ul text-xs"></i>
                         </button>
                       </div>
                     </td>
                   </tr>
                   <tr class="bg-blue-50 font-bold group">
                     <td colspan="3" class="px-6 py-3 text-sm text-blue-900">
                       Total Other COGS
                     </td>
                     <td class="px-6 py-3 text-sm text-right text-blue-900">
                       <div class="flex items-center justify-end gap-2">
                         <span>{{ formatCurrency(data.cogs_breakdown.total_other_cogs) }}</span>
                         <button
                           @click="copyToClipboard(data.cogs_breakdown.total_other_cogs)"
                           class="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-blue-600 transition-opacity"
                           title="Copy amount"
                         >
                           <i class="bi bi-clipboard text-xs"></i>
                         </button>
                       </div>
                     </td>
                   </tr>
                 </tbody>
               </table>
             </div>
           </div>
         </div>
       </div>

      <!-- Expenses Section -->
      <div
        class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden"
      >
        <div class="bg-orange-50 border-b border-orange-100 px-6 py-3">
          <h3 class="text-sm font-bold text-orange-900 uppercase">
            Expenses (Beban)
          </h3>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full">
            <thead class="bg-gray-50 border-b border-gray-200">
              <tr>
                <th
                  class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase"
                >
                  Code
                </th>
                <th
                  class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase"
                >
                  Account Name
                </th>
                <th
                  class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase"
                >
                  Subcategory
                </th>
                <th
                  class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase"
                >
                  Amount
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              <tr v-if="data.expenses.length === 0">
                <td
                  colspan="4"
                  class="px-6 py-8 text-center text-gray-400 text-sm"
                  >
                  No expense entries
                </td>
              </tr>
               <tr
                 v-for="item in data.expenses"
                 :key="item.code"
                 class="hover:bg-gray-50 group cursor-pointer"
                 @click="openCoaDetail(item)"
               >
                 <td
                   class="px-6 py-3 text-sm font-mono font-semibold text-gray-900"
                 >
                   {{ item.code }}
                 </td>
                 <td class="px-6 py-3 text-sm text-gray-900">{{ item.name }}</td>
                 <td class="px-6 py-3 text-sm text-gray-500">
                   {{ item.subcategory || "-" }}
                 </td>
                 <td
                   class="px-6 py-3 text-sm text-right font-semibold text-orange-700"
                 >
                   <div class="flex items-center justify-end gap-2">
                     <span>{{ formatCurrency(item.amount) }}</span>
                     <button
                       @click.stop="copyToClipboard(item.amount)"
                       class="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-orange-600 transition-opacity"
                       title="Copy amount"
                     >
                       <i class="bi bi-clipboard text-xs"></i>
                     </button>
                     <button
                       @click.stop="openCoaDetail(item)"
                       class="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-indigo-600 transition-opacity"
                       title="View transactions"
                     >
                       <i class="bi bi-list-ul text-xs"></i>
                     </button>
                   </div>
                 </td>
               </tr>
              <tr class="bg-orange-50 font-bold group">
                <td colspan="3" class="px-6 py-3 text-sm text-orange-900">
                  Total Expenses
                </td>
                <td class="px-6 py-3 text-sm text-right text-orange-900">
                  <div class="flex items-center justify-end gap-2">
                    <span>{{ formatCurrency(data.total_expenses) }}</span>
                    <button
                      @click="copyToClipboard(data.total_expenses)"
                      class="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-orange-600 transition-opacity"
                      title="Copy amount"
                    >
                      <i class="bi bi-clipboard text-xs"></i>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

       <!-- Net Income Summary -->
       <div
         class="rounded-lg shadow-lg p-6 text-white transition-colors duration-300"
         :class="data.net_income >= 0 ? 'bg-gradient-to-r from-green-600 to-green-700' : 'bg-gradient-to-r from-red-600 to-red-700'"
       >
         <div class="flex items-center justify-between">
           <div>
             <p class="text-sm font-medium opacity-90">Net Income / (Loss)</p>
             <p class="text-xs opacity-75 mt-1">Laba / (Rugi) Bersih</p>
           </div>
           <div class="text-right">
             <p class="text-3xl font-bold">
               {{ formatCurrency(data.net_income) }}
             </p>
             <p class="text-xs opacity-75 mt-1">
               {{ data.net_income >= 0 ? "Profit" : "Loss" }}
             </p>
           </div>
        </div>
      </div>

        <!-- Fiscal Correction Breakdown -->
       <div
         v-if="data.fiscal_correction_breakdown"
         class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden"
       >
         <div class="bg-orange-50 border-b border-orange-100 px-6 py-3">
           <h3 class="text-sm font-bold text-orange-900 uppercase">
             Koreksi Fiskal Akhir Tahun (Pasal 9)
           </h3>
         </div>
         <div class="p-6">
           <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
             <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
               <p class="text-xs font-medium text-blue-600 uppercase mb-1">Amortisasi Komersial</p>
               <p class="text-lg font-bold text-blue-900">{{ formatCurrency(data.fiscal_correction_breakdown.commercial_amortization) }}</p>
             </div>
             <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
               <p class="text-xs font-medium text-blue-600 uppercase mb-1">Amortisasi Fiskal</p>
               <p class="text-lg font-bold text-blue-900">{{ formatCurrency(data.fiscal_correction_breakdown.fiscal_amortization) }}</p>
             </div>
             <div class="bg-orange-100 border border-orange-200 rounded-lg p-4">
               <p class="text-xs font-medium text-orange-600 uppercase mb-1">Koreksi Fiskal</p>
               <p class="text-lg font-bold text-orange-900">{{ formatCurrency(data.fiscal_correction_breakdown.fiscal_correction) }}</p>
             </div>
           </div>
           <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
             <div class="bg-red-50 border border-red-200 rounded-lg p-4">
               <p class="text-xs font-medium text-red-600 uppercase mb-1">PPh atas Koreksi (22%)</p>
               <p class="text-lg font-bold text-red-900">{{ formatCurrency(data.fiscal_correction_breakdown.tax_on_correction) }}</p>
             </div>
             <div class="bg-red-100 border border-red-200 rounded-lg p-4">
               <p class="text-xs font-medium text-red-700 uppercase mb-1">Total Dampak Pajak</p>
               <p class="text-lg font-bold text-red-900">{{ formatCurrency(data.fiscal_correction_breakdown.total_tax_impact) }}</p>
             </div>
           </div>
         </div>
       </div>
    </div>
  </div>
</template>

<script setup>
import { computed, watch } from 'vue';
import { useReportsStore } from '../../stores/reports';

const props = defineProps({
  data: {
    type: Object,
    default: null
  }
});

const emit = defineEmits(['view-coa']);

const store = useReportsStore();

const hasData = computed(() => {
  return store.incomeStatement !== null;
});

const data = computed(() => {
  return store.incomeStatement || {
    period: { start_date: null, end_date: null },
    total_revenue: 0,
    total_expenses: 0,
    revenue: [],
    expenses: [],
    cogs_breakdown: null,
    amortization_breakdown: null,
    net_income: 0
  };
});

const formatDate = (dateStr) => {
  if (!dateStr) return '-';
  const date = new Date(dateStr);
  return date.toLocaleDateString('id-ID', {
    day: '2-digit',
    month: 'long',
    year: 'numeric'
  });
};

const formatCurrency = (value) => {
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(value);
};

const copyToClipboard = (value) => {
  const formatted = formatCurrency(value);
  navigator.clipboard.writeText(formatted);
};

const openCoaDetail = (coa) => {
  emit('view-coa', coa);
};

const getAssetTypeLabel = (type) => {
  const labels = {
    'Tangible': 'Harta Berwujud',
    'Intangible': 'Harta Tidak Berwujud',
    'Building': 'Bangunan',
    'LandRights': 'Hak Guna'
  };
  return labels[type] || type;
};

const getAssetTypeBadgeClass = (type) => {
  const classes = {
    'Tangible': 'bg-blue-100 text-blue-800',
    'Intangible': 'bg-purple-100 text-purple-800',
    'Building': 'bg-orange-100 text-orange-800',
    'LandRights': 'bg-green-100 text-green-800'
  };
  return classes[type] || 'bg-gray-100 text-gray-800';
};

const getAccumulatedDepreciationCoa = (assetType) => {
  if (!data.value.amortization_breakdown || !data.value.amortization_breakdown.accumulated_depreciation_coa_codes) {
    return '-';
  }
  return data.value.amortization_breakdown.accumulated_depreciation_coa_codes[assetType] || '-';
};

const getTotalAmortization = () => {
  if (!data.value.amortization_breakdown || !data.value.amortization_breakdown.by_asset_type) {
    return 0;
  }
  return Object.values(data.value.amortization_breakdown.by_asset_type).reduce((sum, val) => sum + (val || 0), 0);
};

const getUniqueGroups = (items) => {
  if (!items) return [];
  const groups = [...new Set(items.map(item => item.group_name))];
  return groups.filter(g => g && g !== 'null').sort();
};

const getGroupTotal = (items, groupName) => {
  if (!items) return 0;
  return items
    .filter(item => item.group_name === groupName)
    .reduce((sum, item) => sum + (item.annual_amortization || 0), 0);
};
</script>

<style scoped>
.group:hover td {
  background-color: rgba(99, 102, 241, 0.05);
}
</style>
