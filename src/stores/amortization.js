import { defineStore } from 'pinia';
import axios from 'axios';

const api = axios.create({
  baseURL: '/api'
});

export const useAmortizationStore = defineStore('amortization', {
  state: () => ({
    assetGroups: [],
    assets: [],
    calculations: [],
    settings: {},
    isLoading: false,
    error: null
  }),

  getters: {
    groupedAssetGroups: (state) => {
      const grouped = { Tangible: [], Intangible: [], Building: [] };
      state.assetGroups.forEach(group => {
        if (grouped[group.asset_type]) {
          grouped[group.asset_type].push(group);
        }
      });
      return grouped;
    },

    totalAmortization: (state) => {
      return state.calculations.reduce((sum, calc) => sum + calc.annual_amortization, 0);
    }
  },

  actions: {
    // Asset Groups
    async fetchAssetGroups(companyId, assetType = null) {
      this.isLoading = true;
      try {
        const params = {};
        if (companyId) params.company_id = companyId;
        if (assetType) params.asset_type = assetType;
        
        const response = await api.get('/amortization/asset-groups', { params });
        this.assetGroups = response.data.groups || [];
        return this.assetGroups;
      } catch (err) {
        this.error = err.response?.data?.error || 'Failed to fetch asset groups';
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    async createAssetGroup(data) {
      try {
        const response = await api.post('/amortization/asset-groups', data);
        return response.data;
      } catch (err) {
        throw new Error(err.response?.data?.error || 'Failed to create asset group');
      }
    },

    async updateAssetGroup(groupId, data) {
      try {
        const response = await api.put(`/amortization/asset-groups/${groupId}`, data);
        return response.data;
      } catch (err) {
        throw new Error(err.response?.data?.error || 'Failed to update asset group');
      }
    },

    // Assets
    async fetchAssets(companyId, filters = {}) {
      this.isLoading = true;
      try {
        const params = { company_id: companyId, ...filters };
        const response = await api.get('/amortization/assets', { params });
        this.assets = response.data.assets || [];
        return this.assets;
      } catch (err) {
        this.error = err.response?.data?.error || 'Failed to fetch assets';
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    async createAsset(data) {
      try {
        const response = await api.post('/amortization/assets', data);
        return response.data;
      } catch (err) {
        throw new Error(err.response?.data?.error || 'Failed to create asset');
      }
    },

    async updateAsset(assetId, data) {
      try {
        const response = await api.put(`/amortization/assets/${assetId}`, data);
        return response.data;
      } catch (err) {
        throw new Error(err.response?.data?.error || 'Failed to update asset');
      }
    },

    async deleteAsset(assetId) {
      try {
        const response = await api.delete(`/amortization/assets/${assetId}`);
        return response.data;
      } catch (err) {
        throw new Error(err.response?.data?.error || 'Failed to delete asset');
      }
    },

    // Calculations
    async calculateAmortization(companyId, year) {
      this.isLoading = true;
      try {
        const response = await api.post('/amortization/calculate', {
          company_id: companyId,
          year: year
        });
        this.calculations = response.data.calculations || [];
        return response.data;
      } catch (err) {
        this.error = err.response?.data?.error || 'Failed to calculate amortization';
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    async getAmortizationSummary(companyId, year) {
      try {
        const response = await api.get('/amortization/summary', {
          params: { company_id: companyId, year: year }
        });
        return response.data;
      } catch (err) {
        throw new Error(err.response?.data?.error || 'Failed to get amortization summary');
      }
    },

    // Settings
    async fetchAmortizationSettings(companyId) {
      try {
        const response = await api.get('/amortization/settings', {
          params: companyId ? { company_id: companyId } : {}
        });
        this.settings = response.data.settings || {};
        return this.settings;
      } catch (err) {
        console.error("Failed to fetch settings:", err);
        return {};
      }
    },

    async saveAmortizationSettings(data) {
      try {
        const response = await api.post('/amortization/settings', data);
        return response.data;
      } catch (err) {
        throw new Error(err.response?.data?.error || 'Failed to save settings');
      }
    },

    async getAmortizationCoaCodes(companyId) {
      try {
        const response = await api.get('/amortization/coa-codes', {
          params: companyId ? { company_id: companyId } : {}
        });
        return {
          coaCodes: response.data.coa_codes || ['5314'],
          coaDetails: response.data.coa_details || []
        };
      } catch (err) {
        console.error("Failed to fetch COA codes:", err);
        return { coaCodes: ['5314'], coaDetails: [] };
      }
    },

    // Mark-based amortization methods
    async getMarkSettings(companyId) {
      try {
        const response = await api.get('/amortization/mark-settings', {
          params: companyId ? { company_id: companyId } : {}
        });
        return response.data;
      } catch (err) {
        console.error("Failed to fetch mark settings:", err);
        return {
          settings: {
            use_mark_based_amortization: false,
            amortization_asset_marks: ["pembelian aset perusahaan - berwujud", "pembelian aset perusahaan - tidak berwujud", "pembelian bangunan"],
            default_asset_useful_life: "5",
            default_amortization_rate: "20.00"
          },
          available_marks: []
        };
      }
    },

    async saveMarkSettings(data) {
      try {
        const response = await api.post('/amortization/mark-settings', data);
        return response.data;
      } catch (err) {
        throw new Error(err.response?.data?.error || 'Failed to save mark settings');
      }
    },

    async createMarkMapping(data) {
      try {
        const response = await api.post('/amortization/mark-mapping', {
          mark_id: data.mark_id,
          asset_type: data.asset_type,
          useful_life_years: data.useful_life_years,
          amortization_rate: data.amortization_rate,
          asset_group_id: data.asset_group_id || null,
          is_deductible_50_percent: data.is_deductible_50_percent || false
        });
        return response.data;
      } catch (err) {
        throw new Error(err.response?.data?.error || 'Failed to create mark mapping');
      }
    },

    async updateMarkIsAsset(markId, isAsset) {
      try {
        const response = await api.put(`/marks/${markId}/is-asset`, { is_asset: isAsset });
        return response.data;
      } catch (err) {
        throw new Error(err.response?.data?.error || 'Failed to update mark');
      }
    },

    // Amortization Items (Mark-based)
    async fetchAmortizationEligibleMarks(companyId) {
      try {
        const response = await api.get('/marks/amortization-eligible', {
          params: { company_id: companyId }
        });
        return response.data;
      } catch (err) {
        console.error("Failed to fetch amortization eligible marks:", err);
        return { marks: [] };
      }
    },

    async fetchAmortizationItems(companyId, year) {
      try {
        const response = await api.get('/amortization-items', {
          params: { company_id: companyId, year }
        });
        return response.data;
      } catch (err) {
        throw new Error(err.response?.data?.error || 'Failed to fetch amortization items');
      }
    },

    async createAmortizationItem(data) {
      try {
        const response = await api.post('/amortization-items', data);
        return response.data;
      } catch (err) {
        throw new Error(err.response?.data?.error || 'Failed to create amortization item');
      }
    },

    async updateAmortizationItem(itemId, data) {
      try {
        const response = await api.put(`/amortization-items/${itemId}`, data);
        return response.data;
      } catch (err) {
        throw new Error(err.response?.data?.error || 'Failed to update amortization item');
      }
    },

    async deleteAmortizationItem(itemId) {
      try {
        await api.delete(`/amortization-items/${itemId}`);
        return { success: true };
      } catch (err) {
        throw new Error(err.response?.data?.error || 'Failed to delete amortization item');
      }
    },

    async fetchAmortizationEligibleMarks(companyId) {
      try {
        const response = await api.get('/marks/amortization-eligible', {
          params: { company_id: companyId }
        });
        return response.data;
      } catch (err) {
        console.error("Failed to fetch amortization eligible marks:", err);
        return { marks: [] };
      }
    },

    async generateAmortizationJournals(data) {
      try {
        const response = await api.post('/amortization-items/generate-journal', data);
        return response.data;
      } catch (err) {
        throw new Error(err.response?.data?.error || 'Failed to generate amortization journals');
      }
    }
  }
});
