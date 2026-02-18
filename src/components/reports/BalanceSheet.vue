<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-2xl font-bold text-gray-900">Balance Sheet</h2>
          <p class="text-sm text-gray-500 mt-1">Laporan Posisi Keuangan</p>
        </div>
        <div v-if="hasData" class="text-right">
          <p class="text-xs text-gray-500">As of Date</p>
          <p class="text-sm font-semibold text-gray-900">
            {{ formatDate(data.as_of_date) }}
          </p>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-if="!hasData" class="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
      <i class="bi bi-file-earmark-bar-graph text-6xl text-gray-300"></i>
      <p class="text-gray-500 mt-4 text-lg font-medium">No Report Generated</p>
      <p class="text-gray-400 text-sm mt-2">Select a date and click "Generate Report" to view the balance sheet</p>
    </div>

    <!-- Report Content -->
    <div v-else class="space-y-6">
      <!-- Balance Check Alert -->
      <div v-if="!data.is_balanced" class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <div class="flex items-center gap-2">
          <i class="bi bi-exclamation-triangle text-yellow-600"></i>
          <p class="text-sm text-yellow-800 font-medium">
            Warning: Balance Sheet is not balanced! 
            Assets ({{ formatCurrency(data.assets.total) }}) ≠ 
            Liabilities + Equity ({{ formatCurrency(data.total_liabilities_and_equity) }})
          </p>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- ASSETS -->
        <div class="space-y-6">
          <!-- Current Assets -->
          <div class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            <div class="bg-blue-50 border-b border-blue-100 px-6 py-3">
              <h3 class="text-sm font-bold text-blue-900 uppercase">Aset Lancar</h3>
            </div>
            <div class="overflow-x-auto">
              <table class="w-full">
                <thead class="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Code</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Account</th>
                    <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Amount</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-100">
                  <tr v-if="data.assets.current.length === 0">
                    <td colspan="3" class="px-6 py-8 text-center text-gray-400 text-sm">No current assets</td>
                  </tr>
                  <tr v-for="item in data.assets.current" :key="item.id" class="hover:bg-gray-50 group cursor-pointer" @click="openCoaDetail(item)">
                    <td class="px-6 py-3 text-sm font-mono font-semibold text-gray-900">{{ item.code }}</td>
                    <td class="px-6 py-3 text-sm text-gray-900">{{ item.name }}</td>
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
                </tbody>
              </table>
            </div>
          </div>

          <!-- Non-Current Assets -->
          <div class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            <div class="bg-indigo-50 border-b border-indigo-100 px-6 py-3">
              <h3 class="text-sm font-bold text-indigo-900 uppercase">Aset Tidak Lancar</h3>
            </div>
            <div class="overflow-x-auto">
              <table class="w-full">
                <thead class="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Code</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Account</th>
                    <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Amount</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-100">
                  <tr v-if="data.assets.non_current.length === 0">
                    <td colspan="3" class="px-6 py-8 text-center text-gray-400 text-sm">No non-current assets</td>
                  </tr>
                  <tr v-for="item in data.assets.non_current" :key="item.id" class="hover:bg-gray-50 group cursor-pointer" @click="openCoaDetail(item)">
                    <td class="px-6 py-3 text-sm font-mono font-semibold text-gray-900">{{ item.code }}</td>
                    <td class="px-6 py-3 text-sm text-gray-900">{{ item.name }}</td>
                    <td class="px-6 py-3 text-sm text-right font-semibold text-indigo-700">
                      <div class="flex items-center justify-end gap-2">
                        <span>{{ formatCurrency(item.amount) }}</span>
                        <button
                          @click.stop="copyToClipboard(item.amount)"
                          class="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-indigo-600 transition-opacity"
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
                </tbody>
              </table>
            </div>
          </div>

          <!-- Total Assets -->
          <div class="bg-gradient-to-br from-blue-600 to-blue-700 rounded-lg shadow-lg p-6 text-white">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm font-medium opacity-90">Total Assets</p>
                <p class="text-xs opacity-75 mt-1">Jumlah Aset</p>
              </div>
              <div class="text-right">
                <p class="text-3xl font-bold">{{ formatCurrency(data.assets.total) }}</p>
              </div>
            </div>
          </div>
        </div>

        <!-- LIABILITIES & EQUITY -->
        <div class="space-y-6">
          <!-- Current Liabilities -->
          <div class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            <div class="bg-orange-50 border-b border-orange-100 px-6 py-3">
              <h3 class="text-sm font-bold text-orange-900 uppercase">Liabilitas Jangka Pendek</h3>
            </div>
            <div class="overflow-x-auto">
              <table class="w-full">
                <thead class="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Code</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Account</th>
                    <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Amount</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-100">
                  <tr v-if="data.liabilities.current.length === 0">
                    <td colspan="3" class="px-6 py-8 text-center text-gray-400 text-sm">No current liabilities</td>
                  </tr>
                  <tr v-for="item in data.liabilities.current" :key="item.id" class="hover:bg-gray-50 group cursor-pointer" @click="openCoaDetail(item)">
                    <td class="px-6 py-3 text-sm font-mono font-semibold text-gray-900">{{ item.code }}</td>
                    <td class="px-6 py-3 text-sm text-gray-900">{{ item.name }}</td>
                    <td class="px-6 py-3 text-sm text-right font-semibold text-orange-700">
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
                </tbody>
              </table>
            </div>
          </div>

          <!-- Non-Current Liabilities -->
          <div class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            <div class="bg-red-50 border-b border-red-100 px-6 py-3">
              <h3 class="text-sm font-bold text-red-900 uppercase">Liabilitas Jangka Panjang</h3>
            </div>
            <div class="overflow-x-auto">
              <table class="w-full">
                <thead class="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Code</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Account</th>
                    <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Amount</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-100">
                  <tr v-if="data.liabilities.non_current.length === 0">
                    <td colspan="3" class="px-6 py-8 text-center text-gray-400 text-sm">No non-current liabilities</td>
                  </tr>
                  <tr v-for="item in data.liabilities.non_current" :key="item.id" class="hover:bg-gray-50 group cursor-pointer" @click="openCoaDetail(item)">
                    <td class="px-6 py-3 text-sm font-mono font-semibold text-gray-900">{{ item.code }}</td>
                    <td class="px-6 py-3 text-sm text-gray-900">{{ item.name }}</td>
                    <td class="px-6 py-3 text-sm text-right font-semibold text-red-700">
                      <div class="flex items-center justify-end gap-2">
                        <span>{{ formatCurrency(item.amount) }}</span>
                        <button
                          @click.stop="copyToClipboard(item.amount)"
                          class="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-600 transition-opacity"
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
                </tbody>
              </table>
            </div>
          </div>

          <!-- Equity -->
          <div class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            <div class="bg-green-50 border-b border-green-100 px-6 py-3">
              <h3 class="text-sm font-bold text-green-900 uppercase">Ekuitas</h3>
            </div>
            <div class="overflow-x-auto">
              <table class="w-full">
                <thead class="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Code</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Account</th>
                    <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Amount</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-100">
                  <tr v-if="data.equity.items.length === 0">
                    <td colspan="3" class="px-6 py-8 text-center text-gray-400 text-sm">No equity entries</td>
                  </tr>
                  <tr v-for="item in data.equity.items" :key="item.id" class="hover:bg-gray-50 group cursor-pointer" @click="openCoaDetail(item)">
                    <td class="px-6 py-3 text-sm font-mono font-semibold text-gray-900">{{ item.code }}</td>
                    <td class="px-6 py-3 text-sm text-gray-900">{{ item.name }}</td>
                    <td class="px-6 py-3 text-sm text-right font-semibold text-green-700">
                      <div class="flex items-center justify-end gap-2">
                        <span>{{ formatCurrency(item.amount) }}</span>
                        <button
                          @click.stop="copyToClipboard(item.amount)"
                          class="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-green-600 transition-opacity"
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
                </tbody>
              </table>
            </div>
          </div>

          <!-- Total Liabilities & Equity -->
          <div class="bg-gradient-to-br from-green-600 to-green-700 rounded-lg shadow-lg p-6 text-white">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm font-medium opacity-90">Total Liabilities & Equity</p>
                <p class="text-xs opacity-75 mt-1">Jumlah Liabilitas & Ekuitas</p>
              </div>
              <div class="text-right">
                <p class="text-3xl font-bold">{{ formatCurrency(data.total_liabilities_and_equity) }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';

const props = defineProps({
  data: {
    type: Object,
    default: null
  }
});

const emit = defineEmits(['view-coa']);

const hasData = computed(() => props.data !== null);
const copiedAmount = ref(null);

const openCoaDetail = (item) => {
  emit('view-coa', item);
};

const formatDate = (dateStr) => {
  if (!dateStr) return '-';
  const date = new Date(dateStr);
  return date.toLocaleDateString('id-ID', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });
};

const formatCurrency = (amount) => {
  if (amount === null || amount === undefined) return 'Rp 0';
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(amount);
};

const copyToClipboard = async (amount) => {
  try {
    const rawAmount = Math.abs(amount).toString();
    await navigator.clipboard.writeText(rawAmount);

    copiedAmount.value = amount;
    setTimeout(() => {
      copiedAmount.value = null;
    }, 1500);
  } catch (err) {
    console.error('Failed to copy:', err);
  }
};
</script>
