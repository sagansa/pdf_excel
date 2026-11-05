import { defineStore } from 'pinia';
import { authApi } from '../api';

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    isAuthChecked: false,
  }),
  getters: {
    isAuthenticated: (state) => state.user !== null,
  },
  actions: {
    async login(email, password) {
      const response = await authApi.login(email, password);
      this.user = response.data.user;
      return this.user;
    },
    async logout() {
      try {
        await authApi.logout();
      } finally {
        this.user = null;
      }
    },
    async fetchMe() {
      try {
        const response = await authApi.me();
        this.user = response.data.user;
      } catch {
        this.user = null;
      } finally {
        this.isAuthChecked = true;
      }
      return this.user;
    },
  },
});
