<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/50 backdrop-blur-sm">
    <div class="bg-white rounded-xl shadow-2xl w-full max-w-lg overflow-hidden border border-gray-100">
      <!-- Header -->
      <div class="px-6 py-4 border-b border-gray-100 flex items-center justify-between bg-gray-50/50">
        <h3 class="text-lg font-bold text-gray-900 flex items-center gap-2">
          <i class="bi bi-gear-fill text-indigo-600"></i>
          Rental Accounting Settings
        </h3>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 transition-colors">
          <i class="bi bi-x-lg"></i>
        </button>
      </div>

      <!-- Body -->
      <div class="p-6 space-y-6">
        <div v-if="loading" class="flex flex-col items-center py-12">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
          <p class="mt-4 text-sm text-gray-500">Loading settings...</p>
        </div>

        <template v-else>
          <div class="space-y-4">
            <p class="text-xs text-gray-500 bg-blue-50 p-3 rounded-lg border border-blue-100">
              <i class="bi bi-info-circle-fill mr-1"></i>
              Konfigurasi akun Chart of Accounts (COA) yang akan digunakan saat pembuatan jurnal otomatis untuk Kontrak Sewa.
            </p>

            <!-- Prepaid Rent COA -->
            <div class="space-y-1.5">
              <label class="text-xs font-bold text-gray-700 uppercase tracking-wider">Akun Biaya Dibayar Dimuka</label>
              <select v-model="settings.prepaid_prepaid_asset_coa" class="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none text-sm">
                <option v-for="coa in coaList" :key="coa.id" :value="coa.code">
                  {{ coa.code }} - {{ coa.name }}
                </option>
              </select>
              <p class="text-[10px] text-gray-500">Default: 1421 (Biaya Dibayar Dimuka)</p>
            </div>

            <!-- Rent Expense COA -->
            <div class="space-y-1.5">
              <label class="text-xs font-bold text-gray-700 uppercase tracking-wider">Akun Beban Sewa (Amortisasi)</label>
              <select v-model="settings.prepaid_rent_expense_coa" class="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none text-sm">
                <option v-for="coa in coaList" :key="coa.id" :value="coa.code">
                  {{ coa.code }} - {{ coa.name }}
                </option>
              </select>
              <p class="text-[10px] text-gray-500">Default: 5315 (Beban Sewa)</p>
            </div>

            <!-- Tax Payable COA -->
            <div class="space-y-1.5">
              <label class="text-xs font-bold text-gray-700 uppercase tracking-wider">Akun Utang Pajak PPh 4(2)</label>
              <select v-model="settings.prepaid_tax_payable_coa" class="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none text-sm">
                <option v-for="coa in coaList" :key="coa.id" :value="coa.code">
                  {{ coa.code }} - {{ coa.name }}
                </option>
              </select>
              <p class="text-[10px] text-gray-500">Default: 2191 (Utang Pajak - PPh 4(2))</p>
            </div>

            <!-- Cash Account COA -->
            <div class="space-y-1.5">
              <label class="text-xs font-bold text-gray-700 uppercase tracking-wider">Akun Kas/Bank Pembayaran</label>
              <select v-model="settings.rental_cash_coa" class="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none text-sm">
                <option v-for="coa in coaList" :key="coa.id" :value="coa.code">
                  {{ coa.code }} - {{ coa.name }}
                </option>
              </select>
              <p class="text-[10px] text-gray-500">Default: 1101 (Kas dan Setara Kas)</p>
            </div>
          </div>
        </template>
      </div>

      <!-- Footer -->
      <div class="px-6 py-4 bg-gray-50 border-t border-gray-100 flex justify-end gap-3">
        <button 
          @click="$emit('close')" 
          class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
        >
          Cancel
        </button>
        <button 
          @click="saveSettings" 
          :disabled="saving || loading"
          class="px-6 py-2 text-sm font-bold text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50 shadow-lg shadow-indigo-100 flex items-center gap-2"
        >
          <span v-if="saving" class="animate-spin h-4 w-4 border-2 border-white/30 border-t-white rounded-full"></span>
          {{ saving ? 'Saving...' : 'Save Settings' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import { reportsApi, coaApi } from '../../../api';

const props = defineProps({
  isOpen: Boolean,
  companyId: String
});

const emit = defineEmits(['close', 'saved']);

const loading = ref(true);
const saving = ref(false);
const coaList = ref([]);
const settings = ref({
  prepaid_prepaid_asset_coa: '1421',
  prepaid_rent_expense_coa: '5315',
  prepaid_tax_payable_coa: '2191',
  rental_cash_coa: '1101'
});

const fetchData = async () => {
  loading.value = true;
  try {
    const [coaRes, settingsRes] = await Promise.all([
      coaApi.getCoa(),
      reportsApi.getAmortizationSettings(props.companyId)
    ]);
    
    coaList.value = coaRes.data.coa || [];
    
    const s = settingsRes.data.settings || {};
    if (s.prepaid_prepaid_asset_coa) settings.value.prepaid_prepaid_asset_coa = s.prepaid_prepaid_asset_coa;
    if (s.prepaid_rent_expense_coa) settings.value.prepaid_rent_expense_coa = s.prepaid_rent_expense_coa;
    if (s.prepaid_tax_payable_coa) settings.value.prepaid_tax_payable_coa = s.prepaid_tax_payable_coa;
    if (s.rental_cash_coa) settings.value.rental_cash_coa = s.rental_cash_coa;
    
  } catch (err) {
    console.error("Failed to fetch settings data:", err);
  } finally {
    loading.value = false;
  }
};

const saveSettings = async () => {
  saving.value = true;
  try {
    await reportsApi.saveAmortizationSettings({
      company_id: props.companyId,
      ...settings.value
    });
    emit('saved');
    emit('close');
  } catch (err) {
    console.error("Failed to save settings:", err);
    alert("Failed to save settings: " + (err.response?.data?.error || err.message));
  } finally {
    saving.value = false;
  }
};

watch(() => props.isOpen, (newVal) => {
  if (newVal) fetchData();
});
</script>
