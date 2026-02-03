import { defineStore } from 'pinia';
import { historyApi, companyApi, marksApi } from '../api';

export const useHistoryStore = defineStore('history', {
  state: () => ({
    allTransactions: [],
    companies: [],
    marks: [],
    isLoading: false,
    error: null,
    
    // Filters
    filters: {
        year: '',
        dateStart: '',
        dateEnd: '',
        bank: '',
        company: '',
        markStatus: '', // 'marked', 'unmarked', or ''
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
       const { year, dateStart, dateEnd, bank, company, markStatus, search, dbCr, amountMin, amountMax } = state.filters;
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

            // Mark Status
            if (markStatus === 'marked' && !t.mark_id) return false;
            if (markStatus === 'unmarked' && t.mark_id) return false;

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
    }
  },

  actions: {
    async loadData() {
      this.isLoading = true;
      try {
        const [txnRes, compRes, markRes] = await Promise.all([
            historyApi.getTransactions(),
            companyApi.getCompanies(),
            marksApi.getMarks()
        ]);
        
        this.allTransactions = txnRes.data.transactions || [];
        this.companies = compRes.data.companies || [];
        this.marks = markRes.data.marks || [];
      } catch (err) {
        this.error = "Failed to load data";
        console.error(err);
      } finally {
        this.isLoading = false;
      }
    },
    
    setFilter(key, value) {
        this.filters[key] = value;
        this.currentPage = 1; // Reset page on filter change
    },

    resetFilters() {
        this.filters = {
            year: '',
            dateStart: '',
            dateEnd: '',
            bank: '',
            company: '',
            markStatus: '',
            search: '',
            dbCr: '',
            amountMin: null,
            amountMax: null
        };
        this.currentPage = 1;
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
    }
  }
});
