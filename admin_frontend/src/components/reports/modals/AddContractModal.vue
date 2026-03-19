<template>
  <BaseModal
    :isOpen="isOpen"
    size="2xl"
    @close="$emit('close')"
  >
    <template #title>
      {{ editMode ? 'Edit Contract' : 'Add New Contract' }}
    </template>
    
    <form @submit.prevent="handleSubmit" class="space-y-4 px-6">
      <!-- Store and Location -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <FormField label="Store *">
          <SelectInput
            v-model="form.store_id"
            required
            placeholder="Select a store..."
            :options="stores.map(s => ({ value: s.id, label: `${s.store_code} - ${s.store_name}` }))"
          />
        </FormField>

        <FormField label="Location *">
          <SelectInput
            v-model="form.location_id"
            required
            placeholder="Select a location..."
            :options="locations.map(l => ({ value: l.id, label: `${l.location_name} - ${l.address}` }))"
          />
        </FormField>
      </div>

      <!-- Dates -->
      <div class="grid grid-cols-2 gap-4">
        <FormField label="Start Date *">
          <TextInput
            v-model="form.start_date"
            type="date"
            required
          />
        </FormField>
        <FormField label="End Date *">
          <TextInput
            v-model="form.end_date"
            type="date"
            required
          />
        </FormField>
      </div>

      <!-- Accounting Config -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-4 bg-primary/5 border border-primary/10 rounded-2xl">
        <FormField label="Metode">
          <SelectInput
            v-model="form.calculation_method"
            :options="[
              { value: 'BRUTO', label: 'Bruto' },
              { value: 'NETTO', label: 'Netto (Gross-up)' }
            ]"
            size="sm"
          />
        </FormField>
        <FormField label="Tarif PPh (%)">
          <TextInput
            v-model.number="form.pph42_rate"
            type="number"
            min="0"
            max="100"
            step="0.01"
            size="sm"
          />
        </FormField>
        <FormField label="Waktu Bayar">
          <SelectInput
            v-model="form.pph42_payment_timing"
            :options="[
              { value: 'same_period', label: 'Periode sama' },
              { value: 'next_period', label: 'Bulan depan' },
              { value: 'next_year', label: 'Tahun depan' }
            ]"
            size="sm"
          />
        </FormField>
        
        <template v-if="form.pph42_payment_timing !== 'same_period'">
          <FormField label="Tanggal Bayar PPh">
            <TextInput
              v-model="form.pph42_payment_date"
              type="date"
              size="sm"
            />
          </FormField>
          <FormField label="No. Ref Pembayaran PPh">
            <TextInput
              v-model="form.pph42_payment_ref"
              placeholder="NTPN / Ref #"
              size="sm"
            />
          </FormField>
        </template>
      </div>

      <!-- Transaction Selection -->
      <div class="space-y-3">
        <div class="flex items-center justify-between">
          <label class="block text-xs font-bold text-theme">
            <i class="bi bi-link-45deg mr-1"></i>
            Link Transactions
          </label>
          <span class="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
            {{ selectedTransactions.length }} selected
          </span>
        </div>
        
        <div class="border border-border rounded-2xl overflow-hidden">
          <div class="bg-surface-muted px-4 py-2 border-b border-border">
            <div class="flex items-center gap-2">
              <TextInput
                v-model="transactionSearch"
                placeholder="Search transactions..."
                class="flex-1"
                size="sm"
              />
              <button
                type="button"
                @click="refreshTransactions"
                class="text-theme-muted hover:text-primary transition-colors px-2"
                title="Refresh"
              >
                <i class="bi bi-arrow-clockwise"></i>
              </button>
            </div>
          </div>
          
          <div class="max-h-48 overflow-y-auto">
            <div
              v-for="txn in filteredTransactions"
              :key="txn.id"
              class="flex items-center px-4 py-3 hover:bg-surface-muted border-b border-border last:border-0"
              :class="{ 'bg-surface-muted': isSelected(txn.id) }"
            >
              <input
                :id="'txn-' + txn.id"
                v-model="selectedTransactions"
                :value="txn.id"
                type="checkbox"
                class="h-4 w-4 text-primary focus:ring-primary border-border rounded"
              />
              <label :for="'txn-' + txn.id" class="ml-3 flex-1 cursor-pointer">
                <div class="flex items-center justify-between">
                  <div>
                    <div class="text-xs font-semibold text-theme">{{ txn.description }}</div>
                    <div class="text-[10px] text-theme-muted">
                      {{ formatDate(txn.txn_date) }} | {{ txn.personal_use || txn.internal_report || 'No mark' }}
                    </div>
                  </div>
                  <div class="text-right">
                    <div class="text-xs font-bold text-theme font-mono">{{ formatCurrency(txn.amount) }}</div>
                  </div>
                </div>
              </label>
            </div>
            
            <div v-if="filteredTransactions.length === 0" class="px-4 py-8 text-center text-theme-muted text-xs">
              <i class="bi bi-inbox text-2xl mb-2 block opacity-40"></i>
              No linkable transactions found
            </div>
          </div>
        </div>
      </div>

      <!-- Summary -->
      <div class="rounded-2xl px-4 py-3 bg-primary/5 border border-primary/10">
        <div class="text-[10px] font-bold text-theme-muted uppercase mb-3 tracking-wider">Accounting Summary</div>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div>
            <div class="text-theme-muted text-[10px] uppercase font-bold">Dasar Bayar</div>
            <div class="text-xs font-semibold text-theme">{{ formatCurrency(baseSelectedAmount) }}</div>
          </div>
          <div>
            <div class="text-theme-muted text-[10px] uppercase font-bold">Bruto</div>
            <div class="text-xs font-bold text-primary">{{ formatCurrency(calculatedBrutoAmount) }}</div>
          </div>
          <div>
            <div class="text-theme-muted text-[10px] uppercase font-bold">Netto</div>
            <div class="text-xs font-semibold text-theme">{{ formatCurrency(calculatedNetAmount) }}</div>
          </div>
          <div>
             <div class="text-theme-muted text-[10px] uppercase font-bold">PPh 4(2)</div>
            <div class="text-xs font-bold text-amber-600 dark:text-amber-400">{{ formatCurrency(calculatedTaxAmount) }}</div>
          </div>
        </div>
      </div>

      <FormField label="Notes">
        <textarea
          v-model="form.notes"
          rows="2"
          class="input-base w-full text-sm"
          placeholder="Additional contract notes..."
        ></textarea>
      </FormField>
    </form>

    <template #footer>
      <Button
        variant="secondary"
        @click="$emit('close')"
        :disabled="loading"
      >
        Cancel
      </Button>
      <Button
        variant="primary"
        :loading="loading"
        :disabled="loading"
        @click="handleSubmit"
      >
        {{ editMode ? 'Update' : 'Create' }}
      </Button>
    </template>
  </BaseModal>
</template>

<script setup>
import { ref, watch, computed } from 'vue';
import { rentalApi } from '../../../api';
import BaseModal from '../../ui/BaseModal.vue';
import FormField from '../../ui/FormField.vue';
import TextInput from '../../ui/TextInput.vue';
import SelectInput from '../../ui/SelectInput.vue';
import Button from '../../ui/Button.vue';

const props = defineProps({
  isOpen: Boolean,
  contract: Object,
  companyId: String
});

const emit = defineEmits(['close', 'saved']);

// State
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
  pph42_payment_date: '',
  pph42_payment_ref: '',
  status: 'active',
  notes: ''
});

// Helper Functions
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
    pph42_payment_date: '',
    pph42_payment_ref: '',
    status: 'active',
    notes: ''
  };
};

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

// Data Loading Functions
const loadStores = async () => {
  try {
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
    locations.value = [];
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

// Computed
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

const calculatedBrutoAmount = computed(() => {
  const base = baseSelectedAmount.value;
  if (!base) return 0;
  if ((form.value.calculation_method || 'BRUTO').toUpperCase() === 'NETTO') {
    const rate = Number(form.value.pph42_rate ?? 10);
    const divisor = 1 - (rate / 100);
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
  const rate = Number(form.value.pph42_rate ?? 10);
  return bruto * (1 - (rate / 100));
});

const calculatedTaxAmount = computed(() => {
  return Math.max(0, calculatedBrutoAmount.value - calculatedNetAmount.value);
});

// Watches
watch(() => props.contract, (newContract) => {
  if (newContract && newContract.id) {
    editMode.value = true;
    const paymentDate = newContract.pph42_payment_date 
      ? String(newContract.pph42_payment_date).substring(0, 10)
      : '';
    form.value = {
      ...newContract,
      calculation_method: (newContract.calculation_method || 'BRUTO').toUpperCase(),
      pph42_rate: Number(newContract.pph42_rate ?? 10),
      pph42_payment_timing: newContract.pph42_payment_timing || 'same_period',
      pph42_payment_date: paymentDate,
      pph42_payment_ref: newContract.pph42_payment_ref || ''
    };
  } else {
    editMode.value = false;
    if (!props.isOpen) {
      resetForm();
    }
  }
}, { immediate: true });

watch(() => props.isOpen, async (isOpen) => {
  if (isOpen) {
    try {
      await Promise.all([loadStores(), loadLocations(), loadLinkableTransactions()]);
      if (props.contract?.id) {
        await loadExistingLinkedTransactions(props.contract.id);
      }
    } catch (error) {
      console.error('Error loading data:', error);
    }
  } else {
    resetForm();
    editMode.value = false;
    selectedTransactions.value = [];
    transactionSearch.value = '';
  }
});

// Submit handler
const handleSubmit = async () => {
  loading.value = true;
  try {
    const data = {
      ...form.value,
      company_id: props.companyId,
      total_amount: calculatedBrutoAmount.value,
      linked_transaction_ids: selectedTransactions.value,
      pph42_payment_date: form.value.pph42_payment_timing === 'same_period' 
        ? null 
        : (form.value.pph42_payment_date || null)
    };

    if (editMode.value) {
      await rentalApi.updateContract(props.contract.id, data);
    } else {
      await rentalApi.createContract(data);
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
