<template>
  <div v-if="isOpen" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" @click.self="$emit('close')">
    <div class="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
      <div class="p-6 border-b border-gray-200">
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold text-gray-900">{{ editMode ? 'Edit Contract' : 'Add New Contract' }}</h3>
          <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600">
            <i class="bi bi-x-lg"></i>
          </button>
        </div>
      </div>
      
      <form @submit.prevent="handleSubmit" class="p-6 space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Store *</label>
          <select
            v-model="form.store_id"
            required
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="">Select a store...</option>
            <option v-for="store in stores" :key="store.id" :value="store.id">
              {{ store.store_code }} - {{ store.store_name }}
            </option>
          </select>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Location *</label>
          <select
            v-model="form.location_id"
            required
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="">Select a location...</option>
            <option v-for="loc in locations" :key="loc.id" :value="loc.id">
              {{ loc.location_name }} - {{ loc.address }}
            </option>
          </select>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Start Date *</label>
            <input
              v-model="form.start_date"
              type="date"
              required
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">End Date *</label>
            <input
              v-model="form.end_date"
              type="date"
              required
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-indigo-50 border border-indigo-100 rounded-lg">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Metode Perhitungan</label>
            <select
              v-model="form.calculation_method"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            >
              <option value="BRUTO">Bruto</option>
              <option value="NETTO">Netto (Gross-up)</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Tarif PPh 4(2) (%)</label>
            <input
              v-model.number="form.pph42_rate"
              type="number"
              min="0"
              max="100"
              step="0.01"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Waktu Bayar PPh 4(2)</label>
            <select
              v-model="form.pph42_payment_timing"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            >
              <option value="same_period">Periode yang sama</option>
              <option value="next_period">Periode berikutnya</option>
              <option value="next_year">Tahun berikutnya</option>
            </select>
          </div>
        </div>

        <!-- Transaction Selection -->
        <div class="md:col-span-2 space-y-3">
          <div class="flex items-center justify-between">
            <label class="block text-sm font-bold text-gray-700">
              <i class="bi bi-link-45deg mr-1"></i>
              Link Transactions
            </label>
            <span class="text-xs text-indigo-600 bg-indigo-50 px-2 py-1 rounded-full">
              {{ selectedTransactions.length }} selected
            </span>
          </div>
          
          <div class="border border-gray-200 rounded-lg overflow-hidden">
            <div class="bg-gray-50 px-4 py-2 border-b border-gray-200">
              <div class="flex items-center gap-2">
                <input
                  v-model="transactionSearch"
                  type="text"
                  placeholder="Search transactions..."
                  class="flex-1 text-sm px-3 py-1.5 border border-gray-300 rounded focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                />
                <button
                  type="button"
                  @click="refreshTransactions"
                  class="text-gray-500 hover:text-indigo-600"
                  title="Refresh"
                >
                  <i class="bi bi-arrow-clockwise"></i>
                </button>
              </div>
            </div>
            
            <div class="max-h-60 overflow-y-auto">
              <div
                v-for="txn in filteredTransactions"
                :key="txn.id"
                class="flex items-center px-4 py-3 hover:bg-gray-50 border-b border-gray-100 last:border-0"
                :class="{ 'bg-indigo-50': isSelected(txn.id) }"
              >
                <input
                  :id="'txn-' + txn.id"
                  v-model="selectedTransactions"
                  :value="txn.id"
                  type="checkbox"
                  class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                />
                <label :for="'txn-' + txn.id" class="ml-3 flex-1 cursor-pointer">
                  <div class="flex items-center justify-between">
                    <div>
                      <div class="text-sm font-medium text-gray-900">{{ txn.description }}</div>
                      <div class="text-xs text-gray-500">
                        {{ formatDate(txn.txn_date) }} | {{ txn.personal_use || txn.internal_report || 'No mark' }}
                      </div>
                    </div>
                    <div class="text-right">
                      <div class="text-sm font-bold text-gray-900">{{ formatCurrency(txn.amount) }}</div>
                    </div>
                  </div>
                </label>
              </div>
              
              <div v-if="filteredTransactions.length === 0" class="px-4 py-8 text-center text-gray-500 text-sm">
                <i class="bi bi-inbox text-2xl mb-2 block"></i>
                No linkable transactions found
              </div>
            </div>
          </div>
          
          <!-- Total Amount Display -->
          <div class="bg-indigo-50 rounded-lg p-4 flex items-center justify-between">
            <div>
              <div class="text-xs font-bold text-indigo-700 uppercase">Total from Selected</div>
              <div class="text-sm text-indigo-600">
                {{ selectedTransactions.length }} transaction{{ selectedTransactions.length !== 1 ? 's' : '' }}
              </div>
            </div>
            <div class="text-2xl font-bold text-indigo-900">
              {{ formatCurrency(baseSelectedAmount) }}
            </div>
          </div>
        </div>

        <div class="bg-white border border-gray-200 rounded-lg p-4">
          <div class="text-xs font-bold text-gray-500 uppercase mb-3">Ringkasan Otomatis Rent & PPh 4(2)</div>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            <div>
              <div class="text-gray-500 text-xs">Dasar Pembayaran</div>
              <div class="font-semibold text-gray-900">{{ formatCurrency(baseSelectedAmount) }}</div>
            </div>
            <div>
              <div class="text-gray-500 text-xs">Nilai Bruto</div>
              <div class="font-semibold text-indigo-700">{{ formatCurrency(calculatedBrutoAmount) }}</div>
            </div>
            <div>
              <div class="text-gray-500 text-xs">Nilai Netto</div>
              <div class="font-semibold text-gray-900">{{ formatCurrency(calculatedNetAmount) }}</div>
            </div>
            <div>
              <div class="text-gray-500 text-xs">PPh 4(2)</div>
              <div class="font-semibold text-amber-700">{{ formatCurrency(calculatedTaxAmount) }}</div>
            </div>
          </div>
          <p class="text-xs text-gray-500 mt-3">
            Nilai bruto digunakan sebagai dasar perhitungan jurnal kontrak sewa.
          </p>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Total Amount *</label>
          <input
            :value="formatCurrency(calculatedBrutoAmount || 0)"
            type="text"
            readonly
            disabled
            class="w-full px-3 py-2 border border-gray-200 rounded-lg bg-gray-50 text-gray-700 cursor-not-allowed"
            placeholder="Select transactions to calculate total"
          />
          <p class="mt-1 text-xs text-gray-500">
            <i class="bi bi-info-circle mr-1"></i>
            Total is automatically calculated from selected transactions
          </p>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Payment Schedule</label>
          <select
            v-model="form.payment_schedule"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="monthly">Monthly</option>
            <option value="quarterly">Quarterly</option>
            <option value="semi-annual">Semi-Annual</option>
            <option value="annual">Annual</option>
            <option value="one-time">One-Time</option>
          </select>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Status</label>
          <select
            v-model="form.status"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="active">Active</option>
            <option value="expired">Expired</option>
            <option value="terminated">Terminated</option>
          </select>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Notes</label>
          <textarea
            v-model="form.notes"
            rows="3"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          ></textarea>
        </div>

        <div class="flex justify-end gap-3 pt-4 border-t border-gray-200">
          <button
            type="button"
            @click="$emit('close')"
            class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            :disabled="loading"
            class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50"
          >
            {{ loading ? 'Saving...' : (editMode ? 'Update' : 'Create') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue';
import { rentalApi } from '../../../api';

const props = defineProps({
  isOpen: Boolean,
  contract: Object,
  companyId: String
});

const emit = defineEmits(['close', 'saved']);

const editMode = ref(false);
const loading = ref(false);
const stores = ref([]);
const locations = ref([]);
const linkableTransactions = ref([]);
const selectedTransactions = ref([]);
const transactionSearch = ref('');

const form = ref({
  store_id: '',
  location_id: '',
  start_date: '',
  end_date: '',
  total_amount: 0,
  calculation_method: 'BRUTO',
  pph42_rate: 10,
  pph42_payment_timing: 'same_period',
  payment_schedule: 'monthly',
  status: 'active',
  notes: ''
});

watch(() => props.contract, (newContract) => {
  if (newContract && newContract.id) {
    editMode.value = true;
    form.value = {
      ...newContract,
      calculation_method: (newContract.calculation_method || 'BRUTO').toUpperCase(),
      pph42_rate: Number(newContract.pph42_rate ?? 10),
      pph42_payment_timing: newContract.pph42_payment_timing || 'same_period'
    };
  } else {
    editMode.value = false;
    if (!props.isOpen) {
      resetForm();
    }
  }
});

watch(() => props.isOpen, async (isOpen) => {
  if (isOpen) {
    await Promise.all([loadStores(), loadLocations(), loadLinkableTransactions()]);
    if (props.contract?.id) {
      await loadExistingLinkedTransactions(props.contract.id);
    }
    if (!props.contract) {
      resetForm();
    }
  } else {
    resetForm();
    editMode.value = false;
    selectedTransactions.value = [];
    transactionSearch.value = '';
  }
});

// Auto-update total amount when transactions are selected
watch(selectedTransactions, () => {
  // Always sync form.total_amount with calculated total
  form.value.total_amount = calculatedBrutoAmount.value;
}, { deep: true });

const loadStores = async () => {
  try {
    // Fetch all stores (not filtered by company)
    const response = await rentalApi.getStores(null);
    stores.value = response.data.stores || [];
  } catch (error) {
    console.error('Failed to load stores:', error);
    stores.value = [];
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

const loadLinkableTransactions = async () => {
  try {
    const currentContractId = props.contract?.id || null;
    const response = await rentalApi.getLinkableTransactions(props.companyId, currentContractId);
    linkableTransactions.value = response.data.transactions || [];
  } catch (error) {
    console.error('Failed to load linkable transactions:', error);
    linkableTransactions.value = [];
  }
};

const loadExistingLinkedTransactions = async (contractId) => {
  if (!contractId) return;
  try {
    const response = await rentalApi.getContractTransactions(contractId);
    const existing = response.data.transactions || [];
    selectedTransactions.value = existing.map(txn => txn.id).filter(Boolean);
  } catch (error) {
    console.error('Failed to load existing linked transactions:', error);
    selectedTransactions.value = [];
  }
};

const refreshTransactions = () => {
  loadLinkableTransactions();
};

const isSelected = (txnId) => {
  return selectedTransactions.value.includes(txnId);
};

const filteredTransactions = computed(() => {
  if (!transactionSearch.value) return linkableTransactions.value;
  const search = transactionSearch.value.toLowerCase();
  return linkableTransactions.value.filter(txn => 
    (txn.description || '').toLowerCase().includes(search) ||
    (txn.personal_use || '').toLowerCase().includes(search) ||
    (txn.internal_report || '').toLowerCase().includes(search)
  );
});

const baseSelectedAmount = computed(() => {
  return selectedTransactions.value.reduce((total, txnId) => {
    const txn = linkableTransactions.value.find(t => t.id === txnId);
    return total + (txn ? Math.abs(parseFloat(txn.amount || 0)) : 0);
  }, 0);
});

const safeTaxRate = computed(() => {
  const raw = Number(form.value.pph42_rate ?? 10);
  if (Number.isNaN(raw)) return 10;
  return Math.min(Math.max(raw, 0), 100);
});

const calculatedBrutoAmount = computed(() => {
  const base = baseSelectedAmount.value;
  if (!base) return 0;
  if ((form.value.calculation_method || 'BRUTO').toUpperCase() === 'NETTO') {
    const divisor = 1 - (safeTaxRate.value / 100);
    if (divisor <= 0) return 0;
    return base / divisor;
  }
  return base;
});

const calculatedNetAmount = computed(() => {
  const bruto = calculatedBrutoAmount.value;
  if (!bruto) return 0;
  if ((form.value.calculation_method || 'BRUTO').toUpperCase() === 'NETTO') {
    return baseSelectedAmount.value;
  }
  return bruto * (1 - (safeTaxRate.value / 100));
});

const calculatedTaxAmount = computed(() => {
  return Math.max(0, calculatedBrutoAmount.value - calculatedNetAmount.value);
});

const formatCurrency = (amount) => {
  if (!amount) return 'Rp 0';
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    minimumFractionDigits: 0
  }).format(amount);
};

const formatDate = (dateStr) => {
  if (!dateStr) return '-';
  const date = new Date(dateStr);
  return date.toLocaleDateString('id-ID', { year: 'numeric', month: 'short', day: 'numeric' });
};

const resetForm = () => {
  form.value = {
    store_id: '',
    location_id: '',
    start_date: '',
    end_date: '',
    total_amount: 0,
    calculation_method: 'BRUTO',
    pph42_rate: 10,
    pph42_payment_timing: 'same_period',
    payment_schedule: 'monthly',
    status: 'active',
    notes: ''
  };
};

const handleSubmit = async () => {
  loading.value = true;
  try {
    const data = {
      ...form.value,
      company_id: props.companyId,
      total_amount: calculatedBrutoAmount.value,
      linked_transaction_ids: selectedTransactions.value
    };

    console.log('Creating contract with data:', {
      ...data,
      linked_transaction_ids_count: data.linked_transaction_ids?.length || 0
    });

    let contractId;
    if (editMode.value) {
      await rentalApi.updateContract(props.contract.id, data);
      contractId = props.contract.id;
      
      // Ensure selected links are applied (idempotent on backend side)
      if (selectedTransactions.value.length > 0) {
        for (const txnId of selectedTransactions.value) {
          try {
            await rentalApi.linkTransaction(contractId, txnId);
          } catch (linkError) {
            console.error(`Failed to link transaction ${txnId}:`, linkError);
          }
        }
      }
    } else {
      const response = await rentalApi.createContract(data);
      contractId = response.data.id;
    }

    emit('saved');
    emit('close');
  } catch (error) {
    console.error('Failed to save contract:', error);
    alert('Failed to save contract: ' + (error.response?.data?.error || error.message));
  } finally {
    loading.value = false;
  }
};
</script>
