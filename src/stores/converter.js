import { defineStore } from 'pinia';
import { converterApi } from '../api';

export const useConverterStore = defineStore('converter', {
  state: () => ({
    isLoading: false,
    file: null,
    previewData: null,
    error: null,
    successMessage: null,
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
        try {
            const response = await converterApi.checkPassword(formData);
            return response.data;
        } catch (err) {
            console.error(err);
            return { password_protected: false };
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
            this.successMessage = "Conversion & DB Sync successful!";
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
    }
  }
});
