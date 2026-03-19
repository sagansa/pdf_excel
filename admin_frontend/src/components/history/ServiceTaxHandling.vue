<template>
  <div class="space-y-6">
    <!-- Header info -->
    <header class="flex flex-col gap-2">
      <div class="inline-flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.2em] text-accent">
        History & Database
      </div>
      <h2 class="text-3xl font-bold tracking-tight text-theme">
        Service Tax Handling
      </h2>
      <p class="max-w-3xl text-sm leading-relaxed text-theme-muted">
        Kelola konfigurasi pajak untuk transaksi jasa. Mark jasa diatur dari menu 
        <router-link to="/marks" class="text-primary hover:underline font-semibold">Mark</router-link>. 
        Gunakan editor untuk mengatur NPWP, metode perhitungan (Bruto/Netto), dan penjadwalan pembayaran pajak.
      </p>
    </header>

    <!-- Stats & Search -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
      <div class="lg:col-span-8 grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard
          label="Total Transaksi"
          :value="summary.total_txn"
          variant="primary"
          icon="bi-receipt"
        />
        <StatCard
          label="Ada NPWP"
          :value="summary.with_npwp"
          variant="success"
          icon="bi-card-list"
        />
        <StatCard
          label="Preview Total Pajak"
          :value="formatCurrency(summary.total_tax)"
          variant="warning"
          icon="bi-calculator"
        />
      </div>

      <SectionCard class="lg:col-span-4" bodyClass="p-4">
        <div class="flex flex-col gap-3">
          <div class="text-[10px] font-bold text-theme-muted uppercase tracking-widest">
            Search & Filter
          </div>
          <div class="flex items-center gap-2">
            <TextInput
              v-model="search"
              placeholder="Cari deskripsi/mark..."
              @keyup.enter="loadServiceTransactions"
              class="flex-1"
            >
              <template #leading>
                <i class="bi bi-search"></i>
              </template>
            </TextInput>
            <Button
              variant="primary"
              @click="loadServiceTransactions"
            >
              Cari
            </Button>
          </div>
        </div>
      </SectionCard>
    </div>

    <SectionCard bodyClass="p-0 overflow-hidden">
      <template #header>
        <div class="px-5 py-4 border-b border-border bg-surface-raised/50 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <div class="w-1 h-4 bg-primary rounded-full"></div>
            <h4 class="text-xs font-bold text-theme uppercase tracking-widest">
              Service Transactions List
            </h4>
          </div>
          <div class="text-[10px] text-theme-muted font-medium">
            Showing {{ transactions.length }} transactions
          </div>
        </div>
      </template>

      <div class="max-h-[600px] overflow-auto">
        <table class="table-compact min-w-full">
          <thead>
            <tr>
              <th class="text-left">Tanggal / Deskripsi</th>
              <th class="text-right">Nominal</th>
              <th class="text-left">Mark</th>
              <th class="text-left">NPWP</th>
              <th class="text-left">Metode</th>
              <th class="text-left">Waktu Bayar</th>
              <th class="text-left">Tgl Bayar</th>
              <th class="text-left">Preview Pajak</th>
              <th class="text-right">Aksi</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border/50">
            <tr v-if="loadingTransactions">
              <td colspan="9" class="px-6 py-12 text-center text-theme-muted font-medium italic">
                <div class="flex flex-col items-center gap-3">
                  <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
                  Loading transaksi jasa...
                </div>
              </td>
            </tr>
            <tr v-else-if="transactions.length === 0">
              <td colspan="9" class="px-6 py-12 text-center text-theme-muted font-medium italic">
                Tidak ada transaksi jasa untuk filter saat ini
              </td>
            </tr>
            <tr
              v-for="txn in transactions"
              :key="txn.id"
            >
              <td class="px-4 py-3">
                <div class="font-bold text-theme text-[13px]">
                  {{ formatDate(txn.txn_date) }}
                </div>
                <div class="text-[10px] text-theme-muted max-w-[300px] truncate mt-0.5 uppercase tracking-tight">
                  {{ txn.description || "-" }}
                </div>
              </td>
              <td class="px-4 py-3 text-right font-bold text-theme">
                {{ formatCurrency(txn.amount) }}
              </td>
              <td class="px-4 py-3">
                <span class="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-bold bg-surface-muted text-theme-muted uppercase tracking-wider border border-border">
                  {{ txn.personal_use || txn.internal_report || "-" }}
                </span>
              </td>
              <td class="px-4 py-3">
                <span
                  v-if="txn.has_npwp"
                  class="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-bold bg-success/10 text-success uppercase tracking-wider border border-success/20"
                >
                  Ada
                </span>
                <span
                  v-else
                  class="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-bold bg-theme-muted/10 text-theme-muted uppercase tracking-wider border border-border"
                >
                  Tidak Ada
                </span>
              </td>
              <td class="px-4 py-3">
                <span
                  v-if="txn.service_calculation_method === 'NETTO'"
                  class="font-bold text-primary text-[11px] uppercase"
                  >Netto</span
                >
                <span
                  v-else-if="txn.service_calculation_method === 'NONE'"
                  class="font-bold text-theme-muted text-[11px] uppercase italic opacity-60"
                  >Tanpa Pajak</span
                >
                <span v-else class="font-bold text-theme text-[11px] uppercase">Bruto</span>
              </td>
              <td class="px-4 py-3 text-theme/80 text-[11px]">
                {{ formatTiming(txn.service_tax_payment_timing) }}
              </td>
              <td class="px-4 py-3 text-theme/80 text-[11px]">
                {{
                  txn.service_tax_payment_date
                    ? formatDate(txn.service_tax_payment_date)
                    : "-"
                }}
              </td>
              <td class="px-4 py-3">
                <div class="text-[10px]">
                  <div class="flex items-center gap-1">
                    <span class="text-theme-muted uppercase font-bold tracking-tighter opacity-60 w-8">Tarif</span>
                    <span class="font-bold text-theme">{{ getPreview(txn).rate }}%</span>
                  </div>
                  <div class="flex items-center gap-1 mt-0.5">
                    <span class="text-theme-muted uppercase font-bold tracking-tighter opacity-60 w-8">PPh</span>
                    <span class="font-bold text-primary">{{ formatCurrency(getPreview(txn).tax) }}</span>
                  </div>
                </div>
              </td>
              <td class="px-4 py-3 text-right">
                <Button
                  variant="secondary"
                  size="sm"
                  @click="openEditor(txn)"
                  title="Edit Pajak"
                >
                  <i class="bi bi-pencil-square"></i>
                </Button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </SectionCard>

    <BaseModal
      :isOpen="isEditorOpen"
      size="2xl"
      @close="closeEditor"
    >
      <template #title>
        <div>
          <h3 class="text-lg font-bold text-theme">Edit Service Tax</h3>
          <p class="text-[10px] text-theme-muted font-bold uppercase tracking-widest mt-0.5">
            {{ formatDate(selectedTxn?.txn_date) }} | {{ selectedTxn?.description || "-" }}
          </p>
        </div>
      </template>

      <div class="px-6 space-y-6">
        <div class="bg-surface-muted rounded-2xl border border-border p-5">
          <div class="text-[10px] text-theme-muted font-bold uppercase tracking-widest opacity-60">Nominal Transaksi</div>
          <div class="text-3xl font-bold text-theme mt-1">
            {{ formatCurrency(selectedTxn?.amount) }}
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <FormField label="Status NPWP">
            <SelectInput
              v-model="editorForm.has_npwp"
              :options="[
                { value: false, label: 'Tidak Ada NPWP' },
                { value: true, label: 'Ada NPWP' }
              ]"
            />
          </FormField>
          <FormField label="NPWP">
            <TextInput
              v-model="editorForm.npwp"
              :disabled="!editorForm.has_npwp"
              placeholder="15 digit NPWP"
              maxlength="32"
            />
          </FormField>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 p-6 bg-primary/5 rounded-2xl border border-primary/10">
          <FormField label="Metode Perhitungan">
            <SelectInput
              v-model="editorForm.calculation_method"
              :options="[
                { value: 'BRUTO', label: 'Bruto' },
                { value: 'NETTO', label: 'Netto' },
                { value: 'NONE', label: 'Tanpa Pajak' }
              ]"
            />
          </FormField>
          <FormField label="Waktu Bayar Pajak">
            <SelectInput
              v-model="editorForm.tax_payment_timing"
              :options="[
                { value: 'same_period', label: 'Periode yang sama' },
                { value: 'next_period', label: 'Periode berikutnya' },
                { value: 'next_year', label: 'Tahun berikutnya' }
              ]"
            />
          </FormField>
          <FormField label="Tanggal Bayar Pajak">
            <TextInput
              v-model="editorForm.tax_payment_date"
              type="date"
            />
          </FormField>
        </div>

        <div class="bg-surface rounded-2xl border border-border p-5">
          <div class="text-[10px] font-bold text-theme-muted uppercase tracking-widest mb-4">
            Preview Pajak Transaksi
          </div>
          <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div class="p-3 bg-surface-muted rounded-xl border border-border flex items-center gap-3">
              <div class="w-8 h-8 rounded-lg bg-theme/5 flex items-center justify-center text-theme shrink-0">
                <i class="bi bi-percent"></i>
              </div>
              <div class="min-w-0">
                <div class="text-[9px] text-theme-muted uppercase font-bold tracking-tighter opacity-60">Tarif</div>
                <div class="font-bold text-theme text-sm">{{ editorPreview.rate }}%</div>
              </div>
            </div>

            <div class="p-3 bg-primary/10 rounded-xl border border-primary/20 flex items-center gap-3">
              <div class="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary shrink-0">
                <i class="bi bi-box-arrow-in-right"></i>
              </div>
              <div class="min-w-0">
                <div class="text-[9px] text-primary uppercase font-bold tracking-tighter opacity-60">Bruto</div>
                <div class="font-bold text-primary text-sm truncate" :title="formatCurrency(editorPreview.bruto)">
                  {{ formatCurrency(editorPreview.bruto) }}
                </div>
              </div>
            </div>

            <div class="p-3 bg-success/10 rounded-xl border border-success/20 flex items-center gap-3">
              <div class="w-8 h-8 rounded-lg bg-success/10 flex items-center justify-center text-success shrink-0">
                <i class="bi bi-wallet2"></i>
              </div>
              <div class="min-w-0">
                <div class="text-[9px] text-success uppercase font-bold tracking-tighter opacity-60">Netto</div>
                <div class="font-bold text-success text-sm truncate" :title="formatCurrency(editorPreview.netto)">
                  {{ formatCurrency(editorPreview.netto) }}
                </div>
              </div>
            </div>

            <div class="p-3 bg-warning/10 rounded-xl border border-warning/20 flex items-center gap-3">
              <div class="w-8 h-8 rounded-lg bg-warning/10 flex items-center justify-center text-warning shrink-0">
                <i class="bi bi-shield-check"></i>
              </div>
              <div class="min-w-0">
                <div class="text-[9px] text-warning uppercase font-bold tracking-tighter opacity-60">PPh</div>
                <div class="font-bold text-warning text-sm truncate" :title="formatCurrency(editorPreview.tax)">
                  {{ formatCurrency(editorPreview.tax) }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <Button
          variant="secondary"
          @click="closeEditor"
          :disabled="editorSaving"
        >
          Batal
        </Button>
        <Button
          variant="primary"
          @click="saveEditor"
          :loading="editorSaving"
          :disabled="editorSaving"
        >
          Simpan
        </Button>
      </template>
    </BaseModal>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { historyApi } from "../../api";
import SectionCard from "../ui/SectionCard.vue";
import StatCard from "../ui/StatCard.vue";
import TextInput from "../ui/TextInput.vue";
import SelectInput from "../ui/SelectInput.vue";
import Button from "../ui/Button.vue";
import BaseModal from "../ui/BaseModal.vue";
import FormField from "../ui/FormField.vue";

const props = defineProps({
  companyId: {
    type: String,
    default: "",
  },
  year: {
    type: [String, Number],
    default: "",
  },
});

const transactions = ref([]);
const loadingTransactions = ref(false);
const search = ref("");

const selectedTxn = ref(null);
const isEditorOpen = ref(false);
const editorSaving = ref(false);
const editorForm = ref({
  has_npwp: false,
  npwp: "",
  calculation_method: "BRUTO",
  tax_payment_timing: "same_period",
  tax_payment_date: "",
});

const normalizeDigits = (value) => (value || "").toString().replace(/\D/g, "");

const normalizeMethod = (value) => {
  const method = (value || "BRUTO").toString().toUpperCase();
  const allowed = ["BRUTO", "NETTO", "NONE"];
  return allowed.includes(method) ? method : "BRUTO";
};

const normalizeTiming = (value) => {
  const allowed = ["same_period", "next_period", "next_year"];
  return allowed.includes(value) ? value : "same_period";
};

const formatCurrency = (amount) => {
  const val = Number(amount || 0);
  return new Intl.NumberFormat("id-ID", {
    style: "currency",
    currency: "IDR",
    minimumFractionDigits: 0,
  }).format(val);
};

const formatDate = (dateStr) => {
  if (!dateStr) return "-";
  const d = new Date(dateStr);
  if (Number.isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString("id-ID", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
};

const formatTiming = (value) => {
  if (value === "next_period") return "Periode berikutnya";
  if (value === "next_year") return "Tahun berikutnya";
  return "Periode yang sama";
};

const getPreviewByConfig = (amount, hasNpwp, method) => {
  const normMethod = normalizeMethod(method);
  const base = Math.abs(Number(amount || 0));

  if (normMethod === "NONE") {
    return { rate: 0, bruto: base, netto: base, tax: 0 };
  }

  const rate = hasNpwp ? 2 : 4;

  if (normMethod === "NETTO") {
    const divisor = 1 - rate / 100;
    if (divisor <= 0) {
      return { rate, bruto: 0, netto: base, tax: 0 };
    }
    const bruto = base / divisor;
    return {
      rate,
      bruto,
      netto: base,
      tax: Math.max(0, bruto - base),
    };
  }

  const tax = base * (rate / 100);
  return {
    rate,
    bruto: base,
    netto: Math.max(0, base - tax),
    tax,
  };
};

const getPreview = (txn) => {
  return getPreviewByConfig(
    txn.amount,
    Boolean(txn.has_npwp),
    txn.service_calculation_method,
  );
};

const summary = computed(() => {
  const totalTxn = transactions.value.length;
  const withNpwp = transactions.value.filter((txn) => txn.has_npwp).length;
  const totalTax = transactions.value.reduce(
    (acc, txn) => acc + Number(getPreview(txn).tax || 0),
    0,
  );
  return {
    total_txn: totalTxn,
    with_npwp: withNpwp,
    total_tax: totalTax,
  };
});

const editorPreview = computed(() => {
  if (!selectedTxn.value) return { rate: 0, bruto: 0, netto: 0, tax: 0 };
  return getPreviewByConfig(
    selectedTxn.value.amount,
    Boolean(editorForm.value.has_npwp),
    editorForm.value.calculation_method,
  );
});

const normalizeTransaction = (txn) => {
  const npwpDigits = normalizeDigits(txn.service_npwp);
  return {
    ...txn,
    service_npwp: npwpDigits || null,
    has_npwp: npwpDigits.length === 15,
    service_calculation_method: normalizeMethod(txn.service_calculation_method),
    service_tax_payment_timing: normalizeTiming(txn.service_tax_payment_timing),
    service_tax_payment_date: txn.service_tax_payment_date || null,
  };
};

const loadServiceTransactions = async () => {
  loadingTransactions.value = true;
  try {
    const response = await historyApi.getServiceTransactions(
      props.companyId,
      props.year,
      search.value,
    );
    const rows = response.data.transactions || [];
    transactions.value = rows.map(normalizeTransaction);
  } catch (error) {
    console.error("Failed to load service transactions:", error);
    transactions.value = [];
  } finally {
    loadingTransactions.value = false;
  }
};

const openEditor = (txn) => {
  selectedTxn.value = txn;
  editorForm.value = {
    has_npwp: Boolean(txn.has_npwp),
    npwp: txn.service_npwp || "",
    calculation_method: normalizeMethod(txn.service_calculation_method),
    tax_payment_timing: normalizeTiming(txn.service_tax_payment_timing),
    tax_payment_date: txn.service_tax_payment_date || "",
  };
  isEditorOpen.value = true;
};

const closeEditor = () => {
  isEditorOpen.value = false;
  selectedTxn.value = null;
  editorSaving.value = false;
};

const saveEditor = async () => {
  if (!selectedTxn.value) return;

  const npwpDigits = normalizeDigits(editorForm.value.npwp);
  if (editorForm.value.has_npwp && npwpDigits.length !== 15) {
    alert("NPWP harus 15 digit angka.");
    return;
  }

  editorSaving.value = true;
  try {
    const payload = {
      has_npwp: Boolean(editorForm.value.has_npwp),
      npwp: editorForm.value.has_npwp ? npwpDigits : null,
      calculation_method: normalizeMethod(editorForm.value.calculation_method),
      tax_payment_timing: normalizeTiming(editorForm.value.tax_payment_timing),
      tax_payment_date: editorForm.value.tax_payment_date || null,
    };

    const response = await historyApi.updateServiceTransactionTax(
      selectedTxn.value.id,
      payload,
    );
    const updated = {
      ...selectedTxn.value,
      service_npwp: response.data.service_npwp || null,
      has_npwp: Boolean(response.data.has_npwp),
      service_calculation_method: normalizeMethod(
        response.data.service_calculation_method || payload.calculation_method,
      ),
      service_tax_payment_timing: normalizeTiming(
        response.data.service_tax_payment_timing || payload.tax_payment_timing,
      ),
      service_tax_payment_date:
        response.data.service_tax_payment_date ||
        payload.tax_payment_date ||
        null,
    };

    const idx = transactions.value.findIndex(
      (txn) => txn.id === selectedTxn.value.id,
    );
    if (idx >= 0) {
      transactions.value[idx] = updated;
    }
    closeEditor();
  } catch (error) {
    console.error("Failed to save service tax config:", error);
    alert(
      "Gagal simpan konfigurasi pajak jasa: " +
        (error.response?.data?.error || error.message),
    );
  } finally {
    editorSaving.value = false;
  }
};

onMounted(loadServiceTransactions);

watch(
  () => [props.companyId, props.year],
  () => {
    loadServiceTransactions();
  },
);
</script>
