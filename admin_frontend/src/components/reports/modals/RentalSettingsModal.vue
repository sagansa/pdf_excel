<template>
  <BaseModal
    :isOpen="isOpen"
    size="lg"
    @close="$emit('close')"
  >
    <template #title>
      <div class="flex items-center gap-2">
        <i class="bi bi-gear-fill text-primary"></i>
        Rental Accounting Settings
      </div>
    </template>
    
    <div class="px-6 space-y-6">
      <div v-if="loading" class="flex flex-col items-center py-12">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        <p class="mt-4 text-xs text-theme-muted font-bold uppercase tracking-widest">Loading settings...</p>
      </div>

      <template v-else>
        <div class="space-y-4">
          <div class="text-[11px] font-bold text-primary bg-primary/5 p-4 rounded-2xl border border-primary/10 flex gap-3">
             <i class="bi bi-info-circle-fill translate-y-0.5"></i>
             <div class="leading-relaxed">
               Konfigurasi akun Chart of Accounts (COA) yang akan digunakan saat pembuatan jurnal otomatis untuk Kontrak Sewa.
             </div>
          </div>

          <!-- Prepaid Rent COA -->
          <FormField label="Akun Biaya Dibayar Dimuka">
            <SelectInput
              v-model="settings.prepaid_prepaid_asset_coa"
              :options="coaList.map(c => ({ value: c.code, label: `${c.code} - ${c.name}` }))"
            />
            <template #help>Default: 1421 (Biaya Dibayar Dimuka)</template>
          </FormField>

          <!-- Rent Expense COA -->
          <FormField label="Akun Beban Sewa (Amortisasi)">
            <SelectInput
              v-model="settings.prepaid_rent_expense_coa"
              :options="coaList.map(c => ({ value: c.code, label: `${c.code} - ${c.name}` }))"
            />
            <template #help>Default: 5315 (Beban Sewa)</template>
          </FormField>

          <!-- Tax Payable COA -->
          <FormField label="Akun Utang Pajak PPh 4(2)">
            <SelectInput
              v-model="settings.prepaid_tax_payable_coa"
              :options="coaList.map(c => ({ value: c.code, label: `${c.code} - ${c.name}` }))"
            />
            <template #help>Default: 2191 (Utang Pajak - PPh 4(2))</template>
          </FormField>

          <!-- Cash Account COA -->
          <FormField label="Akun Kas/Bank Pembayaran">
            <SelectInput
              v-model="settings.rental_cash_coa"
              :options="coaList.map(c => ({ value: c.code, label: `${c.code} - ${c.name}` }))"
            />
            <template #help>Default: 1101 (Kas dan Setara Kas)</template>
          </FormField>
        </div>
      </template>
    </div>

    <template #footer>
      <Button
        variant="secondary"
        @click="$emit('close')"
        :disabled="saving || loading"
      >
        Cancel
      </Button>
      <Button
        variant="primary"
        @click="saveSettings"
        :loading="saving"
        :disabled="saving || loading"
      >
        Save Settings
      </Button>
    </template>
  </BaseModal>
</template>

<script setup>
import { ref, watch } from 'vue';
import { reportsApi, coaApi } from '../../../api';
import BaseModal from '../../ui/BaseModal.vue';
import FormField from '../../ui/FormField.vue';
import SelectInput from '../../ui/SelectInput.vue';
import Button from '../../ui/Button.vue';

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
