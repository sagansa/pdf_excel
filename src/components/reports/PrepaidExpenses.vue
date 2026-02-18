<template>
  <div class="space-y-6">
    <!-- Header with Actions -->
    <div class="flex items-center justify-between">
      <div>
        <h3 class="text-lg font-bold text-indigo-900">Prepaid Rent & Amortization</h3>
        <p class="text-xs text-indigo-700 mt-0.5">
          Manage prepaid rent, calculate Gross-Up tax, and track monthly amortization.
        </p>
      </div>
      <div class="flex gap-2">
        <button
          @click="showSettings = !showSettings"
          class="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
        >
          <i class="bi bi-gear h-4 w-4 mr-2"></i>
          Mapping Settings
        </button>
        <button
          @click="openAddModal"
          class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
        >
          <i class="bi bi-plus-lg h-4 w-4 mr-2"></i>
          Add Rent Expense
        </button>
      </div>
    </div>

    <!-- Mapping Settings (Collapsible) -->
    <Transition
      enter-active-class="transition ease-out duration-200"
      enter-from-class="opacity-0 -translate-y-2"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition ease-in duration-150"
      leave-from-class="opacity-100 translate-y-0"
      leave-to-class="opacity-0 -translate-y-2"
    >
      <div v-if="showSettings" class="bg-indigo-50 rounded-lg p-6 border border-indigo-100">
        <div class="flex items-center justify-between mb-4">
          <h4 class="text-sm font-bold text-indigo-900 uppercase tracking-wider">Default Mapping & Tax Configuration</h4>
          <button @click="saveAllSettings" class="text-xs font-bold text-indigo-600 hover:text-indigo-800">
            Save All Settings
          </button>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div v-for="setting in settingsList" :key="setting.key" class="space-y-1">
            <label class="block text-[10px] font-bold text-indigo-700 uppercase">{{ setting.label }}</label>
            <div v-if="setting.type === 'coa'" class="relative">
              <select
                v-model="settingsData[setting.key]"
                class="block w-full pl-3 pr-10 py-2 text-xs border-indigo-200 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 rounded-md bg-white"
              >
                <option v-for="coa in coaOptions" :key="coa.id" :value="coa.id">
                  {{ coa.code }} - {{ coa.name }}
                </option>
              </select>
            </div>
            <div v-else class="relative">
              <input
                v-model="settingsData[setting.key]"
                type="number"
                class="block w-full pl-3 pr-10 py-2 text-xs border-indigo-200 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 rounded-md bg-white"
              />
              <span class="absolute inset-y-0 right-0 pr-3 flex items-center text-indigo-500 text-[10px]">%</span>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Main List Table -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead class="bg-gray-50 border-b border-gray-200">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Start Date</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Description</th>
              <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Dur (Mo)</th>
              <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Bruto (Rp)</th>
              <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Monthly (Rp)</th>
              <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Accum. (Rp)</th>
              <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Book Value (Rp)</th>
              <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Accounting</th>
              <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
              <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-if="isLoadingItems" class="animate-pulse">
              <td colspan="10" class="px-4 py-8 text-center text-gray-400 text-sm">Loading items...</td>
            </tr>
            <tr v-else-if="items.length === 0">
              <td colspan="10" class="px-4 py-12 text-center text-gray-400 text-sm">
                <div class="flex flex-col items-center">
                  <i class="bi bi-file-earmark-text h-10 w-10 text-gray-200 mb-2" style="font-size: 2.5rem;"></i>
                  <span>No prepaid rent expenses found.</span>
                </div>
              </td>
            </tr>
            <tr v-for="item in items" :key="item.id" class="hover:bg-indigo-50/10 transition-colors">
              <td class="px-4 py-4 text-xs font-mono text-gray-600">{{ formatDate(item.start_date) }}</td>
              <td class="px-4 py-4">
                <div class="text-sm font-bold text-gray-900 leading-tight">{{ item.description }}</div>
                <div class="text-[10px] text-gray-500 mt-1 uppercase">
                  {{ item.prepaid_coa_code || '1421' }} <i class="bi bi-arrow-right h-2 w-2 inline mx-1"></i> {{ item.expense_coa_code || '5315' }}
                </div>
                <div v-if="item.contract_id" class="mt-2">
                  <button
                    @click="viewContract(item.contract_id)"
                    class="text-xs text-indigo-600 hover:text-indigo-800 flex items-center"
                  >
                    <i class="bi bi-link-45deg mr-1"></i>
                    View Contract
                  </button>
                </div>
                <div v-else-if="item.is_gross_up && !item.contract_id" class="mt-1">
                  <span class="text-[9px] text-gray-400">
                    <i class="bi bi-robot mr-1"></i>
                    Manual entry
                  </span>
                </div>
              </td>
              <td class="px-4 py-4 text-center text-xs font-medium text-gray-700">{{ item.duration_months }}</td>
              <td class="px-4 py-4 text-right text-xs font-bold text-gray-900">{{ formatCurrency(item.amount_bruto) }}</td>
              <td class="px-4 py-4 text-right text-xs text-indigo-600 font-semibold">{{ formatCurrency(item.monthly_expense) }}</td>
              <td class="px-4 py-4 text-right text-xs text-gray-600">{{ formatCurrency(item.accumulated_amortization) }}</td>
              <td class="px-4 py-4 text-right text-xs font-bold text-indigo-700">{{ formatCurrency(item.book_value) }}</td>
              <td class="px-4 py-4 text-center">
                <div v-if="item.is_journaled" class="flex flex-col items-center">
                  <span class="px-2 py-0.5 text-[9px] font-bold bg-green-100 text-green-700 rounded-full border border-green-200">JOURNALED</span>
                  <span v-if="item.txn_bank_code" class="text-[8px] text-gray-400 mt-0.5 font-mono">{{ item.txn_bank_code }}</span>
                </div>
                <button 
                  v-else 
                  @click="openJournalModal(item)"
                  class="px-2 py-1 text-[9px] font-bold bg-amber-50 text-amber-600 hover:bg-amber-100 rounded border border-amber-200 transition-colors"
                >
                  NOT JOURNALED
                </button>
              </td>
              <td class="px-4 py-4 text-center">
                <span 
                  class="px-2 py-1 text-[10px] font-bold rounded uppercase tracking-wider"
                  :class="item.is_fully_amortized ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700'"
                >
                  {{ item.is_fully_amortized ? 'Completed' : 'Active' }}
                </span>
                <div class="text-[9px] text-gray-400 mt-1">{{ item.months_active }} / {{ item.duration_months }} mo</div>
              </td>
              <td class="px-4 py-4 text-center">
                <div class="flex justify-center gap-2">
                  <button @click="openEditModal(item)" class="text-gray-400 hover:text-indigo-600 transition-colors">
                    <i class="bi bi-pencil-square h-5 w-5"></i>
                  </button>
                  <button @click="confirmDelete(item)" class="text-gray-400 hover:text-red-600 transition-colors">
                    <i class="bi bi-trash h-5 w-5"></i>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Add/Edit Modal -->
    <TransitionRoot appear :show="isModalOpen" as="template">
      <Dialog as="div" @close="isModalOpen = false" class="relative z-50">
        <TransitionChild
          as="template"
          enter="duration-300 ease-out"
          enter-from="opacity-0"
          enter-to="opacity-100"
          leave="duration-200 ease-in"
          leave-from="opacity-100"
          leave-to="opacity-0"
        >
          <div class="fixed inset-0 bg-black/30 backdrop-blur-sm" />
        </TransitionChild>

        <div class="fixed inset-0 overflow-y-auto">
          <div class="flex min-h-full items-center justify-center p-4">
            <TransitionChild
              as="template"
              enter="duration-300 ease-out"
              enter-from="opacity-0 scale-95"
              enter-to="opacity-100 scale-100"
              leave="duration-200 ease-in"
              leave-from="opacity-100 scale-100"
              leave-to="opacity-0 scale-95"
            >
              <DialogPanel class="w-full max-w-2xl transform overflow-hidden rounded-2xl bg-white p-6 text-left align-middle shadow-xl transition-all">
                <DialogTitle as="h3" class="text-xl font-bold text-indigo-900 border-b border-gray-100 pb-4 mb-6">
                  {{ editingId ? 'Update Rent Expense' : 'Add New Rent Expense' }}
                </DialogTitle>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <!-- Description (Full span) -->
                  <div class="md:col-span-2 space-y-1">
                    <label class="block text-xs font-bold text-gray-500 uppercase">Item Description</label>
                    <input
                      v-model="formData.description"
                      type="text"
                      placeholder="e.g., Office Rent Aug 2025 - Jul 2027"
                      class="block w-full border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                    />
                  </div>

                  <!-- Link to Bank Transaction -->
                  <div class="md:col-span-2 space-y-1">
                    <div class="flex items-center justify-between mb-1">
                      <label class="block text-xs font-bold text-gray-500 uppercase">Link Bank Transaction (Initial Payment)</label>
                      <span class="flex items-center gap-1 text-[10px] font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full border border-indigo-100">
                        <i class="bi bi-stars"></i>
                        Smart Match
                      </span>
                    </div>
                    <div class="relative">
                      <select
                        v-model="formData.transaction_id"
                        class="block w-full border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm bg-indigo-50/30"
                      >
                        <option :value="null">-- Select Transaction (Smart Match) --</option>
                        <option v-for="txn in linkableTransactions" :key="txn.id" :value="txn.id">
                          {{ formatDate(txn.txn_date) }} - {{ txn.description }} ({{ formatCurrency(txn.amount) }})
                        </option>
                      </select>
                      <button 
                        v-if="formData.transaction_id" 
                        @click="autoFillFromTxn"
                        class="absolute right-8 top-1/2 -translate-y-1/2 text-[10px] font-bold text-indigo-600 hover:text-indigo-800"
                        title="Auto-fill details from this transaction"
                      >
                        Auto-fill
                      </button>
                    </div>
                    <p class="text-[9px] text-gray-400 italic">
                      Showing only transactions marked for <b>Rent Expense</b> (Outgoing/Debit).
                    </p>
                  </div>

                  <!-- Date & Duration -->
                  <div class="space-y-1">
                    <label class="block text-xs font-bold text-gray-500 uppercase">Start Date</label>
                    <input
                      v-model="formData.start_date"
                      type="date"
                      class="block w-full border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                    />
                  </div>
                  <div class="space-y-1">
                    <label class="block text-xs font-bold text-gray-500 uppercase">Duration (Months)</label>
                    <div class="relative">
                      <input
                        v-model.number="formData.duration_months"
                        type="number"
                        class="block w-full border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                      />
                      <span class="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 text-xs">months</span>
                    </div>
                  </div>

                  <!-- Bruto/Net Toggle -->
                  <div class="md:col-span-2 bg-indigo-50/50 p-4 rounded-xl border border-indigo-100 flex items-center justify-between">
                    <div>
                      <h4 class="text-sm font-bold text-indigo-900">Calculation Method</h4>
                      <p class="text-[10px] text-indigo-600 mt-0.5">Choose if the initial amount is Bruto or Net (after PPh 4(2)).</p>
                    </div>
                    <div class="flex items-center bg-white p-1 rounded-lg border border-indigo-200">
                      <button
                        @click="formData.is_gross_up = false"
                        class="px-4 py-1.5 text-xs font-bold rounded-md transition-all"
                        :class="!formData.is_gross_up ? 'bg-indigo-600 text-white shadow-sm' : 'text-gray-500 hover:text-indigo-600'"
                      >
                        Bruto (Before Tax)
                      </button>
                      <button
                        @click="formData.is_gross_up = true"
                        class="px-4 py-1.5 text-xs font-bold rounded-md transition-all"
                        :class="formData.is_gross_up ? 'bg-indigo-600 text-white shadow-sm' : 'text-gray-500 hover:text-indigo-600'"
                      >
                        Net (Gross-Up)
                      </button>
                    </div>
                  </div>

                  <!-- Amount Inputs -->
                  <div v-if="!formData.is_gross_up" class="md:col-span-2 space-y-1">
                    <label class="block text-xs font-bold text-gray-500 uppercase">Bruto Amount (Paid to Landlord)</label>
                    <div class="relative">
                      <span class="absolute inset-y-0 left-0 pl-3 flex items-center text-gray-500 text-sm font-bold">Rp</span>
                      <input
                        v-model.number="formData.amount_bruto"
                        type="number"
                        class="block w-full pl-10 border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm font-bold text-indigo-700"
                      />
                    </div>
                  </div>
                  <template v-else>
                    <div class="space-y-1">
                      <label class="block text-xs font-bold text-gray-500 uppercase">Net Amount Received by Landlord</label>
                      <div class="relative">
                        <span class="absolute inset-y-0 left-0 pl-3 flex items-center text-gray-500 text-sm font-bold">Rp</span>
                        <input
                          v-model.number="formData.amount_net"
                          type="number"
                          class="block w-full pl-10 border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm font-bold"
                        />
                      </div>
                    </div>
                    <div class="space-y-1">
                      <label class="block text-xs font-bold text-gray-500 uppercase">PPh 4(2) Final Rate</label>
                      <div class="relative">
                        <input
                          v-model.number="formData.tax_rate"
                          type="number"
                          class="block w-full border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                        />
                        <span class="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 text-xs">%</span>
                      </div>
                    </div>
                    <div class="md:col-span-2 bg-green-50 p-3 rounded-lg flex items-center gap-3">
                      <div class="bg-green-100 p-2 rounded-full"><i class="bi bi-stars h-5 w-5 text-green-600"></i></div>
                      <div>
                        <div class="text-[10px] text-green-700 font-bold uppercase tracking-wider">Calculated Bruto (Gross-Up)</div>
                        <div class="text-lg font-bold text-green-900">{{ formatCurrency(calculatedBrutoFromNet) }}</div>
                      </div>
                    </div>
                  </template>

                  <!-- Account Override (Optional) -->
                  <div class="md:col-span-2 pt-2">
                    <button 
                      @click="showOverrides = !showOverrides"
                      class="text-[10px] font-bold text-gray-400 uppercase tracking-widest flex items-center hover:text-indigo-500 transition-colors"
                    >
                      <i 
                        class="bi bi-chevron-down h-3 w-3 mr-1 transition-transform" 
                        :class="showOverrides ? 'rotate-180' : ''"
                      ></i>
                      Custom Account Mapping (Optional)
                    </button>
                    
                    <div v-if="showOverrides" class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3 animate-fade-in">
                      <div v-for="setting in coaSettings" :key="setting.key" class="space-y-1">
                        <label class="block text-[10px] font-bold text-gray-500 uppercase">{{ setting.label }}</label>
                        <select
                          v-model="formData[setting.key]"
                          class="block w-full px-2 py-1.5 text-xs border-gray-300 focus:ring-indigo-500 focus:border-indigo-500 rounded-md"
                        >
                          <option :value="null">Use Default Mapping</option>
                          <option v-for="coa in coaOptions" :key="coa.id" :value="coa.id">
                            {{ coa.code }} - {{ coa.name }}
                          </option>
                        </select>
                      </div>
                    </div>
                  </div>
                </div>

                <div class="mt-8 flex justify-end gap-3 border-t border-gray-100 pt-6">
                  <button
                    @click="isModalOpen = false"
                    class="px-4 py-2 text-sm font-bold text-gray-500 hover:text-gray-700"
                  >
                    Cancel
                  </button>
                  <button
                    @click="saveItem"
                    :disabled="isSubmitting"
                    class="inline-flex items-center px-6 py-2 border border-transparent text-sm font-bold rounded-lg shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
                  >
                    <i v-if="isSubmitting" class="bi bi-arrow-repeat spin h-4 w-4 mr-2"></i>
                    {{ editingId ? 'Update Expense' : 'Confirm & Save' }}
                  </button>
                </div>
              </DialogPanel>
            </TransitionChild>
          </div>
        </div>
      </Dialog>
    </TransitionRoot>

    <!-- Journal Preview Modal -->
    <TransitionRoot appear :show="isJournalModalOpen" as="template">
      <Dialog as="div" @close="isJournalModalOpen = false" class="relative z-50">
        <TransitionChild
          as="template"
          enter="duration-300 ease-out"
          enter-from="opacity-0"
          enter-to="opacity-100"
          leave="duration-200 ease-in"
          leave-from="opacity-100"
          leave-to="opacity-0"
        >
          <div class="fixed inset-0 bg-black/30 backdrop-blur-sm" />
        </TransitionChild>

        <div class="fixed inset-0 overflow-y-auto">
          <div class="flex min-h-full items-center justify-center p-4">
            <TransitionChild
              as="template"
              enter="duration-300 ease-out"
              enter-from="opacity-0 scale-95"
              enter-to="opacity-100 scale-100"
              leave="duration-200 ease-in"
              leave-from="opacity-100 scale-100"
              leave-to="opacity-0 scale-95"
            >
              <DialogPanel class="w-full max-w-lg transform overflow-hidden rounded-2xl bg-white p-6 shadow-xl transition-all">
                <DialogTitle as="h3" class="text-lg font-bold text-indigo-900 mb-4 border-b pb-2">
                  Generate Accounting Journals
                </DialogTitle>

                <div v-if="isLoadingJournals" class="py-12 flex flex-col items-center justify-center">
                  <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mb-2"></div>
                  <span class="text-xs text-gray-500">Generating preview...</span>
                </div>
                
                <div v-else-if="journalPreviews.length">
                  <div class="space-y-4 max-h-[400px] overflow-y-auto pr-2">
                    <div v-for="(j, idx) in journalPreviews" :key="idx" class="bg-gray-50 rounded-lg p-3 border border-gray-100">
                      <div class="flex justify-between items-center mb-2">
                        <h4 class="text-[10px] font-bold text-indigo-700 uppercase">{{ j.title }}</h4>
                        <span class="text-[10px] font-mono text-gray-500">{{ j.date }}</span>
                      </div>
                      <table class="w-full text-[10px]">
                        <thead class="text-gray-400 border-b border-gray-200">
                          <tr>
                            <th class="text-left font-normal pb-1">Account</th>
                            <th class="text-right font-normal pb-1">Debit</th>
                            <th class="text-right font-normal pb-1">Credit</th>
                          </tr>
                        </thead>
                        <tbody class="divide-y divide-gray-100">
                          <tr v-for="entry in j.entries" :key="entry.coa_code" class="h-6">
                            <td class="text-gray-700 font-medium whitespace-nowrap overflow-hidden text-ellipsis max-w-[150px]">
                              {{ entry.coa_code }} - {{ entry.coa_name }}
                            </td>
                            <td class="text-right text-gray-900">{{ entry.debit > 0 ? formatCurrency(entry.debit) : '-' }}</td>
                            <td class="text-right text-gray-900">{{ entry.credit > 0 ? formatCurrency(entry.credit) : '-' }}</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>
                  
                  <div class="mt-6 bg-indigo-50 p-3 rounded-lg flex items-start gap-2">
                    <i class="bi bi-info-circle text-indigo-400 mt-0.5"></i>
                    <p class="text-[10px] text-indigo-700">
                      Clicking <b>Confirm Journal</b> will post these initial entries and mark this item as journaled.
                    </p>
                  </div>
                </div>

                <div class="mt-8 flex justify-end gap-3 pt-4 border-t border-gray-100">
                  <button @click="isJournalModalOpen = false" class="text-sm font-bold text-gray-400 hover:text-gray-600">Cancel</button>
                  <button 
                    @click="confirmJournal" 
                    :disabled="isSubmittingJournal"
                    class="px-5 py-2 bg-indigo-600 text-white rounded-lg text-sm font-bold hover:bg-indigo-700 disabled:opacity-50"
                  >
                    Post Journal Entry
                  </button>
                </div>
              </DialogPanel>
            </TransitionChild>
          </div>
        </div>
      </Dialog>
    </TransitionRoot>

    <!-- Delete Confirmation Modal -->
    <ConfirmModal
      :isOpen="showDeleteModal"
      title="Delete Prepaid Expense"
      :message="`Are you sure you want to delete &quot;${itemToDelete?.description}&quot;? This action cannot be undone.`"
      confirmText="Delete"
      variant="danger"
      @close="showDeleteModal = false; itemToDelete = null"
      @confirm="confirmDeleteExpense"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue';
import { useReportsStore } from '../../stores/reports';
import { useCoaStore } from '../../stores/coa';
import { coaApi } from '../../api';
import { 
  Dialog, DialogPanel, DialogTitle, TransitionRoot, TransitionChild 
} from '@headlessui/vue';
import ConfirmModal from '../ui/ConfirmModal.vue';

const props = defineProps({
  filters: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(['navigate-to-contract']);

const reportsStore = useReportsStore();
const coaStore = useCoaStore();
const items = ref([]);
const coaOptions = computed(() => coaStore.coaList);
const isLoadingItems = ref(false);
const isSubmitting = ref(false);
const isModalOpen = ref(false);
const showSettings = ref(false);
const showOverrides = ref(false);
const editingId = ref(null);
const showDeleteModal = ref(false);
const itemToDelete = ref(null);

// Form & Settings Data
const formData = ref({
  description: '',
  start_date: new Date().toISOString().slice(0, 10),
  duration_months: 24,
  amount_net: 0,
  amount_bruto: 0,
  tax_rate: 10,
  is_gross_up: true,
  notes: '',
  prepaid_coa_id: null,
  expense_coa_id: null,
  tax_payable_coa_id: null,
  transaction_id: null
});

const linkableTransactions = ref([]);
const isJournalModalOpen = ref(false);
const isLoadingJournals = ref(false);
const isSubmittingJournal = ref(false);
const journalPreviews = ref([]);
const activeJournalItem = ref(null);
const settingsData = ref({
  prepaid_prepaid_asset_coa: null,
  prepaid_rent_expense_coa: null,
  prepaid_tax_payable_coa: null,
  prepaid_default_tax_rate: 10
});

const settingsList = [
  { key: 'prepaid_prepaid_asset_coa', label: 'Prepaid Asset Account', type: 'coa' },
  { key: 'prepaid_rent_expense_coa', label: 'Rent Expense Account', type: 'coa' },
  { key: 'prepaid_tax_payable_coa', label: 'Tax Payable Account', type: 'coa' },
  { key: 'prepaid_default_tax_rate', label: 'Default PPh 4(2) Rate', type: 'rate' }
];

const coaSettings = [
  { key: 'prepaid_coa_id', label: 'Asset COA (e.g. 1421)' },
  { key: 'expense_coa_id', label: 'Expense COA (e.g. 5315)' },
  { key: 'tax_payable_coa_id', label: 'Tax COA (e.g. 2191)' }
];

// Computed
const calculatedBrutoFromNet = computed(() => {
  if (!formData.value.amount_net || !formData.value.tax_rate) return 0;
  return formData.value.amount_net / (1 - (formData.value.tax_rate / 100));
});

// Methods
const fetchItems = async () => {
  isLoadingItems.value = true;
  try {
    items.value = await reportsStore.fetchPrepaidExpenses(
      props.filters.companyId,
      props.filters.asOfDate
    );
  } finally {
    isLoadingItems.value = false;
  }
};

const fetchInitialData = async () => {
  // Load COA Options from store
  if (coaStore.coaList.length === 0) {
    await coaStore.fetchCoa();
  }

  // Load Settings
  const settings = await reportsStore.fetchAmortizationSettings(props.filters.companyId);
  Object.keys(settingsData.value).forEach(key => {
    if (settings[key]) {
      settingsData.value[key] = settings[key].type === 'number' 
        ? Number(settings[key].value) 
        : settings[key].value;
    }
  });

  await fetchItems();
};

const openAddModal = () => {
  editingId.value = null;
  formData.value = {
    description: '',
    start_date: new Date().toISOString().slice(0, 10),
    duration_months: 24,
    amount_net: 0,
    amount_bruto: 0,
    tax_rate: settingsData.value.prepaid_default_tax_rate || 10,
    is_gross_up: true,
    notes: '',
    prepaid_coa_id: settingsData.value.prepaid_prepaid_asset_coa,
    expense_coa_id: settingsData.value.prepaid_rent_expense_coa,
    tax_payable_coa_id: settingsData.value.prepaid_tax_payable_coa,
    transaction_id: null
  };
  fetchLinkableTransactions();
  isModalOpen.value = true;
};

const openEditModal = (item) => {
  editingId.value = item.id;
  formData.value = {
    ...item,
    amount_net: item.amount_net || 0,
    amount_bruto: item.amount_bruto || 0,
    tax_rate: item.tax_rate || 10,
    is_gross_up: !!item.is_gross_up,
    transaction_id: item.transaction_id
  };
  fetchLinkableTransactions();
  isModalOpen.value = true;
};

const fetchLinkableTransactions = async () => {
  linkableTransactions.value = await reportsStore.fetchPrepaidLinkableTransactions(
    props.filters.companyId,
    formData.value.transaction_id
  );
};

const autoFillFromTxn = () => {
  const txn = linkableTransactions.value.find(t => t.id === formData.value.transaction_id);
  if (txn) {
    if (!formData.value.description) formData.value.description = txn.description;
    formData.value.start_date = txn.txn_date;
    if (formData.value.is_gross_up) {
      formData.value.amount_net = txn.amount;
    } else {
      formData.value.amount_bruto = txn.amount;
    }
  }
};

const openJournalModal = async (item) => {
  activeJournalItem.value = item;
  isJournalModalOpen.value = true;
  isLoadingJournals.value = true;
  try {
    journalPreviews.value = await reportsStore.fetchPrepaidJournalEntries(item.id);
  } finally {
    isLoadingJournals.value = false;
  }
};

const confirmJournal = async () => {
  if (!activeJournalItem.value) return;
  isSubmittingJournal.value = true;
  try {
    await reportsStore.postPrepaidJournal(activeJournalItem.value.id);
    isJournalModalOpen.value = false;
    await fetchItems();
  } catch (e) {
    alert('Error posting journal: ' + e.message);
  } finally {
    isSubmittingJournal.value = false;
  }
};

const saveItem = async () => {
  if (!formData.value.description || !formData.value.start_date) {
    alert('Please fill in Description and Start Date');
    return;
  }

  isSubmitting.value = true;
  try {
    const payload = {
      ...formData.value,
      company_id: props.filters.companyId
    };

    if (editingId.value) {
      await reportsStore.updatePrepaidExpense(editingId.value, payload);
    } else {
      await reportsStore.addPrepaidExpense(payload);
    }
    
    isModalOpen.value = false;
    await fetchItems();
    // Refresh parent reports to show updated amortization
    reportsStore.fetchAllReports();
  } catch (e) {
    alert('Error saving expense: ' + e.message);
  } finally {
    isSubmitting.value = false;
  }
};

const viewContract = (contractId) => {
  emit('navigate-to-contract', contractId);
};

const confirmDelete = (item) => {
  itemToDelete.value = item;
  showDeleteModal.value = true;
};

const confirmDeleteExpense = async () => {
  if (!itemToDelete.value) return;
  
  try {
    await reportsStore.deletePrepaidExpense(itemToDelete.value.id);
    showDeleteModal.value = false;
    itemToDelete.value = null;
    await fetchItems();
    reportsStore.fetchAllReports();
  } catch (error) {
    console.error('Failed to delete prepaid expense:', error);
    alert('Failed to delete prepaid expense: ' + (error.response?.data?.error || error.message));
  }
};

const saveAllSettings = async () => {
  try {
    const promises = Object.keys(settingsData.value).map(key => {
      const type = key === 'prepaid_default_tax_rate' ? 'number' : 'text';
      return reportsStore.saveAmortizationSettings({
        company_id: props.filters.companyId,
        setting_name: key,
        setting_value: String(settingsData.value[key]),
        setting_type: type
      });
    });
    await Promise.all(promises);
    alert('Settings saved successfully');
    showSettings.value = false;
  } catch (e) {
    alert('Error saving settings: ' + e.message);
  }
};

// Utils
const formatCurrency = (val) => {
  if (!val) return 'Rp 0.00';
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    minimumFractionDigits: 2
  }).format(val);
};

const formatDate = (dateStr) => {
  if (!dateStr) return '-';
  const d = new Date(dateStr);
  return d.toLocaleDateString('id-ID', { day: '2-digit', month: 'short', year: 'numeric' });
};

// Watch for filter changes
watch(() => [props.filters.asOfDate, props.filters.companyId], () => {
  fetchItems();
});

onMounted(() => {
  fetchInitialData();
});
</script>

<style scoped>
.animate-fade-in {
  animation: fadeIn 0.3s ease-out;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(5px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
