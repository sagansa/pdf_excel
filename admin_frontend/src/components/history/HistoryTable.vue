<template>
  <TableShell>
      <table class="min-w-full table-compact history-table">
        <thead>
          <tr>
            <th class="w-10 text-center">
                <input 
                    type="checkbox" 
                    class="rounded border-[var(--color-border)] text-[var(--color-primary)] focus:ring-[var(--color-primary)]"
                    :checked="isAllSelected"
                    @change="toggleSelectAll"
                >
            </th>
            <th class="cursor-pointer hover:bg-[var(--color-surface-raised)] transition-colors" @click="store.toggleSort('txn_date')">
                Date 
                <i v-if="store.sortConfig.key === 'txn_date'" :class="{ 'bi-caret-down-fill': store.sortConfig.direction === 'desc', 'bi-caret-up-fill': store.sortConfig.direction === 'asc' }" class="bi ms-1"></i>
            </th>
             <th class="text-center">Co.</th>
            <th class="cursor-pointer hover:bg-[var(--color-surface-raised)] transition-colors" @click="store.toggleSort('description')">
                Description
                <i v-if="store.sortConfig.key === 'description'" :class="{ 'bi-caret-down-fill': store.sortConfig.direction === 'desc', 'bi-caret-up-fill': store.sortConfig.direction === 'asc' }" class="bi ms-1"></i>
            </th>
            <th class="text-right cursor-pointer hover:bg-[var(--color-surface-raised)] transition-colors" @click="store.toggleSort('amount')">
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
        <tbody class="divide-y history-table-body">
              <tr v-if="store.isLoading">
                  <td colspan="10" class="text-center py-12">
                      <span class="spinner-border w-8 h-8" style="color: var(--color-primary)" role="status"></span>
                  </td>
              </tr>
              <tr v-else-if="store.paginatedTransactions.length === 0">
                  <td colspan="10" class="text-center py-12 text-muted">
                      <i class="bi bi-inbox text-3xl mb-2 block"></i>
                      No transactions found
                  </td>
              </tr>
             <tr v-for="t in store.paginatedTransactions" :key="t.id" class="history-row cursor-pointer" :class="{ 'history-row--selected': store.selectedTxnIds.includes(t.id) }" @click="$emit('view-details', t)">
                <td class="text-center" @click.stop>
                    <input 
                        type="checkbox" 
                        class="rounded border-[var(--color-border)] text-[var(--color-primary)] focus:ring-[var(--color-primary)]"
                        :checked="store.selectedTxnIds.includes(t.id)"
                        @change="store.toggleSelection(t.id)"
                    >
                </td>
                <td class="whitespace-nowrap text-xs mono">{{ formatDate(t.txn_date) }}</td>
                <td class="whitespace-nowrap text-xs text-center font-medium text-theme" :title="t.company_name">
                    {{ t.company_short_name || '-' }}
                </td>
                <td class="text-xs break-words max-w-[200px] leading-tight" :title="t.description">{{ t.description }}</td>
                <td class="text-right mono font-bold text-sm" :class="getFlowColorClass(t.db_cr, 'text')">
                    {{ getAmountSign(t.db_cr) }}{{ formatAmount(t.amount) }}
                </td>
                 <td class="text-center">
                     <span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold" :class="getFlowColorClass(t.db_cr, 'bg')">
                       <i :class="getFlowIcon(t.db_cr)" class="text-[9px]"></i>
                       {{ getFlowLabel(t.db_cr) }}
                    </span>
                 </td>
                 <td class="text-xs mono">{{ t.bank_code }}</td>
                 <td class="text-xs max-w-[240px]" :title="coaTitleText(t)">
                      <div v-if="visibleCoas(t).length > 0" class="flex flex-wrap gap-1 items-center">
                          <i v-if="t.is_linked_to_manual" class="bi bi-link-45deg text-primary text-sm -ml-0.5" title="Referenced by manual journal"></i>
                          <span
                              v-for="coa in visibleCoas(t)"
                              :key="coa.key"
                              class="inline-flex items-center px-1.5 py-0.5 rounded-md text-[10px] font-semibold history-coa-tag"
                          >
                              {{ coa.label }}
                          </span>
                          <span
                              v-if="hiddenCoaCount(t) > 0"
                              class="inline-flex items-center px-1.5 py-0.5 rounded-md text-[10px] font-semibold history-coa-more"
                          >
                              +{{ hiddenCoaCount(t) }}
                          </span>
                      </div>
                      <span v-else class="text-[10px] text-muted italic">No COA mapping</span>
                  </td>
                  <td class="min-w-[150px]" @click.stop>
                      <div class="flex items-center gap-2">
                          <SearchableSelect
                              v-if="!t.is_split && !t.is_linked_to_manual"
                              class="w-full flex-1"
                              :model-value="t.mark_id || ''"
                              :options="markOptions"
                              placeholder="-- Unmarked --"
                              @update:model-value="onMarkSelected(t.id, $event)"
                          />
                          <div
                              v-else-if="t.is_split"
                              class="text-[10px] font-bold px-2 py-1 rounded-md flex-1 flex items-center gap-1.5 border"
                              :class="t.is_multi_marked ? 'history-chip history-chip--primary' : 'history-chip history-chip--warning'"
                          >
                             <i class="bi bi-stack"></i>
                             {{ t.is_multi_marked ? 'Mixed Marks' : 'Split (No Active Mark)' }}
                          </div>
                          <div
                              v-else-if="t.is_linked_to_manual"
                              class="text-[10px] font-bold px-2 py-1 rounded-md flex-1 flex items-center gap-1.5 border border-primary/20 bg-primary/5 text-primary"
                              :title="`Linked to: ${t.manual_mark_name || 'Manual Journal'}`"
                          >
                              <i class="bi bi-link-45deg text-sm"></i>
                              {{ t.manual_mark_name || 'Manual Journal' }}
                          </div>
                           <button
                               @click.stop="$emit('split-transaction', t)"
                               class="p-1 transition-all transform active:scale-90"
                               :class="t.is_split ? 'text-[var(--color-primary)] hover:opacity-80' : 'text-[var(--color-text-muted)] hover:text-[var(--color-primary)]'"
                               :title="t.is_split ? 'Transaction is split into multiple parts' : 'Split this transaction'"
                           >
                               <i class="bi bi-diagram-3-fill text-sm"></i>
                           </button>
                      </div>
                  </td>
                <td class="text-[10px] text-muted truncate max-w-[80px]" :title="t.source_file">{{ t.source_file }}</td>
             </tr>
        </tbody>
        <tfoot v-if="!store.isLoading && store.filteredTransactions.length > 0" class="history-table-foot">
            <!-- Page Totals -->
            <tr class="mono text-xs">
                <td colspan="5" class="py-1 text-right font-bold text-muted uppercase tracking-tighter">
                  <i class="bi bi-arrow-up-circle-fill text-danger mr-1"></i>Page Total Keluar
                </td>
                <td class="text-right font-bold py-1 text-danger">
                    {{ formatAmount(store.pageCreditTotal) }}
                </td>
                <td colspan="4"></td>
            </tr>
            <tr class="mono text-xs">
                <td colspan="5" class="py-1 text-right font-bold text-muted uppercase tracking-tighter">
                  <i class="bi bi-arrow-down-circle-fill text-success mr-1"></i>Page Total Masuk
                </td>
                <td class="text-right font-bold py-1 text-success">
                    {{ formatAmount(store.pageDebitTotal) }}
                </td>
                <td colspan="4"></td>
            </tr>
            <tr class="mono text-xs">
                <td colspan="5" class="py-2 text-right font-bold text-theme uppercase tracking-tighter">Page Net</td>
                <td class="text-right font-bold py-2 border-t history-table-divider" :class="store.pageTotal >= 0 ? 'text-success' : 'text-danger'">
                    {{ store.pageTotal >= 0 ? '+' : '-' }}{{ formatAmount(Math.abs(store.pageTotal)) }}
                    <span class="text-[10px] ml-1">{{ store.pageTotal >= 0 ? 'Masuk' : 'Keluar' }}</span>
                </td>
                <td colspan="4"></td>
            </tr>
            <!-- Filtered Totals -->
            <tr class="mono text-xs">
                <td colspan="5" class="py-1 text-right font-bold text-muted uppercase tracking-tighter">
                  <i class="bi bi-arrow-up-circle-fill text-danger mr-1"></i>Total Keluar
                </td>
                <td class="text-right font-black py-1 text-danger">
                    {{ formatAmount(store.filteredCreditTotal) }}
                </td>
                <td colspan="4"></td>
            </tr>
            <tr class="mono text-xs">
                <td colspan="5" class="py-1 text-right font-bold text-muted uppercase tracking-tighter">
                  <i class="bi bi-arrow-down-circle-fill text-success mr-1"></i>Total Masuk
                </td>
                <td class="text-right font-black py-1 text-success">
                    {{ formatAmount(store.filteredDebitTotal) }}
                </td>
                <td colspan="4"></td>
            </tr>
            <tr class="mono text-xs">
                <td colspan="5" class="py-2 text-right font-black text-theme uppercase tracking-tighter">Total Net</td>
                <td class="text-right font-black py-2 border-t history-table-divider" :class="store.filteredTotal >= 0 ? 'text-success' : 'text-danger'">
                    {{ store.filteredTotal >= 0 ? '+' : '-' }}{{ formatAmount(Math.abs(store.filteredTotal)) }}
                    <span class="text-[10px] ml-1">{{ store.filteredTotal >= 0 ? 'Masuk' : 'Keluar' }}</span>
                </td>
                <td colspan="4"></td>
            </tr>
        </tfoot>
      </table>

    <template #footer>
      <div class="history-pagination px-6 py-4 flex items-center justify-between" v-if="!store.isLoading && store.paginatedTransactions.length > 0">
          <div class="flex flex-col md:flex-row md:items-center gap-4 w-full justify-between">
              <p class="text-[10px] text-muted font-medium whitespace-nowrap">
                  Showing {{ ((store.currentPage - 1) * store.itemsPerPage) + 1 }} - {{ Math.min(store.currentPage * store.itemsPerPage, store.filteredTransactions.length) }} of {{ store.filteredTransactions.length }}
              </p>
              
              <div class="flex flex-wrap gap-2 items-center justify-center">
                  <select class="input-base !w-auto !px-2 !py-1 !text-[10px]" v-model="store.itemsPerPage" @change="store.currentPage = 1">
                      <option :value="10">10 / Page</option>
                      <option :value="25">25 / Page</option>
                      <option :value="50">50 / Page</option>
                      <option :value="100">100 / Page</option>
                  </select>

                  <div class="flex gap-1">
                      <button 
                          class="history-page-button"
                          :disabled="store.currentPage === 1"
                          @click="store.currentPage = 1"
                          title="First Page"
                      >
                          <i class="bi bi-chevron-double-left text-xs"></i>
                      </button>
                      <button 
                          class="history-page-button"
                          :disabled="store.currentPage === 1"
                          @click="store.currentPage--"
                      >
                          <i class="bi bi-chevron-left text-xs"></i>
                      </button>

                      <div class="flex gap-1">
                          <template v-for="page in visiblePages" :key="page">
                              <button 
                                  v-if="page !== '...'"
                                  class="history-page-button !w-8"
                                  :class="{ 'history-page-button--active': store.currentPage === page }"
                                  @click="store.currentPage = page"
                              >
                                  {{ page }}
                              </button>
                              <span v-else class="w-8 h-8 flex items-center justify-center text-muted">...</span>
                          </template>
                      </div>

                      <button 
                          class="history-page-button"
                          :disabled="store.currentPage === store.totalPages"
                          @click="store.currentPage++"
                      >
                          <i class="bi bi-chevron-right text-xs"></i>
                      </button>
                      <button 
                          class="history-page-button"
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
    </template>
  </TableShell>

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
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { useHistoryStore } from '../../stores/history';
import { getFlowLabel, getFlowIcon, getFlowColorClass, getAmountSign } from '../../composables/useBankDirection';
import ConfirmModal from '../ui/ConfirmModal.vue';
import SearchableSelect from '../ui/SearchableSelect.vue';
import TableShell from '../ui/TableShell.vue';

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

const markOptions = computed(() => {
    const options = [{ id: '__UNMARKED__', label: '-- Unmarked --' }];
    for (const m of store.sortedMarks || []) {
        options.push({
            id: m.id,
            label: buildMarkLabel(m)
        });
    }
    return options;
});

const toggleSelectAll = () => {
    if (isAllSelected.value) {
        store.deselectAll();
    } else {
        store.selectAll();
    }
};

const onMarkSelected = (txnId, selectedValue) => {
    const normalized = selectedValue === '__UNMARKED__' ? null : (selectedValue || null);
    store.assignMark(txnId, normalized);
};

const buildMarkLabel = (mark) => {
    const parts = [mark?.internal_report, mark?.personal_use, mark?.tax_report]
        .map(value => String(value || '').trim())
        .filter(Boolean);
    const uniqueParts = [...new Set(parts)];
    return uniqueParts.length ? uniqueParts.join(' / ') : 'Marked';
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

const normalizeCoaKey = (coa) => {
    return `${coa?.coa_id || coa?.id || ''}-${coa?.code || ''}-${coa?.name || ''}-${coa?.type || ''}`;
};

const coaRows = (txn) => {
    const list = Array.isArray(txn?.coas) ? txn.coas : [];
    const uniq = new Set();
    const rows = [];

    for (const coa of list) {
        const key = normalizeCoaKey(coa);
        if (!key || uniq.has(key)) continue;
        uniq.add(key);

        const code = coa?.code || '';
        const name = coa?.name || '';
        const label = code && name ? `${code} - ${name}` : (code || name || '-');
        rows.push({ key, label });
    }

    return rows;
};

const visibleCoas = (txn) => {
    return coaRows(txn).slice(0, 3);
};

const hiddenCoaCount = (txn) => {
    const total = coaRows(txn).length;
    return total > 3 ? total - 3 : 0;
};

const coaTitleText = (txn) => {
    const rows = coaRows(txn);
    if (rows.length === 0) return 'No COA mapping';
    return rows.map(r => r.label).join(', ');
};
</script>

<style scoped>
.history-table {
  border-color: var(--color-border);
}

.history-table-body {
  border-color: var(--color-border);
}

.history-row {
  transition: background-color 160ms ease;
}

.history-row:hover {
  background: rgba(15, 118, 110, 0.05);
}

.history-row--selected {
  background: rgba(15, 118, 110, 0.10);
}

.history-coa-tag {
  background: rgba(15, 118, 110, 0.10);
  border: 1px solid rgba(15, 118, 110, 0.18);
  color: var(--color-primary);
}

.history-coa-more {
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
  color: var(--color-text-muted);
}

.history-chip {
  border: 1px solid transparent;
}

.history-chip--primary {
  color: var(--color-primary);
  background: rgba(15, 118, 110, 0.10);
  border-color: rgba(15, 118, 110, 0.18);
}

.history-chip--warning {
  color: var(--color-warning);
  background: rgba(180, 83, 9, 0.10);
  border-color: rgba(180, 83, 9, 0.18);
}

.history-table-foot {
  background: var(--color-surface-muted);
  border-top: 2px solid var(--color-border);
}

.history-table-divider {
  border-color: var(--color-border);
}

.history-pagination {
  background: var(--color-surface-muted);
  border-top: 1px solid var(--color-border);
}

.history-page-button {
  @apply min-w-[32px] h-8 rounded text-xs font-medium transition-all;
  border: 1px solid var(--color-border);
  background: var(--color-surface-raised);
  color: var(--color-text-muted);
}

.history-page-button:hover:not(:disabled) {
  border-color: var(--color-border-strong);
  color: var(--color-text);
}

.history-page-button:disabled {
  opacity: 0.3;
}

.history-page-button--active {
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-strong));
  border-color: transparent;
  color: #fff;
}
</style>
