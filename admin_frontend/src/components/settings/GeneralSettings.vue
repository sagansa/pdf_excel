<template>
  <div class="space-y-6">
    <SectionCard
      title="Tampilan"
      subtitle="Pilih mode terang, gelap, atau ikut preferensi sistem. Diterapkan seketika."
      body-class="p-6"
    >
      <div class="max-w-xl">
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <button
            v-for="option in themeOptions"
            :key="option.value"
            type="button"
            :aria-pressed="theme === option.value"
            class="flex items-center justify-between rounded-xl px-4 py-3.5 text-sm transition-all"
            :class="theme === option.value
              ? 'bg-primary/10 border-primary/20 text-primary font-bold border dark:bg-primary/20 dark:border-primary/30'
              : 'bg-surface-muted border-transparent text-gray-600 border hover:border-gray-300 dark:text-gray-400 dark:hover:border-gray-600'"
            @click="setTheme(option.value)"
          >
            <span class="flex items-center gap-2.5">
              <i class="bi text-base" :class="option.icon"></i>
              {{ option.label }}
            </span>
            <i v-if="theme === option.value" class="bi bi-check2-circle"></i>
          </button>
        </div>
        <p class="field-hint mt-3">
          Sistem mengikuti tampilan perangkat Anda dan berubah otomatis.
        </p>
      </div>
    </SectionCard>

    <SectionCard
      title="Ganti Password"
      subtitle="Perbarui password untuk akun Anda."
      body-class="p-6"
    >
      <div class="max-w-md space-y-5">
        <div class="rounded-xl border border-blue-100 bg-blue-50 p-4 transition-colors dark:border-blue-900/50 dark:bg-blue-900/20">
          <div class="flex gap-3">
            <i class="bi bi-info-circle text-blue-600 dark:text-blue-400"></i>
            <div class="text-xs leading-relaxed text-blue-800 dark:text-blue-200">
              Setelah password diganti, sesi login lain di perangkat mana pun akan otomatis
              keluar. Sesi Anda saat ini tetap aktif.
            </div>
          </div>
        </div>

        <form class="space-y-4" @submit.prevent="handleChangePassword">
          <div class="field-stack">
            <label class="label-base" for="current-password">Password saat ini</label>
            <TextInput
              id="current-password"
              v-model="currentPassword"
              type="password"
              autocomplete="current-password"
              placeholder="Password saat ini"
              :disabled="isSaving"
              required
            >
              <template #leading>
                <i class="bi bi-lock-fill text-gray-400 dark:text-gray-500"></i>
              </template>
            </TextInput>
          </div>

          <div class="field-stack">
            <label class="label-base" for="new-password">Password baru</label>
            <TextInput
              id="new-password"
              v-model="newPassword"
              type="password"
              autocomplete="new-password"
              placeholder="Minimal 8 karakter"
              :disabled="isSaving"
              required
              minlength="8"
            >
              <template #leading>
                <i class="bi bi-key-fill text-gray-400 dark:text-gray-500"></i>
              </template>
            </TextInput>
            <p class="field-hint">Minimal 8 karakter.</p>
          </div>

          <div class="field-stack">
            <label class="label-base" for="confirm-password">Konfirmasi password baru</label>
            <TextInput
              id="confirm-password"
              v-model="confirmPassword"
              type="password"
              autocomplete="new-password"
              placeholder="Ulangi password baru"
              :disabled="isSaving"
              required
              minlength="8"
            >
              <template #leading>
                <i class="bi bi-shield-check text-gray-400 dark:text-gray-500"></i>
              </template>
            </TextInput>
          </div>

          <p v-if="formError" class="text-sm font-medium text-danger">{{ formError }}</p>

          <div class="flex justify-end pt-4">
            <button
              type="submit"
              :disabled="isSaving || !canSubmit"
              class="btn-primary rounded-xl px-6 py-2.5 text-sm font-bold gap-2 flex items-center shadow-lg shadow-primary/20"
            >
              <i v-if="isSaving" class="bi bi-arrow-repeat animate-spin"></i>
              <i v-else class="bi bi-shield-lock"></i>
              {{ isSaving ? 'Menyimpan...' : 'Simpan Perubahan' }}
            </button>
          </div>
        </form>
      </div>
    </SectionCard>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';
import SectionCard from '../ui/SectionCard.vue';
import TextInput from '../ui/TextInput.vue';
import { useTheme } from '../../composables/useTheme';
import { useNotifications } from '../../composables/useNotifications';
import { authApi } from '../../api';

const { theme, setTheme } = useTheme();
const notify = useNotifications();

const themeOptions = [
  { label: 'Terang', value: 'light', icon: 'bi-sun-fill' },
  { label: 'Gelap', value: 'dark', icon: 'bi-moon-stars-fill' },
  { label: 'Sistem', value: 'system', icon: 'bi-circle-half' }
];

const currentPassword = ref('');
const newPassword = ref('');
const confirmPassword = ref('');
const isSaving = ref(false);
const formError = ref('');

const canSubmit = computed(() =>
  currentPassword.value && newPassword.value && confirmPassword.value
);

const handleChangePassword = async () => {
  formError.value = '';
  if (newPassword.value.length < 8) {
    formError.value = 'Password minimal 8 karakter.';
    return;
  }
  if (newPassword.value !== confirmPassword.value) {
    formError.value = 'Konfirmasi password tidak cocok.';
    return;
  }

  isSaving.value = true;
  try {
    await authApi.changePassword(currentPassword.value, newPassword.value);
    currentPassword.value = '';
    newPassword.value = '';
    confirmPassword.value = '';
    notify.success('Password berhasil diubah.');
  } catch (err) {
    const code = err.response?.data?.code;
    if (code === 'invalid_credentials') {
      formError.value = 'Password saat ini salah.';
    } else if (err.response?.status === 400) {
      formError.value = err.response?.data?.error || 'Password minimal 8 karakter.';
    } else if (err.response?.status === 429) {
      formError.value = err.response?.data?.error || 'Terlalu banyak percobaan. Coba lagi beberapa menit.';
    } else {
      formError.value = 'Gagal mengubah password. Periksa koneksi Anda dan coba lagi.';
    }
  } finally {
    isSaving.value = false;
  }
};
</script>
