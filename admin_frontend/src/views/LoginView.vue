<template>
  <div class="login-page min-h-screen flex items-center justify-center p-4">
    <div class="w-full max-w-sm">
      <div class="text-center mb-8">
        <div class="mx-auto mb-4 w-12 h-12 rounded-2xl flex items-center justify-center text-white text-lg font-bold shadow-lg"
             style="background: linear-gradient(135deg, var(--color-primary), var(--color-primary-strong));">S</div>
        <h1 class="text-2xl font-bold text-theme">StatementX</h1>
        <p class="text-sm text-muted mt-1">Sign in to the operations console</p>
      </div>

      <form class="surface-card rounded-2xl p-6 space-y-4" @submit.prevent="handleSubmit">
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

        <div>
          <label for="password" class="block text-xs font-bold text-theme mb-1.5 uppercase tracking-wide">Password</label>
          <input
            id="password"
            v-model="password"
            type="password"
            autocomplete="current-password"
            class="input-base py-2.5"
            :disabled="isLoading"
            placeholder="Password"
            required
          />
        </div>

        <p v-if="resetNotice" class="text-sm text-green-600 dark:text-green-400">{{ resetNotice }}</p>
        <p v-if="error" class="text-sm text-red-500 dark:text-red-400">{{ error }}</p>

        <button
          type="submit"
          class="btn-primary w-full"
          :disabled="isLoading || !email || !password"
        >
          {{ isLoading ? 'Signing in…' : 'Sign In' }}
        </button>

        <div class="text-center">
          <router-link to="/forgot-password" class="text-xs text-muted hover:opacity-80">
            Forgot password?
          </router-link>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '../stores/auth';

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();

const email = ref('');
const password = ref('');
const isLoading = ref(false);
const error = ref('');
const resetNotice = ref(
  route.query.reset === 'success'
    ? 'Password changed. Please sign in with your new password.'
    : ''
);

const handleSubmit = async () => {
  isLoading.value = true;
  error.value = '';
  try {
    await auth.login(email.value.trim(), password.value);
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/';
    router.push(redirect);
  } catch (err) {
    const status = err.response?.status;
    if (status === 429) {
      error.value = err.response?.data?.error || 'Too many attempts. Try again in a few minutes.';
    } else if (status === 401) {
      error.value = err.response?.data?.error || 'Invalid email or password';
    } else {
      error.value = 'Login failed. Check your connection and try again.';
    }
  } finally {
    isLoading.value = false;
  }
};
</script>
