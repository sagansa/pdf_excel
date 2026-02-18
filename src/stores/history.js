import { defineStore } from 'pinia';
import { historyApi, companyApi, marksApi, filterApi, coaApi } from '../api';

export const useHistoryStore = defineStore('history', {
  state: () => ({
    allTransactions: [],
    uploadSummary: [],
    companies: [],
    marks: [],
    coaList: [],
    isLoading: false,
    error: null,

    // Filters
    filters: {
        year: '',
        dateStart: '',
        dateEnd: '',
        asOfDate: '', // Added for PrepaidExpenses component
        bank: '',
        company: '',
        markStatus: [], // Array of mark IDs, 'marked', 'unmarked'
        coaIds: [], // Array of COA IDs
        search: '',
        dbCr: '', // 'DB', 'CR', or ''
        amountMin: null,
        amountMax: null
    },
    
    // Pagination
    currentPage: 1,
    itemsPerPage: 10,
    
    // Sorting
    sortConfig: { key: 'txn_date', direction: 'desc' },

    // Selection
    selectedTxnIds: []
  }),

  getters: {
    // Derived state: Filtered transactions
    filteredTransactions(state) {
       let result = [...state.allTransactions];
        const { year, dateStart, dateEnd, bank, company, markStatus, coaIds, search, dbCr, amountMin, amountMax } = state.filters;
       const searchLower = (search || '').toLowerCase();

        result = result.filter(t => {
            const txnDate = t.txn_date ? t.txn_date.split(' ')[0] : '';
            const txnYear = txnDate ? txnDate.split('-')[0] : '';

            // Date Filters
            if (year && txnYear !== year.toString()) return false;
            if (dateStart && txnDate < dateStart) return false;
            if (dateEnd && txnDate > dateEnd) return false;

            // Property Filters
            if (bank && t.bank_code !== bank) return false;
            // Note: company filter value checks ID
            if (company && t.company_id !== company) return false;

            // Mark Status (multi-select)
            if (markStatus && markStatus.length > 0) {
                const hasUnmarked = markStatus.includes('unmarked');
                const hasMarked = markStatus.includes('marked');
                const specificMarks = markStatus.filter(m => m !== 'marked' && m !== 'unmarked');

                let matches = false;

                // Check if transaction matches any selected mark criteria
                if (hasUnmarked && !t.mark_id) {
                    matches = true;
                }
                if (hasMarked && t.mark_id) {
                    matches = true;
                }
                if (specificMarks.length > 0 && t.mark_id && specificMarks.includes(t.mark_id)) {
                    matches = true;
                }

                if (!matches) return false;
            }

            // COA Filter (multi-select)
            if (coaIds && coaIds.length > 0) {
                if (!t.coa_id || !coaIds.includes(t.coa_id)) return false;
            }

            // Type Filter (DB/CR)
            if (dbCr && t.db_cr !== dbCr) return false;

            // Amount Filter
            if ((amountMin !== null && amountMin !== '') || (amountMax !== null && amountMax !== '')) {
                const amtString = (t.amount || '0').toString().replace(/,/g, '');
                const amt = parseFloat(amtString);
                
                if (amountMin !== null && amountMin !== '' && amt < parseFloat(amountMin)) return false;
                if (amountMax !== null && amountMax !== '' && amt > parseFloat(amountMax)) return false;
            }

            // Search
            if (search) {
                const desc = (t.description || '').toLowerCase();
                const amount = (t.amount || '').toString();
                const compName = (t.company_name || '').toLowerCase();
                
                if (!desc.includes(searchLower) && 
                    !amount.includes(searchLower) && 
                    !compName.includes(searchLower)) {
                    return false;
                }
            }
            return true;
       });
       
       // Sort
       result.sort((a, b) => {
           const dir = state.sortConfig.direction === 'asc' ? 1 : -1;
           const valA = a[state.sortConfig.key];
           const valB = b[state.sortConfig.key];
           if (valA < valB) return -1 * dir;
           if (valA > valB) return 1 * dir;
           return 0;
       });

       return result;
    },

    paginatedTransactions(state) {
        const start = (state.currentPage - 1) * state.itemsPerPage;
        const end = start + state.itemsPerPage;
        return this.filteredTransactions.slice(start, end);
    },

    totalPages(state) {
        return Math.ceil(this.filteredTransactions.length / state.itemsPerPage);
    },
    
    availableYears(state) {
        // Extract unique years from transactions
        const years = new Set(state.allTransactions.map(t => {
            return t.txn_date ? t.txn_date.split('-')[0] : null
        }).filter(y => y));
        return Array.from(years).sort().reverse();
    },

    sortedMarks(state) {
        return [...state.marks].sort((a, b) => {
            const nameA = (a.personal_use || '').toLowerCase();
            const nameB = (b.personal_use || '').toLowerCase();
            return nameA.localeCompare(nameB);
        });
    },

    coaOptions(state) {
        const categoryOrder = ['ASSET', 'LIABILITY', 'EQUITY', 'REVENUE', 'EXPENSE'];
        const options = [];

        categoryOrder.forEach((category, index) => {
            const coas = state.coaList.filter(coa => coa.category === category);
            if (coas.length > 0) {
                // Add separator before each category except the first
                if (index > 0 && options.length > 0) {
                    options.push({
                        id: `separator-${category}`,
                        type: 'separator',
                        category: category
                    });
                }
                coas.forEach(coa => {
                    options.push({
                        id: coa.id,
                        label: `${coa.code} - ${coa.name}`,
                        category: category
                    });
                });
            }
        });

        return options;
    },

    filteredTotal() {
        if (!this.filteredTransactions) return 0;
        return this.filteredTransactions.reduce((acc, t) => {
            const amt = Number(t.amount) || 0;
            return t.db_cr === 'CR' ? acc + amt : acc - amt;
        }, 0);
    },

    filteredDebitTotal() {
        if (!this.filteredTransactions) return 0;
        return this.filteredTransactions.reduce((acc, t) => {
            const amt = Number(t.amount) || 0;
            return t.db_cr === 'DB' ? acc + amt : acc;
        }, 0);
    },

    filteredCreditTotal() {
        if (!this.filteredTransactions) return 0;
        return this.filteredTransactions.reduce((acc, t) => {
            const amt = Number(t.amount) || 0;
            return t.db_cr === 'CR' ? acc + amt : acc;
        }, 0);
    },

    pageTotal() {
        if (!this.paginatedTransactions) return 0;
        return this.paginatedTransactions.reduce((acc, t) => {
            const amt = Number(t.amount) || 0;
            return t.db_cr === 'CR' ? acc + amt : acc - amt;
        }, 0);
    },

    pageDebitTotal() {
        if (!this.paginatedTransactions) return 0;
        return this.paginatedTransactions.reduce((acc, t) => {
            const amt = Number(t.amount) || 0;
            return t.db_cr === 'DB' ? acc + amt : acc;
        }, 0);
    },

    pageCreditTotal() {
        if (!this.paginatedTransactions) return 0;
        return this.paginatedTransactions.reduce((acc, t) => {
            const amt = Number(t.amount) || 0;
            return t.db_cr === 'CR' ? acc + amt : acc;
        }, 0);
    }
  },

  actions: {
    async loadData() {
      this.isLoading = true;
      try {
        // Load persistence filters first if not already loaded
        if (!this.allTransactions.length) {
            await this.loadFilters();
        }

        const [txnRes, compRes, markRes, coaRes] = await Promise.all([
            historyApi.getTransactions(),
            companyApi.getCompanies(),
            marksApi.getMarks(),
            coaApi.getCoa()
        ]);

        this.allTransactions = txnRes.data.transactions || [];
        this.companies = compRes.data.companies || [];
        this.marks = markRes.data.marks || [];
        this.coaList = coaRes.data.coa || [];
      } catch (err) {
        this.error = "Failed to load data";
        console.error(err);
      } finally {
        this.isLoading = false;
      }
    },
    
    async fetchUploadSummary() {
      this.isLoading = true;
      try {
        const res = await historyApi.getUploadSummary();
        this.uploadSummary = res.data.summary || [];
      } catch (err) {
        this.error = "Failed to load upload summary";
        console.error(err);
      } finally {
        this.isLoading = false;
      }
    },
    
    setFilter(key, value) {
        this.filters[key] = value;
        this.currentPage = 1; // Reset page on filter change
        this.saveFilters();
    },

    resetFilters() {
        this.filters = {
            year: '',
            dateStart: '',
            dateEnd: '',
            asOfDate: '',
            bank: '',
            company: '',
            markStatus: [],
            coaIds: [],
            search: '',
            dbCr: '', // 'DB', 'CR', or ''
            amountMin: null,
            amountMax: null
        };
        this.currentPage = 1;
        this.saveFilters();
    },

    async loadFilters() {
        try {
            const res = await filterApi.getFilters('history');
            if (res.data.filters && Object.keys(res.data.filters).length > 0) {
                this.filters = { ...this.filters, ...res.data.filters };
            }
        } catch (e) {
            console.error("Failed to load history filters:", e);
        }
    },

    async saveFilters() {
        try {
            // Simplified: Save on every significant change
            await filterApi.saveFilters('history', this.filters);
        } catch (e) {
            console.error("Failed to save history filters:", e);
        }
    },

    toggleSort(key) {
        if (this.sortConfig.key === key) {
            this.sortConfig.direction = this.sortConfig.direction === 'asc' ? 'desc' : 'asc';
        } else {
            this.sortConfig.key = key;
            this.sortConfig.direction = 'asc'; // Default new sort to asc
        }
    },

    toggleSelection(id) {
        const index = this.selectedTxnIds.indexOf(id);
        if (index > -1) {
            this.selectedTxnIds.splice(index, 1);
        } else {
            this.selectedTxnIds.push(id);
        }
    },

    selectAll() {
        const ids = this.filteredTransactions.map(t => t.id);
        this.selectedTxnIds = [...new Set([...this.selectedTxnIds, ...ids])];
    },

    deselectAll() {
        this.selectedTxnIds = [];
    },
    
    async assignMark(id, markId) {
        try {
            await historyApi.assignMark(id, markId);
            // Optimistic update or refetch
            const txn = this.allTransactions.find(t => t.id === id);
            if (txn) txn.mark_id = markId;
        } catch (e) {
            console.error(e);
            throw e;
        }
    },

    async bulkAssignMark(markId) {
        if (this.selectedTxnIds.length === 0) return;
        this.isLoading = true;
        try {
            await historyApi.bulkAssignMark(this.selectedTxnIds, markId);
            await this.loadData();
            this.selectedTxnIds = [];
        } catch (e) {
            console.error(e);
            throw e;
        } finally {
            this.isLoading = false;
        }
    },

    async assignCompany(id, companyId) {
        try {
            await historyApi.assignCompany(id, companyId);
            const txn = this.allTransactions.find(t => t.id === id);
            if (txn) txn.company_id = companyId;
        } catch (e) {
            console.error(e);
            throw e;
        }
    },

    async bulkAssignCompany(companyId) {
        if (this.selectedTxnIds.length === 0) return;
        this.isLoading = true;
        try {
            await historyApi.bulkAssignCompany(this.selectedTxnIds, companyId);
            await this.loadData();
            this.selectedTxnIds = [];
        } catch (e) {
            console.error(e);
            throw e;
        } finally {
            this.isLoading = false;
        }
    },

    async bulkDelete() {
        if (this.selectedTxnIds.length === 0) return;
        this.isLoading = true;
        try {
            await historyApi.bulkDelete(this.selectedTxnIds);
            await this.loadData();
            this.selectedTxnIds = [];
        } catch (e) {
            console.error(e);
            throw e;
        } finally {
            this.isLoading = false;
        }
    },

    async deleteBySourceFile(source_file, bank_code, company_id) {
        this.isLoading = true;
        try {
            await historyApi.deleteBySourceFile(source_file, bank_code, company_id);
            await this.fetchUploadSummary();
            // Also reload all transactions to reflect deletion in history view
            await this.loadData();
        } catch (e) {
            console.error(e);
            throw e;
        } finally {
            this.isLoading = false;
        }
    },

    async deleteTransaction(id) {
        this.isLoading = true;
        try {
            await historyApi.deleteTransaction(id);
            this.allTransactions = this.allTransactions.filter(t => t.id !== id);
            const index = this.selectedTxnIds.indexOf(id);
            if (index > -1) this.selectedTxnIds.splice(index, 1);
        } catch (e) {
            console.error(e);
            throw e;
        } finally {
            this.isLoading = false;
        }
    },

      async exportTransactions(format) {
        this.isLoading = true;
        try {
            // Prepare filters
            const params = {
                bank: this.filters.bank,
                company_id: this.filters.company,
                search: this.filters.search
            };

            // Handle dates
            if (this.filters.dateStart) params.start_date = this.filters.dateStart;
            if (this.filters.dateEnd) params.end_date = this.filters.dateEnd;

            // If year is selected but specific dates aren't, use year boundaries
            if (this.filters.year) {
                if (!params.start_date) params.start_date = `${this.filters.year}-01-01`;
                if (!params.end_date) params.end_date = `${this.filters.year}-12-31`;
            }

            const response = await historyApi.exportTransactions(format, params);
            const blob = new Blob([response.data], { type: response.headers.get('content-type') });
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            const extension = format === 'excel' ? 'xlsx' : 'csv';
            const date = new Date().toISOString().split('T')[0];
            link.download = `transactions_export_${date}.${extension}`;
            link.click();
            window.URL.revokeObjectURL(url);
        } catch (e) {
            console.error('Failed to export transactions:', e);
            throw e;
        } finally {
            this.isLoading = false;
        }
    },

    async fetchSplits(id) {
        try {
            const res = await historyApi.getSplits(id);
            return res.data.splits || [];
        } catch (e) {
            console.error(e);
            throw e;
        }
    },

    async saveSplits(id, splits) {
        this.isLoading = true;
        try {
            const res = await historyApi.saveSplits(id, splits);
            const txn = this.allTransactions.find(t => t.id === id);
            if (txn) {
                txn.is_split = splits.length > 0;
            }
            await this.loadData();
            return res.data;
        } catch (e) {
            console.error(e);
            throw e;
        } finally {
            this.isLoading = false;
        }
    },

    async importTransactions(file, bankCode, companyId) {
        this.isLoading = true;
        try {
            const res = await historyApi.importTransactions(file, bankCode, companyId);
            await this.loadData();
            return res.data;
        } catch (e) {
            console.error('Failed to import transactions:', e);
            throw e;
        } finally {
            this.isLoading = false;
        }
    }
  }
});
