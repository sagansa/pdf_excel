<template>
  <div class="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden flex flex-col">
    <!-- Main Table -->
    <div class="overflow-x-auto">
      <table class="min-w-full divide-y divide-gray-200 table-compact">
        <thead>
          <tr>
            <th class="w-10 text-center">
                <input 
                    type="checkbox" 
                    class="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                    :checked="isAllSelected"
                    @change="toggleSelectAll"
                >
            </th>
            <th class="cursor-pointer hover:bg-gray-100 transition-colors" @click="store.toggleSort('txn_date')">
                Date 
                <i v-if="store.sortConfig.key === 'txn_date'" :class="{ 'bi-caret-down-fill': store.sortConfig.direction === 'desc', 'bi-caret-up-fill': store.sortConfig.direction === 'asc' }" class="bi ms-1"></i>
            </th>
             <th class="text-center">Co.</th>
            <th class="cursor-pointer hover:bg-gray-100 transition-colors" @click="store.toggleSort('description')">
                Description
                <i v-if="store.sortConfig.key === 'description'" :class="{ 'bi-caret-down-fill': store.sortConfig.direction === 'desc', 'bi-caret-up-fill': store.sortConfig.direction === 'asc' }" class="bi ms-1"></i>
            </th>
            <th class="text-right cursor-pointer hover:bg-gray-100 transition-colors" @click="store.toggleSort('amount')">
                Amount
                <i v-if="store.sortConfig.key === 'amount'" :class="{ 'bi-caret-down-fill': store.sortConfig.direction === 'desc', 'bi-caret-up-fill': store.sortConfig.direction === 'asc' }" class="bi ms-1"></i>
            </th>
             <th class="text-center">Type</th>
             <th>Bank</th>
             <th>COA</th>
             <th class="text-center">Marking</th>
             <th>Source</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
              <tr v-if="store.isLoading">
                  <td colspan="10" class="text-center py-12">
                      <span class="spinner-border text-indigo-500 w-8 h-8" role="status"></span>
                  </td>
              </tr>
              <tr v-else-if="store.paginatedTransactions.length === 0">
                  <td colspan="10" class="text-center py-12 text-gray-400">
                      <i class="bi bi-inbox text-3xl mb-2 block"></i>
                      No transactions found
                  </td>
              </tr>
             <tr v-for="t in store.paginatedTransactions" :key="t.id" class="hover:bg-gray-50 transition-colors cursor-pointer" :class="{ 'bg-indigo-50/50': store.selectedTxnIds.includes(t.id) }" @click="$emit('view-details', t)">
                <td class="text-center" @click.stop>
                    <input 
                        type="checkbox" 
                        class="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                        :checked="store.selectedTxnIds.includes(t.id)"
                        @change="store.toggleSelection(t.id)"
                    >
                </td>
                <td class="whitespace-nowrap text-xs">{{ formatDate(t.txn_date) }}</td>
                <td class="whitespace-nowrap text-xs text-center font-medium text-gray-700" :title="t.company_name">
                    {{ t.company_short_name || '-' }}
                </td>
                <td class="text-xs break-words max-w-[200px] leading-tight" :title="t.description">{{ t.description }}</td>
                <td class="text-right font-mono font-bold text-sm" :class="t.db_cr === 'CR' ? 'text-green-600' : 'text-red-500'">
                    {{ formatAmount(t.amount) }}
                </td>
                 <td class="text-center">
                     <span class="px-1.5 py-0.5 rounded text-[10px] font-bold"
                      :class="t.db_cr === 'CR' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'">
                      {{ t.db_cr }}
                    </span>
                 </td>
                 <td class="text-xs">{{ t.bank_code }}</td>
                 <td class="text-xs truncate max-w-[180px]" :title="coaDisplayText(t)">
                      {{ coaDisplayText(t) }}
                      <span v-if="t.coas && t.coas.length > 1" class="ml-1 bg-indigo-100 text-indigo-700 text-[10px] px-1.5 py-0.5 rounded-full font-bold">+{{ t.coas.length - 1 }}</span>
                  </td>
                  <td class="min-w-[150px]" @click.stop>
                      <div class="flex items-center gap-2">
                          <select
                              v-if="!t.is_split"
                              class="text-xs border-transparent bg-transparent hover:border-gray-300 hover:bg-white rounded-md p-1 w-full focus:ring-indigo-500 transition-all flex-1"
                              :value="t.mark_id || ''"
                              @change="store.assignMark(t.id, $event.target.value || null)"
                          >
                              <option value="">-- Unmarked --</option>
                              <option v-for="m in store.sortedMarks" :key="m.id" :value="m.id">
                                  {{ m.internal_report || m.personal_use || 'Marked' }}
                              </option>
                          </select>
                          <div v-else class="text-[10px] text-indigo-700 font-bold px-2 py-1 bg-indigo-50 rounded-md flex-1 flex items-center gap-1.5 border border-indigo-100">
                             <i class="bi bi-stack"></i>
                             Mixed Marks
                          </div>
                           <button
                               @click.stop="$emit('split-transaction', t)"
                               class="p-1 transition-all transform active:scale-90"
                               :class="t.is_split ? 'text-indigo-600 hover:text-indigo-800' : 'text-gray-300 hover:text-indigo-600'"
                               :title="t.is_split ? 'Transaction is split into multiple parts' : 'Split this transaction'"
                           >
                               <i class="bi bi-diagram-3-fill text-sm"></i>
                           </button>
                      </div>
                  </td>
                <td class="text-[10px] text-gray-400 truncate max-w-[80px]" :title="t.source_file">{{ t.source_file }}</td>
             </tr>
        </tbody>
        <tfoot v-if="!store.isLoading && store.filteredTransactions.length > 0" class="bg-gray-50/50 border-t-2 border-gray-100">
            <!-- Page Totals -->
            <tr class="font-mono text-xs">
                <td colspan="5" class="py-1 text-right font-bold text-gray-500 uppercase tracking-tighter">Page Debit (DB)</td>
                <td class="text-right font-bold py-1 text-red-500">
                    {{ formatAmount(store.pageDebitTotal) }}
                </td>
                <td colspan="4"></td>
            </tr>
            <tr class="font-mono text-xs">
                <td colspan="5" class="py-1 text-right font-bold text-gray-500 uppercase tracking-tighter">Page Credit (CR)</td>
                <td class="text-right font-bold py-1 text-green-600">
                    {{ formatAmount(store.pageCreditTotal) }}
                </td>
                <td colspan="4"></td>
            </tr>
            <tr class="font-mono text-xs">
                <td colspan="5" class="py-2 text-right font-bold text-gray-700 uppercase tracking-tighter">Page Net Total</td>
                <td class="text-right font-bold py-2 border-t border-gray-200" :class="store.pageTotal >= 0 ? 'text-green-700' : 'text-red-600'">
                    {{ formatAmount(Math.abs(store.pageTotal)) }}
                    <span class="text-[10px]">{{ store.pageTotal >= 0 ? 'CR' : 'DB' }}</span>
                </td>
                <td colspan="4"></td>
            </tr>
            <!-- Filtered Totals -->
            <tr class="font-mono text-xs">
                <td colspan="5" class="py-1 text-right font-bold text-gray-500 uppercase tracking-tighter">Total Debit (DB)</td>
                <td class="text-right font-black py-1 text-red-600">
                    {{ formatAmount(store.filteredDebitTotal) }}
                </td>
                <td colspan="4"></td>
            </tr>
            <tr class="font-mono text-xs">
                <td colspan="5" class="py-1 text-right font-bold text-gray-500 uppercase tracking-tighter">Total Credit (CR)</td>
                <td class="text-right font-black py-1 text-green-700">
                    {{ formatAmount(store.filteredCreditTotal) }}
                </td>
                <td colspan="4"></td>
            </tr>
            <tr class="font-mono text-xs">
                <td colspan="5" class="py-2 text-right font-black text-gray-900 uppercase tracking-tighter">Total Net</td>
                <td class="text-right font-black py-2 border-t border-gray-300" :class="store.filteredTotal >= 0 ? 'text-green-800' : 'text-red-700'">
                    {{ formatAmount(Math.abs(store.filteredTotal)) }}
                    <span class="text-[10px]">{{ store.filteredTotal >= 0 ? 'CR' : 'DB' }}</span>
                </td>
                <td colspan="4"></td>
            </tr>
        </tfoot>
      </table>
    </div>

    <!-- Individual Delete Selection Modal -->
    <ConfirmModal 
        :isOpen="isDeleteModalOpen"
        title="Delete Transaction"
        :message="`Are you sure you want to delete this transaction from ${formatDate(transactionToDelete?.txn_date)}?`"
        confirmText="Delete"
        :loading="isDeleting"
        variant="danger"
        @close="isDeleteModalOpen = false"
        @confirm="handleConfirmDelete"
    />


    <!-- Pagination -->
    <div class="bg-gray-50/50 px-6 py-4 flex items-center justify-between border-t border-gray-100" v-if="!store.isLoading && store.paginatedTransactions.length > 0">
        <div class="flex flex-col md:flex-row md:items-center gap-4 w-full justify-between">
            <p class="text-[10px] text-gray-500 font-medium whitespace-nowrap">
                Showing {{ ((store.currentPage - 1) * store.itemsPerPage) + 1 }} - {{ Math.min(store.currentPage * store.itemsPerPage, store.filteredTransactions.length) }} of {{ store.filteredTransactions.length }}
            </p>
            
            <div class="flex flex-wrap gap-2 items-center justify-center">
                <select class="text-[10px] border-gray-300 rounded-lg bg-white px-2 py-1" v-model="store.itemsPerPage" @change="store.currentPage = 1">
                    <option :value="10">10 / Page</option>
                    <option :value="25">25 / Page</option>
                    <option :value="50">50 / Page</option>
                    <option :value="100">100 / Page</option>
                </select>

                <div class="flex gap-1">
                    <button 
                        class="p-1 min-w-[32px] h-8 rounded border border-gray-200 bg-white text-gray-500 hover:bg-gray-50 disabled:opacity-30 transition-colors"
                        :disabled="store.currentPage === 1"
                        @click="store.currentPage = 1"
                        title="First Page"
                    >
                        <i class="bi bi-chevron-double-left text-xs"></i>
                    </button>
                    <button 
                        class="p-1 min-w-[32px] h-8 rounded border border-gray-200 bg-white text-gray-500 hover:bg-gray-50 disabled:opacity-30 transition-colors"
                        :disabled="store.currentPage === 1"
                        @click="store.currentPage--"
                    >
                        <i class="bi bi-chevron-left text-xs"></i>
                    </button>

                    <!-- Page Numbers -->
                    <div class="flex gap-1">
                        <template v-for="page in visiblePages" :key="page">
                            <button 
                                v-if="page !== '...'"
                                class="w-8 h-8 rounded text-xs font-medium transition-all"
                                :class="store.currentPage === page ? 'bg-indigo-600 text-white shadow-sm' : 'border border-gray-200 bg-white text-gray-600 hover:bg-gray-50'"
                                @click="store.currentPage = page"
                            >
                                {{ page }}
                            </button>
                            <span v-else class="w-8 h-8 flex items-center justify-center text-gray-400">...</span>
                        </template>
                    </div>

                    <button 
                        class="p-1 min-w-[32px] h-8 rounded border border-gray-200 bg-white text-gray-500 hover:bg-gray-50 disabled:opacity-30 transition-colors"
                        :disabled="store.currentPage === store.totalPages"
                        @click="store.currentPage++"
                    >
                        <i class="bi bi-chevron-right text-xs"></i>
                    </button>
                    <button 
                        class="p-1 min-w-[32px] h-8 rounded border border-gray-200 bg-white text-gray-500 hover:bg-gray-50 disabled:opacity-30 transition-colors"
                        :disabled="store.currentPage === store.totalPages"
                        @click="store.currentPage = store.totalPages"
                        title="Last Page"
                    >
                        <i class="bi bi-chevron-double-right text-xs"></i>
                    </button>
                </div>
            </div>
        </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { useHistoryStore } from '../../stores/history';
import ConfirmModal from '../ui/ConfirmModal.vue';

const store = useHistoryStore();
const emit = defineEmits(['view-details', 'split-transaction']);

watch(() => store.paginatedTransactions, (newVal) => {
    console.log('HistoryTable: paginatedTransactions updated', newVal.length);
});

// Individual Delete State
const isDeleteModalOpen = ref(false);
const isDeleting = ref(false);
const transactionToDelete = ref(null);

const promptDelete = (txn) => {
    transactionToDelete.value = txn;
    isDeleteModalOpen.value = true;
};

const handleConfirmDelete = async () => {
    if (!transactionToDelete.value) return;
    isDeleting.value = true;
    try {
        await store.deleteTransaction(transactionToDelete.value.id);
        isDeleteModalOpen.value = false;
    } catch (e) {
        console.error(e);
    } finally {
        isDeleting.value = false;
        transactionToDelete.value = null;
    }
};


const isAllSelected = computed(() => {
    return store.paginatedTransactions.length > 0 && 
           store.paginatedTransactions.every(t => store.selectedTxnIds.includes(t.id));
});

const visiblePages = computed(() => {
    const total = store.totalPages;
    if (total < 1) return [];
    const current = store.currentPage;
    const delta = 2;
    const range = [];
    const rangeWithDots = [];
    let l;

    if (total <= 7) {
        for (let i = 1; i <= total; i++) range.push(i);
        return range;
    }

    range.push(1);
    for (let i = current - delta; i <= current + delta; i++) {
        if (i < total && i > 1) {
            range.push(i);
        }
    }
    range.push(total);

    for (let i of range) {
        if (l) {
            if (i - l === 2) {
                rangeWithDots.push(l + 1);
            } else if (i - l !== 1) {
                rangeWithDots.push('...');
            }
        }
        rangeWithDots.push(i);
        l = i;
    }

    return rangeWithDots;
});

const toggleSelectAll = () => {
    if (isAllSelected.value) {
        store.deselectAll();
    } else {
        store.selectAll();
    }
};

// Utils
const formatDate = (dateStr) => {
    if (!dateStr || typeof dateStr !== 'string') return "-";
    try {
      return dateStr.split(" ")[0];
    } catch (e) { return dateStr; }
};

const formatAmount = (val) => {
    if (val === undefined || val === null) return "0";
    const num = typeof val === 'string' ? parseFloat(val.replace(/,/g, '')) : val;
    return new Intl.NumberFormat('id-ID').format(num || 0);
};

const coaDisplayText = (txn) => {
    if (!txn.coas || txn.coas.length === 0) {
        return '';
    }
    const firstCoa = txn.coas[0];
    if (txn.coas.length === 1) {
        return `${firstCoa.code} - ${firstCoa.name}`;
    }
    return `${firstCoa.code} - ${firstCoa.name} ...`;
};
</script>
