import { defineStore } from 'pinia';
import { hppApi } from '../api';

export const useHppBatchStore = defineStore('hppBatch', {
  state: () => ({
    batches: [],
    currentBatch: null,
    linkableTransactions: [],
    isLoading: false,
    error: null
  }),
  actions: {
    async fetchBatches(companyId) {
      this.isLoading = true;
      try {
        const response = await hppApi.getBatches(companyId);
        this.batches = response.data.batches || [];
      } catch (err) {
        this.error = err.message;
      } finally {
        this.isLoading = false;
      }
    },
    async fetchBatchDetails(batchId) {
      this.isLoading = true;
      try {
        const response = await hppApi.getBatchDetails(batchId);
        this.currentBatch = response.data;
        return response.data;
      } catch (err) {
        this.error = err.message;
        throw err;
      } finally {
        this.isLoading = false;
      }
    },
    async fetchLinkableTransactions(companyId, startDate, endDate) {
      this.isLoading = true;
      try {
        const response = await hppApi.getLinkableTransactions(companyId, startDate, endDate);
        this.linkableTransactions = response.data.transactions || [];
      } catch (err) {
        this.error = err.message;
      } finally {
        this.isLoading = false;
      }
    },
    async saveBatch(data) {
      this.isLoading = true;
      try {
        console.log('Store: Saving batch with data:', data);
        const response = await hppApi.saveBatch(data);
        console.log('Store: Batch saved response:', response.data);
        // Refresh batches if we have a company ID context? Actually better to let the component decide when to refresh
        return response.data;
      } catch (err) {
        console.error('Store: Error saving batch:', err);
        this.error = err.response?.data?.error || err.message || 'Unknown error';
        throw err;
      } finally {
        this.isLoading = false;
      }
    },
    async deleteBatch(batchId) {
      this.isLoading = true;
      try {
        await hppApi.deleteBatch(batchId);
        this.batches = this.batches.filter(b => b.id !== batchId);
      } catch (err) {
        this.error = err.message;
        throw err;
      } finally {
        this.isLoading = false;
      }
    }
  }
});
