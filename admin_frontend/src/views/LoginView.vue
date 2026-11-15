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
          <div class="relative">
            <input
              id="password"
              v-model="password"
              :type="showPassword ? 'text' : 'password'"
              autocomplete="current-password"
              class="input-base py-2.5 pr-11"
              :disabled="isLoading"
              placeholder="Password"
              required
            />
            <button
              type="button"
              class="password-toggle"
              :class="{ 'password-toggle--disabled': isLoading }"
              :disabled="isLoading"
              :aria-label="showPassword ? 'Hide password' : 'Show password'"
              :aria-pressed="showPassword"
              :title="showPassword ? 'Hide password' : 'Show password'"
              @click="showPassword = !showPassword"
            >
              <i class="bi" :class="showPassword ? 'bi-eye-slash' : 'bi-eye'" aria-hidden="true"></i>
            </button>
          </div>
        </div>

        <p v-if="resetNotice" class="text-sm login-notice">{{ resetNotice }}</p>
        <p v-if="error" class="text-sm login-error">{{ error }}</p>

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
const showPassword = ref(false);
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

<style scoped>
.login-notice {
  color: var(--color-success);
}

.login-error {
  color: var(--color-danger);
}

.password-toggle {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  padding: 0 11px;
  border: none;
  background: none;
  font-size: 14px;
  color: var(--color-text-muted);
  cursor: pointer;
  transition: color 140ms ease;
}

.password-toggle:hover:not(:disabled) {
  color: var(--color-text);
}

.password-toggle:focus-visible {
  outline: 2px solid var(--color-primary-ring);
  outline-offset: 1px;
  border-radius: 8px;
}

.password-toggle--disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
