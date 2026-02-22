<template>
  <div class="space-y-6">
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <h2 class="text-2xl font-bold text-gray-900">Amortization Settings</h2>
      <p class="text-sm text-gray-500 mt-1">
        Pengaturan global Coretax: kelompok aset dan mapping akun akumulasi.
      </p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div class="flex items-center gap-2 mb-2">
          <i class="bi bi-building text-blue-600"></i>
          <h3 class="font-semibold text-blue-900">Harta Berwujud</h3>
        </div>
        <p class="text-xs text-blue-700">
          Mesin, peralatan, kendaraan, furniture, dan aset fisik lainnya.
        </p>
      </div>
      <div class="bg-purple-50 border border-purple-200 rounded-lg p-4">
        <div class="flex items-center gap-2 mb-2">
          <i class="bi bi-cloud text-purple-600"></i>
          <h3 class="font-semibold text-purple-900">Harta Tidak Berwujud</h3>
        </div>
        <p class="text-xs text-purple-700">
          Hak paten, lisensi, goodwill, software, dan aset non-fisik.
        </p>
      </div>
      <div class="bg-orange-50 border border-orange-200 rounded-lg p-4">
        <div class="flex items-center gap-2 mb-2">
          <i class="bi bi-house-door text-orange-600"></i>
          <h3 class="font-semibold text-orange-900">Bangunan</h3>
        </div>
        <p class="text-xs text-orange-700">
          Bangunan permanen dan non-permanen.
        </p>
      </div>
    </div>

    <div class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      <div class="bg-slate-50 border-b border-slate-200 px-6 py-4 flex items-center justify-between">
        <div>
          <h3 class="text-lg font-bold text-slate-800">Kelompok Aset & Tarif</h3>
          <p class="text-xs text-slate-500 mt-0.5">
            Standar tarif global yang dipakai di seluruh perusahaan.
          </p>
        </div>
        <button
          @click="openAddGroupModal"
          class="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg font-medium text-sm transition-all flex items-center gap-2"
        >
          <i class="bi bi-plus-lg"></i>
          Tambah Kelompok
        </button>
      </div>

      <div class="p-6">
        <div class="space-y-6">
          <div
            v-for="(typeGroups, assetType) in groupedGroups"
            :key="assetType"
            class="border border-slate-200 rounded-lg overflow-hidden"
          >
            <div class="bg-slate-100 px-4 py-2 border-b border-slate-200">
              <h4 class="font-semibold text-slate-700">{{ getAssetTypeLabel(assetType) }}</h4>
            </div>
            <table class="w-full">
              <thead class="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th class="px-4 py-2 text-left text-xs font-medium text-slate-500 uppercase">Kelompok</th>
                  <th class="px-4 py-2 text-left text-xs font-medium text-slate-500 uppercase">Masa Manfaat</th>
                  <th class="px-4 py-2 text-center text-xs font-medium text-slate-500 uppercase">Tarif (100%)</th>
                  <th class="px-4 py-2 text-center text-xs font-medium text-slate-500 uppercase">Tarif (50%)</th>
                  <th class="px-4 py-2 text-center text-xs font-medium text-slate-500 uppercase">Aksi</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100">
                <tr v-for="group in typeGroups" :key="group.id" class="hover:bg-slate-50">
                  <td class="px-4 py-3">
                    <div class="font-medium text-slate-900">{{ group.group_name }}</div>
                    <div class="text-xs text-slate-500">Kelompok {{ group.group_number }}</div>
                  </td>
                  <td class="px-4 py-3 text-sm text-slate-600">{{ group.useful_life_years }} tahun</td>
                  <td class="px-4 py-3 text-center">
                    <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                      {{ group.tarif_rate }}%
                    </span>
                  </td>
                  <td class="px-4 py-3 text-center">
                    <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                      {{ group.tarif_half_rate }}%
                    </span>
                  </td>
                  <td class="px-4 py-3 text-center">
                    <button
                      @click="editGroup(group)"
                      class="text-slate-400 hover:text-indigo-600 transition-colors"
                      title="Edit"
                    >
                      <i class="bi bi-pencil-square"></i>
                    </button>
                  </td>
                </tr>
                <tr v-if="typeGroups.length === 0">
                  <td colspan="5" class="px-4 py-6 text-center text-sm text-slate-400">
                    Tidak ada data kelompok untuk tipe ini.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <div class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      <div class="bg-purple-50 border-b border-purple-100 px-6 py-4">
        <h3 class="text-lg font-bold text-purple-900">Mapping COA Akumulasi Penyusutan</h3>
        <p class="text-xs text-purple-600 mt-0.5">
          Dipakai untuk klasifikasi akumulasi penyusutan/amortisasi di Balance Sheet.
        </p>
      </div>

      <div class="p-6 space-y-4">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-semibold text-slate-700 mb-2">
              Building (Bangunan) <span class="text-xs text-purple-600">- default 1524</span>
            </label>
            <select
              v-model="settings.accumulated_depreciation_coa_codes.Building"
              class="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition-all text-sm"
              @change="saveSettings"
            >
              <option value="">Pilih COA...</option>
              <option v-for="coa in availableAssetCoa" :key="coa.id" :value="coa.code">
                {{ coa.code }} - {{ coa.name }}
              </option>
            </select>
          </div>

          <div>
            <label class="block text-sm font-semibold text-slate-700 mb-2">
              Tangible (Harta Berwujud) <span class="text-xs text-purple-600">- default 1530</span>
            </label>
            <select
              v-model="settings.accumulated_depreciation_coa_codes.Tangible"
              class="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition-all text-sm"
              @change="saveSettings"
            >
              <option value="">Pilih COA...</option>
              <option v-for="coa in availableAssetCoa" :key="coa.id" :value="coa.code">
                {{ coa.code }} - {{ coa.name }}
              </option>
            </select>
          </div>

          <div>
            <label class="block text-sm font-semibold text-slate-700 mb-2">
              LandRights (Hak Guna) <span class="text-xs text-purple-600">- default 1534</span>
            </label>
            <select
              v-model="settings.accumulated_depreciation_coa_codes.LandRights"
              class="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition-all text-sm"
              @change="saveSettings"
            >
              <option value="">Pilih COA...</option>
              <option v-for="coa in availableAssetCoa" :key="coa.id" :value="coa.code">
                {{ coa.code }} - {{ coa.name }}
              </option>
            </select>
          </div>

          <div>
            <label class="block text-sm font-semibold text-slate-700 mb-2">
              Intangible (Tidak Berwujud) <span class="text-xs text-purple-600">- default 1601</span>
            </label>
            <select
              v-model="settings.accumulated_depreciation_coa_codes.Intangible"
              class="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition-all text-sm"
              @change="saveSettings"
            >
              <option value="">Pilih COA...</option>
              <option v-for="coa in availableAssetCoa" :key="coa.id" :value="coa.code">
                {{ coa.code }} - {{ coa.name }}
              </option>
            </select>
          </div>
        </div>
      </div>
    </div>

    <div
      v-if="showGroupModal"
      class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
    >
      <div class="bg-white rounded-lg shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
        <div class="bg-slate-50 border-b border-slate-200 px-6 py-4 flex items-center justify-between">
          <h3 class="text-lg font-bold text-slate-800">{{ editingGroup ? "Edit" : "Tambah" }} Kelompok Aset</h3>
          <button @click="closeGroupModal" class="text-gray-400 hover:text-gray-600">
            <i class="bi bi-x-lg"></i>
          </button>
        </div>

        <div class="p-6 space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-semibold text-slate-700 mb-1">
                Jenis Aset <span class="text-red-500">*</span>
              </label>
              <select
                v-model="groupForm.asset_type"
                class="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all text-sm"
              >
                <option value="Tangible">Harta Berwujud</option>
                <option value="Intangible">Harta Tidak Berwujud</option>
                <option value="Building">Bangunan</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-semibold text-slate-700 mb-1">
                Nomor Kelompok <span class="text-red-500">*</span>
              </label>
              <input
                v-model.number="groupForm.group_number"
                type="number"
                min="1"
                class="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all text-sm"
                placeholder="1, 2, 3, 4..."
              />
            </div>
          </div>

          <div>
            <label class="block text-sm font-semibold text-slate-700 mb-1">
              Nama Kelompok <span class="text-red-500">*</span>
            </label>
            <input
              v-model="groupForm.group_name"
              type="text"
              class="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all text-sm"
              placeholder="Kelompok 1 - Harta Berwujud"
            />
          </div>

          <div class="grid grid-cols-3 gap-4">
            <div>
              <label class="block text-sm font-semibold text-slate-700 mb-1">
                Masa Manfaat (th) <span class="text-red-500">*</span>
              </label>
              <input
                v-model.number="groupForm.useful_life_years"
                type="number"
                min="1"
                class="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all text-sm"
                placeholder="4"
              />
            </div>
            <div>
              <label class="block text-sm font-semibold text-slate-700 mb-1">
                Tarif 100% (%) <span class="text-red-500">*</span>
              </label>
              <input
                v-model="groupForm.tarif_rate"
                type="text"
                class="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all text-sm"
                placeholder="25"
              />
            </div>
            <div>
              <label class="block text-sm font-semibold text-slate-700 mb-1">
                Tarif 50% (%) <span class="text-red-500">*</span>
              </label>
              <input
                v-model="groupForm.tarif_half_rate"
                type="text"
                class="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all text-sm"
                placeholder="12.5"
              />
            </div>
          </div>

          <div
            v-if="saveError"
            class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-start gap-3"
          >
            <i class="bi bi-exclamation-circle mt-0.5"></i>
            <div class="text-xs">
              <p class="font-bold">Gagal Menyimpan</p>
              <p>{{ saveError }}</p>
            </div>
          </div>
        </div>

        <div class="bg-slate-50 border-t border-slate-200 px-6 py-4 flex items-center justify-end gap-3">
          <button
            @click="closeGroupModal"
            class="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg font-medium text-sm transition-all"
          >
            Batal
          </button>
          <button
            @click="saveGroup"
            :disabled="!isGroupFormValid || isSavingGroup"
            class="bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white px-6 py-2 rounded-lg font-medium text-sm transition-all flex items-center gap-2"
          >
            <i class="bi bi-check-lg" v-if="!isSavingGroup"></i>
            <i class="bi bi-arrow-repeat spin" v-else></i>
            Simpan
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useAmortizationStore } from "../../stores/amortization";

const props = defineProps({
  companyId: {
    type: String,
    default: null,
  },
});

const store = useAmortizationStore();

const assetGroups = ref([]);
const showGroupModal = ref(false);
const editingGroup = ref(null);
const isSavingGroup = ref(false);
const saveError = ref(null);
const availableAssetCoa = ref([]);

const settings = ref({
  accumulated_depreciation_coa_codes: {
    Building: "1524",
    Tangible: "1530",
    LandRights: "1534",
    Intangible: "1601",
  },
  default_amortization_rate: 20.0,
});

const groupForm = ref({
  asset_type: "Tangible",
  group_number: 1,
  group_name: "",
  useful_life_years: 4,
  tarif_rate: 25.0,
  tarif_half_rate: 12.5,
});

const groupedGroups = computed(() => {
  const grouped = { Tangible: [], Intangible: [], Building: [] };
  assetGroups.value.forEach((group) => {
    if (grouped[group.asset_type]) grouped[group.asset_type].push(group);
  });
  Object.keys(grouped).forEach((type) => {
    grouped[type].sort((a, b) => a.group_number - b.group_number);
  });
  return grouped;
});

const isGroupFormValid = computed(() => {
  return (
    groupForm.value.group_name &&
    groupForm.value.group_number > 0 &&
    groupForm.value.useful_life_years > 0 &&
    String(groupForm.value.tarif_rate).length > 0
  );
});

const getAssetTypeLabel = (type) => {
  const labels = {
    Tangible: "Harta Berwujud",
    Intangible: "Harta Tidak Berwujud",
    Building: "Bangunan",
  };
  return labels[type] || type;
};

const fetchAssetGroups = async () => {
  const groups = await store.fetchAssetGroups(props.companyId || null);
  if (props.companyId) {
    assetGroups.value = groups.filter(
      (g) => !g.company_id || g.company_id === props.companyId,
    );
    return;
  }

  const globalGroups = groups.filter((g) => !g.company_id);
  assetGroups.value = globalGroups.length > 0 ? globalGroups : groups;
};

const fetchSettings = async () => {
  try {
    const response = await store.fetchAmortizationSettings(props.companyId || null);
    settings.value = {
      ...settings.value,
      ...response,
      accumulated_depreciation_coa_codes: {
        ...settings.value.accumulated_depreciation_coa_codes,
        ...(response.accumulated_depreciation_coa_codes || {}),
      },
    };
  } catch (error) {
    console.error("Failed to fetch amortization settings:", error);
  }
};

const fetchAvailableAssetCoa = async () => {
  try {
    const { useCoaStore } = await import("../../stores/coa");
    const coaStore = useCoaStore();
    await coaStore.fetchCoa();
    availableAssetCoa.value = coaStore.coaList.filter(
      (c) => c.category === "ASSET" && c.is_active !== false,
    );
  } catch (err) {
    console.error("Failed to fetch COA:", err);
  }
};

const fetchData = async () => {
  await Promise.all([fetchAssetGroups(), fetchSettings(), fetchAvailableAssetCoa()]);
};

const openAddGroupModal = () => {
  editingGroup.value = null;
  groupForm.value = {
    asset_type: "Tangible",
    group_number: 1,
    group_name: "",
    useful_life_years: 4,
    tarif_rate: 25.0,
    tarif_half_rate: 12.5,
  };
  showGroupModal.value = true;
};

const editGroup = (group) => {
  editingGroup.value = group;
  groupForm.value = { ...group };
  showGroupModal.value = true;
};

const closeGroupModal = () => {
  showGroupModal.value = false;
  editingGroup.value = null;
  saveError.value = null;
};

const saveGroup = async () => {
  if (!isGroupFormValid.value) return;

  isSavingGroup.value = true;
  saveError.value = null;
  try {
    const payload = {
      ...groupForm.value,
      company_id: props.companyId || null,
    };

    if (editingGroup.value) {
      await store.updateAssetGroup(editingGroup.value.id, payload);
    } else {
      await store.createAssetGroup(payload);
    }

    closeGroupModal();
    await fetchAssetGroups();
  } catch (err) {
    saveError.value = err.message || "Terjadi kesalahan saat menyimpan data.";
    console.error("Failed to save group:", err);
  } finally {
    isSavingGroup.value = false;
  }
};

const saveSettings = async () => {
  try {
    await store.saveAmortizationSettings({
      company_id: props.companyId || null,
      accumulated_depreciation_coa_codes: settings.value.accumulated_depreciation_coa_codes,
      default_amortization_rate: settings.value.default_amortization_rate,
    });
  } catch (err) {
    console.error("Failed to save amortization settings:", err);
  }
};

onMounted(fetchData);
</script>

<style scoped>
.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
