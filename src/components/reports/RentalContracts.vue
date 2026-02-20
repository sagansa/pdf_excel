<template>
  <div class="space-y-6">
    <!-- Header with Actions -->
    <div class="flex items-center justify-between">
      <div>
        <h3 class="text-lg font-semibold text-gray-900">Rental Contracts & Locations</h3>
        <p class="text-sm text-gray-500 mt-1">Manage rental contracts, stores, and locations</p>
      </div>
      <div class="flex gap-2">
        <button
          @click="showLocationModal = true"
          class="px-4 py-2 text-sm font-medium text-indigo-700 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors"
        >
          <i class="bi bi-geo-alt mr-2"></i>
          Add Location
        </button>
        <button
          @click="showStoreModal = true"
          class="px-4 py-2 text-sm font-medium text-indigo-700 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors"
        >
          <i class="bi bi-shop mr-2"></i>
          Add Store
        </button>
        <button
          @click="showContractModal = true"
          class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors"
        >
          <i class="bi bi-file-earmark-text mr-2"></i>
          Add Contract
        </button>
      </div>
    </div>

    <!-- Contracts List -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Store</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Location</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Period</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Total Amount</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Payments</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
              <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr v-for="contract in contracts" :key="contract.id" class="hover:bg-gray-50">
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm font-medium text-gray-900">{{ contract.store_name }}</div>
                <div class="text-xs text-gray-500">{{ contract.store_code }}</div>
              </td>
              <td class="px-6 py-4">
                <div class="text-sm text-gray-900">{{ contract.location_name }}</div>
                <div class="text-xs text-gray-500">{{ contract.location_address }}</div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm text-gray-900">{{ formatDate(contract.start_date) }}</div>
                <div class="text-xs text-gray-500">to {{ formatDate(contract.end_date) }}</div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                {{ formatCurrency(contract.total_amount) }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm text-gray-900">{{ contract.transaction_count }} txns</div>
                <div class="text-xs text-gray-500">{{ formatCurrency(contract.total_paid) }} paid</div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span :class="getStatusClass(contract.status)" class="px-2 py-1 text-xs font-medium rounded-full">
                  {{ contract.status }}
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                <button
                  @click="viewContractDetails(contract)"
                  class="text-indigo-600 hover:text-indigo-900 mr-3"
                >
                  View
                </button>
                <button
                  @click="editContract(contract)"
                  class="text-gray-600 hover:text-gray-900 mr-3"
                >
                  Edit
                </button>
                <button
                  @click="deleteContractConfirm(contract)"
                  class="text-red-600 hover:text-red-900"
                >
                  Delete
                </button>
              </td>
            </tr>
            <tr v-if="contracts.length === 0">
              <td colspan="7" class="px-6 py-12 text-center text-gray-500">
                <i class="bi bi-inbox text-4xl mb-2"></i>
                <p>No rental contracts found</p>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Contract Details Modal -->
    <div v-if="showDetailsModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div class="p-6 border-b border-gray-200">
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold text-gray-900">Contract Details</h3>
            <button @click="showDetailsModal = false" class="text-gray-400 hover:text-gray-600">
              <i class="bi bi-x-lg"></i>
            </button>
          </div>
        </div>
        
        <div class="p-6 space-y-6" v-if="selectedContract">
          <!-- Contract Info -->
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Store</label>
              <p class="text-sm text-gray-900">{{ selectedContract.store_name }}</p>
            </div>
            <div>
              <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Location</label>
              <p class="text-sm text-gray-900">{{ selectedContract.location_name }}</p>
            </div>
            <div>
              <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Contract Period</label>
              <p class="text-sm text-gray-900">{{ formatDate(selectedContract.start_date) }} - {{ formatDate(selectedContract.end_date) }}</p>
            </div>
            <div>
              <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Total Amount</label>
              <p class="text-sm text-gray-900">{{ formatCurrency(selectedContract.total_amount) }}</p>
            </div>
          </div>

          <!-- Linked Transactions -->
          <div>
            <div class="flex items-center justify-between mb-3">
              <h4 class="text-sm font-semibold text-gray-900">Linked Transactions</h4>
              <button
                @click="showLinkTransactionModal = true"
                class="px-3 py-1 text-xs font-medium text-indigo-700 bg-indigo-50 rounded hover:bg-indigo-100"
              >
                <i class="bi bi-link-45deg mr-1"></i>
                Link Transaction
              </button>
            </div>
            <div class="border border-gray-200 rounded-lg overflow-hidden">
              <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                  <tr>
                    <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                    <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Description</th>
                    <th class="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Amount</th>
                    <th class="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase">Status</th>
                    <th class="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
                  <tr v-for="txn in contractTransactions" :key="txn.id">
                    <td class="px-4 py-2 text-sm text-gray-900">{{ formatDate(txn.txn_date) }}</td>
                    <td class="px-4 py-2 text-sm text-gray-900">{{ txn.description }}</td>
                    <td class="px-4 py-2 text-sm text-right text-gray-900">{{ formatCurrency(txn.amount) }}</td>
                    <td class="px-4 py-2 text-center">
                      <span v-if="txn.is_journaled" class="px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded-full">
                        Journaled
                      </span>
                      <span v-else class="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-800 rounded-full">
                        Not Journaled
                      </span>
                    </td>
                    <td class="px-4 py-2 text-right">
                      <button
                        @click="unlinkTransaction(txn.id)"
                        class="text-xs text-red-600 hover:text-red-900"
                      >
                        Unlink
                      </button>
                    </td>
                  </tr>
                  <tr v-if="contractTransactions.length === 0">
                    <td colspan="5" class="px-4 py-8 text-center text-gray-500 text-sm">
                      No transactions linked yet
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Journal Entries Section -->
          <div class="border-t border-gray-200 pt-6">
            <div class="flex items-center justify-between mb-3">
              <h4 class="text-sm font-semibold text-gray-900">
                <i class="bi bi-journal-text mr-1"></i>
                Journal Entries
              </h4>
              <div class="flex gap-2">
                <button
                  v-if="generatedJournals.length > 0"
                  @click="showJournals = !showJournals"
                  class="px-3 py-1 text-xs font-medium text-gray-600 bg-gray-100 rounded hover:bg-gray-200"
                >
                  {{ showJournals ? 'Hide' : 'Show' }} Journals
                </button>
                <button
                  @click="generateJournals"
                  :disabled="isGeneratingJournals || contractTransactions.length === 0"
                  class="px-3 py-1 text-xs font-medium text-indigo-700 bg-indigo-50 rounded hover:bg-indigo-100 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <i v-if="isGeneratingJournals" class="bi bi-arrow-repeat spin mr-1"></i>
                  <i v-else class="bi bi-calculator mr-1"></i>
                  {{ isGeneratingJournals ? 'Generating...' : 'Generate Journals' }}
                </button>
              </div>
            </div>

            <!-- Journal Preview -->
            <div v-if="showJournals && generatedJournals.length > 0" class="space-y-4">
              <div
                v-for="(journal, idx) in generatedJournals"
                :key="idx"
                class="bg-gray-50 rounded-lg p-4 border border-gray-200"
              >
                <div class="flex items-center justify-between mb-2">
                  <h5 class="text-xs font-bold text-indigo-700 uppercase">
                    {{ journal.description || 'Payment' }}
                  </h5>
                  <span class="text-xs text-gray-500">{{ journal.transaction_date }}</span>
                </div>
                <table class="w-full text-xs">
                  <thead class="text-gray-400 border-b border-gray-200">
                    <tr>
                      <th class="text-left font-normal pb-1">Account</th>
                      <th class="text-right font-normal pb-1">Debit</th>
                      <th class="text-right font-normal pb-1">Credit</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-gray-100">
                    <tr v-for="entry in journal.entries" :key="entry.coa_code">
                      <td class="text-gray-700 font-medium py-1">
                        {{ entry.coa_code }} - {{ entry.coa_name }}
                      </td>
                      <td class="text-right text-gray-900">
                        {{ entry.debit > 0 ? formatCurrency(entry.debit) : '-' }}
                      </td>
                      <td class="text-right text-gray-900">
                        {{ entry.credit > 0 ? formatCurrency(entry.credit) : '-' }}
                      </td>
                    </tr>
                  </tbody>
                </table>
                <div class="mt-2 pt-2 border-t border-gray-200 flex items-center justify-between">
                  <span
                    :class="journal.is_posted ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'"
                    class="px-2 py-0.5 text-[10px] font-bold rounded uppercase"
                  >
                    {{ journal.is_posted ? 'Posted' : 'Not Posted' }}
                  </span>
                </div>
              </div>

              <!-- Amortization Summary -->
              <div v-if="amortizationSchedule.length > 0" class="bg-indigo-50 rounded-lg p-4 border border-indigo-200">
                <h5 class="text-xs font-bold text-indigo-700 uppercase mb-2">Amortization Schedule</h5>
                <div class="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span class="text-indigo-600">Duration:</span>
                    <span class="font-bold text-indigo-900 ml-1">{{ amortizationSchedule.length }} months</span>
                  </div>
                  <div>
                    <span class="text-indigo-600">Monthly Amount:</span>
                    <span class="font-bold text-indigo-900 ml-1">{{ formatCurrency(monthlyAmount) }}</span>
                  </div>
                </div>
              </div>
            </div>

            <div v-else-if="contractTransactions.length === 0" class="text-center py-6 text-gray-400 text-sm">
              <i class="bi bi-calculator text-2xl mb-2 block"></i>
              Link transactions to generate journal entries
            </div>
          </div>

        </div>
      </div>
    </div>

    <!-- Add/Edit Location Modal -->
    <AddLocationModal
      :isOpen="showLocationModal"
      :location="selectedLocation"
      :companyId="companyId"
      @close="showLocationModal = false; selectedLocation = null"
      @saved="handleLocationSaved"
    />

    <!-- Add/Edit Store Modal -->
    <AddStoreModal
      :isOpen="showStoreModal"
      :store="selectedStore"
      :companyId="companyId"
      @close="showStoreModal = false; selectedStore = null"
      @saved="handleStoreSaved"
    />

    <!-- Add/Edit Contract Modal -->
    <AddContractModal
      :isOpen="showContractModal"
      :contract="selectedContractForEdit"
      :companyId="companyId"
      @close="showContractModal = false; selectedContractForEdit = null"
      @saved="handleContractSaved"
    />

    <!-- Delete Confirmation Modal -->
    <ConfirmModal
      :isOpen="showDeleteModal"
      title="Delete Contract"
      :message="`Are you sure you want to delete the contract for ${contractToDelete?.store_name}? This action cannot be undone.`"
      confirmText="Delete"
      variant="danger"
      @close="showDeleteModal = false; contractToDelete = null"
      @confirm="confirmDeleteContract"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import { rentalApi } from '../../api';
import AddLocationModal from './modals/AddLocationModal.vue';
import AddStoreModal from './modals/AddStoreModal.vue';
import AddContractModal from './modals/AddContractModal.vue';
import ConfirmModal from '../ui/ConfirmModal.vue';

const props = defineProps({
  companyId: {
    type: String,
    required: true
  }
});

const contracts = ref([]);
const locations = ref([]);
const stores = ref([]);
const selectedContract = ref(null);
const contractTransactions = ref([]);
const generatedJournals = ref([]);
const amortizationSchedule = ref([]);
const monthlyAmount = ref(0);
const showJournals = ref(false);
const isGeneratingJournals = ref(false);

const showContractModal = ref(false);
const showLocationModal = ref(false);
const showStoreModal = ref(false);
const showDetailsModal = ref(false);
const showLinkTransactionModal = ref(false);
const showDeleteModal = ref(false);
const contractToDelete = ref(null);

const selectedLocation = ref(null);
const selectedStore = ref(null);
const selectedContractForEdit = ref(null);

const loadContracts = async () => {
  try {
    const response = await rentalApi.getContracts(props.companyId);
    contracts.value = response.data.contracts || [];
  } catch (error) {
    console.error('Failed to load contracts:', error);
  }
};

const loadLocations = async () => {
  try {
    const response = await rentalApi.getLocations(props.companyId);
    locations.value = response.data.locations || [];
  } catch (error) {
    console.error('Failed to load locations:', error);
  }
};

const loadStores = async () => {
  try {
    const response = await rentalApi.getStores(props.companyId);
    stores.value = response.data.stores || [];
  } catch (error) {
    console.error('Failed to load stores:', error);
  }
};

const viewContractDetails = async (contract) => {
  selectedContract.value = contract;
  showDetailsModal.value = true;
  
  // Reset journal-related state when opening new contract
  generatedJournals.value = [];
  amortizationSchedule.value = [];
  monthlyAmount.value = 0;
  showJournals.value = false;
  
  try {
    const response = await rentalApi.getContractTransactions(contract.id);
    contractTransactions.value = response.data.transactions || [];
  } catch (error) {
    console.error('Failed to load contract transactions:', error);
  }
};

const formatDate = (dateStr) => {
  if (!dateStr) return '-';
  const date = new Date(dateStr);
  return date.toLocaleDateString('id-ID', { year: 'numeric', month: 'short', day: 'numeric' });
};

const formatCurrency = (amount) => {
  if (!amount) return 'Rp 0';
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    minimumFractionDigits: 0
  }).format(amount);
};

const getStatusClass = (status) => {
  const classes = {
    'active': 'bg-green-100 text-green-800',
    'expired': 'bg-red-100 text-red-800',
    'terminated': 'bg-gray-100 text-gray-800'
  };
  return classes[status] || 'bg-gray-100 text-gray-800';
};

onMounted(() => {
  loadContracts();
  loadLocations();
  loadStores();
});

watch(() => props.companyId, () => {
  loadContracts();
  loadLocations();
  loadStores();
});

const handleLocationSaved = () => {
  loadLocations();
  loadContracts(); // Reload contracts in case location info changed
};

const handleStoreSaved = () => {
  loadStores();
  loadContracts(); // Reload contracts in case store info changed
};

const handleContractSaved = () => {
  loadContracts();
};

const editContract = (contract) => {
  selectedContractForEdit.value = contract;
  showContractModal.value = true;
};

const deleteContractConfirm = (contract) => {
  contractToDelete.value = contract;
  showDeleteModal.value = true;
};

const confirmDeleteContract = async () => {
  if (!contractToDelete.value) return;
  
  try {
    await rentalApi.deleteContract(contractToDelete.value.id);
    showDeleteModal.value = false;
    contractToDelete.value = null;
    loadContracts();
  } catch (error) {
    console.error('Failed to delete contract:', error);
    alert('Failed to delete contract: ' + (error.response?.data?.error || error.message));
  }
};

const unlinkTransaction = async (transactionId) => {
  if (!selectedContract.value) return;
  
  try {
    await rentalApi.unlinkTransaction(selectedContract.value.id, transactionId);
    // Reload transactions for this contract
    const response = await rentalApi.getContractTransactions(selectedContract.value.id);
    contractTransactions.value = response.data.transactions || [];
    loadContracts(); // Refresh contract list to update payment counts
  } catch (error) {
    console.error('Failed to unlink transaction:', error);
    alert('Failed to unlink transaction: ' + (error.response?.data?.error || error.message));
  }
};

const generateJournals = async () => {
  if (!selectedContract.value) return;
  
  isGeneratingJournals.value = true;
  try {
    const response = await rentalApi.generateJournals(selectedContract.value.id, props.companyId);
    generatedJournals.value = response.data.journals || [];
    amortizationSchedule.value = response.data.amortization_schedule || [];
    monthlyAmount.value = response.data.monthly_amount || 0;
    showJournals.value = true;
  } catch (error) {
    console.error('Failed to generate journals:', error);
    alert('Failed to generate journals: ' + (error.response?.data?.error || error.message));
  } finally {
    isGeneratingJournals.value = false;
  }
};

</script>
