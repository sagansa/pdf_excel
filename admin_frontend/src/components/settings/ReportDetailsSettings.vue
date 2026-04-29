<template>
  <SectionCard 
    title="Laporan & Tanda Tangan"
    subtitle="Konfigurasi nama direktur dan lokasi penandatanganan laporan keuangan berdasarkan periode (tahun)."
    icon="bi bi-file-earmark-pdf"
  >
    <div class="space-y-6">
      <!-- Company Selector -->
      <div>
        <label class="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-2 dark:text-gray-400">
          <i class="bi bi-building text-primary mr-1"></i> Pilih Perusahaan
        </label>
        <div class="max-w-md">
          <select 
            class="w-full rounded-xl border border-gray-200 bg-gray-50/50 py-2.5 px-4 text-sm focus:border-primary focus:bg-white focus:outline-none transition-all dark:border-border dark:bg-surface-muted dark:text-gray-200 dark:focus:bg-surface" 
            v-model="selectedCompany"
            :disabled="loadingCompanies"
            @change="handleCompanyChange"
          >
            <option value="">-- Pilih Perusahaan --</option>
            <option 
              v-for="company in companies" 
              :key="company.id" 
              :value="company.id"
            >
              {{ company.name || company.id }}
            </option>
          </select>
        </div>
      </div>

      <!-- Info Header -->
      <div 
        class="rounded-xl border border-blue-100 bg-blue-50 p-4 transition-colors dark:border-blue-900/50 dark:bg-blue-900/20"
      >
        <div class="flex gap-3">
          <i class="bi bi-info-circle text-blue-600 dark:text-blue-400"></i>
          <div class="text-xs leading-relaxed text-blue-800 dark:text-blue-200">
            Detail ini akan ditampilkan pada bagian tanda tangan di laporan PDF (Income Statement, dll). 
            Anda dapat mengatur nama yang berbeda untuk tahun yang berbeda jika terjadi perubahan manajemen.
          </div>
        </div>
      </div>

      <!-- Year Selector & Form -->
      <div class="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <!-- Left: Year Selection -->
        <div class="lg:col-span-4 space-y-4">
          <div class="text-sm font-semibold text-gray-700 dark:text-gray-200">Pilih Tahun Laporan</div>
          <div class="flex flex-col gap-2">
            <button
              v-for="year in availableYears"
              :key="year"
              @click="selectYear(year)"
              class="flex items-center justify-between rounded-xl px-4 py-3 text-sm transition-all"
              :class="selectedYear === year 
                ? 'bg-primary/10 border-primary/20 text-primary font-bold border dark:bg-primary/20 dark:border-primary/30' 
                : 'bg-surface-muted border-transparent text-gray-600 border hover:border-gray-300 dark:text-gray-400 dark:hover:border-gray-600'"
            >
              <span>Periode Tahun {{ year }}</span>
              <i v-if="selectedYear === year" class="bi bi-check2-circle"></i>
            </button>
          </div>
        </div>

        <!-- Right: Form -->
        <div class="lg:col-span-8">
          <div v-if="isLoading" class="flex h-48 items-center justify-center">
            <div class="flex flex-col items-center gap-2">
              <div class="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent"></div>
              <span class="text-xs text-gray-500 dark:text-gray-400">Memuat data...</span>
            </div>
          </div>
          
          <form v-else @submit.prevent="handleSave" class="space-y-5 rounded-2xl border border-gray-100 bg-white p-6 shadow-sm dark:border-border dark:bg-surface">
            <div class="flex items-center justify-between border-b border-gray-100 pb-4 mb-4 dark:border-border">
              <h4 class="text-sm font-bold text-gray-800 dark:text-gray-100">Detail Penandatanganan {{ selectedYear }}</h4>
              <span class="text-[10px] uppercase tracking-wider text-gray-400 font-bold dark:text-gray-500">Entry Database</span>
            </div>

            <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div class="space-y-1.5">
                <label class="text-xs font-bold text-gray-500 uppercase tracking-tight dark:text-gray-400">Nama Direktur Utama</label>
                <div class="relative">
                  <i class="bi bi-person absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500"></i>
                  <input
                    v-model="form.director_name"
                    type="text"
                    required
                    placeholder="Contoh: Budi Santoso"
                    class="w-full rounded-xl border border-gray-200 bg-gray-50/50 py-2.5 pl-10 pr-4 text-sm focus:border-primary focus:bg-white focus:outline-none transition-all dark:border-border dark:bg-surface-muted dark:text-gray-200 dark:focus:bg-surface"
                  />
                </div>
              </div>

              <div class="space-y-1.5">
                <label class="text-xs font-bold text-gray-500 uppercase tracking-tight dark:text-gray-400">Jabatan (Title)</label>
                <div class="relative">
                  <i class="bi bi-briefcase absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500"></i>
                  <input
                    v-model="form.director_title"
                    type="text"
                    required
                    placeholder="Contoh: Direktur Utama"
                    class="w-full rounded-xl border border-gray-200 bg-gray-50/50 py-2.5 pl-10 pr-4 text-sm focus:border-primary focus:bg-white focus:outline-none transition-all dark:border-border dark:bg-surface-muted dark:text-gray-200 dark:focus:bg-surface"
                  />
                </div>
              </div>
            </div>

            <div class="space-y-1.5">
              <label class="text-xs font-bold text-gray-500 uppercase tracking-tight dark:text-gray-400">Lokasi Penandatanganan</label>
              <div class="relative">
                <i class="bi bi-geo-alt absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500"></i>
                <input
                  v-model="form.location"
                  type="text"
                  required
                  placeholder="Contoh: Jakarta"
                  class="w-full rounded-xl border border-gray-200 bg-gray-50/50 py-2.5 pl-10 pr-4 text-sm focus:border-primary focus:bg-white focus:outline-none transition-all dark:border-border dark:bg-surface-muted dark:text-gray-200 dark:focus:bg-surface"
                />
              </div>
              <p class="text-[10px] text-gray-400 italic dark:text-gray-500">Biasanya berupa nama kota dimana laporan ditandatangani.</p>
            </div>

            <div class="flex justify-end pt-4">
              <button
                type="submit"
                :disabled="isSaving"
                class="btn-primary rounded-xl px-6 py-2.5 text-sm font-bold gap-2 flex items-center shadow-lg shadow-primary/20"
              >
                <i v-if="isSaving" class="bi bi-arrow-repeat animate-spin"></i>
                <i v-else class="bi bi-save"></i>
                {{ isSaving ? 'Menyimpan...' : 'Simpan Perubahan' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </SectionCard>
</template>

<script setup>
import { ref, onMounted, reactive, watch } from 'vue';
import { useReportsStore } from '../../stores/reports';
import SectionCard from '../ui/SectionCard.vue';
import { useNotifications } from '../../composables/useNotifications';

const props = defineProps({
  companyId: {
    type: String,
    default: ''
  }
});

const store = useReportsStore();
const notifications = useNotifications();

const selectedCompany = ref(props.companyId || '');
const companies = ref([]);
const loadingCompanies = ref(false);

const selectedYear = ref(new Date().getFullYear());
const availableYears = ref([]);
const isLoading = ref(false);
const isSaving = ref(false);

const form = reactive({
  director_name: '',
  director_title: 'Direktur Utama',
  location: 'Jakarta'
});

const selectYear = (year) => {
  selectedYear.value = year;
  fetchSettings();
};

const loadCompanies = async () => {
  loadingCompanies.value = true;
  try {
    const response = await fetch('/api/companies');
    const data = await response.json();
    companies.value = data.companies || data || [];
  } catch (err) {
    console.error('Error loading companies:', err);
  } finally {
    loadingCompanies.value = false;
  }
};

const fetchAvailableYearsForCompany = async () => {
  if (!selectedCompany.value) {
    availableYears.value = [new Date().getFullYear()];
    return;
  }
  availableYears.value = await store.fetchAvailableYears(selectedCompany.value);
  if (availableYears.value.length === 0) {
    availableYears.value = [new Date().getFullYear()];
  }
  if (!availableYears.value.includes(selectedYear.value)) {
    selectedYear.value = availableYears.value[0];
  }
};

const handleCompanyChange = async () => {
  if (!selectedCompany.value) {
    form.director_name = '';
    form.director_title = 'Direktur Utama';
    form.location = 'Jakarta';
    return;
  }
  await fetchAvailableYearsForCompany();
  await fetchSettings();
};

const fetchSettings = async () => {
  if (!selectedCompany.value) return;
  isLoading.value = true;
  try {
    const data = await store.fetchReportSettings(selectedCompany.value, selectedYear.value);
    if (data) {
      form.director_name = data.director_name || '';
      form.director_title = data.director_title || 'Direktur Utama';
      form.location = data.location || 'Jakarta';
    } else {
      // Defaults if not found
      form.director_name = '';
      form.director_title = 'Direktur Utama';
      form.location = 'Jakarta';
    }
  } catch (err) {
    console.error(err);
  } finally {
    isLoading.value = false;
  }
};

const handleSave = async () => {
  if (!selectedCompany.value) {
    notifications.error('Pilih perusahaan terlebih dahulu');
    return;
  }
  
  isSaving.value = true;
  try {
    await store.saveReportSettings({
      company_id: selectedCompany.value,
      year: selectedYear.value,
      ...form
    });
    notifications.success('Konfigurasi laporan berhasil disimpan');
  } catch (err) {
    notifications.error('Gagal menyimpan konfigurasi');
  } finally {
    isSaving.value = false;
  }
};

onMounted(async () => {
  await loadCompanies();
  if (selectedCompany.value) {
    await fetchAvailableYearsForCompany();
    fetchSettings();
  }
});

// Watch for company change
watch(() => props.companyId, async (newId) => {
  if (newId) {
    selectedCompany.value = newId;
    await fetchAvailableYearsForCompany();
    fetchSettings();
  }
});
</script>
