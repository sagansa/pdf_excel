<template>
  <div class="space-y-6">
    <div class="bg-white rounded-xl border border-gray-200 p-5">
      <h3 class="text-lg font-semibold text-gray-900">
        Service Transactions & Tax
      </h3>
      <p class="text-sm text-gray-500 mt-1">
        Mark jasa diatur dari menu Mark. Di sini tiap transaksi jasa punya
        konfigurasi pajak sendiri: NPWP, metode bruto/netto, dan waktu bayar
        pajak.
      </p>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 p-4">
      <div
        class="flex flex-col lg:flex-row gap-3 lg:items-center lg:justify-between"
      >
        <div class="grid grid-cols-1 md:grid-cols-3 gap-3 w-full lg:w-auto">
          <div
            class="bg-indigo-50 border border-indigo-100 rounded-lg px-3 py-2"
          >
            <div class="text-xs uppercase font-semibold text-indigo-600">
              Total Transaksi
            </div>
            <div class="text-lg font-bold text-indigo-900">
              {{ summary.total_txn }}
            </div>
          </div>
          <div
            class="bg-emerald-50 border border-emerald-100 rounded-lg px-3 py-2"
          >
            <div class="text-xs uppercase font-semibold text-emerald-600">
              Ada NPWP
            </div>
            <div class="text-lg font-bold text-emerald-900">
              {{ summary.with_npwp }}
            </div>
          </div>
          <div class="bg-amber-50 border border-amber-100 rounded-lg px-3 py-2">
            <div class="text-xs uppercase font-semibold text-amber-700">
              Preview Total Pajak
            </div>
            <div class="text-lg font-bold text-amber-900">
              {{ formatCurrency(summary.total_tax) }}
            </div>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <input
            v-model="search"
            @keyup.enter="loadServiceTransactions"
            type="text"
            placeholder="Cari deskripsi/mark..."
            class="w-64 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
          <button
            @click="loadServiceTransactions"
            class="px-3 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700"
          >
            Cari
          </button>
        </div>
      </div>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div class="px-4 py-3 border-b border-gray-200 bg-gray-50">
        <h4 class="text-sm font-semibold text-gray-800">
          Service Transactions List
        </h4>
      </div>
      <div class="max-h-[560px] overflow-auto">
        <table class="min-w-full divide-y divide-gray-200 text-sm">
          <thead class="bg-white sticky top-0">
            <tr>
              <th
                class="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase"
              >
                Tanggal / Deskripsi
              </th>
              <th
                class="px-4 py-2 text-right text-xs font-semibold text-gray-500 uppercase"
              >
                Nominal
              </th>
              <th
                class="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase"
              >
                Mark
              </th>
              <th
                class="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase"
              >
                NPWP
              </th>
              <th
                class="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase"
              >
                Metode
              </th>
              <th
                class="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase"
              >
                Waktu Bayar
              </th>
              <th
                class="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase"
              >
                Tgl Bayar
              </th>
              <th
                class="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase"
              >
                Preview Pajak
              </th>
              <th
                class="px-4 py-2 text-right text-xs font-semibold text-gray-500 uppercase"
              >
                Aksi
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-if="loadingTransactions">
              <td colspan="9" class="px-4 py-6 text-center text-gray-500">
                Loading transaksi jasa...
              </td>
            </tr>
            <tr v-else-if="transactions.length === 0">
              <td colspan="9" class="px-4 py-6 text-center text-gray-500">
                Tidak ada transaksi jasa untuk filter saat ini
              </td>
            </tr>
            <tr
              v-for="txn in transactions"
              :key="txn.id"
              class="hover:bg-gray-50"
            >
              <td class="px-4 py-3">
                <div class="font-medium text-gray-900">
                  {{ formatDate(txn.txn_date) }}
                </div>
                <div class="text-xs text-gray-600 max-w-[300px] truncate">
                  {{ txn.description || "-" }}
                </div>
              </td>
              <td class="px-4 py-3 text-right font-medium text-gray-900">
                {{ formatCurrency(txn.amount) }}
              </td>
              <td class="px-4 py-3 text-gray-700">
                {{ txn.personal_use || txn.internal_report || "-" }}
              </td>
              <td class="px-4 py-3">
                <span
                  v-if="txn.has_npwp"
                  class="inline-flex items-center px-2 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800"
                >
                  Ada
                </span>
                <span
                  v-else
                  class="inline-flex items-center px-2 py-1 rounded-full text-xs font-semibold bg-gray-100 text-gray-700"
                >
                  Tidak Ada
                </span>
              </td>
              <td class="px-4 py-3 text-gray-700">
                <span
                  v-if="txn.service_calculation_method === 'NETTO'"
                  class="font-medium text-indigo-700"
                  >Netto</span
                >
                <span
                  v-else-if="txn.service_calculation_method === 'NONE'"
                  class="font-medium text-gray-500 italic"
                  >Tanpa Pajak</span
                >
                <span v-else class="font-medium text-gray-700">Bruto</span>
              </td>
              <td class="px-4 py-3 text-gray-700">
                {{ formatTiming(txn.service_tax_payment_timing) }}
              </td>
              <td class="px-4 py-3 text-gray-700">
                {{
                  txn.service_tax_payment_date
                    ? formatDate(txn.service_tax_payment_date)
                    : "-"
                }}
              </td>
              <td class="px-4 py-3">
                <div class="text-xs text-gray-700">
                  <div>
                    Tarif:
                    <span class="font-semibold"
                      >{{ getPreview(txn).rate }}%</span
                    >
                  </div>
                  <div>
                    PPh:
                    <span class="font-semibold">{{
                      formatCurrency(getPreview(txn).tax)
                    }}</span>
                  </div>
                </div>
              </td>
              <td class="px-4 py-3 text-right">
                <button
                  @click="openEditor(txn)"
                  class="p-2 text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                  title="Edit Pajak"
                >
                  <i class="bi bi-pencil-square text-lg"></i>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div
      v-if="isEditorOpen && selectedTxn"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="closeEditor"
    >
      <div
        class="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto"
      >
        <div
          class="p-6 border-b border-gray-200 flex items-center justify-between"
        >
          <div>
            <h3 class="text-lg font-semibold text-gray-900">
              Edit Service Tax
            </h3>
            <p class="text-xs text-gray-500 mt-1">
              {{ formatDate(selectedTxn.txn_date) }} |
              {{ selectedTxn.description || "-" }}
            </p>
          </div>
          <button
            @click="closeEditor"
            class="text-gray-400 hover:text-gray-600"
          >
            <i class="bi bi-x-lg"></i>
          </button>
        </div>

        <div class="p-6 space-y-4">
          <div class="bg-gray-50 rounded-lg border border-gray-200 p-4">
            <div class="text-xs text-gray-500">Nominal Transaksi</div>
            <div class="text-2xl font-bold text-gray-900">
              {{ formatCurrency(selectedTxn.amount) }}
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1"
                >Status NPWP</label
              >
              <select
                v-model="editorForm.has_npwp"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              >
                <option :value="false">Tidak Ada NPWP</option>
                <option :value="true">Ada NPWP</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1"
                >NPWP</label
              >
              <input
                v-model="editorForm.npwp"
                :disabled="!editorForm.has_npwp"
                type="text"
                maxlength="32"
                placeholder="15 digit NPWP"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 disabled:bg-gray-100 disabled:text-gray-400"
              />
            </div>
          </div>

          <div
            class="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-indigo-50 border border-indigo-100 rounded-lg"
          >
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1"
                >Metode Perhitungan</label
              >
              <select
                v-model="editorForm.calculation_method"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              >
                <option value="BRUTO">Bruto</option>
                <option value="NETTO">Netto</option>
                <option value="NONE">Tanpa Pajak</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1"
                >Waktu Bayar Pajak</label
              >
              <select
                v-model="editorForm.tax_payment_timing"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              >
                <option value="same_period">Periode yang sama</option>
                <option value="next_period">Periode berikutnya</option>
                <option value="next_year">Tahun berikutnya</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1"
                >Tanggal Bayar Pajak</label
              >
              <input
                v-model="editorForm.tax_payment_date"
                type="date"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              />
            </div>
          </div>

          <div class="bg-white border border-gray-200 rounded-lg p-4">
            <div class="text-xs font-bold text-gray-500 uppercase mb-3">
              Preview Pajak Transaksi
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div
                class="p-2 sm:p-3 bg-gray-50 rounded-lg border border-gray-100 flex items-center gap-2 sm:gap-3 overflow-hidden"
              >
                <div
                  class="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center text-gray-500 shrink-0"
                >
                  <i class="bi bi-percent"></i>
                </div>
                <div class="min-w-0">
                  <div
                    class="text-[10px] text-gray-500 uppercase font-bold tracking-wider truncate"
                  >
                    Tarif
                  </div>
                  <div class="font-bold text-gray-900 text-sm sm:text-base">
                    {{ editorPreview.rate }}%
                  </div>
                </div>
              </div>

              <div
                class="p-2 sm:p-3 bg-indigo-50 rounded-lg border border-indigo-100 flex items-center gap-2 sm:gap-3 overflow-hidden"
              >
                <div
                  class="w-8 h-8 rounded-lg bg-indigo-100 flex items-center justify-center text-indigo-600 shrink-0"
                >
                  <i class="bi bi-box-arrow-in-right"></i>
                </div>
                <div class="min-w-0">
                  <div
                    class="text-[10px] text-indigo-500 uppercase font-bold tracking-wider truncate"
                  >
                    Nilai Bruto
                  </div>
                  <div
                    class="font-bold text-indigo-700 text-sm sm:text-base truncate"
                    :title="formatCurrency(editorPreview.bruto)"
                  >
                    {{ formatCurrency(editorPreview.bruto) }}
                  </div>
                </div>
              </div>

              <div
                class="p-2 sm:p-3 bg-emerald-50 rounded-lg border border-emerald-100 flex items-center gap-2 sm:gap-3 overflow-hidden"
              >
                <div
                  class="w-8 h-8 rounded-lg bg-emerald-100 flex items-center justify-center text-emerald-600 shrink-0"
                >
                  <i class="bi bi-wallet2"></i>
                </div>
                <div class="min-w-0">
                  <div
                    class="text-[10px] text-emerald-500 uppercase font-bold tracking-wider truncate"
                  >
                    Nilai Netto
                  </div>
                  <div
                    class="font-bold text-emerald-700 text-sm sm:text-base truncate"
                    :title="formatCurrency(editorPreview.netto)"
                  >
                    {{ formatCurrency(editorPreview.netto) }}
                  </div>
                </div>
              </div>

              <div
                class="p-2 sm:p-3 bg-amber-50 rounded-lg border border-amber-100 flex items-center gap-2 sm:gap-3 overflow-hidden"
              >
                <div
                  class="w-8 h-8 rounded-lg bg-amber-100 flex items-center justify-center text-amber-600 shrink-0"
                >
                  <i class="bi bi-shield-check"></i>
                </div>
                <div class="min-w-0">
                  <div
                    class="text-[10px] text-amber-600 uppercase font-bold tracking-wider truncate"
                  >
                    PPh
                  </div>
                  <div
                    class="font-bold text-amber-700 text-sm sm:text-base truncate"
                    :title="formatCurrency(editorPreview.tax)"
                  >
                    {{ formatCurrency(editorPreview.tax) }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
          <button
            type="button"
            @click="closeEditor"
            class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Batal
          </button>
          <button
            type="button"
            :disabled="editorSaving"
            @click="saveEditor"
            class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50"
          >
            {{ editorSaving ? "Menyimpan..." : "Simpan" }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { historyApi } from "../../api";

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
