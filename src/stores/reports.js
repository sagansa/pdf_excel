import { defineStore } from 'pinia';
import { reportsApi, filterApi } from '../api';
import axios from 'axios';

const api = axios.create({
  baseURL: '/api'
});

export const useReportsStore = defineStore('reports', {
  state: () => ({
    incomeStatement: null,
    balanceSheet: null,
    cashFlow: null,
    payrollSalarySummary: null,
    coaDetail: null,
    monthlyRevenue: null,
    monthlyRevenuePrevYear: null,
    availableYears: [],
    isLoading: false,
    error: null,
    // Filter states
    filters: {
      year: new Date().getFullYear().toString(),
      startDate: '',
      endDate: '',
      asOfDate: '',
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

    async fetchAvailableYears(companyId = null) {
      try {
        const response = await reportsApi.getAvailableReportYears(companyId);
        const years = Array.isArray(response?.data?.years) ? response.data.years : [];
        const normalized = years
          .map((year) => parseInt(year, 10))
          .filter((year) => !Number.isNaN(year))
          .sort((a, b) => b - a);

        this.availableYears = normalized.length > 0 ? normalized : [new Date().getFullYear()];
        return this.availableYears;
      } catch (err) {
        console.error('Failed to fetch available report years:', err);
        this.availableYears = [new Date().getFullYear()];
        return this.availableYears;
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
        console.log('ReportsStore: fetchMonthlyRevenue called with year:', year, 'companyId:', companyId);
        
        // Ensure year is a valid number
        const parsedYear = parseInt(year);
        if (isNaN(parsedYear)) {
          console.error('ReportsStore: Invalid year provided:', year);
          return { data: [], prev_year_data: [], year: parsedYear };
        }
        
        const params = new URLSearchParams({
          year: parsedYear.toString()
        });
        
        if (companyId) {
          params.append('company_id', companyId);
        }

        const response = await reportsApi.getMonthlyRevenue(parsedYear.toString(), companyId);
        console.log('ReportsStore: fetchMonthlyRevenue response:', response.data);
        this.monthlyRevenue = response.data.data;
        this.monthlyRevenuePrevYear = response.data.prev_year_data;
        console.log('ReportsStore: monthlyRevenue set to:', this.monthlyRevenue);
        return response.data;
      } catch (err) {
        this.error = err.response?.data?.error || 'Failed to fetch monthly revenue';
        console.error(err);
        throw new Error(this.error);
      } finally {
        this.isLoading = false;
      }
    },

    async fetchBalanceSheet(asOfDate, companyId = null) {
      this.isLoading = true;
      this.error = null;
      try {
        const response = await reportsApi.getBalanceSheet(asOfDate, companyId);
        this.balanceSheet = response.data;
        return response.data;
      } catch (err) {
        this.error = err.response?.data?.error || 'Failed to fetch balance sheet';
        console.error(err);
        throw new Error(this.error);
      } finally {
        this.isLoading = false;
      }
    },

    async fetchCashFlow(startDate, endDate, companyId = null) {
      this.isLoading = true;
      this.error = null;
      try {
        const response = await reportsApi.getCashFlow(startDate, endDate, companyId);
        this.cashFlow = response.data;
        return response.data;
      } catch (err) {
        this.error = err.response?.data?.error || 'Failed to fetch cash flow';
        console.error(err);
        throw new Error(this.error);
      } finally {
        this.isLoading = false;
      }
    },

    async fetchPayrollSalarySummary(startDate, endDate, companyId = null) {
      this.isLoading = true;
      this.error = null;
      try {
        const response = await reportsApi.getPayrollSalarySummary(startDate, endDate, companyId);
        this.payrollSalarySummary = response.data;
        return response.data;
      } catch (err) {
        this.error = err.response?.data?.error || 'Failed to fetch payroll salary summary';
        console.error(err);
        throw new Error(this.error);
      } finally {
        this.isLoading = false;
      }
    },

    async fetchAllReports() {
      this.isLoading = true;
      this.error = null;
      try {
        // Parallel fetch for all core reports
        await Promise.all([
          this.fetchIncomeStatement(this.filters.startDate, this.filters.endDate, this.filters.companyId),
          this.fetchBalanceSheet(this.filters.asOfDate, this.filters.companyId),
          this.fetchMonthlyRevenue(this.filters.year, this.filters.companyId),
          this.fetchCashFlow(this.filters.startDate, this.filters.endDate, this.filters.companyId),
          this.fetchPayrollSalarySummary(this.filters.startDate, this.filters.endDate, this.filters.companyId)
        ]);
        return true;
      } catch (err) {
        console.error("Error fetching all reports:", err);
        // Error state is already set by individual fetchers
        return false;
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
      this.cashFlow = null;
      this.payrollSalarySummary = null;
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
    },

    // Amortization Items Management
    async fetchAmortizationItems(year, companyId) {
      try {
        const res = await reportsApi.getAmortizationItems(year, companyId);
        return {
          items: res.data.items || [],
          totalAmount: res.data.total_amount || 0,
          calculated_total: res.data.calculated_total || 0,
          settings: res.data.settings || {}
        };
      } catch (e) {
        console.error("Failed to fetch amortization items:", e);
        return { items: [], totalAmount: 0, calculated_total: 0, settings: {} };
      }
    },

    async createAmortizationItem(data) {
      try {
        await reportsApi.createAmortizationItem(data);
        return true;
      } catch (e) {
        console.error("Failed to create amortization item:", e);
        throw e;
      }
    },

    async updateAmortizationItem(itemId, data) {
      try {
        await reportsApi.updateAmortizationItem(itemId, data);
        return true;
      } catch (e) {
        console.error("Failed to update amortization item:", e);
        throw e;
      }
    },

    async deleteAmortizationItem(itemId) {
      try {
        await reportsApi.deleteAmortizationItem(itemId);
        return true;
      } catch (e) {
        console.error("Failed to delete amortization item:", e);
        throw e;
      }
    },

    // Amortization Settings
    async fetchAmortizationSettings(companyId) {
      try {
        const res = await reportsApi.getAmortizationSettings(companyId);
        return res.data.settings || {};
      } catch (e) {
        console.error("Failed to fetch amortization settings:", e);
        return {};
      }
    },

    async saveAmortizationSettings(data) {
      try {
        await reportsApi.saveAmortizationSettings(data);
        return true;
      } catch (e) {
        console.error("Failed to save amortization settings:", e);
        throw e;
      }
    },

    async fetchAmortizationCoaCodes(companyId) {
      try {
        const res = await reportsApi.getAmortizationCoaCodes(companyId);
        return {
          coaCodes: res.data.coa_codes || ['5314'],
          coaDetails: res.data.coa_details || []
        };
      } catch (e) {
        console.error("Failed to fetch amortization COA codes:", e);
        return { coaCodes: ['5314'], coaDetails: [] };
      }
    },

    async saveFilters() {
      try {
        const filtersToSave = {
          ...this.filters,
          savedAt: new Date().toISOString()
        };
        await filterApi.saveFilters('reports', filtersToSave);
        console.log('Filters saved:', filtersToSave);
        return true;
      } catch (e) {
        console.error("Failed to save filters:", e);
        throw e;
      }
    }
  }
});
