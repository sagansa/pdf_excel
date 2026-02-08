import { defineStore } from 'pinia';
import axios from 'axios';

const api = axios.create({
  baseURL: '/api'
});

export const useCoaStore = defineStore('coa', {
  state: () => ({
    coaList: [],
    isLoading: false,
    error: null
  }),

  getters: {
    // Group COA by category
    coaByCategory: (state) => {
      const grouped = {
        ASSET: [],
        LIABILITY: [],
        EQUITY: [],
        REVENUE: [],
        EXPENSE: []
      };
      
      state.coaList.forEach(coa => {
        if (grouped[coa.category]) {
          grouped[coa.category].push(coa);
        }
      });
      
      return grouped;
    },

    // Get COA options for dropdowns
    coaOptions: (state) => {
      return state.coaList.map(coa => ({
        value: coa.id,
        label: `${coa.code} - ${coa.name}`,
        category: coa.category
      }));
    }
  },

  actions: {
    async fetchCoa() {
      this.isLoading = true;
      this.error = null;
      try {
        const response = await api.get('/coa');
        this.coaList = response.data.coa || [];
      } catch (err) {
        this.error = err.response?.data?.error || 'Failed to fetch COA';
        console.error(err);
      } finally {
        this.isLoading = false;
      }
    },

    async createCoa(data) {
      try {
        const response = await api.post('/coa', data);
        await this.fetchCoa(); // Refresh list
        return response.data;
      } catch (err) {
        throw new Error(err.response?.data?.error || 'Failed to create COA');
      }
    },

    async updateCoa(id, data) {
      try {
        const response = await api.put(`/coa/${id}`, data);
        await this.fetchCoa(); // Refresh list
        return response.data;
      } catch (err) {
        throw new Error(err.response?.data?.error || 'Failed to update COA');
      }
    },

    async deleteCoa(id) {
      try {
        const response = await api.delete(`/coa/${id}`);
        await this.fetchCoa(); // Refresh list
        return response.data;
      } catch (err) {
        throw new Error(err.response?.data?.error || 'Failed to delete COA');
      }
    },

    // Mark-COA Mapping actions
    async fetchMarkMappings(markId) {
      try {
        const response = await api.get(`/marks/${markId}/coa-mappings`);
        return response.data.mappings || [];
      } catch (err) {
        console.error(err);
        return [];
      }
    },

    async createMapping(markId, coaId, mappingType, notes = null) {
      try {
        const response = await api.post(`/marks/${markId}/coa-mappings`, {
          coa_id: coaId,
          mapping_type: mappingType,
          notes
        });
        return response.data;
      } catch (err) {
        throw new Error(err.response?.data?.error || 'Failed to create mapping');
      }
    },

    async deleteMapping(mappingId) {
      try {
        const response = await api.delete(`/mark-coa-mappings/${mappingId}`);
        return response.data;
      } catch (err) {
        throw new Error(err.response?.data?.error || 'Failed to delete mapping');
      }
    }
  }
});
