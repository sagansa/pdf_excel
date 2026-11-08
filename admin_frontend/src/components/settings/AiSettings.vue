<template>
  <div class="space-y-6">
    <SectionCard
      title="Asisten AI Lokal"
      subtitle="Saran mark otomatis memakai LLM yang berjalan di laptop Anda (LM Studio / Ollama)."
      body-class="p-6"
    >
      <div class="max-w-xl space-y-6">
        <p v-if="isLoading" class="field-hint flex items-center gap-2" role="status">
          <i class="bi bi-arrow-repeat animate-spin"></i>
          Memuat pengaturan AI...
        </p>

        <div class="rounded-xl border border-blue-100 bg-blue-50 p-4 transition-colors dark:border-blue-900/50 dark:bg-blue-900/20">
          <div class="flex gap-3">
            <i class="bi bi-info-circle text-blue-600 dark:text-blue-400"></i>
            <div class="text-xs leading-relaxed text-blue-800 dark:text-blue-200">
              AI hanya <strong>menyarankan</strong> mark — tidak pernah mengisi langsung.
              Setiap saran ditandai beserta tingkat keyakinan dan alasan, lalu menunggu Anda
              terima/tolak di halaman History. Semua data diproses di server AI lokal Anda,
              tidak dikirim ke internet.
            </div>
          </div>
        </div>

        <div class="field-stack">
          <span class="label-base">Status fitur</span>
          <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <button
              v-for="option in enabledOptions"
              :key="option.value"
              type="button"
              :aria-pressed="form.enabled === option.value"
              :disabled="isLoading"
              class="flex items-center justify-between rounded-xl px-4 py-3.5 text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              :class="form.enabled === option.value
                ? 'bg-primary/10 border-primary/20 text-primary font-bold border dark:bg-primary/20 dark:border-primary/30'
                : 'bg-surface-muted border-transparent text-gray-600 border hover:border-gray-300 dark:text-gray-400 dark:hover:border-gray-600'"
              @click="form.enabled = option.value"
            >
              <span class="flex items-center gap-2.5">
                <i class="bi text-base" :class="option.icon"></i>
                {{ option.label }}
              </span>
              <i v-if="form.enabled === option.value" class="bi bi-check2-circle"></i>
            </button>
          </div>
        </div>

        <div class="field-stack">
          <span class="label-base">Provider AI</span>
          <div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <button
              v-for="option in providerOptions"
              :key="option.value"
              type="button"
              :aria-pressed="form.provider === option.value"
              :disabled="isLoading"
              class="flex items-center justify-between rounded-xl px-4 py-3.5 text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              :class="form.provider === option.value
                ? 'bg-primary/10 border-primary/20 text-primary font-bold border dark:bg-primary/20 dark:border-primary/30'
                : 'bg-surface-muted border-transparent text-gray-600 border hover:border-gray-300 dark:text-gray-400 dark:hover:border-gray-600'"
              @click="selectProvider(option.value)"
            >
              <span class="flex items-center gap-2.5">
                <i class="bi text-base" :class="option.icon"></i>
                {{ option.label }}
              </span>
              <i v-if="form.provider === option.value" class="bi bi-check2-circle"></i>
            </button>
          </div>
          <p class="field-hint">
            Server AI harus berjalan di laptop yang sama dengan aplikasi ini.
          </p>
        </div>

        <div class="field-stack">
          <label class="label-base" for="ai-base-url">Base URL</label>
          <TextInput
            id="ai-base-url"
            v-model="form.baseUrl"
            type="text"
            placeholder="http://localhost:1234/v1"
            :disabled="isLoading || isSaving || isTesting"
          >
            <template #leading>
              <i class="bi bi-link-45deg text-gray-400 dark:text-gray-500"></i>
            </template>
          </TextInput>
          <p class="field-hint">
            Endpoint OpenAI-compatible dari server AI lokal Anda.
          </p>
        </div>

        <div class="field-stack">
          <label class="label-base" for="ai-model">Model</label>
          <SearchableSelect
            v-if="modelOptions.length > 0"
            :model-value="form.model"
            :options="modelOptions"
            placeholder="Pilih model..."
            @update:model-value="form.model = $event || ''"
          />
          <TextInput
            v-else
            id="ai-model"
            v-model="form.model"
            type="text"
            placeholder="mis. qwen2.5:7b-instruct"
            :disabled="isLoading || isSaving || isTesting"
          >
            <template #leading>
              <i class="bi bi-box text-gray-400 dark:text-gray-500"></i>
            </template>
          </TextInput>
          <p class="field-hint">
            Nama model persis seperti di server AI Anda — gunakan &quot;Tes Koneksi&quot; untuk memuat daftar model.
          </p>
        </div>

        <div class="flex flex-wrap items-center gap-4">
          <button
            type="button"
            class="btn-secondary rounded-xl px-4 py-2.5 text-sm font-bold gap-2 inline-flex items-center"
            :disabled="isLoading || isTesting || isSaving"
            @click="handleTestConnection"
          >
            <i v-if="isTesting" class="bi bi-arrow-repeat animate-spin"></i>
            <i v-else class="bi bi-plug"></i>
            {{ isTesting ? 'Menguji...' : 'Tes Koneksi' }}
          </button>
          <p
            v-if="testStatus.message"
            class="text-xs font-medium"
            :class="testStatus.ok ? 'text-success' : 'text-danger'"
          >
            {{ testStatus.message }}
          </p>
        </div>

        <p v-if="formError" class="text-sm font-medium text-danger">{{ formError }}</p>

        <div class="flex justify-end pt-2">
          <button
            type="button"
            :disabled="isLoading || isSaving || isTesting"
            class="btn-primary rounded-xl px-6 py-2.5 text-sm font-bold gap-2 flex items-center shadow-lg shadow-primary/20"
            @click="handleSave"
          >
            <i v-if="isLoading" class="bi bi-arrow-repeat animate-spin"></i>
            <i v-else-if="isSaving" class="bi bi-arrow-repeat animate-spin"></i>
            <i v-else class="bi bi-check2-circle"></i>
            {{ isLoading ? 'Memuat...' : isSaving ? 'Menyimpan...' : 'Simpan Pengaturan' }}
          </button>
        </div>
      </div>
    </SectionCard>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue';
import SectionCard from '../ui/SectionCard.vue';
import TextInput from '../ui/TextInput.vue';
import SearchableSelect from '../ui/SearchableSelect.vue';
import { aiApi } from '../../api';
import { useNotifications } from '../../composables/useNotifications';

const notify = useNotifications();

const PROVIDER_DEFAULTS = {
  lmstudio: 'http://localhost:1234/v1',
  ollama: 'http://localhost:11434/v1',
  custom: ''
};

const enabledOptions = [
  { label: 'Aktif', value: true, icon: 'bi-stars' },
  { label: 'Nonaktif', value: false, icon: 'bi-slash-circle' }
];

const providerOptions = [
  { label: 'LM Studio', value: 'lmstudio', icon: 'bi-pc-display' },
  { label: 'Ollama', value: 'ollama', icon: 'bi-robot' },
  { label: 'Custom', value: 'custom', icon: 'bi-gear-wide-connected' }
];

const form = reactive({
  enabled: false,
  provider: 'lmstudio',
  baseUrl: '',
  model: ''
});

const modelOptions = ref([]);
const isSaving = ref(false);
const isTesting = ref(false);
const isLoading = ref(true);
const formError = ref('');
const testStatus = ref({ ok: null, message: '' });

const selectProvider = (value) => {
  const previousDefault = PROVIDER_DEFAULTS[form.provider] || '';
  form.provider = value;
  const current = form.baseUrl.trim();
  // Ganti default base URL hanya bila sebelumnya masih memakai default provider lama.
  if (!current || current === previousDefault) {
    form.baseUrl = PROVIDER_DEFAULTS[value] || '';
  }
};

const applySettings = (settings) => {
  if (!settings) return;
  form.enabled = Boolean(settings.enabled);
  form.provider = settings.provider || 'lmstudio';
  form.baseUrl = settings.base_url || PROVIDER_DEFAULTS[form.provider] || '';
  form.model = settings.model || '';
};

onMounted(async () => {
  try {
    const { data } = await aiApi.getSettings();
    applySettings(data.settings);
  } catch (err) {
    formError.value = 'Gagal memuat pengaturan AI. Coba muat ulang halaman.';
  } finally {
    isLoading.value = false;
  }
});

const handleTestConnection = async () => {
  testStatus.value = { ok: null, message: '' };
  if (!form.baseUrl.trim()) {
    testStatus.value = { ok: false, message: 'Isi Base URL terlebih dahulu.' };
    return;
  }
  isTesting.value = true;
  try {
    const { data } = await aiApi.testConnection({ base_url: form.baseUrl, model: form.model });
    modelOptions.value = (data.models || []).map((id) => ({ id, label: id }));
    let message = data.message || 'Koneksi berhasil.';
    if (form.model && !data.model_found) {
      message += ` Model "${form.model}" belum termuat di server.`;
    }
    testStatus.value = { ok: true, message };
  } catch (err) {
    const detail = err.response?.data?.error || 'Server AI tidak dapat dihubungi.';
    testStatus.value = { ok: false, message: detail };
    modelOptions.value = [];
  } finally {
    isTesting.value = false;
  }
};

const handleSave = async () => {
  formError.value = '';
  if (!form.baseUrl.trim()) {
    formError.value = 'Base URL server AI wajib diisi.';
    return;
  }
  isSaving.value = true;
  try {
    const { data } = await aiApi.saveSettings({
      enabled: form.enabled,
      provider: form.provider,
      base_url: form.baseUrl.trim(),
      model: form.model.trim()
    });
    applySettings(data.settings);
    notify.success('Pengaturan AI tersimpan.');
  } catch (err) {
    formError.value = err.response?.data?.error || 'Gagal menyimpan pengaturan AI. Coba lagi.';
  } finally {
    isSaving.value = false;
  }
};
</script>
