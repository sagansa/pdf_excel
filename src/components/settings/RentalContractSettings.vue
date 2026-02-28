<template>
  <div class="space-y-6">
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <h2 class="text-2xl font-bold text-gray-900">Rental Contract Settings</h2>
      <p class="text-sm text-gray-500 mt-1">
        Konfigurasi akun COA yang digunakan untuk jurnal otomatis kontrak sewa di Income Statement dan Balance Sheet.
      </p>
    </div>

    <!-- Journal Flow Diagram -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      <div class="bg-indigo-50 border-b border-indigo-100 px-6 py-4">
        <h3 class="text-lg font-bold text-indigo-900">
          <i class="bi bi-diagram-3 mr-2"></i>
          Alur Jurnal Kontrak Sewa
        </h3>
        <p class="text-xs text-indigo-600 mt-0.5">
          Visualisasi posting jurnal otomatis berdasarkan konfigurasi akun di bawah.
        </p>
      </div>

      <div class="p-6">
        <div class="space-y-4">
          <!-- Step 1: Payment Recognition -->
          <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div class="flex items-center gap-2 mb-3">
              <span class="bg-blue-600 text-white text-xs font-bold px-2 py-1 rounded">1</span>
              <h4 class="font-semibold text-blue-900">Pembayaran Sewa (Recognition)</h4>
            </div>
            <div class="grid grid-cols-2 gap-4 text-sm">
              <div class="flex items-center gap-2">
                <span class="bg-green-100 text-green-800 text-xs font-bold px-2 py-0.5 rounded">Dr</span>
                <span class="text-gray-700">{{ settings.prepaid_prepaid_asset_coa || '1421' }} - Biaya Dibayar Dimuka</span>
              </div>
              <div class="flex items-center gap-2">
                <span class="bg-red-100 text-red-800 text-xs font-bold px-2 py-0.5 rounded">Cr</span>
                <span class="text-gray-700">{{ settings.rental_cash_coa || '1101' }} - Kas dan Setara Kas</span>
              </div>
            </div>
          </div>

          <!-- Step 2: Monthly Amortization -->
          <div class="bg-amber-50 border border-amber-200 rounded-lg p-4">
            <div class="flex items-center gap-2 mb-3">
              <span class="bg-amber-600 text-white text-xs font-bold px-2 py-1 rounded">2</span>
              <h4 class="font-semibold text-amber-900">Amortisasi Bulanan (proporsional s.d. 31 Des)</h4>
            </div>
            <div class="grid grid-cols-2 gap-4 text-sm">
              <div class="flex items-center gap-2">
                <span class="bg-green-100 text-green-800 text-xs font-bold px-2 py-0.5 rounded">Dr</span>
                <span class="text-gray-700">{{ settings.prepaid_rent_expense_coa || '5315' }} - Beban Sewa</span>
              </div>
              <div class="flex items-center gap-2">
                <span class="bg-red-100 text-red-800 text-xs font-bold px-2 py-0.5 rounded">Cr</span>
                <span class="text-gray-700">{{ settings.prepaid_prepaid_asset_coa || '1421' }} - Biaya Dibayar Dimuka</span>
              </div>
            </div>
          </div>

          <!-- Step 3: PPh 4(2) Tax -->
          <div class="bg-rose-50 border border-rose-200 rounded-lg p-4">
            <div class="flex items-center gap-2 mb-3">
              <span class="bg-rose-600 text-white text-xs font-bold px-2 py-1 rounded">3</span>
              <h4 class="font-semibold text-rose-900">Pembayaran PPh 4(2)</h4>
            </div>
            <div class="grid grid-cols-2 gap-4 text-sm">
              <div class="flex items-center gap-2">
                <span class="bg-green-100 text-green-800 text-xs font-bold px-2 py-0.5 rounded">Dr</span>
                <span class="text-gray-700">{{ settings.prepaid_tax_payable_coa || '2191' }} - Utang Pajak</span>
              </div>
              <div class="flex items-center gap-2">
                <span class="bg-red-100 text-red-800 text-xs font-bold px-2 py-0.5 rounded">Cr</span>
                <span class="text-gray-700">{{ settings.rental_cash_coa || '1101' }} - Kas dan Setara Kas</span>
              </div>
            </div>
            <p class="text-[10px] text-rose-600 mt-2">
              <i class="bi bi-info-circle mr-1"></i>
              Nominal sesuai perhitungan PPh 4(2). Tanggal pembayaran diinput melalui kontrak.
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- COA Configuration -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      <div class="bg-emerald-50 border-b border-emerald-100 px-6 py-4">
        <h3 class="text-lg font-bold text-emerald-900">
          <i class="bi bi-gear-fill mr-2"></i>
          Konfigurasi Akun (COA)
        </h3>
        <p class="text-xs text-emerald-600 mt-0.5">
          Pilih akun untuk masing-masing pos jurnal. Perubahan tersimpan otomatis.
        </p>
      </div>

      <div class="p-6">
        <div v-if="loading" class="flex flex-col items-center py-12">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
          <p class="mt-4 text-sm text-gray-500">Loading COA data...</p>
        </div>

        <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <!-- Prepaid Rent COA -->
          <div class="space-y-2">
            <label class="block text-sm font-semibold text-slate-700">
              <i class="bi bi-arrow-right-circle text-blue-500 mr-1"></i>
              Biaya Dibayar Dimuka
              <span class="text-xs text-gray-400 font-normal ml-1">default: 1421</span>
            </label>
            <select
              v-model="settings.prepaid_prepaid_asset_coa"
              @change="saveSettings"
              class="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all text-sm"
            >
              <option value="">Pilih COA...</option>
              <option v-for="coa in assetCoas" :key="coa.id" :value="coa.code">
                {{ coa.code }} - {{ coa.name }}
              </option>
            </select>
            <p class="text-[10px] text-gray-400">Dr saat pembayaran, Cr saat amortisasi bulanan</p>
          </div>

          <!-- Rent Expense COA -->
          <div class="space-y-2">
            <label class="block text-sm font-semibold text-slate-700">
              <i class="bi bi-receipt text-amber-500 mr-1"></i>
              Beban Sewa (Amortisasi)
              <span class="text-xs text-gray-400 font-normal ml-1">default: 5315</span>
            </label>
            <select
              v-model="settings.prepaid_rent_expense_coa"
              @change="saveSettings"
              class="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all text-sm"
            >
              <option value="">Pilih COA...</option>
              <option v-for="coa in expenseCoas" :key="coa.id" :value="coa.code">
                {{ coa.code }} - {{ coa.name }}
              </option>
            </select>
            <p class="text-[10px] text-gray-400">Dr saat amortisasi bulanan ke Income Statement</p>
          </div>

          <!-- Tax Payable COA -->
          <div class="space-y-2">
            <label class="block text-sm font-semibold text-slate-700">
              <i class="bi bi-bank text-rose-500 mr-1"></i>
              Utang Pajak PPh 4(2)
              <span class="text-xs text-gray-400 font-normal ml-1">default: 2191</span>
            </label>
            <select
              v-model="settings.prepaid_tax_payable_coa"
              @change="saveSettings"
              class="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all text-sm"
            >
              <option value="">Pilih COA...</option>
              <option v-for="coa in liabilityCoas" :key="coa.id" :value="coa.code">
                {{ coa.code }} - {{ coa.name }}
              </option>
            </select>
            <p class="text-[10px] text-gray-400">Muncul di Balance Sheet sebagai liabilitas jangka pendek</p>
          </div>

          <!-- Cash Account COA -->
          <div class="space-y-2">
            <label class="block text-sm font-semibold text-slate-700">
              <i class="bi bi-cash-stack text-green-500 mr-1"></i>
              Kas/Bank Pembayaran
              <span class="text-xs text-gray-400 font-normal ml-1">default: 1101</span>
            </label>
            <select
              v-model="settings.rental_cash_coa"
              @change="saveSettings"
              class="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all text-sm"
            >
              <option value="">Pilih COA...</option>
              <option v-for="coa in assetCoas" :key="coa.id" :value="coa.code">
                {{ coa.code }} - {{ coa.name }}
              </option>
            </select>
            <p class="text-[10px] text-gray-400">Cr saat pembayaran sewa dan pembayaran pajak</p>
          </div>
        </div>

        <!-- Save Status -->
        <div v-if="saveStatus" class="mt-4">
          <div
            :class="saveStatus === 'success'
              ? 'bg-green-50 border-green-200 text-green-700'
              : 'bg-red-50 border-red-200 text-red-700'"
            class="px-4 py-2 rounded-lg border text-sm flex items-center gap-2"
          >
            <i :class="saveStatus === 'success' ? 'bi bi-check-circle-fill' : 'bi bi-exclamation-circle-fill'"></i>
            {{ saveStatus === 'success' ? 'Settings berhasil disimpan!' : saveErrorMsg }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { reportsApi, coaApi } from '../../api';

const props = defineProps({
  companyId: {
    type: String,
    default: null
  }
});

const loading = ref(true);
const saving = ref(false);
const saveStatus = ref(null);
const saveErrorMsg = ref('');
const coaList = ref([]);

const settings = ref({
  prepaid_prepaid_asset_coa: '1421',
  prepaid_rent_expense_coa: '5315',
  prepaid_tax_payable_coa: '2191',
  rental_cash_coa: '1101'
});

const assetCoas = computed(() =>
  coaList.value.filter(c => c.category === 'ASSET' && c.is_active !== false)
);
const expenseCoas = computed(() =>
  coaList.value.filter(c => (c.category === 'EXPENSE' || c.category === 'COGS') && c.is_active !== false)
);
const liabilityCoas = computed(() =>
  coaList.value.filter(c => c.category === 'LIABILITY' && c.is_active !== false)
);

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
    console.error('Failed to fetch settings data:', err);
  } finally {
    loading.value = false;
  }
};

const saveSettings = async () => {
  saving.value = true;
  saveStatus.value = null;
  try {
    await reportsApi.saveAmortizationSettings({
      company_id: props.companyId,
      ...settings.value
    });
    saveStatus.value = 'success';
    setTimeout(() => { saveStatus.value = null; }, 3000);
  } catch (err) {
    console.error('Failed to save settings:', err);
    saveStatus.value = 'error';
    saveErrorMsg.value = err.response?.data?.error || err.message;
  } finally {
    saving.value = false;
  }
};

onMounted(fetchData);
</script>
