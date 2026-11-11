<template>
  <div class="space-y-6">
    <p v-if="isLoading" class="field-hint flex items-center gap-2" role="status">
      <i class="bi bi-arrow-repeat animate-spin"></i>
      Memuat kredensial...
    </p>

    <SectionCard
      v-for="group in groups"
      :key="group.id"
      :title="group.title"
      :subtitle="group.subtitle"
      body-class="p-6"
    >
      <div class="space-y-5">
        <div v-for="cred in byGroup[group.id] || []" :key="cred.key" class="field-stack">
          <label class="label-base" :for="`cred-${cred.key}`">{{ cred.label }}</label>
          <div class="flex flex-wrap items-center gap-2">
            <TextInput
              :id="`cred-${cred.key}`"
              v-model="form[cred.key]"
              :type="cred.secret ? 'password' : 'text'"
              autocomplete="off"
              :placeholder="placeholderFor(cred)"
              class="flex-1 min-w-[220px]"
            >
              <template #leading>
                <i class="bi bi-key-fill text-gray-400 dark:text-gray-500"></i>
              </template>
            </TextInput>
            <span
              v-if="cred.set"
              class="whitespace-nowrap rounded-full px-2.5 py-1 text-[11px] font-bold"
              :class="cred.source === 'env'
                ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200'
                : 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200'"
              :title="cred.source === 'env'
                ? 'Nilai masih dibaca dari environment — klik Simpan untuk memindahkan ke database.'
                : 'Tersimpan di database.'"
            >
              {{ cred.source === 'env' ? 'dari env' : 'tersimpan' }}
            </span>
            <button
              v-if="cred.test"
              type="button"
              class="text-xs font-bold text-primary hover:underline disabled:opacity-50"
              :disabled="isTesting === cred.key"
              @click="handleTest(cred)"
            >
              {{ isTesting === cred.key ? 'Menguji...' : 'Test' }}
            </button>
            <button
              v-if="cred.secret && cred.set && !isDirtySecret(cred)"
              type="button"
              class="text-xs font-bold text-danger hover:underline disabled:opacity-50"
              :disabled="isSaving"
              title="Hapus nilai yang tersimpan"
              @click="markClear(cred)"
            >
              Hapus
            </button>
          </div>
          <p class="field-hint">{{ hintFor(cred) }}</p>
          <p
            v-if="testStatus[cred.key]"
            class="text-xs font-bold flex items-center gap-1.5"
            :class="testStatus[cred.key].ok
              ? 'text-emerald-600 dark:text-emerald-400'
              : 'text-danger'"
          >
            <i :class="testStatus[cred.key].ok ? 'bi bi-check-circle' : 'bi bi-x-circle'"></i>
            {{ testStatus[cred.key].message }}
          </p>
        </div>

        <div class="flex items-center justify-between gap-3 pt-1">
          <p v-if="groupError[group.id]" class="text-xs font-bold text-danger">{{ groupError[group.id] }}</p>
          <span v-else></span>
          <button
            type="button"
            class="rounded-xl bg-primary px-4 py-2.5 text-sm font-bold text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="isSaving"
            @click="handleSaveGroup(group.id)"
          >
            {{ isSaving ? 'Menyimpan...' : 'Simpan' }}
          </button>
        </div>
      </div>
    </SectionCard>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue';

import { credentialsApi } from '../../api';
import SectionCard from '../ui/SectionCard.vue';
import TextInput from '../ui/TextInput.vue';
import { useNotifications } from '../../composables/useNotifications';

const notify = useNotifications();

const CLEAR = '__CLEAR__';

const groups = [
  {
    id: 'sagansa',
    title: 'Sagansa Superadmin API',
    subtitle: 'Token untuk menarik presensi, stok, dan data penjualan dari superadmin.sagansa.id.',
  },
  {
    id: 'ai',
    title: 'AI Provider',
    subtitle: 'API key provider AI cloud. Provider, base URL, dan model diatur di tab AI.',
  },
  {
    id: 'telegram',
    title: 'Telegram Notifikasi',
    subtitle: 'Notifikasi masalah pipeline e-statement ke chat Telegram Anda.',
  },
  {
    id: 'smtp',
    title: 'Email SMTP',
    subtitle: 'Dipakai untuk mengirim email reset password.',
  },
  {
    id: 'n8n',
    title: 'n8n Integration',
    subtitle: 'Kunci yang wajib dikirim n8n pada header X-API-Key. Tanpa kunci, endpoint integrasi nonaktif.',
  },
];

const credentials = ref([]);
const form = reactive({});
const originals = reactive({});
const clearFlags = reactive(new Set());
const testStatus = reactive({});
const groupError = reactive({});
const isLoading = ref(true);
const isSaving = ref(false);
const isTesting = ref('');

const byGroup = computed(() => {
  const map = {};
  for (const cred of credentials.value) {
    (map[cred.group] ||= []).push(cred);
  }
  return map;
});

const placeholderFor = (cred) => (cred.set
  ? 'Tersimpan — isi untuk mengganti'
  : 'Belum diisi — tempel nilai di sini');

const isDirtySecret = (cred) => Boolean(String(form[cred.key] || '').trim());

const hintFor = (cred) => {
  if (!cred.secret) return '';
  if (clearFlags.has(cred.key)) return 'Akan dihapus saat Anda menekan Simpan.';
  if (isDirtySecret(cred)) return 'Nilai baru akan tersimpan saat Anda menekan Simpan.';
  if (cred.set) return 'Kunci tersimpan di server dan tidak pernah ditampilkan kembali.';
  return 'Belum diisi — fitur terkait tidak berfungsi sampai kunci diisi.';
};

const applyStatus = (items) => {
  credentials.value = items;
  for (const cred of items) {
    originals[cred.key] = cred.secret ? '' : String(cred.value ?? '');
    if (!(cred.key in form)) {
      form[cred.key] = cred.secret ? '' : String(cred.value ?? '');
    }
    if (clearFlags.has(cred.key) && !cred.set) clearFlags.delete(cred.key);
  }
};

const load = async () => {
  isLoading.value = true;
  try {
    const { data } = await credentialsApi.list();
    applyStatus(data.credentials || []);
  } catch (err) {
    notify.error('Gagal memuat kredensial. Coba muat ulang halaman.');
  } finally {
    isLoading.value = false;
  }
};

const markClear = (cred) => {
  clearFlags.add(cred.key);
  form[cred.key] = '';
};

const buildUpdates = (groupId) => {
  const updates = {};
  for (const cred of byGroup.value[groupId] || []) {
    const value = String(form[cred.key] ?? '').trim();
    if (clearFlags.has(cred.key)) {
      updates[cred.key] = CLEAR;
    } else if (cred.secret) {
      if (value) updates[cred.key] = value;
    } else if (value !== String(originals[cred.key] ?? '')) {
      updates[cred.key] = value;
    }
  }
  return updates;
};

const handleSaveGroup = async (groupId) => {
  groupError[groupId] = '';
  const updates = buildUpdates(groupId);
  if (!Object.keys(updates).length) {
    notify.info('Tidak ada perubahan untuk disimpan.');
    return;
  }
  isSaving.value = true;
  try {
    const { data } = await credentialsApi.save(updates);
    applyStatus(data.credentials || []);
    // field secret kosongkan setelah simpan; nilai non-secret resinkron.
    // Resinkron hanya kunci milik grup yang disimpan — PUT mengembalikan semua
    // kredensial, dan form grup lain bisa berisi edit yang belum disimpan.
    const savedKeys = new Set((byGroup.value[groupId] || []).map((c) => c.key));
    for (const cred of data.credentials || []) {
      if (!savedKeys.has(cred.key)) continue;
      form[cred.key] = cred.secret ? '' : String(cred.value ?? '');
    }
    for (const key of Object.keys(updates)) delete testStatus[key];
    notify.success('Kredensial tersimpan.');
  } catch (err) {
    groupError[groupId] = err.response?.data?.error || 'Gagal menyimpan kredensial. Coba lagi.';
  } finally {
    isSaving.value = false;
  }
};

const handleTest = async (cred) => {
  testStatus[cred.key] = null;
  isTesting.value = cred.key;
  try {
    const body = {};
    const typed = String(form[cred.key] ?? '').trim();
    if (typed) body.value = typed;
    const extra = {};
    if (cred.test === 'telegram') {
      const chatId = String(form.telegram_chat_id ?? '').trim();
      if (chatId) extra.telegram_chat_id = chatId;
    } else if (cred.test === 'smtp') {
      for (const key of ['smtp_host', 'smtp_port', 'smtp_user', 'smtp_pass', 'smtp_from', 'smtp_use_tls']) {
        const v = String(form[key] ?? '').trim();
        if (v) extra[key] = v;
      }
    }
    if (Object.keys(extra).length) body.extra = extra;
    const { data } = await credentialsApi.test(cred.key, body);
    testStatus[cred.key] = { ok: Boolean(data.ok), message: data.message };
  } catch (err) {
    testStatus[cred.key] = {
      ok: false,
      message: err.response?.data?.error || 'Test gagal dijalankan.',
    };
  } finally {
    isTesting.value = '';
  }
};

onMounted(load);
</script>
