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
    requiresPassword: false
  }),
  
  actions: {
    setFile(file) {
      this.file = file;
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
        this.error = err.response?.data?.error || err.message;
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
            return { param_protected: false };
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
            this.error = err.response?.data?.error || err.message;
            throw err;
        } finally {
            this.isLoading = false;
        }
    }
  }
});
