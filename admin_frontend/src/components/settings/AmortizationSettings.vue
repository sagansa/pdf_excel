<template>
  <div class="space-y-6">
    <!-- Header -->
    <SectionCard body-class="p-6">
      <h2 class="text-2xl font-bold" style="color: var(--color-text)">Amortization Settings</h2>
      <p class="text-sm mt-1" style="color: var(--color-text-muted)">
        Pengaturan global Coretax: kelompok aset dan mapping akun akumulasi.
      </p>
    </SectionCard>

    <!-- Info Cards -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div class="info-card info-card--blue">
        <div class="flex items-center gap-2 mb-2">
          <i class="bi bi-building text-blue-500"></i>
          <h3 class="font-semibold" style="color: var(--color-text)">Harta Berwujud</h3>
        </div>
        <p class="text-xs" style="color: var(--color-text-muted)">
          Mesin, peralatan, kendaraan, furniture, dan aset fisik lainnya.
        </p>
      </div>
      <div class="info-card info-card--purple">
        <div class="flex items-center gap-2 mb-2">
          <i class="bi bi-cloud text-purple-500"></i>
          <h3 class="font-semibold" style="color: var(--color-text)">Harta Tidak Berwujud</h3>
        </div>
        <p class="text-xs" style="color: var(--color-text-muted)">
          Hak paten, lisensi, goodwill, software, dan aset non-fisik.
        </p>
      </div>
      <div class="info-card info-card--orange">
        <div class="flex items-center gap-2 mb-2">
          <i class="bi bi-house-door text-orange-500"></i>
          <h3 class="font-semibold" style="color: var(--color-text)">Bangunan</h3>
        </div>
        <p class="text-xs" style="color: var(--color-text-muted)">
          Bangunan permanen dan non-permanen.
        </p>
      </div>
    </div>

    <!-- Kelompok Aset & Tarif -->
    <SectionCard body-class="p-0 overflow-hidden">
      <template #header>
        <div class="flex items-center justify-between w-full">
          <div>
            <h3 class="section-card__title">Kelompok Aset & Tarif</h3>
            <p class="section-card__subtitle">Standar tarif global yang dipakai di seluruh perusahaan.</p>
          </div>
          <button @click="openAddGroupModal" class="btn-primary flex items-center gap-2">
            <i class="bi bi-plus-lg"></i>
            Tambah Kelompok
          </button>
        </div>
      </template>

      <div class="p-4 md:p-6 space-y-6">
        <div
          v-for="(typeGroups, assetType) in groupedGroups"
          :key="assetType"
          class="asset-type-group"
        >
          <div class="asset-type-header">
            <h4 class="font-semibold">{{ getAssetTypeLabel(assetType) }}</h4>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead class="bg-surface-muted border-b" style="border-color: var(--color-border)">
                <tr>
                  <th class="px-4 py-2 text-left font-medium uppercase tracking-wider" style="color: var(--color-text-muted); font-size: 10px;">Kelompok</th>
                  <th class="px-4 py-2 text-left font-medium uppercase tracking-wider" style="color: var(--color-text-muted); font-size: 10px;">Masa Manfaat</th>
                  <th class="px-4 py-2 text-center font-medium uppercase tracking-wider" style="color: var(--color-text-muted); font-size: 10px;">Tarif (100%)</th>
                  <th class="px-4 py-2 text-center font-medium uppercase tracking-wider" style="color: var(--color-text-muted); font-size: 10px;">Tarif (50%)</th>
                  <th class="px-4 py-2 text-center font-medium uppercase tracking-wider" style="color: var(--color-text-muted); font-size: 10px;">Aksi</th>
                </tr>
              </thead>
              <tbody class="divide-y" style="border-color: var(--color-border)">
                <tr v-for="group in typeGroups" :key="group.id" class="hover:bg-surface-muted transition-colors">
                  <td class="px-4 py-3">
                    <div class="font-medium" style="color: var(--color-text)">{{ group.group_name }}</div>
                    <div class="text-xs" style="color: var(--color-text-muted)">Kelompok {{ group.group_number }}</div>
                  </td>
                  <td class="px-4 py-3" style="color: var(--color-text-muted)">{{ group.useful_life_years }} tahun</td>
                  <td class="px-4 py-3 text-center">
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                      {{ group.tarif_rate }}%
                    </span>
                  </td>
                  <td class="px-4 py-3 text-center">
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-500 border border-amber-500/20">
                      {{ group.tarif_half_rate }}%
                    </span>
                  </td>
                  <td class="px-4 py-3 text-center">
                    <button
                      @click="editGroup(group)"
                      class="p-1.5 rounded-lg hover:bg-surface-strong transition-colors"
                      style="color: var(--color-text-muted)"
                      title="Edit"
                    >
                      <i class="bi bi-pencil-square"></i>
                    </button>
                  </td>
                </tr>
                <tr v-if="typeGroups.length === 0">
                  <td colspan="5" class="px-4 py-8 text-center text-sm italic" style="color: var(--color-text-muted)">
                    Tidak ada data kelompok untuk tipe ini.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </SectionCard>

    <!-- Mapping COA -->
    <SectionCard>
      <template #header>
        <div class="w-full">
          <h3 class="section-card__title">Mapping COA Akumulasi Penyusutan</h3>
          <p class="section-card__subtitle">Dipakai untuk klasifikasi akumulasi penyusutan/amortisasi di Balance Sheet.</p>
        </div>
      </template>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4 pt-2">
        <div class="space-y-1.5">
          <label class="block text-xs font-bold uppercase tracking-wider" style="color: var(--color-text-muted)">
            Building (Bangunan) <span class="ml-1 text-[10px] font-normal" style="color: var(--color-primary)">- default 1524</span>
          </label>
          <SelectInput
            v-model="settings.accumulated_depreciation_coa_codes.Building"
            :options="availableAssetCoa"
            label-key="display"
            value-key="code"
            placeholder="Pilih COA..."
            @change="saveSettings"
          />
        </div>

        <div class="space-y-1.5">
          <label class="block text-xs font-bold uppercase tracking-wider" style="color: var(--color-text-muted)">
            Tangible (Harta Berwujud) <span class="ml-1 text-[10px] font-normal" style="color: var(--color-primary)">- default 1530</span>
          </label>
          <SelectInput
            v-model="settings.accumulated_depreciation_coa_codes.Tangible"
            :options="availableAssetCoa"
            label-key="display"
            value-key="code"
            placeholder="Pilih COA..."
            @change="saveSettings"
          />
        </div>

        <div class="space-y-1.5">
          <label class="block text-xs font-bold uppercase tracking-wider" style="color: var(--color-text-muted)">
            LandRights (Hak Guna) <span class="ml-1 text-[10px] font-normal" style="color: var(--color-primary)">- default 1534</span>
          </label>
          <SelectInput
            v-model="settings.accumulated_depreciation_coa_codes.LandRights"
            :options="availableAssetCoa"
            label-key="display"
            value-key="code"
            placeholder="Pilih COA..."
            @change="saveSettings"
          />
        </div>

        <div class="space-y-1.5">
          <label class="block text-xs font-bold uppercase tracking-wider" style="color: var(--color-text-muted)">
            Intangible (Tidak Berwujud) <span class="ml-1 text-[10px] font-normal" style="color: var(--color-primary)">- default 1601</span>
          </label>
          <SelectInput
            v-model="settings.accumulated_depreciation_coa_codes.Intangible"
            :options="availableAssetCoa"
            label-key="display"
            value-key="code"
            placeholder="Pilih COA..."
            @change="saveSettings"
          />
        </div>
      </div>
    </SectionCard>

    <!-- Modal Tambah/Edit -->
    <div
      v-if="showGroupModal"
      class="fixed inset-0 bg-black/60 backdrop-blur-sm z-[1000] flex items-center justify-center p-4"
    >
      <div class="modal-content-shell max-w-lg w-full overflow-hidden flex flex-col shadow-2xl">
        <div class="modal-header-shell flex items-center justify-between px-6 py-4 border-b" style="border-color: var(--color-border)">
          <h3 class="text-lg font-bold" style="color: var(--color-text)">{{ editingGroup ? "Edit" : "Tambah" }} Kelompok Aset</h3>
          <button @click="closeGroupModal" class="p-1 px-2 rounded-lg hover:bg-surface-muted transition-colors" style="color: var(--color-text-muted)">
            <i class="bi bi-x-lg"></i>
          </button>
        </div>

        <div class="p-6 space-y-4 overflow-y-auto">
          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-1.5">
              <label class="block text-xs font-bold uppercase tracking-wider" style="color: var(--color-text-muted)">
                Jenis Aset <span class="text-red-500">*</span>
              </label>
              <SelectInput
                v-model="groupForm.asset_type"
                :options="assetTypeOptions"
                placeholder="Pilih Jenis..."
              />
            </div>
            <div class="space-y-1.5">
              <label class="block text-xs font-bold uppercase tracking-wider" style="color: var(--color-text-muted)">
                Nomor Kelompok <span class="text-red-500">*</span>
              </label>
              <TextInput
                v-model.number="groupForm.group_number"
                type="number"
                min="1"
                placeholder="1, 2, 3..."
              />
            </div>
          </div>

          <div class="space-y-1.5">
            <label class="block text-xs font-bold uppercase tracking-wider" style="color: var(--color-text-muted)">
              Nama Kelompok <span class="text-red-500">*</span>
            </label>
            <TextInput
              v-model="groupForm.group_name"
              placeholder="Contoh: Kelompok 1 - Perabot Kantor"
            />
          </div>

          <div class="grid grid-cols-3 gap-4">
            <div class="space-y-1.5">
              <label class="block text-xs font-bold uppercase tracking-wider" style="color: var(--color-text-muted)">
                Masa Manfaat (th)
              </label>
              <TextInput
                v-model.number="groupForm.useful_life_years"
                type="number"
                min="1"
                placeholder="4"
              />
            </div>
            <div class="space-y-1.5">
              <label class="block text-xs font-bold uppercase tracking-wider" style="color: var(--color-text-muted)">
                Tarif 100% (%)
              </label>
              <TextInput
                v-model="groupForm.tarif_rate"
                type="text"
                placeholder="25"
              />
            </div>
            <div class="space-y-1.5">
              <label class="block text-xs font-bold uppercase tracking-wider" style="color: var(--color-text-muted)">
                Tarif 50% (%)
              </label>
              <TextInput
                v-model="groupForm.tarif_half_rate"
                type="text"
                placeholder="12.5"
              />
            </div>
          </div>

          <div
            v-if="saveError"
            class="p-3 rounded-xl flex items-start gap-3 border"
            style="background: rgba(var(--color-danger-rgb), 0.05); border-color: rgba(var(--color-danger-rgb), 0.2); color: var(--color-danger)"
          >
            <i class="bi bi-exclamation-circle mt-0.5"></i>
            <div class="text-xs">
              <p class="font-bold">Gagal Menyimpan</p>
              <p>{{ saveError }}</p>
            </div>
          </div>
        </div>

        <div class="px-6 py-4 border-t flex items-center justify-end gap-3 bg-surface-muted" style="border-color: var(--color-border)">
          <button
            @click="closeGroupModal"
            class="btn-secondary"
          >
            Batal
          </button>
          <button
            @click="saveGroup"
            :disabled="!isGroupFormValid || isSavingGroup"
            class="btn-primary min-w-[100px] flex items-center justify-center gap-2"
          >
            <i class="bi bi-check-lg" v-if="!isSavingGroup"></i>
            <i class="bi bi-arrow-repeat animate-spin" v-else></i>
            {{ editingGroup ? 'Update' : 'Simpan' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useAmortizationStore } from "../../stores/amortization";
import SectionCard from "../ui/SectionCard.vue";
import TextInput from "../ui/TextInput.vue";
import SelectInput from "../ui/SelectInput.vue";

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

const assetTypeOptions = [
  { value: "Tangible", label: "Harta Berwujud" },
  { value: "Intangible", label: "Harta Tidak Berwujud" },
  { value: "Building", label: "Bangunan" },
];

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
    availableAssetCoa.value = coaStore.coaList
      .filter((c) => c.category === "ASSET" && c.is_active !== false)
      .map(c => ({
        ...c,
        display: `${c.code} - ${c.name}`
      }));
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
.info-card {
  @apply rounded-xl border p-4 transition-all duration-200 border-opacity-20;
  background: var(--color-surface);
  border-color: var(--color-border);
}

.info-card--blue { background: rgba(59, 130, 246, 0.05); border-color: rgba(59, 130, 246, 0.2); }
.info-card--purple { background: rgba(168, 85, 247, 0.05); border-color: rgba(168, 85, 247, 0.2); }
.info-card--orange { background: rgba(249, 115, 22, 0.05); border-color: rgba(249, 115, 22, 0.2); }

.asset-type-group {
  @apply border rounded-xl overflow-hidden;
  border-color: var(--color-border);
}

.asset-type-header {
  @apply px-4 py-2 border-b;
  background: var(--color-surface-muted);
  border-color: var(--color-border);
  color: var(--color-text);
}

.modal-content-shell {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-2xl, 20px);
}
</style>
