import { defineStore } from 'pinia';
import { converterApi } from '../api';

export const useConverterStore = defineStore('converter', {
  state: () => ({
    isLoading: false,
    file: null,
    previewData: null,
    error: null,
    successMessage: null,
    // Pass AI lokal yang ditunda setelah konversi (provider AI lokal — dijalankan dari browser).
    aiPendingLocal: null,
    isPasswordProtected: false,
    requiresPassword: false,
    pdfPassword: null
  }),
  
  actions: {
    setFile(file) {
      this.file = file;
      this.pdfPassword = null;
      this.error = null;
      this.successMessage = null;
      this.isPasswordProtected = false;
      this.requiresPassword = false;
    },

    async checkUploadName(fileName) {
      this.isLoading = true;
      this.error = null;
      try {
        const response = await converterApi.checkUploadName(fileName);
        return response.data;
      } catch (err) {
        const errorMsg = err.response?.data?.error || err.message || 'Failed to check uploaded file name';
        this.error = errorMsg;
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    async uploadFile(formData) {
      this.isLoading = true;
      this.error = null;
      try {
        const response = await converterApi.uploadFile(formData);
        return response.data;
      } catch (err) {
        const errorMsg = err.response?.data?.error || err.message || '';
        if (err.response?.data?.require_password || errorMsg.toLowerCase().includes('password')) {
            this.requiresPassword = true;
        }
        this.error = errorMsg;
        throw err;
      } finally {
        this.isLoading = false;
      }
    },
    
    async checkPassword(formData) {
        this.isLoading = true;
        this.error = null;
        try {
            const response = await converterApi.checkPassword(formData);
            this.isPasswordProtected = Boolean(response.data?.password_protected);
            return response.data;
        } catch (err) {
            const errorMsg = err.response?.data?.error || err.message || 'Failed to check PDF password protection';
            this.isPasswordProtected = false;
            this.error = errorMsg;
            throw err;
        } finally {
            this.isLoading = false;
        }
    },

    async confirmSave(formData) {
        this.isLoading = true;
        this.error = null;
        try {
            // Ensure preview is false
            formData.set('preview', 'false');
            const response = await converterApi.uploadFile(formData);
            // Header X-AI-Pass: hasil penjadwalan pass penandaan AI setelah konversi.
            // skipped-local = provider AI lokal: server tidak dapat memanggil LLM di
            // laptop user — saran dijalankan manual dari browser (banner + tombol).
            const aiHeader = response.headers?.['x-ai-pass'];
            const aiCount = Number(response.headers?.['x-ai-pass-count']) || 0;
            const aiIds = String(response.headers?.['x-ai-pass-ids'] || '')
              .split(',').map((id) => id.trim()).filter(Boolean);
            this.aiPendingLocal = aiHeader === 'skipped-local'
              ? { count: aiCount || aiIds.length, ids: aiIds }
              : null;
            this.successMessage = aiHeader === 'queued'
                ? `Conversion & DB Sync successful! AI sedang menandai ${aiCount ?? 'baru'} transaksi di latar belakang.`
                : aiHeader === 'skipped-local'
                    ? `Conversion & DB Sync successful! ${this.aiPendingLocal.count} transaksi baru siap untuk saran AI.`
                    : "Conversion & DB Sync successful!";
            return response.data;
        } catch (err) {
            const errorMsg = err.response?.data?.error || err.message || '';
        if (err.response?.data?.require_password || errorMsg.toLowerCase().includes('password')) {
            this.requiresPassword = true;
        }
            this.error = errorMsg;
            throw err;
        } finally {
            this.isLoading = false;
        }
    },

    /** Jalankan saran AI (via bridge browser) untuk transaksi hasil konversi yang ditunda. */
    async runLocalAiPass() {
      const pending = this.aiPendingLocal;
      if (!pending || pending.ids.length === 0) return null;
      const { useHistoryStore } = await import('./history');
      const historyStore = useHistoryStore();
      const summary = await historyStore.aiSuggestSelected(pending.ids);
      this.aiPendingLocal = null;
      return summary;
    }
  }
});
