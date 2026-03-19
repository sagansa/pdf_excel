<template>
  <BaseModal
    :isOpen="isOpen"
    size="2xl"
    @close="close"
  >
    <template #title>
      {{
        isEditMode
          ? "Edit Aset Amortisasi"
          : "Daftarkan Aset Amortisasi Baru"
      }}
    </template>

    <form @submit.prevent="handleSubmit" class="space-y-5 px-6">
      <!-- Asset Information -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div class="md:col-span-2">
          <FormField label="Nama Aset" :required="true">
            <TextInput
              v-model="form.asset_name"
              required
              placeholder="Misal: Pembelian Software ERP 2025"
            />
          </FormField>
        </div>

        <div>
          <FormField label="Kelompok Aset" :required="true">
            <SelectInput
              v-model="form.asset_group_id"
              required
              placeholder="Pilih Kelompok Aset..."
              :options="groupedAssetGroupOptions"
              label-key="label"
              value-key="id"
            />
          </FormField>
        </div>

        <div>
          <FormField label="Tanggal Mulai Amortisasi" :required="true" hint="Bulan amortisasi dimulai.">
            <TextInput
              v-model="form.acquisition_date"
              required
              type="date"
            />
          </FormField>
        </div>
      </div>

      <!-- Link Transactions Section -->
      <div class="space-y-3 px-2">
        <div class="flex items-center justify-between">
          <label class="block text-xs font-bold text-theme">
            <i class="bi bi-link-45deg mr-1"></i>
            Link Transaksi Pembayaran
          </label>
          <span
            class="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20"
          >
            {{ selectedTransactionIds.length }} selected
          </span>
        </div>

        <div class="border border-border rounded-2xl overflow-hidden">
          <div class="bg-surface-muted px-4 py-2 border-b border-border">
            <div class="flex items-center gap-2">
              <TextInput
                v-model="searchQuery"
                placeholder="Cari transaksi..."
                class="flex-1"
              />
              <button
                type="button"
                @click="toggleSortDirection"
                class="text-muted hover:text-theme px-2"
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
                class="text-muted hover:text-theme px-2"
                title="Refresh"
              >
                <i class="bi bi-arrow-clockwise"></i>
              </button>
            </div>
          </div>

          <div class="max-h-48 overflow-y-auto">
            <div v-if="isLoadingTxns" class="px-4 py-6 text-center">
              <span
                class="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin inline-block"
              ></span>
              <p class="text-xs text-muted mt-2">Memuat transaksi...</p>
            </div>

            <div
              v-else-if="filteredTransactions.length === 0"
              class="px-4 py-8 text-center text-muted text-xs"
            >
              <i class="bi bi-inbox text-2xl mb-2 block"></i>
              Tidak ada transaksi aset yang belum terdaftar
            </div>

            <div
              v-else
              v-for="txn in filteredTransactions"
              :key="txn.id"
              class="flex items-center px-4 py-3 hover:bg-surface-muted border-b border-border last:border-0"
              :class="{ 'bg-surface-muted': isSelected(txn.id) }"
            >
              <input
                :id="'asset-txn-' + txn.id"
                v-model="selectedTransactionIds"
                :value="txn.id"
                type="checkbox"
                class="h-4 w-4 text-primary focus:ring-primary border-border rounded"
              />
              <label
                :for="'asset-txn-' + txn.id"
                class="ml-3 flex-1 cursor-pointer"
              >
                <div class="flex items-center justify-between">
                  <div>
                    <div class="text-xs font-semibold text-theme">
                      {{ txn.description }}
                    </div>
                    <div class="text-[10px] text-muted">
                      {{ txn.txn_date }} |
                      {{ txn.mark_name || txn.internal_report || "-" }}
                    </div>
                  </div>
                  <div class="text-right">
                    <div class="text-xs font-bold text-theme font-mono">
                      {{ formatCurrency(txn.amount) }}
                    </div>
                  </div>
                </div>
              </label>
            </div>
          </div>
        </div>
      </div>

      <div
        v-if="selectedTransactionIds.length > 0"
        class="rounded-2xl px-4 py-3 bg-primary/5 border border-primary/10"
      >
        <div
          class="text-[10px] font-bold uppercase mb-2 tracking-wider text-primary"
        >
          Ringkasan Aset
        </div>
        <div class="grid grid-cols-2 gap-3 text-xs">
          <div>
            <div class="text-muted text-[10px] uppercase">
              Jumlah Transaksi
            </div>
            <div class="font-semibold text-theme">
              {{ selectedTransactionIds.length }} transaksi
            </div>
          </div>
          <div>
            <div class="text-theme-muted text-[10px] uppercase font-bold tracking-tight">
              Total Nilai Perolehan
            </div>
            <div class="font-bold text-lg font-mono text-primary">
              {{ formatCurrency(totalSelectedAmount) }}
            </div>
          </div>
        </div>
      </div>
    </form>

    <template #footer>
      <button
        type="button"
        @click="close"
        class="btn-secondary px-5 py-2 text-xs font-semibold transition-colors"
        :disabled="isSubmitting"
      >
        Batal
      </button>
      <button
        type="submit"
        @click="handleSubmit"
        class="btn-primary px-5 py-2 text-xs font-semibold transition-colors inline-flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        :disabled="isSubmitting || !isFormValid"
      >
        <span
          v-if="isSubmitting"
          class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"
        ></span>
        <i v-else class="bi bi-check2-circle"></i>
        {{ isEditMode ? "Simpan Perubahan" : "Daftarkan Aset" }}
      </button>
    </template>
  </BaseModal>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import api from "../../../api/index";
import BaseModal from "../../ui/BaseModal.vue";
import FormField from "../../ui/FormField.vue";
import TextInput from "../../ui/TextInput.vue";
import SelectInput from "../../ui/SelectInput.vue";

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

const groupedAssetGroupOptions = computed(() => {
  const options = [];
  
  // Add grouped options by asset type
  const types = ['Tangible', 'Intangible', 'Building'];
  const typeLabels = {
    Tangible: '=== Harta Berwujud ===',
    Intangible: '=== Harta Tidak Berwujud ===',
    Building: '=== Bangunan ==='
  };
  
  types.forEach(type => {
    const groupsOfType = props.assetGroups
      .filter(g => g.asset_type === type)
      .sort((a, b) => a.group_number - b.group_number);
    
    if (groupsOfType.length > 0) {
      // Add type header as a disabled option
      options.push({
        id: '',
        label: typeLabels[type],
        disabled: true
      });
      
      // Add groups of this type
      groupsOfType.forEach(group => {
        options.push({
          ...group,
          label: `${group.group_name} (${group.useful_life_years} tahun / ${group.tarif_rate}%)`
        });
      });
    }
  });
  
  return options;
});

const isSelected = (txnId) => {
  return selectedTransactionIds.value.includes(txnId);
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
