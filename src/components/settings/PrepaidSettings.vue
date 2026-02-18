<template>
  <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
    <div class="mb-6">
      <h3 class="text-lg font-semibold text-gray-900 mb-2">Prepaid Rent & Expense Settings</h3>
      <p class="text-sm text-gray-500">Configure default accounts and tax settings for prepaid rent expenses</p>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="flex items-center justify-center py-12">
      <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
    </div>

    <!-- Settings Form -->
    <div v-else class="space-y-6">
      <!-- Rent Expense COA -->
      <div>
        <label class="block text-sm font-semibold text-gray-700 mb-2">
          <i class="bi bi-house-door mr-1"></i>
          Rent Expense Account (Beban Sewa)
        </label>
        <select
          v-model="settings.prepaid_rent_expense_coa"
          class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
        >
          <option value="">-- Select Account --</option>
          <option v-for="coa in expenseAccounts" :key="coa.id" :value="coa.id">
            {{ coa.code }} - {{ coa.name }}
          </option>
        </select>
        <p class="text-xs text-gray-400 mt-1">
          This account will be used for monthly rent amortization entries. Default: 5315 - Beban Sewa
        </p>
      </div>

      <!-- Prepaid Asset COA -->
      <div>
        <label class="block text-sm font-semibold text-gray-700 mb-2">
          <i class="bi bi-calendar-check mr-1"></i>
          Prepaid Asset Account (Sewa Dibayar Dimuka)
        </label>
        <select
          v-model="settings.prepaid_asset_coa"
          class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
        >
          <option value="">-- Select Account --</option>
          <option v-for="coa in assetAccounts" :key="coa.id" :value="coa.id">
            {{ coa.code }} - {{ coa.name }}
          </option>
        </select>
        <p class="text-xs text-gray-400 mt-1">
          This account will be debited when recording prepaid rent. Default: 1421 - Sewa Dibayar Dimuka
        </p>
      </div>

      <!-- Tax Payable COA -->
      <div>
        <label class="block text-sm font-semibold text-gray-700 mb-2">
          <i class="bi bi-receipt mr-1"></i>
          Tax Payable Account (Utang PPh 4(2))
        </label>
        <select
          v-model="settings.tax_payable_coa"
          class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
        >
          <option value="">-- Select Account --</option>
          <option v-for="coa in liabilityAccounts" :key="coa.id" :value="coa.id">
            {{ coa.code }} - {{ coa.name }}
          </option>
        </select>
        <p class="text-xs text-gray-400 mt-1">
          This account will be credited for PPh 4(2) tax withholding. Default: 2111 - Utang PPh Pasal 4 Ayat 2
        </p>
      </div>

      <!-- Default Tax Rate -->
      <div>
        <label class="block text-sm font-semibold text-gray-700 mb-2">
          <i class="bi bi-percent mr-1"></i>
          Default PPh 4(2) Tax Rate
        </label>
        <div class="flex items-center gap-2">
          <input
            v-model.number="settings.default_tax_rate"
            type="number"
            step="0.01"
            min="0"
            max="100"
            class="w-32 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
          <span class="text-gray-600">%</span>
        </div>
        <p class="text-xs text-gray-400 mt-1">
          Default tax rate for rent expense withholding. Standard rate: 10%
        </p>
      </div>

      <!-- Save Button -->
      <div class="flex items-center justify-between pt-4 border-t border-gray-200">
        <div v-if="saveMessage" class="flex items-center gap-2">
          <i class="bi bi-check-circle-fill text-green-600"></i>
          <span class="text-sm text-green-600">{{ saveMessage }}</span>
        </div>
        <div v-else-if="errorMessage" class="flex items-center gap-2">
          <i class="bi bi-exclamation-circle-fill text-red-600"></i>
          <span class="text-sm text-red-600">{{ errorMessage }}</span>
        </div>
        <div v-else></div>
        
        <button
          @click="saveSettings"
          :disabled="isSaving"
          class="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          <i v-if="isSaving" class="bi bi-arrow-repeat animate-spin"></i>
          <i v-else class="bi bi-save"></i>
          <span>{{ isSaving ? 'Saving...' : 'Save Settings' }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import api from '../../api';

const props = defineProps({
  companyId: {
    type: [String, Number],
    required: true
  }
});

const isLoading = ref(true);
const isSaving = ref(false);
const saveMessage = ref('');
const errorMessage = ref('');

const settings = ref({
  prepaid_rent_expense_coa: '',
  prepaid_asset_coa: '',
  tax_payable_coa: '',
  default_tax_rate: 10
});

const expenseAccounts = ref([]);
const assetAccounts = ref([]);
const liabilityAccounts = ref([]);

// Load COA accounts
const loadAccounts = async () => {
  try {
    const response = await api.get('/api/coa', {
      params: { company_id: props.companyId }
    });
    
    const accounts = response.data.coa || [];
    
    // Filter by account categories
    expenseAccounts.value = accounts.filter(a => a.code && a.code.startsWith('5'));
    assetAccounts.value = accounts.filter(a => a.code && a.code.startsWith('1'));
    liabilityAccounts.value = accounts.filter(a => a.code && a.code.startsWith('2'));
  } catch (error) {
    console.error('Failed to load accounts:', error);
    errorMessage.value = 'Failed to load chart of accounts';
  }
};

// Load current settings
const loadSettings = async () => {
  isLoading.value = true;
  try {
    const response = await api.get('/api/amortization/settings', {
      params: { company_id: props.companyId }
    });
    
    const data = response.data.settings || {};
    
    // Map settings to form
    settings.value = {
      prepaid_rent_expense_coa: data.prepaid_rent_expense_coa || '',
      prepaid_asset_coa: data.prepaid_asset_coa || '',
      tax_payable_coa: data.tax_payable_coa || '',
      default_tax_rate: data.default_tax_rate || 10
    };
  } catch (error) {
    console.error('Failed to load settings:', error);
    errorMessage.value = 'Failed to load settings';
  } finally {
    isLoading.value = false;
  }
};

// Save settings
const saveSettings = async () => {
  isSaving.value = true;
  saveMessage.value = '';
  errorMessage.value = '';
  
  try {
    await api.post('/api/amortization/settings', {
      company_id: props.companyId,
      settings: settings.value
    });
    
    saveMessage.value = 'Settings saved successfully!';
    setTimeout(() => {
      saveMessage.value = '';
    }, 3000);
  } catch (error) {
    console.error('Failed to save settings:', error);
    errorMessage.value = 'Failed to save settings';
  } finally {
    isSaving.value = false;
  }
};

// Watch for company changes
watch(() => props.companyId, async () => {
  await loadAccounts();
  await loadSettings();
}, { immediate: true });

onMounted(async () => {
  await loadAccounts();
  await loadSettings();
});
</script>
