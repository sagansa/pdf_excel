import { defineStore } from 'pinia';
import { productApi } from '../api';

export const useProductStore = defineStore('product', {
  state: () => ({
    products: [],
    isLoading: false,
    error: null
  }),

  actions: {
    async fetchProducts(companyId) {
      this.isLoading = true;
      try {
        const response = await productApi.getProducts(companyId);
        this.products = response.data.products || [];
      } catch (err) {
        this.error = err.message;
      } finally {
        this.isLoading = false;
      }
    },

    async createProduct(data) {
      this.isLoading = true;
      try {
        await productApi.createProduct(data);
        await this.fetchProducts(data.company_id); // Refresh list
      } catch (err) {
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    async updateProduct(id, data) {
      this.isLoading = true;
      try {
        await productApi.updateProduct(id, data);
        await this.fetchProducts(data.company_id);
      } catch (err) {
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    async deleteProduct(id, companyId) {
      this.isLoading = true;
      try {
        await productApi.deleteProduct(id);
        await this.fetchProducts(companyId);
      } catch (err) {
        throw err;
      } finally {
        this.isLoading = false;
      }
    }
  }
});
