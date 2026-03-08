<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    @click.self="close"
  >
    <div
      class="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto"
    >
      <div class="p-6 border-b border-gray-200">
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-bold text-gray-900">
            {{
              isEditMode
                ? "Edit Aset Amortisasi"
                : "Daftarkan Aset Amortisasi Baru"
            }}
          </h3>
          <button
            @click="close"
            class="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <i class="bi bi-x-lg text-xl"></i>
          </button>
        </div>
      </div>

      <form @submit.prevent="handleSubmit" class="p-6 space-y-5">
        <!-- Asset Information -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="md:col-span-2">
            <label class="block text-sm font-semibold text-gray-700 mb-1">
              Nama Aset <span class="text-red-500">*</span>
            </label>
            <input
              v-model="form.asset_name"
              required
              type="text"
              class="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors text-sm"
              placeholder="Misal: Pembelian Software ERP 2025"
            />
          </div>

          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-1">
              Kelompok Aset <span class="text-red-500">*</span>
            </label>
            <select
              v-model="form.asset_group_id"
              required
              class="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors text-sm"
            >
              <option value="" disabled>Pilih Kelompok Aset...</option>
              <optgroup
                v-for="(groups, type) in groupedAssetGroups"
                :key="type"
                :label="getAssetTypeLabel(type)"
              >
                <option
                  v-for="group in groups"
                  :key="group.id"
                  :value="group.id"
                >
                  {{ group.group_name }} ({{ group.useful_life_years }} tahun /
                  {{ group.tarif_rate }}%)
                </option>
              </optgroup>
            </select>
          </div>

          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-1">
              Tanggal Mulai Amortisasi <span class="text-red-500">*</span>
            </label>
            <input
              v-model="form.acquisition_date"
              required
              type="date"
              class="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors text-sm"
            />
            <p class="text-[10px] text-gray-500 mt-1">
              Bulan amortisasi dimulai.
            </p>
          </div>
        </div>

        <!-- Link Transactions Section (like Rental Contract) -->
        <div class="space-y-3">
          <div class="flex items-center justify-between">
            <label class="block text-sm font-bold text-gray-700">
              <i class="bi bi-link-45deg mr-1"></i>
              Link Transaksi Pembayaran
            </label>
            <span
              class="text-xs text-indigo-600 bg-indigo-50 px-2 py-1 rounded-full font-medium"
            >
              {{ selectedTransactionIds.length }} selected
            </span>
          </div>

          <div class="border border-gray-200 rounded-lg overflow-hidden">
            <div class="bg-gray-50 px-4 py-2 border-b border-gray-200">
              <div class="flex items-center gap-2">
                <input
                  v-model="searchQuery"
                  type="text"
                  placeholder="Cari transaksi..."
                  class="flex-1 text-xs px-3 py-1.5 border border-gray-300 rounded focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                />
                <button
                  type="button"
                  @click="toggleSortDirection"
                  class="text-gray-500 hover:text-indigo-600 px-2"
                  :title="
                    sortDirection === 'asc'
                      ? 'Urutkan: Baru ke Lama'
                      : 'Urutkan: Lama ke Baru'
                  "
                >
                  <i
                    :class="
                      sortDirection === 'asc'
                        ? 'bi bi-sort-numeric-down'
                        : 'bi bi-sort-numeric-up'
                    "
                  ></i>
                </button>
                <button
                  type="button"
                  @click="fetchLinkableTransactions"
                  class="text-gray-500 hover:text-indigo-600 px-2"
                  title="Refresh"
                >
                  <i class="bi bi-arrow-clockwise"></i>
                </button>
              </div>
            </div>

            <div class="max-h-48 overflow-y-auto">
              <div v-if="isLoadingTxns" class="px-4 py-6 text-center">
                <span
                  class="w-5 h-5 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin inline-block"
                ></span>
                <p class="text-xs text-gray-500 mt-2">Memuat transaksi...</p>
              </div>

              <div
                v-else-if="filteredTransactions.length === 0"
                class="px-4 py-8 text-center text-gray-500 text-xs"
              >
                <i class="bi bi-inbox text-2xl mb-2 block"></i>
                Tidak ada transaksi aset yang belum terdaftar
              </div>

              <div
                v-else
                v-for="txn in filteredTransactions"
                :key="txn.id"
                class="flex items-center px-4 py-3 hover:bg-gray-50 border-b border-gray-100 last:border-0"
                :class="{ 'bg-indigo-50': isSelected(txn.id) }"
              >
                <input
                  :id="'asset-txn-' + txn.id"
                  v-model="selectedTransactionIds"
                  :value="txn.id"
                  type="checkbox"
                  class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                />
                <label
                  :for="'asset-txn-' + txn.id"
                  class="ml-3 flex-1 cursor-pointer"
                >
                  <div class="flex items-center justify-between">
                    <div>
                      <div class="text-xs font-semibold text-gray-900">
                        {{ txn.description }}
                      </div>
                      <div class="text-[10px] text-gray-500">
                        {{ txn.txn_date }} |
                        {{ txn.mark_name || txn.internal_report || "-" }}
                      </div>
                    </div>
                    <div class="text-right">
                      <div class="text-sm font-bold text-gray-900">
                        {{ formatCurrency(txn.amount) }}
                      </div>
                    </div>
                  </div>
                </label>
              </div>
            </div>
          </div>
        </div>

        <!-- Summary -->
        <div
          v-if="selectedTransactionIds.length > 0"
          class="bg-indigo-50 border border-indigo-100 rounded-lg p-4"
        >
          <div
            class="text-[10px] font-bold text-indigo-500 uppercase mb-2 tracking-wider"
          >
            Ringkasan Aset
          </div>
          <div class="grid grid-cols-2 gap-3 text-sm">
            <div>
              <div class="text-gray-500 text-[10px] uppercase">
                Jumlah Transaksi
              </div>
              <div class="font-semibold text-gray-900">
                {{ selectedTransactionIds.length }} transaksi
              </div>
            </div>
            <div>
              <div class="text-gray-500 text-[10px] uppercase">
                Total Nilai Perolehan
              </div>
              <div class="font-bold text-indigo-700 text-lg">
                {{ formatCurrency(totalSelectedAmount) }}
              </div>
            </div>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="flex justify-end gap-3 pt-4 border-t border-gray-200">
          <button
            type="button"
            @click="close"
            class="px-5 py-2 text-sm font-semibold text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-200 transition-colors"
            :disabled="isSubmitting"
          >
            Batal
          </button>
          <button
            type="submit"
            class="px-5 py-2 text-sm font-semibold text-white bg-indigo-600 border border-transparent rounded-lg hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 transition-colors inline-flex items-center gap-2"
            :disabled="isSubmitting || !isFormValid"
          >
            <span
              v-if="isSubmitting"
              class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"
            ></span>
            <i v-else class="bi bi-check2-circle"></i>
            {{ isEditMode ? "Simpan Perubahan" : "Daftarkan Aset" }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import api from "../../../api/index";

const props = defineProps({
  isOpen: {
    type: Boolean,
    required: true,
  },
  companyId: {
    type: String,
    required: true,
  },
  year: {
    type: [String, Number],
    default: null,
  },
  assetGroups: {
    type: Array,
    default: () => [],
  },
  asset: {
    type: Object,
    default: null,
  },
});

const emit = defineEmits(["close", "save"]);

const form = ref({
  asset_name: "",
  asset_group_id: "",
  acquisition_date: new Date().toISOString().split("T")[0],
});

const isSubmitting = ref(false);
const isLoadingTxns = ref(false);
const searchQuery = ref("");
const linkableTransactions = ref([]);
const selectedTransactionIds = ref([]);
const sortDirection = ref("asc"); // "asc" for oldest-first, "desc" for newest-first

// Computed
const isEditMode = computed(() => !!props.asset);

const totalSelectedAmount = computed(() => {
  return selectedTransactionIds.value.reduce((total, txnId) => {
    const txn = linkableTransactions.value.find((t) => t.id === txnId);
    return total + (txn ? parseFloat(txn.amount || 0) : 0);
  }, 0);
});

const isFormValid = computed(() => {
  if (isEditMode.value) {
    return (
      form.value.asset_name &&
      form.value.asset_group_id &&
      form.value.acquisition_date
    );
  }
  return (
    form.value.asset_name &&
    form.value.asset_group_id &&
    form.value.acquisition_date &&
    selectedTransactionIds.value.length > 0 &&
    props.companyId
  );
});

const filteredTransactions = computed(() => {
  let result = linkableTransactions.value;

  // Filter by search query
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase();
    result = result.filter(
      (txn) =>
        (txn.description || "").toLowerCase().includes(q) ||
        (txn.mark_name || "").toLowerCase().includes(q) ||
        (txn.internal_report || "").toLowerCase().includes(q),
    );
  }

  // Sort by date based on sortDirection
  return result.slice().sort((a, b) => {
    const dateA = new Date(a.txn_date).getTime();
    const dateB = new Date(b.txn_date).getTime();
    return sortDirection.value === "asc" ? dateA - dateB : dateB - dateA;
  });
});

const toggleSortDirection = () => {
  sortDirection.value = sortDirection.value === "asc" ? "desc" : "asc";
};

const groupedAssetGroups = computed(() => {
  const grouped = { Tangible: [], Intangible: [], Building: [] };
  props.assetGroups.forEach((group) => {
    if (grouped[group.asset_type]) {
      grouped[group.asset_type].push(group);
    }
  });
  Object.keys(grouped).forEach((type) => {
    grouped[type].sort((a, b) => a.group_number - b.group_number);
  });
  return grouped;
});

const isSelected = (txnId) => {
  return selectedTransactionIds.value.includes(txnId);
};

const getAssetTypeLabel = (type) => {
  const labels = {
    Tangible: "Harta Berwujud",
    Intangible: "Harta Tidak Berwujud",
    Building: "Bangunan",
  };
  return labels[type] || type;
};

// Data fetching
const fetchLinkableTransactions = async () => {
  if (!props.companyId) return;
  isLoadingTxns.value = true;
  try {
    const params = { company_id: props.companyId };
    if (isEditMode.value) {
      params.current_asset_id = props.asset.asset_id;
    }
    const response = await api.get("/reports/pending-amortization", { params });
    linkableTransactions.value = response.data.transactions || [];

    // Auto-select transactions that are currently linked to this asset if in edit mode
    if (isEditMode.value) {
      const existingIds = linkableTransactions.value
        .filter((t) => t.amortization_asset_id === props.asset.asset_id)
        .map((t) => t.id);

      // Merge unique IDs
      const allSelected = new Set([
        ...selectedTransactionIds.value,
        ...existingIds,
      ]);
      selectedTransactionIds.value = Array.from(allSelected);
    }
    // Remove any selected IDs that no longer exist
    selectedTransactionIds.value = selectedTransactionIds.value.filter((id) =>
      linkableTransactions.value.some((t) => t.id === id),
    );
  } catch (error) {
    console.error("Failed to fetch linkable transactions:", error);
    linkableTransactions.value = [];
  } finally {
    isLoadingTxns.value = false;
  }
};

// Auto-fill defaults when modal opens
watch(
  () => props.isOpen,
  async (newVal) => {
    if (newVal) {
      if (isEditMode.value) {
        form.value = {
          asset_name: props.asset.asset_name || "",
          asset_group_id: props.asset.asset_group_id || "",
          acquisition_date:
            props.asset.acquisition_date ||
            new Date().toISOString().split("T")[0],
        };
        selectedTransactionIds.value = [];
        searchQuery.value = "";
        await fetchLinkableTransactions();
      } else {
        // Reset form
        form.value = {
          asset_name: "",
          asset_group_id: "",
          acquisition_date: new Date().toISOString().split("T")[0],
        };
        selectedTransactionIds.value = [];
        searchQuery.value = "";
        // Load linkable transactions
        await fetchLinkableTransactions();
      }
    }
  },
);

const close = () => {
  if (!isSubmitting.value) {
    emit("close");
  }
};

const formatCurrency = (amount) => {
  if (amount === null || amount === undefined) return "Rp 0";
  return new Intl.NumberFormat("id-ID", {
    style: "currency",
    currency: "IDR",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
};

const handleSubmit = async () => {
  if (!isFormValid.value) return;

  isSubmitting.value = true;
  try {
    const payload = {
      company_id: props.companyId,
      asset_name: form.value.asset_name,
      asset_group_id: form.value.asset_group_id,
      acquisition_date: form.value.acquisition_date,
      transaction_ids: selectedTransactionIds.value,
    };
    if (isEditMode.value) {
      payload.asset_id = props.asset.asset_id;
    }

    emit("save", payload, isEditMode.value);
  } catch (error) {
    console.error("Submission failed", error);
  } finally {
    isSubmitting.value = false;
  }
};
</script>
