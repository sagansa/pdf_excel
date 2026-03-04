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
