import { defineStore } from 'pinia';
import { reportsApi, filterApi } from '../api';
import axios from 'axios';

const api = axios.create({
  baseURL: '/api'
});

export const useReportsStore = defineStore('reports', {
  state: () => ({
    incomeStatement: null,
    coaDetail: null,
    monthlyRevenue: null,
    monthlyRevenuePrevYear: null,
    isLoading: false,
    error: null,
    // Filter states
    filters: {
      year: new Date().getFullYear().toString(),
      startDate: '',
      endDate: '',
      companyId: null
    }
  }),

  getters: {
    // Calculate totals
    totalRevenue: (state) => {
      return state.incomeStatement?.total_revenue || 0;
    },
    
    totalExpenses: (state) => {
      return state.incomeStatement?.total_expenses || 0;
    },
    
    netIncome: (state) => {
      return state.incomeStatement?.net_income || 0;
    },

    // Check if we have data
    hasIncomeStatement: (state) => {
      return state.incomeStatement !== null;
    }
  },

  actions: {
    setFilters(filters) {
      this.filters = { ...this.filters, ...filters };
      this.saveFilters();
    },

    async loadFilters() {
      try {
        const res = await filterApi.getFilters('reports');
        if (res.data.filters && Object.keys(res.data.filters).length > 0) {
          this.filters = { ...this.filters, ...res.data.filters };
        }
      } catch (e) {
        console.error("Failed to load reports filters:", e);
      }
    },

    async saveFilters() {
      try {
        await filterApi.saveFilters('reports', this.filters);
      } catch (e) {
        console.error("Failed to save reports filters:", e);
      }
    },

    async fetchIncomeStatement(startDate, endDate, companyId = null) {
      this.isLoading = true;
      this.error = null;
      
      try {
        const params = new URLSearchParams({
          start_date: startDate,
          end_date: endDate
        });
        
        if (companyId) {
          params.append('company_id', companyId);
        }

        const response = await reportsApi.getIncomeStatement(startDate, endDate, companyId);
        this.incomeStatement = response.data;
        
        // Update filters
        this.filters.startDate = startDate;
        this.filters.endDate = endDate;
        this.filters.companyId = companyId;
        
        return response.data;
      } catch (err) {
        this.error = err.response?.data?.error || 'Failed to fetch income statement';
        console.error(err);
        throw new Error(this.error);
      } finally {
        this.isLoading = false;
      }
    },

    async fetchCoaDetail(coaId, startDate = null, endDate = null, companyId = null) {
      this.isLoading = true;
      this.error = null;
      
      try {
        const params = new URLSearchParams({
          coa_id: coaId
        });
        
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);
        if (companyId) params.append('company_id', companyId);

        const response = await api.get(`/reports/coa-detail?${params}`);
        this.coaDetail = response.data;
        return response.data;
      } catch (err) {
        this.error = err.response?.data?.error || 'Failed to fetch COA detail';
        console.error(err);
        throw new Error(this.error);
      } finally {
        this.isLoading = false;
      }
    },

    async fetchMonthlyRevenue(year, companyId = null) {
      this.isLoading = true;
      this.error = null;
      try {
        const params = new URLSearchParams({
          year: year
        });
        
        if (companyId) {
          params.append('company_id', companyId);
        }

        const response = await reportsApi.getMonthlyRevenue(year, companyId);
        this.monthlyRevenue = response.data.data;
        this.monthlyRevenuePrevYear = response.data.prev_year_data;
        return response.data;
      } catch (err) {
        this.error = err.response?.data?.error || 'Failed to fetch monthly revenue';
        console.error(err);
        throw new Error(this.error);
      } finally {
        this.isLoading = false;
      }
    },

    async exportReport(reportType, format, filters) {
      this.isLoading = true;
      this.error = null;
      try {
        const response = await api.post('/reports/export', {
          report_type: reportType,
          format: format,
          filters: filters
        }, {
          responseType: 'blob' // Important for file download
        });
        
        // Create download link
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        
        // Extract filename from header or default
        const contentDisposition = response.headers['content-disposition'];
        let filename = `report.${format === 'excel' ? 'xlsx' : 'xml'}`;
        if (contentDisposition) {
          const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
          if (filenameMatch.length === 2)
            filename = filenameMatch[1];
        }
        
        link.setAttribute('download', filename);
        document.body.appendChild(link);
        link.click();
        link.remove();
        
        return true;
      } catch (err) {
        this.error = 'Failed to export report';
        console.error(err);
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    clearReports() {
      this.incomeStatement = null;
      this.coaDetail = null;
      this.error = null;
    },

    // Specific persistence for Monthly Revenue View
    async loadMonthlyRevenueFilters() {
      try {
        const res = await filterApi.getFilters('monthly_revenue');
        return res.data.filters || {};
      } catch (e) {
        console.error("Failed to load monthly revenue filters:", e);
        return {};
      }
    },

    async saveMonthlyRevenueFilters(filters) {
      try {
        await filterApi.saveFilters('monthly_revenue', filters);
      } catch (e) {
        console.error("Failed to save monthly revenue filters:", e);
      }
    },

    async fetchInventoryBalances(year, companyId) {
      try {
        const res = await reportsApi.getInventoryBalances(year, companyId);
        return res.data.balance || {};
      } catch (e) {
        console.error("Failed to fetch inventory balances:", e);
        return {};
      }
    },

    async saveInventoryBalances(data) {
      try {
        await reportsApi.saveInventoryBalances(data);
        return true;
      } catch (e) {
        console.error("Failed to save inventory balances:", e);
        throw e;
      }
    }
  }
});
