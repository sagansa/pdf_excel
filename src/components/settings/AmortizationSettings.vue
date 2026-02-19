<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-2xl font-bold text-gray-900">
            Amortization Settings
          </h2>
          <p class="text-sm text-gray-500 mt-1">
            Kelola kelompok aset, tarif, dan aturan amortisasi sesuai ketentuan
            perpajakan
          </p>
        </div>
      </div>
    </div>

    <!-- Asset Types Info -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div class="flex items-center gap-2 mb-2">
          <i class="bi bi-building text-blue-600"></i>
          <h3 class="font-semibold text-blue-900">Harta Berwujud</h3>
        </div>
        <p class="text-xs text-blue-700">
          Mesin, peralatan, kendaraan, furniture, dan aset fisik lainnya
        </p>
      </div>
      <div class="bg-purple-50 border border-purple-200 rounded-lg p-4">
        <div class="flex items-center gap-2 mb-2">
          <i class="bi bi-cloud text-purple-600"></i>
          <h3 class="font-semibold text-purple-900">Harta Tidak Berwujud</h3>
        </div>
        <p class="text-xs text-purple-700">
          Hak paten, lisensi, goodwill, software, dan aset non-fisik
        </p>
      </div>
      <div class="bg-orange-50 border border-orange-200 rounded-lg p-4">
        <div class="flex items-center gap-2 mb-2">
          <i class="bi bi-house-door text-orange-600"></i>
          <h3 class="font-semibold text-orange-900">Bangunan</h3>
        </div>
        <p class="text-xs text-orange-700">
          Bangunan permanen dan non-permanen
        </p>
      </div>
    </div>

    <!-- Asset Groups Configuration -->
    <div
      class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden"
    >
      <div
        class="bg-slate-50 border-b border-slate-200 px-6 py-4 flex items-center justify-between"
      >
        <div>
          <h3 class="text-lg font-bold text-slate-800">
            Kelompok Aset & Tarif
          </h3>
          <p class="text-xs text-slate-500 mt-0.5">
            Pengaturan tarif amortisasi berdasarkan kelompok dan jenis aset
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
        <!-- Grouped by Asset Type -->
        <div class="space-y-6">
          <div
            v-for="(typeGroups, assetType) in groupedGroups"
            :key="assetType"
            class="border border-slate-200 rounded-lg overflow-hidden"
          >
            <div class="bg-slate-100 px-4 py-2 border-b border-slate-200">
              <h4 class="font-semibold text-slate-700">
                {{ getAssetTypeLabel(assetType) }}
              </h4>
            </div>
            <table class="w-full">
              <thead class="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th
                    class="px-4 py-2 text-left text-xs font-medium text-slate-500 uppercase"
                  >
                    Kelompok
                  </th>
                  <th
                    class="px-4 py-2 text-left text-xs font-medium text-slate-500 uppercase"
                  >
                    Masa Manfaat
                  </th>
                  <th
                    class="px-4 py-2 text-center text-xs font-medium text-slate-500 uppercase"
                  >
                    Tarif (100%)
                  </th>
                  <th
                    class="px-4 py-2 text-center text-xs font-medium text-slate-500 uppercase"
                  >
                    Tarif (50%)
                  </th>
                  <th
                    class="px-4 py-2 text-center text-xs font-medium text-slate-500 uppercase"
                  >
                    Aksi
                  </th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100">
                <tr
                  v-for="group in typeGroups"
                  :key="group.id"
                  class="hover:bg-slate-50"
                >
                  <td class="px-4 py-3">
                    <div class="font-medium text-slate-900">
                      {{ group.group_name }}
                    </div>
                    <div class="text-xs text-slate-500">
                      Kelompok {{ group.group_number }}
                    </div>
                  </td>
                  <td class="px-4 py-3 text-sm text-slate-600">
                    {{ group.useful_life_years }} tahun
                  </td>
                  <td class="px-4 py-3 text-center">
                    <span
                      class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800"
                    >
                      {{ group.tarif_rate }}%
                    </span>
                  </td>
                  <td class="px-4 py-3 text-center">
                    <span
                      class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800"
                    >
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
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- Amortization Detection Settings -->
    <div
      class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden"
    >
      <div class="bg-slate-50 border-b border-slate-200 px-6 py-4">
        <h3 class="text-lg font-bold text-slate-800">
          Deteksi Amortisasi Berbasis Mark
        </h3>
        <p class="text-xs text-slate-500 mt-0.5">
          Tentukan marks mana saja yang secara otomatis dianggap sebagai
          transaksi aset/amortisasi
        </p>
      </div>

      <div class="p-6 space-y-6">
        <div
          class="flex items-center justify-between p-4 bg-indigo-50 border border-indigo-100 rounded-lg"
        >
          <div>
            <h4 class="font-semibold text-indigo-900">Aktifkan Deteksi Mark</h4>
            <p class="text-xs text-indigo-700">
              Jika aktif, transaksi dengan mark terpilih akan muncul di laporan
              Amortisasi
            </p>
          </div>
          <label class="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              v-model="markSettings.use_mark_based_amortization"
              class="sr-only peer"
              @change="saveMarkSettings"
            />
            <div
              class="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-indigo-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"
            ></div>
          </label>
        </div>

        <div v-if="markSettings.use_mark_based_amortization" class="space-y-4">
          <div>
            <label class="block text-sm font-semibold text-slate-700 mb-2"
              >Pilih Mark yang Dianggap Amortisasi</label
            >
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              <div
                v-for="mark in availableMarks"
                :key="mark.id"
                class="flex items-center p-3 border rounded-lg transition-all cursor-pointer"
                :class="
                  markSettings.amortization_asset_marks.includes(
                    mark.personal_use,
                  )
                    ? 'bg-indigo-50 border-indigo-200'
                    : 'bg-white border-slate-200 hover:border-indigo-200'
                "
                @click="toggleMarkSelection(mark.personal_use)"
              >
                <input
                  type="checkbox"
                  :checked="
                    markSettings.amortization_asset_marks.includes(
                      mark.personal_use,
                    )
                  "
                  class="rounded text-indigo-600 mr-2 focus:ring-indigo-500"
                />
                <span class="text-sm font-medium text-slate-700">{{
                  mark.personal_use
                }}</span>
      </div>
    </div>

    <!-- Fiscal Correction COA Configuration -->
    <div
      class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden"
    >
      <div class="bg-orange-50 border-b border-orange-100 px-6 py-4">
        <h3 class="text-lg font-bold text-orange-900">
          Koreksi Fiskal Akhir Tahun
        </h3>
        <p class="text-xs text-orange-600 mt-0.5">
          Pilih COA untuk posting koreksi fiskal (selisih komersial vs fiskal)
        </p>
      </div>

      <div class="p-6 space-y-4">
        <div>
          <label class="block text-sm font-semibold text-slate-700 mb-2">
            Pilih COA Koreksi Fiskal
          </label>
          <select
            v-model="markSettings.fiscal_correction_coa_codes"
            multiple
            class="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all text-sm"
            @change="saveMarkSettings"
          >
            <option v-for="coa in availableCoa" :key="coa.id" :value="coa.code">
              {{ coa.code }} - {{ coa.name }}
            </option>
          </select>
          <p class="text-xs text-slate-500 mt-2">
            Pilih COA untuk koreksi fiskal akhir tahun.
            Kalkulasi otomatis akan ditambahkan ke laporan Income Statement.
          </p>
        </div>

        <div
          v-if="markSettings.fiscal_correction_coa_codes && markSettings.fiscal_correction_coa_codes.length > 0"
          class="bg-orange-50 border border-orange-200 rounded-lg p-4"
        >
          <div class="text-sm font-medium text-orange-900 mb-2">
            COA Terpilih:
          </div>
          <div class="space-y-1">
            <div
              v-for="code in markSettings.fiscal_correction_coa_codes"
              :key="code"
              class="flex items-center justify-between text-sm text-orange-700"
            >
              <span>{{ code }}</span>
            </div>
          </div>
        </div>

        <div
          class="bg-yellow-50 border border-yellow-200 rounded-lg p-4 flex gap-3"
        >
          <i class="bi bi-info-circle text-yellow-600 mt-0.5"></i>
          <div class="text-xs text-yellow-700">
            <p class="font-bold mb-1">Keterangan:</p>
            <p>
              Koreksi fiskal akan dihitung sebagai selisih antara amortisasi komersial
              dan fiskal (Pasal 9). Nilai ini akan ditambahkan ke beban dan
              dikenakan pajak sesuai tarif PPh Badan (default 22%).
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Amortization Expense COA Configuration -->
    <div
      class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden"
    >
      <div class="bg-slate-50 border-b border-slate-200 px-6 py-4">
        <h3 class="text-lg font-bold text-slate-800">
          COA Beban Amortisasi
        </h3>
        <p class="text-xs text-slate-500 mt-0.5">
          Tentukan akun COA mana di Income Statement yang akan menerima nilai
          amortisasi yang dihitung
        </p>
      </div>

      <div class="p-6 space-y-4">
        <div>
          <label class="block text-sm font-semibold text-slate-700 mb-2">
            Pilih COA Beban Amortisasi
          </label>
          <select
            v-model="markSettings.amortization_expense_coa_codes"
            multiple
            class="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all text-sm"
            @change="saveMarkSettings"
          >
            <option v-for="coa in availableCoa" :key="coa.id" :value="coa.code">
              {{ coa.code }} - {{ coa.name }}
            </option>
          </select>
          <p class="text-xs text-slate-500 mt-2">
            Pilih satu atau lebih COA untuk memposting nilai amortisasi.
            Nilai amortisasi akan di-posting ke COA pertama yang dipilih.
          </p>
        </div>

        <div
          v-if="markSettings.amortization_expense_coa_codes && markSettings.amortization_expense_coa_codes.length > 0"
          class="bg-indigo-50 border border-indigo-200 rounded-lg p-4"
        >
          <div class="text-sm font-medium text-indigo-900 mb-2">
            COA Terpilih:
          </div>
          <div class="space-y-1">
            <div
              v-for="code in markSettings.amortization_expense_coa_codes"
              :key="code"
              class="flex items-center justify-between text-sm text-indigo-700"
            >
              <span>{{ code }}</span>
              <span class="font-bold text-indigo-900">
                {{
                  code === markSettings.amortization_expense_coa_codes[0] ? 'Utama' : ''
                }}
              </span>
            </div>
          </div>
          <p class="text-xs text-indigo-600 mt-2">
            <i class="bi bi-info-circle mr-1"></i>
            Nilai amortisasi akan di-posting ke COA "Utama"
          </p>
        </div>
      </div>
    </div>
          </div>

          <div
            class="bg-blue-50 border border-blue-200 rounded-lg p-4 flex gap-3"
          >
            <i class="bi bi-lightbulb text-blue-600 mt-0.5"></i>
            <div class="text-xs text-blue-700">
              <p class="font-bold mb-1">Tips:</p>
              <p>
                Anda dapat memilih beberapa mark sekaligus. Perubahan akan
                disimpan secara otomatis.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Add/Edit Group Modal -->
    <div
      v-if="showGroupModal"
      class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
    >
      <div
        class="bg-white rounded-lg shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto"
      >
        <div
          class="bg-slate-50 border-b border-slate-200 px-6 py-4 flex items-center justify-between"
        >
          <h3 class="text-lg font-bold text-slate-800">
            {{ editingGroup ? "Edit" : "Tambah" }} Kelompok Aset
          </h3>
          <button
            @click="closeGroupModal"
            class="text-gray-400 hover:text-gray-600"
          >
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

          <!-- Error Message -->
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

          <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <h4 class="text-sm font-semibold text-yellow-800 mb-2">
              <i class="bi bi-info-circle mr-1"></i> Petunjuk Tarif
            </h4>
            <ul class="text-xs text-yellow-700 space-y-1">
              <li>• Tarif 100%: Digunakan untuk amortisasi tahun penuh</li>
              <li>
                • Tarif 50%: Digunakan untuk amortisasi tahun parsial (aset
                diperoleh pertengahan tahun)
              </li>
              <li>• Contoh: Kelompok 1 = 25% (100%), 12.5% (50%)</li>
            </ul>
          </div>
        </div>

        <div
          class="bg-slate-50 border-t border-slate-200 px-6 py-4 flex items-center justify-end gap-3"
        >
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

    <!-- Accumulated Depreciation COA Configuration -->
    <div
      class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden"
    >
      <div class="bg-purple-50 border-b border-purple-100 px-6 py-4">
        <h3 class="text-lg font-bold text-purple-900">
          Mapping COA Akumulasi Penyusutan
        </h3>
        <p class="text-xs text-purple-600 mt-0.5">
          Tentukan akun akumulasi penyusutan/amortisasi untuk setiap tipe aset
        </p>
      </div>

      <div class="p-6 space-y-4">
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-4">
          <!-- Building -->
          <div>
            <label class="block text-sm font-semibold text-slate-700 mb-2">
              Building (Bangunan) <span class="text-xs text-purple-600">- 1524</span>
            </label>
            <select
              v-model="markSettings.accumulated_depreciation_coa_codes.Building"
              class="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition-all text-sm"
              @change="saveMarkSettings"
            >
              <option value="">Pilih COA...</option>
              <option v-for="coa in availableAssetCoa" :key="coa.id" :value="coa.code">
                {{ coa.code }} - {{ coa.name }}
              </option>
            </select>
          </div>

          <!-- Tangible -->
          <div>
            <label class="block text-sm font-semibold text-slate-700 mb-2">
              Tangible (Harta Berwujud) <span class="text-xs text-purple-600">- 1530</span>
            </label>
            <select
              v-model="markSettings.accumulated_depreciation_coa_codes.Tangible"
              class="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition-all text-sm"
              @change="saveMarkSettings"
            >
              <option value="">Pilih COA...</option>
              <option v-for="coa in availableAssetCoa" :key="coa.id" :value="coa.code">
                {{ coa.code }} - {{ coa.name }}
              </option>
            </select>
          </div>

          <!-- LandRights -->
          <div>
            <label class="block text-sm font-semibold text-slate-700 mb-2">
              LandRights (Hak Guna) <span class="text-xs text-purple-600">- 1534</span>
            </label>
            <select
              v-model="markSettings.accumulated_depreciation_coa_codes.LandRights"
              class="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition-all text-sm"
              @change="saveMarkSettings"
            >
              <option value="">Pilih COA...</option>
              <option v-for="coa in availableAssetCoa" :key="coa.id" :value="coa.code">
                {{ coa.code }} - {{ coa.name }}
              </option>
            </select>
          </div>

          <!-- Intangible -->
          <div>
            <label class="block text-sm font-semibold text-slate-700 mb-2">
              Intangible (Tidak Berwujud) <span class="text-xs text-purple-600">- 1601</span>
            </label>
            <select
              v-model="markSettings.accumulated_depreciation_coa_codes.Intangible"
              class="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition-all text-sm"
              @change="saveMarkSettings"
            >
              <option value="">Pilih COA...</option>
              <option v-for="coa in availableAssetCoa" :key="coa.id" :value="coa.code">
                {{ coa.code }} - {{ coa.name }}
              </option>
            </select>
          </div>
        </div>

        <div
          class="bg-purple-50 border border-purple-200 rounded-lg p-4 flex gap-3"
        >
          <i class="bi bi-info-circle text-purple-600 mt-0.5"></i>
          <div class="text-xs text-purple-700">
            <p class="font-bold mb-1">Penting:</p>
            <p>
              Mapping ini menentukan akun akumulasi penyusutan yang akan digunakan
              di neraca. Nilai amortisasi akan diposting ke akun beban (5314)
              di laporan laba rugi dan ke akun akumulasi penyusutan sesuai tipe aset di neraca.
            </p>
          </div>
        </div>
      </div>
    </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { useAmortizationStore } from "../../stores/amortization";

const props = defineProps({
  companyId: {
    type: String,
    default: null,
  },
});

const store = useAmortizationStore();

// State
const assetGroups = ref([]);
const showGroupModal = ref(false);
const editingGroup = ref(null);
const isSavingGroup = ref(false);
const saveError = ref(null);

// Mark-based amortization state
const markSettings = ref({
  use_mark_based_amortization: false,
  amortization_asset_marks: [
    "pembelian aset perusahaan - berwujud",
    "pembelian aset perusahaan - tidak berwujud",
    "pembelian bangunan",
  ],
  default_asset_useful_life: "5",
  default_amortization_rate: "20.00",
  amortization_expense_coa_codes: ["5314"],
  fiscal_correction_coa_codes: [],
  accumulated_depreciation_coa_codes: {
    Building: "1524",
    Tangible: "1530",
    LandRights: "1534",
    Intangible: "1601"
  }
});
const availableMarks = ref([]);
const availableCoa = ref([]);
const availableAssetCoa = ref([]);

const groupForm = ref({
  asset_type: "Tangible",
  group_number: 1,
  group_name: "",
  useful_life_years: 4,
  tarif_rate: 25.0,
  tarif_half_rate: 12.5,
});

// Computed
const groupedGroups = computed(() => {
  const grouped = { Tangible: [], Intangible: [], Building: [] };
  assetGroups.value.forEach((group) => {
    if (grouped[group.asset_type]) {
      grouped[group.asset_type].push(group);
    }
  });
  // Sort by group number
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

// Methods
const fetchData = async () => {
  if (!props.companyId) return;

  // Fetch asset groups
  const groups = await store.fetchAssetGroups(props.companyId);
  assetGroups.value = groups;

  // Fetch mark-based settings
  await fetchMarkSettings();

  // Fetch available COA
  await fetchAvailableCoa();
};

const fetchAssetGroups = async () => {
  if (!props.companyId) return;

  // Fetch asset groups
  const groups = await store.fetchAssetGroups(props.companyId);
  assetGroups.value = groups;
};

const getAssetTypeLabel = (type) => {
  const labels = {
    Tangible: "Harta Berwujud",
    Intangible: "Harta Tidak Berwujud",
    Building: "Bangunan",
  };
  return labels[type] || type;
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
    if (editingGroup.value) {
      await store.updateAssetGroup(editingGroup.value.id, {
        ...groupForm.value,
        company_id: props.companyId,
      });
    } else {
      await store.createAssetGroup({
        ...groupForm.value,
        company_id: props.companyId,
      });
    }
    closeGroupModal();
    await fetchData();
  } catch (err) {
    saveError.value = err.message || "Terjadi kesalahan saat menyimpan data.";
    console.error("Failed to save group:", err);
  } finally {
    isSavingGroup.value = false;
  }
};

// Mark-based amortization methods
const fetchMarkSettings = async () => {
  try {
    const data = await store.getMarkSettings(props.companyId);
    markSettings.value = { ...markSettings.value, ...data.settings };
    availableMarks.value = data.available_marks || [];
  } catch (err) {
    console.error("Failed to fetch mark settings:", err);
  }
};

const fetchAvailableCoa = async () => {
  try {
    const { useCoaStore } = await import('../../stores/coa');
    const coaStore = useCoaStore();
    await coaStore.fetchCoa();
    // Filter for expense category only
    availableCoa.value = coaStore.coaList.filter(c =>
      c.category === 'EXPENSE' && c.is_active !== false
    );
    // Filter for asset accounts (for accumulated depreciation)
    availableAssetCoa.value = coaStore.coaList.filter(c =>
      c.category === 'ASSET' && c.is_active !== false
    );
  } catch (err) {
    console.error("Failed to fetch COA:", err);
  }
};

const toggleMarkSelection = (markName) => {
  const index = markSettings.value.amortization_asset_marks.indexOf(markName);
  if (index > -1) {
    markSettings.value.amortization_asset_marks.splice(index, 1);
  } else {
    markSettings.value.amortization_asset_marks.push(markName);
  }
  saveMarkSettings();
};

const saveMarkSettings = async () => {
  try {
    await store.saveMarkSettings({
      company_id: props.companyId,
      ...markSettings.value,
    });
  } catch (err) {
    console.error("Failed to save mark settings:", err);
  }
};

const addAssetMarkPattern = () => {
  markSettings.value.amortization_asset_marks.push("");
};

const removeAssetMarkPattern = (index) => {
  markSettings.value.amortization_asset_marks.splice(index, 1);
  saveMarkSettings();
};

const updateMarkMapping = async (mark) => {
  try {
    if (mark.asset_type) {
      await store.createMarkMapping({
        mark_id: mark.id,
        asset_type: mark.asset_type,
        useful_life_years:
          mark.useful_life_years ||
          markSettings.value.default_asset_useful_life,
        amortization_rate:
          mark.amortization_rate ||
          markSettings.value.default_amortization_rate,
      });
    }
  } catch (err) {
    console.error("Failed to update mark mapping:", err);
  }
};

const clearMarkMapping = async (mark) => {
  try {
    // Reset mark properties
    mark.asset_type = "";
    mark.useful_life_years = null;
    mark.amortization_rate = null;

    // Delete mapping from database (would need a delete endpoint)
    // For now, just update with empty values
    await store.createMarkMapping({
      mark_id: mark.id,
      asset_type: "",
      useful_life_years: null,
      amortization_rate: null,
    });
  } catch (err) {
    console.error("Failed to clear mark mapping:", err);
  }
};

const toggleMarkIsAsset = async (mark) => {
  try {
    const newIsAsset = !mark.is_asset;
    await store.updateMarkIsAsset(mark.id, newIsAsset);
    mark.is_asset = newIsAsset;

    // If unchecking is_asset, clear the mapping
    if (!newIsAsset) {
      await clearMarkMapping(mark);
    }
  } catch (err) {
    console.error("Failed to toggle mark is_asset:", err);
  }
};

watch(() => props.companyId, fetchData, { immediate: true });
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
