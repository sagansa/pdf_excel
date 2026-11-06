<template>
  <div class="space-y-6">
    <SectionCard
      title="Appearance"
      subtitle="Choose light, dark, or follow your system preference. Applied instantly."
    >
      <div class="flex flex-wrap items-center gap-4">
        <SegmentedControl
          :model-value="theme"
          :options="themeOptions"
          variant="primary"
          @update:model-value="setTheme"
        >
          <template #option="{ option }">
            <i class="bi mr-1.5" :class="option.icon"></i>
            {{ option.label }}
          </template>
        </SegmentedControl>
        <p class="text-xs text-muted">
          System follows your device's appearance and updates automatically.
        </p>
      </div>
    </SectionCard>

    <SectionCard title="Change password" subtitle="Update the password for your account.">
      <form class="space-y-4 max-w-md" @submit.prevent="handleChangePassword">
        <div class="field-stack">
          <label class="label-base" for="current-password">Current password</label>
          <TextInput
            id="current-password"
            v-model="currentPassword"
            type="password"
            autocomplete="current-password"
            placeholder="Current password"
            :disabled="isSaving"
            required
          />
        </div>

        <div class="field-stack">
          <label class="label-base" for="new-password">New password</label>
          <TextInput
            id="new-password"
            v-model="newPassword"
            type="password"
            autocomplete="new-password"
            placeholder="Minimum 8 characters"
            :disabled="isSaving"
            required
            minlength="8"
          />
          <p class="field-hint">Minimum 8 characters.</p>
        </div>

        <div class="field-stack">
          <label class="label-base" for="confirm-password">Confirm new password</label>
          <TextInput
            id="confirm-password"
            v-model="confirmPassword"
            type="password"
            autocomplete="new-password"
            placeholder="Repeat new password"
            :disabled="isSaving"
            required
            minlength="8"
          />
        </div>

        <p v-if="formError" class="text-sm text-red-500 dark:text-red-400">{{ formError }}</p>

        <div class="flex items-center gap-3">
          <button type="submit" class="btn-primary" :disabled="isSaving || !canSubmit">
            {{ isSaving ? 'Saving…' : 'Update password' }}
          </button>
          <p class="text-xs text-muted">Other signed-in sessions will be logged out.</p>
        </div>
      </form>
    </SectionCard>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';
import SectionCard from '../ui/SectionCard.vue';
import SegmentedControl from '../ui/SegmentedControl.vue';
import TextInput from '../ui/TextInput.vue';
import { useTheme } from '../../composables/useTheme';
import { useNotifications } from '../../composables/useNotifications';
import { authApi } from '../../api';

const { theme, setTheme } = useTheme();
const notify = useNotifications();

const themeOptions = [
  { label: 'Light', value: 'light', icon: 'bi-sun-fill' },
  { label: 'Dark', value: 'dark', icon: 'bi-moon-stars-fill' },
  { label: 'System', value: 'system', icon: 'bi-circle-half' }
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
    formError.value = 'Password must be at least 8 characters.';
    return;
  }
  if (newPassword.value !== confirmPassword.value) {
    formError.value = 'Passwords do not match.';
    return;
  }

  isSaving.value = true;
  try {
    const response = await authApi.changePassword(currentPassword.value, newPassword.value);
    currentPassword.value = '';
    newPassword.value = '';
    confirmPassword.value = '';
    notify.success(response.data?.message || 'Password updated.');
  } catch (err) {
    const code = err.response?.data?.code;
    if (code === 'invalid_credentials') {
      formError.value = err.response?.data?.error || 'Current password is incorrect.';
    } else if (err.response?.status === 400) {
      formError.value = err.response?.data?.error || 'Password must be at least 8 characters.';
    } else if (err.response?.status === 429) {
      formError.value = err.response?.data?.error || 'Too many attempts. Try again in a few minutes.';
    } else {
      formError.value = 'Failed to update password. Check your connection and try again.';
    }
  } finally {
    isSaving.value = false;
  }
};
</script>
