import { defineStore } from 'pinia';
import { companyApi } from '../api';

export const useCompanyStore = defineStore('company', {
  state: () => ({
    companies: [],
    isLoading: false,
    error: null
  }),

  actions: {
    async fetchCompanies() {
      this.isLoading = true;
      try {
        const response = await companyApi.getCompanies();
        this.companies = response.data.companies || [];
      } catch (err) {
        this.error = err.message;
      } finally {
        this.isLoading = false;
      }
    },

    async createCompany(data) {
      this.isLoading = true;
      try {
        await companyApi.createCompany(data);
        await this.fetchCompanies(); // Refresh list
      } catch (err) {
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    async updateCompany(id, data) {
      this.isLoading = true;
      try {
        await companyApi.updateCompany(id, data);
        await this.fetchCompanies();
      } catch (err) {
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    async deleteCompany(id) {
      this.isLoading = true;
      try {
        await companyApi.deleteCompany(id);
        this.companies = this.companies.filter(c => c.id !== id);
      } catch (err) {
        throw err;
      } finally {
        this.isLoading = false;
      }
    }
  }
});
