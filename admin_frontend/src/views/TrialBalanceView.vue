<template>
  <div class="space-y-6">
    <PageHeader
      eyebrow="Integritas Data"
      icon="bi bi-columns-gap"
      title="Trial Balance"
      subtitle="Saldo awal + mutasi periode = saldo akhir per akun COA, dengan cek keseimbangan debit = kredit."
    >
      <template #actions>
        <div class="flex items-center gap-2">
          <Button variant="secondary" @click="toggleEditor" class="gap-2">
            <i class="bi bi-pencil-square"></i>
            <span>Saldo Awal</span>
          </Button>
          <Button variant="primary" :disabled="loading" @click="loadTrialBalance" class="gap-2">
            <i class="bi bi-arrow-clockwise" :class="{ 'animate-spin': loading }"></i>
            <span>Refresh</span>
          </Button>
        </div>
      </template>
    </PageHeader>

    <!-- Filters -->
    <SectionCard body-class="p-4">
      <div class="flex flex-wrap items-end gap-4">
        <FormField label="Tahun" label-class="!text-xs" wrapper-class="w-32">
          <TextInput v-model="year" type="number" min="2000" max="2100" @keyup.enter="loadTrialBalance" />
        </FormField>
        <FormField label="Perusahaan" label-class="!text-xs" wrapper-class="w-64">
          <select v-model="companyId" class="form-input" @change="loadTrialBalance">
            <option value="">Semua perusahaan</option>
            <option v-for="company in companies" :key="company.id" :value="company.id">
              {{ company.name }}
            </option>
          </select>
        </FormField>
        <FormField label="Jenis Laporan" label-class="!text-xs" wrapper-class="w-40">
          <select v-model="reportType" class="form-input" @change="loadTrialBalance">
            <option value="real">Real</option>
            <option value="coretax">CoreTax</option>
          </select>
        </FormField>
      </div>
    </SectionCard>

    <!-- Opening balance editor -->
    <SectionCard v-if="showOpeningEditor" body-class="p-4">
      <div class="flex items-center justify-between mb-3">
        <div>
          <h3 class="font-bold text-sm">Saldo Awal per {{ year }}</h3>
          <p class="text-xs text-theme-muted mt-0.5">
            Harus seimbang: total debit = total kredit. Disimpan sebagai satu set (mengganti yang lama).
          </p>
        </div>
        <div class="flex items-center gap-2">
          <span class="text-xs font-mono" :class="openingTotalsDifference === 0 ? 'text-success' : 'text-danger'">
            D {{ formatCurrency(openingTotals.debit) }} · K {{ formatCurrency(openingTotals.credit) }}
          </span>
          <Button variant="primary" :disabled="savingOpening || openingTotalsDifference !== 0" @click="saveOpening" class="gap-2">
            <i class="bi bi-save"></i>
            <span>{{ savingOpening ? 'Menyimpan...' : 'Simpan Saldo Awal' }}</span>
          </Button>
        </div>
      </div>
      <p v-if="openingError" class="text-xs text-danger font-bold mb-2">{{ openingError }}</p>
      <div class="space-y-1 max-h-80 overflow-y-auto pr-1">
        <div
          v-for="entry in openingEntries"
          :key="entry.coa_id"
          class="grid grid-cols-12 gap-2 items-center text-xs"
        >
          <div class="col-span-5 truncate" :title="`${entry.code} — ${entry.name}`">
            <span class="font-mono text-theme-muted">{{ entry.code }}</span>
            <span class="ml-2">{{ entry.name }}</span>
          </div>
          <div class="col-span-3">
            <input
              v-model.number="entry.opening_debit"
              type="number"
              min="0"
              class="form-input !py-1 text-right font-mono"
              placeholder="Debit"
            />
          </div>
          <div class="col-span-3">
            <input
              v-model.number="entry.opening_credit"
              type="number"
              min="0"
              class="form-input !py-1 text-right font-mono"
              placeholder="Kredit"
            />
          </div>
          <div class="col-span-1 text-center">
            <button
              class="text-theme-muted hover:text-danger"
              title="Kosongkan"
              @click="entry.opening_debit = 0; entry.opening_credit = 0"
            >
              <i class="bi bi-eraser"></i>
            </button>
          </div>
        </div>
      </div>
    </SectionCard>

    <!-- Balance status -->
    <div
      v-if="!loading && trialBalance.rows?.length"
      :class="trialBalance.is_balanced
        ? 'bg-success/5 border-success/20 text-success'
        : 'bg-warning/5 border-warning/20 text-warning'"
      class="rounded-2xl border p-4 flex items-start gap-4 shadow-sm"
    >
      <div class="mt-0.5">
        <i :class="trialBalance.is_balanced ? 'bi bi-check-circle-fill' : 'bi bi-exclamation-triangle-fill'" class="text-lg"></i>
      </div>
      <div>
        <h4 class="font-bold text-sm">{{ trialBalance.is_balanced ? 'Seimbang (D = C)' : 'Belum seimbang' }}</h4>
        <p class="text-xs mt-1 opacity-90">
          <template v-if="!trialBalance.is_balanced">
            Selisih closing: <strong>{{ formatCurrency(Math.abs(trialBalance.unbalanced_amount)) }}</strong>
            ({{ trialBalance.unbalanced_amount > 0 ? 'debit lebih besar' : 'kredit lebih besar' }}).
            Transaksi statement ter-map satu sisi — butuh jurnal penyeimbang/saldo awal lengkap.
          </template>
          <template v-else>Total debit dan kredit saldo akhir seimbang.</template>
        </p>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex flex-col items-center justify-center py-20 grayscale opacity-50">
      <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-primary"></div>
      <p class="mt-4 text-xs font-bold uppercase tracking-widest text-theme-muted">Memuat Trial Balance...</p>
    </div>

    <!-- No data -->
    <div v-if="!loading && !trialBalance.rows?.length" class="flex flex-col items-center justify-center py-24 text-center">
      <i class="bi bi-inbox text-5xl text-theme-muted opacity-30"></i>
      <p class="mt-4 text-sm font-bold text-theme-muted">
        Belum ada data untuk tahun {{ year }} — isi saldo awal atau tunggu transaksi ter-mark.
      </p>
    </div>

    <!-- TB table -->
    <SectionCard v-if="!loading && trialBalance.rows?.length" body-class="p-0">
      <div class="overflow-x-auto">
        <table class="report-table">
          <thead>
            <tr>
              <th class="text-left">Akun</th>
              <th class="text-right">Opening D</th>
              <th class="text-right">Opening K</th>
              <th class="text-right">Mutasi D</th>
              <th class="text-right">Mutasi K</th>
              <th class="text-right">Closing D</th>
              <th class="text-right">Closing K</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in trialBalance.rows" :key="row.coa_code">
              <td class="text-left">
                <span class="font-mono text-theme-muted">{{ row.coa_code }}</span>
                <span class="ml-2">{{ row.coa_name }}</span>
                <span class="ml-2 text-[10px] uppercase text-theme-muted opacity-60">{{ row.coa_category }}</span>
              </td>
              <td class="text-right font-mono">{{ fmt(row.opening_debit) }}</td>
              <td class="text-right font-mono">{{ fmt(row.opening_credit) }}</td>
              <td class="text-right font-mono">{{ fmt(row.period_debit) }}</td>
              <td class="text-right font-mono">{{ fmt(row.period_credit) }}</td>
              <td class="text-right font-mono font-bold">{{ fmt(row.closing_debit) }}</td>
              <td class="text-right font-mono font-bold">{{ fmt(row.closing_credit) }}</td>
            </tr>
          </tbody>
          <tfoot>
            <tr class="font-bold">
              <td class="text-left">TOTAL</td>
              <td class="text-right font-mono">{{ fmt(trialBalance.totals?.opening_debit) }}</td>
              <td class="text-right font-mono">{{ fmt(trialBalance.totals?.opening_credit) }}</td>
              <td class="text-right font-mono">{{ fmt(trialBalance.totals?.period_debit) }}</td>
              <td class="text-right font-mono">{{ fmt(trialBalance.totals?.period_credit) }}</td>
              <td class="text-right font-mono">{{ fmt(trialBalance.totals?.closing_debit) }}</td>
              <td class="text-right font-mono">{{ fmt(trialBalance.totals?.closing_credit) }}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </SectionCard>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import PageHeader from '../components/ui/PageHeader.vue';
import SectionCard from '../components/ui/SectionCard.vue';
import Button from '../components/ui/Button.vue';
import FormField from '../components/ui/FormField.vue';
import TextInput from '../components/ui/TextInput.vue';

const currentYear = new Date().getFullYear();
const year = ref(currentYear);
const companyId = ref('');
const reportType = ref('real');
const loading = ref(false);
const trialBalance = ref({});
const companies = ref([]);

const showOpeningEditor = ref(false);
const openingEntries = ref([]);
const savingOpening = ref(false);
const openingError = ref('');

const fmt = (num) => new Intl.NumberFormat('id-ID').format(num || 0);
const formatCurrency = (amount) => `Rp ${fmt(amount)}`;

const openingTotals = computed(() => {
  const debit = openingEntries.value.reduce((sum, e) => sum + (Number(e.opening_debit) || 0), 0);
  const credit = openingEntries.value.reduce((sum, e) => sum + (Number(e.opening_credit) || 0), 0);
  return { debit, credit };
});
const openingTotalsDifference = computed(
  () => Math.round((openingTotals.value.debit - openingTotals.value.credit) * 100) / 100,
);

const loadTrialBalance = async () => {
  loading.value = true;
  try {
    const params = new URLSearchParams({
      year: String(year.value),
      report_type: reportType.value,
    });
    if (companyId.value) params.append('company_id', companyId.value);
    const response = await fetch(`/api/reports/trial-balance?${params}`);
    const data = await response.json();
    if (data.success) trialBalance.value = data.data;
  } catch (error) {
    console.error('Error loading trial balance:', error);
  } finally {
    loading.value = false;
  }
};

const loadCompanies = async () => {
  try {
    const response = await fetch('/api/companies');
    const data = await response.json();
    companies.value = data.companies || data.data || [];
  } catch (error) {
    console.error('Error loading companies:', error);
  }
};

const loadOpeningEntries = async () => {
  try {
    const [coaResponse, savedResponse] = await Promise.all([
      fetch('/api/coa'),
      fetch(`/api/reports/opening-balances?year=${year.value}${companyId.value ? `&company_id=${companyId.value}` : ''}`),
    ]);
    const coaData = await coaResponse.json();
    const savedData = await savedResponse.json();
    const coaList = coaData.coa_accounts || coaData.data || [];
    const savedByCoa = new Map(
      (savedData.data || []).map((entry) => [entry.coa_id, entry]),
    );
    openingEntries.value = coaList.map((coa) => {
      const saved = savedByCoa.get(coa.id);
      return {
        coa_id: coa.id,
        code: coa.code,
        name: coa.name,
        opening_debit: saved ? saved.opening_debit : 0,
        opening_credit: saved ? saved.opening_credit : 0,
      };
    });
  } catch (error) {
    console.error('Error loading opening balances:', error);
    openingError.value = 'Gagal memuat data COA / saldo awal.';
  }
};

const toggleOpeningEditor = async () => {
  showOpeningEditor.value = !showOpeningEditor.value;
  if (showOpeningEditor.value) await loadOpeningEntries();
};

const saveOpening = async () => {
  savingOpening.value = true;
  openingError.value = '';
  try {
    const response = await fetch('/api/reports/opening-balances', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        company_id: companyId.value || null,
        year: year.value,
        entries: openingEntries.value.map((entry) => ({
          coa_id: entry.coa_id,
          opening_debit: Number(entry.opening_debit) || 0,
          opening_credit: Number(entry.opening_credit) || 0,
        })),
      }),
    });
    const data = await response.json();
    if (data.success) {
      await loadTrialBalance();
    } else {
      openingError.value = data.error || 'Gagal menyimpan saldo awal.';
    }
  } catch (error) {
    openingError.value = 'Gagal menyimpan saldo awal.';
  } finally {
    savingOpening.value = false;
  }
};

// Buka/tutup editor via tombol header (muat data COA + saldo tersimpan saat dibuka).
const toggleEditor = () => toggleOpeningEditor();

watch(year, () => {
  if (showOpeningEditor.value) loadOpeningEntries();
});

onMounted(async () => {
  await Promise.all([loadCompanies(), loadTrialBalance()]);
});
</script>
