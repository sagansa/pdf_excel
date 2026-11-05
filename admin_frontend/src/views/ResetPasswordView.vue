<template>
  <div class="login-page min-h-screen flex items-center justify-center p-4">
    <div class="w-full max-w-sm">
      <div class="text-center mb-8">
        <div class="mx-auto mb-4 w-12 h-12 rounded-2xl flex items-center justify-center text-white text-lg font-bold shadow-lg"
             style="background: linear-gradient(135deg, var(--color-primary), var(--color-primary-strong));">S</div>
        <h1 class="text-2xl font-bold text-theme">StatementX</h1>
        <p class="text-sm text-muted mt-1">Choose a new password</p>
      </div>

      <div v-if="!token" class="surface-card rounded-2xl p-6 space-y-4">
        <p class="text-sm text-muted">This reset link is missing its token.</p>
        <router-link to="/forgot-password" class="btn-primary w-full flex items-center justify-center py-2.5">
          Request a new link
        </router-link>
      </div>

      <div v-else-if="done" class="surface-card rounded-2xl p-6 space-y-4">
        <p class="text-sm text-muted">Password changed. Please sign in with your new password.</p>
        <router-link to="/login?reset=success" class="btn-primary w-full flex items-center justify-center py-2.5">
          Go to Sign In
        </router-link>
      </div>

      <form v-else class="surface-card rounded-2xl p-6 space-y-4" @submit.prevent="handleSubmit">
        <div>
          <label for="new-password" class="block text-xs font-bold text-theme mb-1.5 uppercase tracking-wide">New password</label>
          <input
            id="new-password"
            v-model="password"
            type="password"
            autocomplete="new-password"
            class="input-base py-2.5"
            :disabled="isLoading"
            placeholder="Minimum 8 characters"
            required
            minlength="8"
            autofocus
          />
        </div>
        <div>
          <label for="confirm-password" class="block text-xs font-bold text-theme mb-1.5 uppercase tracking-wide">Confirm password</label>
          <input
            id="confirm-password"
            v-model="confirm"
            type="password"
            autocomplete="new-password"
            class="input-base py-2.5"
            :disabled="isLoading"
            placeholder="Repeat new password"
            required
            minlength="8"
          />
        </div>

        <p v-if="error" class="text-sm text-red-500 dark:text-red-400">{{ error }}</p>

        <router-link v-if="invalidLink" to="/forgot-password" class="btn-primary w-full flex items-center justify-center py-2.5">
          Request a new link
        </router-link>

        <button type="submit" class="btn-primary w-full" :disabled="isLoading || !password || !confirm">
          {{ isLoading ? 'Saving…' : 'Reset Password' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';
import { useRoute } from 'vue-router';
import { authApi } from '../api';

const route = useRoute();
const token = computed(() => (typeof route.query.token === 'string' ? route.query.token : ''));

const password = ref('');
const confirm = ref('');
const isLoading = ref(false);
const error = ref('');
const done = ref(false);
const invalidLink = ref(false);

const handleSubmit = async () => {
  error.value = '';
  if (password.value.length < 8) {
    error.value = 'Password must be at least 8 characters.';
    return;
  }
  if (password.value !== confirm.value) {
    error.value = 'Passwords do not match.';
    return;
  }
  isLoading.value = true;
  try {
    await authApi.resetPassword(token.value, password.value);
    done.value = true;
  } catch (err) {
    const code = err.response?.data?.code;
    if (code === 'invalid_token') {
      error.value = 'This reset link is invalid or has expired. Request a new one.';
      invalidLink.value = true;
    } else if (err.response?.status === 400) {
      error.value = err.response?.data?.error || 'Password must be at least 8 characters.';
    } else {
      error.value = 'Request failed. Check your connection and try again.';
    }
  } finally {
    isLoading.value = false;
  }
};
</script>
