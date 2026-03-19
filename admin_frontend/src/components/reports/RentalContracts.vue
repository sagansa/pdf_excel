<template>
  <div class="space-y-6">
    <!-- Header with Actions -->
    <SectionCard bodyClass="p-4 bg-surface-raised/30">
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 class="text-xl font-bold text-theme">Rental Contracts</h2>
          <p class="text-sm text-theme-muted mt-1">Manage rental contracts, link transactions, and track amortization.</p>
        </div>
        <div class="flex items-center gap-2">
          <Button
            variant="secondary"
            @click="showSettingsModal = true"
          >
            <i class="bi bi-gear mr-2"></i>
            Settings
          </Button>
          <Button
            variant="primary"
            @click="showContractModal = true"
          >
            <i class="bi bi-file-earmark-text mr-2"></i>
            Add Contract
          </Button>
        </div>
      </div>
    </SectionCard>

    <!-- Pending Transactions Alert -->
    <div v-if="pendingTransactions?.length > 0" class="bg-warning/5 border border-warning/20 rounded-2xl p-5 shadow-sm">
      <div class="flex items-start gap-4">
        <div class="w-10 h-10 rounded-xl bg-warning/10 flex items-center justify-center text-warning shrink-0">
          <i class="bi bi-exclamation-triangle-fill text-xl"></i>
        </div>
        <div class="flex-1 min-w-0">
          <h4 class="text-sm font-bold text-warning uppercase tracking-wider">Pending Rental Transactions ({{ pendingTransactions.length }})</h4>
          <p class="text-xs text-theme-muted mt-1 leading-relaxed">
            Berikut adalah transaksi yang sudah ditandai sebagai "Sewa Tempat" namun belum dihubungkan ke kontrak apapun. 
            Segera buat atau hubungkan ke kontrak agar perhitungan laporan keuangan akurat.
          </p>
          <div class="mt-4 max-h-40 overflow-y-auto bg-surface/50 border border-warning/10 rounded-xl p-3">
            <table class="table-compact min-w-full !bg-transparent">
              <thead>
                <tr class="!bg-transparent">
                  <th class="text-left py-2 font-bold !bg-transparent border-warning/10">Tanggal</th>
                  <th class="text-left py-2 font-bold !bg-transparent border-warning/10">Keterangan</th>
                  <th class="text-right py-2 font-bold !bg-transparent border-warning/10">Jumlah</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-warning/5">
                <tr v-for="txn in pendingTransactions" :key="txn.id" class="hover:bg-warning/5">
                  <td class="py-2 whitespace-nowrap text-theme/80">{{ formatDate(txn.txn_date) }}</td>
                  <td class="py-2 truncate max-w-[300px] text-theme/80" :title="txn.description">{{ txn.description }}</td>
                  <td class="py-2 text-right font-bold text-warning">{{ formatCurrency(txn.amount) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="mt-4">
            <Button
              variant="secondary"
              size="sm"
              class="!bg-warning/10 !border-warning/20 !text-warning hover:!bg-warning/20"
              @click="showContractModal = true"
            >
              Buat Kontrak Baru
            </Button>
          </div>
        </div>
      </div>
    </div>

    <!-- Contracts List -->
    <SectionCard padding="none">
      <template #header>
        <div class="px-5 py-4 border-b border-border bg-surface-raised/50 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <div class="w-1 h-4 bg-primary rounded-full"></div>
            <h4 class="text-xs font-bold text-theme uppercase tracking-widest">
              Rental Contracts List
            </h4>
          </div>
          <div class="text-[10px] text-theme-muted font-medium">
            Showing {{ contracts.length }} contracts
          </div>
        </div>
      </template>

      <div class="overflow-x-auto">
        <table class="table-compact min-w-full">
          <thead>
            <tr>
              <th class="text-left">Store</th>
              <th class="text-left">Location</th>
              <th class="text-left">Period</th>
              <th class="text-left">Accounting (Monthly)</th>
              <th class="text-left">Amortization (Remaining)</th>
              <th class="text-left">Status</th>
              <th class="text-right">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border/50">
            <tr v-for="contract in contracts" :key="contract.id" class="hover:bg-surface-raised/30 transition-colors">
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm font-bold text-theme">{{ contract.store_name }}</div>
                <div class="text-[10px] text-theme-muted font-bold uppercase tracking-widest mt-0.5">{{ contract.store_code }}</div>
              </td>
              <td class="px-6 py-4">
                <div class="text-sm text-theme">{{ contract.location_name }}</div>
                <div class="text-[10px] text-theme-muted line-clamp-1 mt-0.5">{{ contract.location_address }}</div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm font-bold text-theme">{{ formatDate(contract.start_date) }}</div>
                <div class="text-[10px] text-theme-muted font-bold uppercase mt-0.5">to {{ formatDate(contract.end_date) }}</div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm font-bold text-theme">{{ formatCurrency(getAccountingSummary(contract).monthly_amortization) }}</div>
                <div class="text-[10px] text-theme-muted font-bold uppercase mt-0.5">{{ contract.calculation_method }} • {{ contract.pph42_rate }}% PPh</div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm text-primary font-bold">{{ formatCurrency(getAccountingSummary(contract).remaining_prepaid) }}</div>
                <div class="text-[10px] text-theme-muted font-bold uppercase mt-0.5">Amortized: {{ formatCurrency(getAccountingSummary(contract).total_amortized) }}</div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span 
                  :class="[
                    'inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border',
                    getStatusClass(contract.status)
                  ]"
                >
                  {{ contract.status }}
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-right">
                <div class="flex items-center justify-end gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    @click="viewContractDetails(contract)"
                    title="View Details"
                  >
                    <i class="bi bi-eye text-primary"></i>
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    @click="editContract(contract)"
                    title="Edit"
                  >
                    <i class="bi bi-pencil-square text-theme-muted"></i>
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    @click="deleteContractConfirm(contract)"
                    title="Delete"
                  >
                    <i class="bi bi-trash text-danger"></i>
                  </Button>
                </div>
              </td>
            </tr>
            <tr v-if="contracts.length === 0">
              <td colspan="7" class="px-6 py-16 text-center text-theme-muted">
                <div class="flex flex-col items-center gap-3">
                  <i class="bi bi-inbox text-4xl opacity-20"></i>
                  <p class="font-medium italic">No rental contracts found</p>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </SectionCard>

    <!-- Contract Details Modal -->
    <BaseModal
      :isOpen="showDetailsModal"
      size="4xl"
      @close="showDetailsModal = false"
    >
      <template #title>
        <div>
          <h3 class="text-lg font-bold text-theme">Contract Details</h3>
          <p class="text-[10px] text-theme-muted font-bold uppercase tracking-widest mt-0.5">
            {{ selectedContract?.store_name }} | {{ selectedContract?.location_name }}
          </p>
        </div>
      </template>

      <div class="px-6 space-y-8" v-if="selectedContract">
        <!-- Contract Info Grid -->
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-6 p-5 bg-surface-raised rounded-2xl border border-border">
          <FormField label="Store" labelClass="!text-[10px] uppercase tracking-wider">
            <p class="text-sm font-bold text-theme">{{ selectedContract.store_name }}</p>
          </FormField>
          <FormField label="Location" labelClass="!text-[10px] uppercase tracking-wider">
            <p class="text-sm font-bold text-theme">{{ selectedContract.location_name }}</p>
          </FormField>
          <FormField label="Period" labelClass="!text-[10px] uppercase tracking-wider">
            <p class="text-sm font-bold text-theme">{{ formatDate(selectedContract.start_date) }} - {{ formatDate(selectedContract.end_date) }}</p>
          </FormField>
          <FormField label="Total Amount" labelClass="!text-[10px] uppercase tracking-wider">
            <p class="text-sm font-bold text-theme">{{ formatCurrency(selectedContract.total_amount) }}</p>
          </FormField>
        </div>
        
        <!-- Accounting Stats Grid -->
        <div class="space-y-4">
          <div class="flex items-center gap-2 px-1">
            <div class="w-1 h-3 bg-primary rounded-full"></div>
            <h4 class="text-[10px] font-bold text-theme-muted uppercase tracking-[0.2em]">Accounting Summary</h4>
          </div>
          <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              label="Bruto (Base)"
              :value="formatCurrency(getAccountingSummary(selectedContract).bruto)"
              variant="default"
              icon="bi-receipt"
            />
            <StatCard
              label="Netto (Payment)"
              :value="formatCurrency(getAccountingSummary(selectedContract).net)"
              variant="primary"
              icon="bi-wallet2"
            />
            <StatCard
              label="PPh 4(2)"
              :value="formatCurrency(getAccountingSummary(selectedContract).tax)"
              variant="warning"
              icon="bi-shield-check"
              :subtext="`${selectedContract.pph42_rate}% rate`"
            />
            <StatCard
              label="Monthly Amort."
              :value="formatCurrency(getAccountingSummary(selectedContract).monthly_amortization)"
              variant="success"
              icon="bi-calculator"
            />
          </div>
          
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
             <div class="p-4 bg-surface-raised rounded-2xl border border-border flex flex-col justify-center">
                <div class="text-[10px] font-bold text-theme-muted uppercase tracking-widest mb-1">Status Amortasi</div>
                <div class="text-lg font-bold text-theme">{{ formatCurrency(getAccountingSummary(selectedContract).total_amortized) }}</div>
                <div class="text-[10px] text-theme-muted font-medium mt-1 uppercase">{{ getAccountingSummary(selectedContract).elapsed_months }} of {{ getAccountingSummary(selectedContract).total_months }} months elapsed</div>
             </div>
             <div class="p-4 bg-primary/5 rounded-2xl border border-primary/20 flex flex-col justify-center">
                <div class="text-[10px] font-bold text-primary uppercase tracking-widest mb-1">Remaining Prepaid</div>
                <div class="text-lg font-bold text-primary">{{ formatCurrency(getAccountingSummary(selectedContract).remaining_prepaid) }}</div>
             </div>
             <div class="p-4 bg-surface-raised rounded-2xl border border-border flex flex-col justify-center">
                <div class="text-[10px] font-bold text-theme-muted uppercase tracking-widest mb-1">PPh Payment</div>
                <div class="text-sm font-bold text-theme flex items-center gap-2">
                  {{ selectedContract.pph42_payment_timing }}
                  <span v-if="selectedContract.pph42_payment_date" class="text-[9px] bg-success/10 text-success px-1.5 py-0.5 rounded border border-success/20">PAID</span>
                </div>
                <div v-if="selectedContract.pph42_payment_date" class="text-[10px] text-theme-muted font-medium mt-1 uppercase">Paid on: {{ formatDate(selectedContract.pph42_payment_date) }}</div>
             </div>
          </div>
        </div>

        <!-- Linked Transactions -->
        <div class="space-y-4">
          <div class="flex items-center justify-between px-1">
            <div class="flex items-center gap-2 text-theme">
              <div class="w-1 h-3 bg-primary rounded-full"></div>
              <h4 class="text-[10px] font-bold uppercase tracking-[0.2em]">Linked Transactions</h4>
            </div>
            <Button
              variant="secondary"
              size="sm"
              @click="showLinkTransactionModal = true"
            >
              <i class="bi bi-link-45deg mr-1"></i>
              Link Transaction
            </Button>
          </div>
          <div class="border border-border rounded-2xl overflow-hidden">
            <table class="table-compact min-w-full">
              <thead>
                <tr>
                  <th class="text-left">Date</th>
                  <th class="text-left">Description</th>
                  <th class="text-right">Amount</th>
                  <th class="text-center">Status</th>
                  <th class="text-right">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-border/50">
                <tr v-for="txn in contractTransactions" :key="txn.id" class="hover:bg-surface-raised/30">
                  <td class="px-4 py-3 text-sm font-bold text-theme">{{ formatDate(txn.txn_date) }}</td>
                  <td class="px-4 py-3 text-sm text-theme/80">{{ txn.description }}</td>
                  <td class="px-4 py-3 text-sm text-right font-bold text-theme">{{ formatCurrency(txn.amount) }}</td>
                  <td class="px-4 py-3 text-center">
                    <span 
                      v-if="txn.is_journaled" 
                      class="px-2 py-0.5 text-[9px] font-bold bg-success/10 text-success rounded-full border border-success/20 uppercase"
                    >
                      Journaled
                    </span>
                    <span 
                      v-else 
                      class="px-2 py-0.5 text-[9px] font-bold bg-theme-muted/10 text-theme-muted rounded-full border border-border uppercase"
                    >
                      Not Journaled
                    </span>
                  </td>
                  <td class="px-4 py-3 text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      @click="unlinkTransaction(txn.id)"
                      class="text-danger hover:bg-danger/10"
                    >
                      Unlink
                    </Button>
                  </td>
                </tr>
                <tr v-if="contractTransactions.length === 0">
                  <td colspan="5" class="px-4 py-12 text-center text-theme-muted italic">
                    No transactions linked yet
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Journal Entries Section -->
        <div class="border-t border-border pt-8 space-y-4">
          <div class="flex items-center justify-between px-1">
            <div class="flex items-center gap-2 text-theme">
              <div class="w-1 h-3 bg-primary rounded-full"></div>
              <h4 class="text-[10px] font-bold uppercase tracking-[0.2em]">Journal Entries</h4>
            </div>
            <div class="flex gap-2">
              <Button
                v-if="generatedJournals.length > 0"
                variant="secondary"
                size="sm"
                @click="showJournals = !showJournals"
              >
                {{ showJournals ? 'Hide' : 'Show' }} Journals
              </Button>
              <Button
                variant="primary"
                size="sm"
                @click="generateJournals"
                :disabled="isGeneratingJournals || contractTransactions.length === 0"
                :loading="isGeneratingJournals"
              >
                Generate Journals
              </Button>
            </div>
          </div>

          <!-- Journal Preview -->
          <div v-if="showJournals && generatedJournals.length > 0" class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div
              v-for="(journal, idx) in generatedJournals"
              :key="idx"
              class="bg-surface-raised rounded-2xl p-5 border border-border space-y-4"
            >
              <div class="flex items-center justify-between">
                <h5 class="text-[10px] font-bold text-primary uppercase tracking-widest">
                  {{ journal.description || 'Payment' }}
                </h5>
                <span class="text-[10px] font-bold text-theme-muted uppercase">{{ journal.transaction_date }}</span>
              </div>
              <table class="w-full text-[11px]">
                <thead class="text-theme-muted border-b border-border">
                  <tr>
                    <th class="text-left font-bold pb-2 uppercase tracking-tighter opacity-60">Account</th>
                    <th class="text-right font-bold pb-2 uppercase tracking-tighter opacity-60">Debit</th>
                    <th class="text-right font-bold pb-2 uppercase tracking-tighter opacity-60">Credit</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-border/30">
                  <tr v-for="entry in journal.entries" :key="entry.coa_code">
                    <td class="text-theme font-medium py-2">
                      <div class="font-bold">{{ entry.coa_code }}</div>
                      <div class="text-[9px] text-theme-muted uppercase tracking-tight">{{ entry.coa_name }}</div>
                    </td>
                    <td class="text-right text-theme font-bold py-2">
                      {{ entry.debit > 0 ? formatCurrency(entry.debit) : '-' }}
                    </td>
                    <td class="text-right text-theme font-bold py-2">
                      {{ entry.credit > 0 ? formatCurrency(entry.credit) : '-' }}
                    </td>
                  </tr>
                </tbody>
              </table>
              <div class="pt-3 border-t border-border flex items-center justify-between">
                <span
                  :class="journal.is_posted ? 'bg-success/10 text-success border-success/20' : 'bg-warning/10 text-warning border-warning/20'"
                  class="px-2 py-0.5 text-[9px] font-bold rounded border uppercase tracking-widest"
                >
                  {{ journal.is_posted ? 'Posted' : 'Not Posted' }}
                </span>
              </div>
            </div>
          </div>
          
          <div v-else-if="contractTransactions.length === 0" class="bg-surface-raised rounded-2xl p-12 text-center border border-dashed border-border text-theme-muted">
            <div class="flex flex-col items-center gap-3">
              <i class="bi bi-calculator text-3xl opacity-20"></i>
              <p class="text-sm font-medium italic">Link transactions to generate journal entries</p>
            </div>
          </div>
        </div>
      </div>
    </BaseModal>

    <!-- Sub-Modals -->
    <AddContractModal
      :isOpen="showContractModal"
      :contract="selectedContractForEdit"
      :companyId="companyId"
      @close="showContractModal = false; selectedContractForEdit = null"
      @saved="handleContractSaved"
    />

    <ConfirmModal
      :isOpen="showDeleteModal"
      title="Delete Contract"
      :message="`Are you sure you want to delete the contract for ${contractToDelete?.store_name}? This action cannot be undone.`"
      confirmText="Delete"
      variant="danger"
      @close="showDeleteModal = false; contractToDelete = null"
      @confirm="confirmDeleteContract"
    />

    <RentalSettingsModal
      :isOpen="showSettingsModal"
      :companyId="companyId"
      @close="showSettingsModal = false"
      @saved="onSettingsSaved"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import { rentalApi, reportsApi } from '../../api';
import AddContractModal from './modals/AddContractModal.vue';
import RentalSettingsModal from './modals/RentalSettingsModal.vue';
import ConfirmModal from '../ui/ConfirmModal.vue';
import SectionCard from '../ui/SectionCard.vue';
import Button from '../ui/Button.vue';
import BaseModal from '../ui/BaseModal.vue';
import StatCard from '../ui/StatCard.vue';
import FormField from '../ui/FormField.vue';

const props = defineProps({
  companyId: {
    type: String,
    required: true
  }
});

const contracts = ref([]);
const selectedContract = ref(null);
const contractTransactions = ref([]);
const generatedJournals = ref([]);
const amortizationSchedule = ref([]);
const monthlyAmount = ref(0);
const pendingTransactions = ref([]);
const showJournals = ref(false);
const isGeneratingJournals = ref(false);

const showContractModal = ref(false);
const showSettingsModal = ref(false);
const showDetailsModal = ref(false);
const showLinkTransactionModal = ref(false);
const showDeleteModal = ref(false);
const contractToDelete = ref(null);

const selectedContractForEdit = ref(null);

const loadContracts = async () => {
  try {
    const [contractsRes, pendingRes] = await Promise.all([
      rentalApi.getContracts(props.companyId),
      rentalApi.getLinkableTransactions(props.companyId, null)
    ]);
    contracts.value = contractsRes.data.contracts || [];
    pendingTransactions.value = (pendingRes.data.transactions || []).filter(t => !t.rental_contract_id);
  } catch (error) {
    console.error('Failed to load rental data:', error);
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
    'pending': 'bg-amber-100 text-amber-800',
    'terminated': 'bg-gray-100 text-gray-800'
  };
  return classes[status] || 'bg-gray-100 text-gray-800';
};

const getAccountingSummary = (contract) => {
  if (!contract) return {};
  
  const totalAmount = parseFloat(contract.total_amount) || 0;
  const totalPaid = parseFloat(contract.total_paid) || 0;
  const method = contract.calculation_method || 'BRUTO';
  const rate = parseFloat(contract.pph42_rate) || 10;
  
  let bruto = 0;
  let net = 0;
  let tax = 0;
  
  if (totalAmount > 0) {
    bruto = totalAmount;
    if (method === 'NETTO') {
      net = totalAmount;
      bruto = net / (1 - (rate / 100));
    } else {
      net = bruto * (1 - (rate / 100));
    }
  } else if (totalPaid > 0) {
    if (method === 'NETTO') {
      net = totalPaid;
      bruto = net / (1 - (rate / 100));
    } else {
      bruto = totalPaid;
      net = bruto * (1 - (rate / 100));
    }
  }
  tax = bruto - net;

  // Amortization
  const start = new Date(contract.start_date);
  const end = new Date(contract.end_date);
  const today = new Date();
  
  // Total months (inclusive of start and end months)
  let totalMonths = (end.getFullYear() - start.getFullYear()) * 12 + (end.getMonth() - start.getMonth()) + 1;
  if (totalMonths <= 0) totalMonths = 1;
  
  // Amortization based on netto (matches 1421 balance from bank transactions)
  const monthlyAmortization = net / totalMonths;
  
  // Elapsed months through today
  const amortEnd = today < end ? today : end;
  let elapsed = 0;
  if (amortEnd >= start) {
    elapsed = (amortEnd.getFullYear() - start.getFullYear()) * 12 + (amortEnd.getMonth() - start.getMonth());
    if (amortEnd.getDate() >= start.getDate() || amortEnd.getMonth() !== start.getMonth() || amortEnd >= end) {
      elapsed += 1;
    }
    elapsed = Math.min(elapsed, totalMonths);
  }
  
  const totalAmortized = monthlyAmortization * elapsed;
  const remainingPrepaid = net - totalAmortized;

  return {
    bruto,
    net,
    tax,
    monthly_amortization: monthlyAmortization,
    total_amortized: totalAmortized,
    remaining_prepaid: remainingPrepaid,
    total_months: totalMonths,
    elapsed_months: elapsed
  };
};

onMounted(() => {
  loadContracts();
});

watch(() => props.companyId, () => {
  loadContracts();
});

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

const onSettingsSaved = () => {
  loadContracts();
};

</script>
