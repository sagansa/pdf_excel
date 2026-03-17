import { defineStore } from 'pinia';
import { historyApi, companyApi, marksApi, filterApi, coaApi } from '../api';

const normalizeDbCr = (value) => {
    const raw = String(value || '').trim().toUpperCase();
    if (!raw) return '';

    if (raw === 'CR' || raw === 'CREDIT' || raw === 'KREDIT' || raw === 'K') {
        return 'CR';
    }
    if (raw === 'DB' || raw === 'DEBIT' || raw === 'D' || raw === 'DE') {
        return 'DB';
    }
    if (raw.startsWith('CR') || raw.includes('CREDIT') || raw.startsWith('K')) {
        return 'CR';
    }
    if (raw.startsWith('DB') || raw.startsWith('DE') || raw.includes('DEBIT')) {
        return 'DB';
    }

    return '';
};

const normalizeId = (value) => {
    if (value === null || value === undefined) return '';
    return String(value).trim();
};

const toNumeric = (value) => {
    if (value === null || value === undefined || value === '') return 0;
    if (typeof value === 'number') return value;
    const cleaned = String(value).replace(/,/g, '');
    const parsed = Number(cleaned);
    return Number.isFinite(parsed) ? parsed : 0;
};

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
    selectedTxnIds: [],
    filterResetToken: 0
  }),

  getters: {
    // Derived state: Filtered transactions
    filteredTransactions(state) {
       let result = [...state.allTransactions];
       const { year, dateStart, dateEnd, bank, company, markStatus, coaIds, search, dbCr, amountMin, amountMax } = state.filters;
       const searchLower = (search || '').toLowerCase();
       const selectedDbCr = normalizeDbCr(dbCr);
       const selectedCoaIds = new Set((coaIds || []).map(id => String(id)));

        result = result.filter(t => {
            const txnDate = t.txn_date ? t.txn_date.split(' ')[0] : '';
            const txnYear = txnDate ? txnDate.split('-')[0] : '';

            // Date Filters
            if (year && txnYear !== year.toString()) return false;
            if (dateStart && txnDate < dateStart) return false;
            if (dateEnd && txnDate > dateEnd) return false;

            // Property Filters
            if (bank && String(t.bank_code || '').trim() !== String(bank).trim()) return false;
            // Note: company filter value checks ID
            if (company && t.company_id !== company) return false;

            // Mark Status (multi-select)
            if (markStatus && markStatus.length > 0) {
                const hasUnmarked = markStatus.includes('unmarked');
                const hasMarked = markStatus.includes('marked');
                const hasMissingMark = markStatus.includes('missing_mark');
                const hasMultiMarked = markStatus.includes('multi_marked');
                const specificMarks = markStatus
                    .filter(m => !['marked', 'unmarked', 'missing_mark', 'multi_marked'].includes(m))
                    .map(m => String(m));

                const txnMarkId = normalizeId(t.mark_id);
                const relatedMarkIds = Array.isArray(t.related_mark_ids)
                    ? t.related_mark_ids.map(id => String(id))
                    : (txnMarkId ? [txnMarkId] : []);
                const isMissingMarkTxn = Boolean(t.has_missing_mark);
                const isMultiMarkedTxn = Boolean(t.is_multi_marked);
                const hasValidMarkTxn = Boolean(txnMarkId) && !isMissingMarkTxn;
                const isUnmarkedTxn = (!txnMarkId || isMissingMarkTxn) && !isMultiMarkedTxn;
                const isMarkedTxn = hasValidMarkTxn || isMultiMarkedTxn;

                let matches = false;

                // Exclusive modes should still continue evaluating other filters (search, amount, etc).
                if (hasUnmarked && !hasMarked && !hasMissingMark && !hasMultiMarked && specificMarks.length === 0) {
                    matches = isUnmarkedTxn;
                } else if (hasMarked && !hasUnmarked && !hasMissingMark && !hasMultiMarked && specificMarks.length === 0) {
                    matches = isMarkedTxn;
                } else {
                    // Check if transaction matches any selected mark criteria
                    if (hasUnmarked && isUnmarkedTxn) {
                        matches = true;
                    }
                    if (hasMarked && isMarkedTxn) {
                        matches = true;
                    }
                    if (hasMissingMark && isMissingMarkTxn) {
                        matches = true;
                    }
                    if (hasMultiMarked && isMultiMarkedTxn) {
                        matches = true;
                    }
                    if (specificMarks.length > 0 && relatedMarkIds.some(id => specificMarks.includes(id))) {
                        matches = true;
                    }
                }

                if (!matches) return false;
            }

            // COA Filter (multi-select)
            if (coaIds && coaIds.length > 0) {
                const txnCoaIds = Array.isArray(t.coa_ids) ? t.coa_ids.map(id => String(id)) : [];
                const hasMatchingCoa = txnCoaIds.some(id => selectedCoaIds.has(id));
                if (!hasMatchingCoa) return false;
            }

            // Type Filter (DB/CR)
            if (selectedDbCr) {
                const txnDbCr = normalizeDbCr(t.db_cr);
                if (txnDbCr !== selectedDbCr) return false;
            }

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
                const markText = `${t.internal_report || ''} ${t.personal_use || ''} ${t.tax_report || ''}`.toLowerCase();
                const sourceFile = (t.source_file || '').toLowerCase();
                const coaText = Array.isArray(t.coas)
                    ? t.coas.map(coa => `${coa.code || ''} ${coa.name || ''}`).join(' ').toLowerCase()
                    : '';
                
                if (!desc.includes(searchLower) && 
                    !amount.includes(searchLower) && 
                    !compName.includes(searchLower) &&
                    !markText.includes(searchLower) &&
                    !sourceFile.includes(searchLower) &&
                    !coaText.includes(searchLower)) {
                    return false;
                }
            }
            return true;
       });
       
       // Sort
       result.sort((a, b) => {
           const dir = state.sortConfig.direction === 'asc' ? 1 : -1;
           const valA = state.sortConfig.key === 'amount'
               ? toNumeric(a[state.sortConfig.key])
               : a[state.sortConfig.key];
           const valB = state.sortConfig.key === 'amount'
               ? toNumeric(b[state.sortConfig.key])
               : b[state.sortConfig.key];
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
        const marks = [...state.marks].sort((a, b) => {
            const nameA = (a.personal_use || '').toLowerCase();
            const nameB = (b.personal_use || '').toLowerCase();
            return nameA.localeCompare(nameB);
        });
        
        console.log('HistoryStore: sortedMarks computed, count:', marks.length);
        
        return marks;
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
            return normalizeDbCr(t.db_cr) === 'CR' ? acc + amt : acc - amt;
        }, 0);
    },

    filteredDebitTotal() {
        if (!this.filteredTransactions) return 0;
        return this.filteredTransactions.reduce((acc, t) => {
            const amt = Number(t.amount) || 0;
            return normalizeDbCr(t.db_cr) === 'DB' ? acc + amt : acc;
        }, 0);
    },

    filteredCreditTotal() {
        if (!this.filteredTransactions) return 0;
        return this.filteredTransactions.reduce((acc, t) => {
            const amt = Number(t.amount) || 0;
            return normalizeDbCr(t.db_cr) === 'CR' ? acc + amt : acc;
        }, 0);
    },

    pageTotal() {
        if (!this.paginatedTransactions) return 0;
        return this.paginatedTransactions.reduce((acc, t) => {
            const amt = Number(t.amount) || 0;
            return normalizeDbCr(t.db_cr) === 'CR' ? acc + amt : acc - amt;
        }, 0);
    },

    pageDebitTotal() {
        if (!this.paginatedTransactions) return 0;
        return this.paginatedTransactions.reduce((acc, t) => {
            const amt = Number(t.amount) || 0;
            return normalizeDbCr(t.db_cr) === 'DB' ? acc + amt : acc;
        }, 0);
    },

    pageCreditTotal() {
        if (!this.paginatedTransactions) return 0;
        return this.paginatedTransactions.reduce((acc, t) => {
            const amt = Number(t.amount) || 0;
            return normalizeDbCr(t.db_cr) === 'CR' ? acc + amt : acc;
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

        let transactions = txnRes.data.transactions || [];
        const marks = markRes.data.marks || [];
        const coas = coaRes.data.coa || [];
        const marksById = new Map(
            marks
                .filter(mark => normalizeId(mark.id))
                .map(mark => [normalizeId(mark.id), mark])
        );
        const coaIdByCode = new Map(
            coas
                .filter(coa => normalizeId(coa.code) && normalizeId(coa.id))
                .map(coa => [normalizeId(coa.code), normalizeId(coa.id)])
        );
        const mapCoaMapping = (mapping = {}) => {
            const code = normalizeId(mapping.code);
            const name = mapping.name || '';
            const type = normalizeId(mapping.type || mapping.mapping_type);
            const coaId = normalizeId(mapping.coa_id || mapping.id) || coaIdByCode.get(code) || '';
            return { id: coaId || '', coa_id: coaId || '', code, name, type };
        };
        const collectCoasFromMarkId = (markId, bucket, idSet, uniqSet) => {
            const normalizedMarkId = normalizeId(markId);
            if (!normalizedMarkId) return false;
            const mark = marksById.get(normalizedMarkId);
            if (!mark || !Array.isArray(mark.mappings)) return false;

            for (const mapping of mark.mappings) {
                const normalized = mapCoaMapping(mapping);
                const uniqKey = `${normalized.coa_id}|${normalized.code}|${normalized.name}|${normalized.type}`;
                if (uniqSet.has(uniqKey)) continue;
                uniqSet.add(uniqKey);
                bucket.push(normalized);
                if (normalized.coa_id) {
                    idSet.add(normalized.coa_id);
                }
            }

            return true;
        };
        
        // Debug: Check if parent_id is present in any transaction
        const sampleWithParent = transactions.find(t => t.parent_id);
        console.log('HistoryStore: Sample transaction with parent_id:', sampleWithParent ? {id: sampleWithParent.id, parent_id: sampleWithParent.parent_id} : 'None found');
        
        // Mark transactions that have splits
        console.log('HistoryStore: Checking for split transactions...');
        
        // Get all parent IDs of split transactions
        const parentIds = new Set();
        const childrenByParentId = new Map();
        for (const txn of transactions) {
          const parentId = normalizeId(txn.parent_id);
          if (parentId) {
            parentIds.add(parentId);
            if (!childrenByParentId.has(parentId)) {
                childrenByParentId.set(parentId, []);
            }
            childrenByParentId.get(parentId).push(txn);
          }
        }
        
        console.log('HistoryStore: Found', parentIds.size, 'unique parent IDs');
        
        // Mark transactions that have children
        for (const txn of transactions) {
          const txnId = normalizeId(txn.id);
          const txnMarkId = normalizeId(txn.mark_id);
          txn.is_split = txnId ? parentIds.has(txnId) : false;
          txn.has_missing_mark = Boolean(txnMarkId) && !marksById.has(txnMarkId);

          // Populate COA mappings from own mark + split child marks.
          const resolvedCoas = [];
          const resolvedCoaIds = new Set();
          const uniqCoas = new Set();
          const relatedMarkIds = new Set();

          const hasOwnValidMark = collectCoasFromMarkId(txnMarkId, resolvedCoas, resolvedCoaIds, uniqCoas);
          if (hasOwnValidMark) {
              relatedMarkIds.add(txnMarkId);
          }

          let splitMarkedCount = 0;
          if (txn.is_split) {
            const children = childrenByParentId.get(txnId) || [];
            for (const childTxn of children) {
                const childMarkId = normalizeId(childTxn.mark_id);
                const hasChildMark = collectCoasFromMarkId(childMarkId, resolvedCoas, resolvedCoaIds, uniqCoas);
                if (hasChildMark) {
                    splitMarkedCount += 1;
                    relatedMarkIds.add(childMarkId);
                }
            }
          }

          // Inherit COAs from linked manual journal
          const linkedManualId = normalizeId(txn.linked_manual_id);
          if (linkedManualId) {
            const manualChildren = childrenByParentId.get(linkedManualId) || [];
            const txnAmount = toNumeric(txn.amount);
            const txnDbCr = normalizeDbCr(txn.db_cr);
            
            // Look for matching lines in the manual journal (by amount only)
            for (const mChild of manualChildren) {
              const mAmount = toNumeric(mChild.amount);
              if (Math.abs(mAmount - txnAmount) < 0.01) {
                const mChildMarkId = normalizeId(mChild.mark_id);
                const hasMChildMark = collectCoasFromMarkId(mChildMarkId, resolvedCoas, resolvedCoaIds, uniqCoas);
                if (hasMChildMark) {
                  relatedMarkIds.add(mChildMarkId);
                  txn.is_linked_to_manual = true;
                }
              }
            }
          }

          if (txn.coa_id) {
              resolvedCoaIds.add(normalizeId(txn.coa_id));
          }

          txn.coas = resolvedCoas;
          txn.coa_ids = Array.from(resolvedCoaIds).filter(Boolean);
          txn.related_mark_ids = Array.from(relatedMarkIds);
          txn.is_multi_marked = txn.is_split && splitMarkedCount > 0;

          const normalizedDbCr = normalizeDbCr(txn.db_cr);
          if (normalizedDbCr) {
            txn.db_cr = normalizedDbCr;
          }
        }
        
        // Debug: Check a few transactions that should be marked as split
        const splitTxns = transactions.filter(t => t.is_split);
        console.log('HistoryStore: Marked', splitTxns.length, 'transactions as having splits');
        if (splitTxns.length > 0) {
            console.log('HistoryStore: Sample split transactions:', splitTxns.slice(0, 3).map(t => ({id: t.id, is_split: t.is_split, description: t.description?.substring(0, 50)})));
        }

        this.allTransactions = transactions;
        this.companies = compRes.data.companies || [];
        this.marks = marks;
        this.coaList = coas;
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
        this.filterResetToken += 1;
        this.saveFilters();
    },

    async loadFilters() {
        try {
            const res = await filterApi.getFilters('history');
            if (res.data.filters && Object.keys(res.data.filters).length > 0) {
                const nextFilters = { ...this.filters, ...res.data.filters };
                nextFilters.bank = nextFilters.bank || '';
                nextFilters.markStatus = Array.isArray(nextFilters.markStatus) ? nextFilters.markStatus : [];
                nextFilters.coaIds = Array.isArray(nextFilters.coaIds) ? nextFilters.coaIds : [];
                this.filters = nextFilters;
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
            if (txn) {
                const normalizedMarkId = normalizeId(markId);
                const matchedMark = normalizedMarkId
                    ? this.marks.find(m => normalizeId(m.id) === normalizedMarkId)
                    : null;

                txn.mark_id = normalizedMarkId || null;
                txn.has_missing_mark = Boolean(normalizedMarkId) && !matchedMark;

                if (matchedMark && Array.isArray(matchedMark.mappings)) {
                    const coaIdByCode = new Map(
                        (this.coaList || [])
                            .filter(coa => normalizeId(coa.code) && normalizeId(coa.id))
                            .map(coa => [normalizeId(coa.code), normalizeId(coa.id)])
                    );
                    txn.coas = matchedMark.mappings.map(mapping => {
                        const code = normalizeId(mapping.code);
                        const coaId = normalizeId(mapping.coa_id || mapping.id) || coaIdByCode.get(code) || '';
                        return {
                            ...mapping,
                            id: coaId || mapping.id || '',
                            coa_id: coaId
                        };
                    });
                    txn.coa_ids = txn.coas
                        .map(mapping => normalizeId(mapping.coa_id || mapping.id))
                        .filter(Boolean);
                    txn.related_mark_ids = [normalizeId(matchedMark.id)].filter(Boolean);
                } else {
                    txn.coas = [];
                    txn.coa_ids = txn.coa_id ? [normalizeId(txn.coa_id)] : [];
                    txn.related_mark_ids = [];
                }
            }
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
            
            // Reload all transactions to reflect the change in the table
            console.log('Company assigned, reloading transactions...');
            await this.loadData();
        } catch (e) {
            console.error('Failed to assign company:', e);
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

    async deleteBySourceFile(source_file, bank_code, company_id = undefined) {
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
                company_id: this.filters.company,
                search: this.filters.search,
                bank: this.filters.bank || undefined
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
            console.log('HistoryStore: fetchSplits response:', res.data);
            return res.data.splits || [];
        } catch (e) {
            console.error(e);
            throw e;
        }
    },

    async saveSplits(id, splits) {
        this.isLoading = true;
        try {
            console.log('HistoryStore: saveSplits called with id:', id, 'splits:', splits);
            const res = await historyApi.saveSplits(id, splits);
            console.log('HistoryStore: saveSplits response:', res.data);
            
            // Mark the transaction as split without reloading all data
            const txn = this.allTransactions.find(t => t.id === id);
            if (txn) {
                txn.is_split = splits.length > 0;
                console.log('HistoryStore: marked transaction as split:', txn.is_split);
            }
            
            // Don't reload all data - just mark as split
            return res.data;
        } catch (e) {
            console.error('HistoryStore: saveSplits error:', e);
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
