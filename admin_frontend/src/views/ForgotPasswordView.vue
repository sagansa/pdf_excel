<template>
  <div class="login-page min-h-screen flex items-center justify-center p-4">
    <div class="w-full max-w-sm">
      <div class="text-center mb-8">
        <div class="mx-auto mb-4 w-12 h-12 rounded-2xl flex items-center justify-center text-white text-lg font-bold shadow-lg"
             style="background: linear-gradient(135deg, var(--color-primary), var(--color-primary-strong));">S</div>
        <h1 class="text-2xl font-bold text-theme">StatementX</h1>
        <p class="text-sm text-muted mt-1">Reset your password</p>
      </div>

      <form v-if="!sent" class="surface-card rounded-2xl p-6 space-y-4" @submit.prevent="handleSubmit">
        <div>
          <label for="email" class="block text-xs font-bold text-theme mb-1.5 uppercase tracking-wide">Email</label>
          <input
            id="email"
            v-model="email"
            type="email"
            autocomplete="email"
            class="input-base py-2.5"
            :disabled="isLoading"
            placeholder="you@company.com"
            required
            autofocus
          />
        </div>

        <p v-if="error" class="text-sm text-red-500 dark:text-red-400">{{ error }}</p>

        <button type="submit" class="btn-primary w-full" :disabled="isLoading || !email">
          {{ isLoading ? 'Sending…' : 'Send Reset Link' }}
        </button>
      </form>

      <div v-else class="surface-card rounded-2xl p-6 space-y-4">
        <p class="text-sm text-muted">
          If an account exists for that email, a reset link has been sent.
          Check your inbox (and spam folder). The link expires in 30 minutes.
        </p>
        <router-link to="/login" class="btn-primary w-full flex items-center justify-center py-2.5">
          Back to Sign In
        </router-link>
      </div>

      <p v-if="!sent" class="text-center mt-4">
        <router-link to="/login" class="text-xs text-muted hover:opacity-80">Back to sign in</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { authApi } from '../api';

const email = ref('');
const isLoading = ref(false);
const error = ref('');
const sent = ref(false);

const handleSubmit = async () => {
  isLoading.value = true;
  error.value = '';
  try {
    await authApi.forgotPassword(email.value.trim());
    sent.value = true;
  } catch (err) {
    const status = err.response?.status;
    if (status === 429) {
      error.value = err.response?.data?.error || 'Too many requests. Try again in a few minutes.';
    } else {
      error.value = 'Request failed. Check your connection and try again.';
    }
  } finally {
    isLoading.value = false;
  }
};
</script>
