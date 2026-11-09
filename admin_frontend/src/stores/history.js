import { defineStore } from 'pinia';
import { historyApi, companyApi, marksApi, filterApi, coaApi, aiApi } from '../api';

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

// Ukuran chunk fetch transaksi & slice pemrosesan agar progress tetap bergerak
// dan UI tidak membeku saat dataset besar.
const TXN_CHUNK_SIZE = 2000;
const PROCESS_SLICE_SIZE = 400;
const yieldToUi = () => new Promise(resolve => setTimeout(resolve, 0));

// Debounce penyimpanan filter: satu panggilan API setelah ketikan berhenti,
// bukan satu panggilan per huruf.
let filterSaveTimer = null;

export const useHistoryStore = defineStore('history', {
  state: () => ({
    allTransactions: [],
    uploadSummary: [],
    uploadChecklist: null,
    checklistYear: new Date().getFullYear(),
    companies: [],
    marks: [],
    coaList: [],
    isLoading: false,
    error: null,

    // Progress fetch bertahap — persentase mengikuti pekerjaan nyata yang selesai.
    loadProgress: { active: false, phase: 'idle', percent: 0, loaded: 0, total: null, message: '' },
    hasLoadedOnce: false,

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
    filterResetToken: 0,

    // AI mark assist
    aiSettings: null,
    aiBusyTxnIds: [], // transaksi yang sedang diminta saran AI-nya
    aiBulkBusy: false,
    aiBulkProgress: { done: 0, total: 0 }
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
            // Hide child transactions for manual journals (since parent aggregates COAs)
            if (t.parent_id && t.bank_code === 'MANUAL') return false;

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
                const hasAiPending = markStatus.includes('ai_pending');
                const hasAiAuto = markStatus.includes('ai_auto');
                const hasAiAny = markStatus.includes('ai_any');
                const specificMarks = markStatus
                    .filter(m => !['marked', 'unmarked', 'missing_mark', 'multi_marked', 'ai_pending', 'ai_auto', 'ai_any'].includes(m))
                    .map(m => String(m));

                const txnMarkId = normalizeId(t.mark_id);
                const relatedMarkIds = Array.isArray(t.related_mark_ids)
                    ? t.related_mark_ids.map(id => String(id))
                    : (txnMarkId ? [txnMarkId] : []);
                const isMissingMarkTxn = Boolean(t.has_missing_mark);
                const isMultiMarkedTxn = Boolean(t.is_multi_marked);
                const isLinkedToManual = Boolean(t.is_linked_to_manual);
                const hasValidMarkTxn = (Boolean(txnMarkId) && !isMissingMarkTxn) || isLinkedToManual;
                const isUnmarkedTxn = (!txnMarkId || isMissingMarkTxn) && !isMultiMarkedTxn && !isLinkedToManual;
                const isMarkedTxn = hasValidMarkTxn || isMultiMarkedTxn;
                const isAiPendingTxn = t.ai_status === 'pending' && Boolean(t.ai_suggested_mark_id);
                const isAiAutoTxn = t.ai_status === 'auto_applied';
                const isAiAnyTxn = Boolean(t.ai_suggested_mark_id);

                let matches = false;

                // Exclusive modes should still continue evaluating other filters (search, amount, etc).
                if (hasUnmarked && !hasMarked && !hasMissingMark && !hasMultiMarked && !hasAiPending && !hasAiAuto && !hasAiAny && specificMarks.length === 0) {
                    matches = isUnmarkedTxn;
                } else if (hasMarked && !hasUnmarked && !hasMissingMark && !hasMultiMarked && !hasAiPending && !hasAiAuto && !hasAiAny && specificMarks.length === 0) {
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
                    if (hasAiPending && isAiPendingTxn) {
                        matches = true;
                    }
                    if (hasAiAuto && isAiAutoTxn) {
                        matches = true;
                    }
                    if (hasAiAny && isAiAnyTxn) {
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

    // Jumlah filter aktif — dipakai badge toggle filter lanjutan & empty state.
    activeFilterCount(state) {
        const f = state.filters;
        let count = 0;
        if (f.search) count += 1;
        if (f.year || f.dateStart || f.dateEnd) count += 1; // grup Periode = 1
        if (f.company) count += 1;
        if (f.bank) count += 1;
        if (f.dbCr) count += 1;
        if (f.amountMin !== null && f.amountMin !== '') count += 1;
        if (f.amountMax !== null && f.amountMax !== '') count += 1;
        if (f.markStatus.length > 0) count += 1;
        if (f.coaIds.length > 0) count += 1;
        return count;
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
            return normalizeDbCr(t.db_cr) === 'DB' ? acc + amt : acc - amt;
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
            return normalizeDbCr(t.db_cr) === 'DB' ? acc + amt : acc - amt;
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
    /**
     * Muat seluruh data History dalam tiga fase dengan persentase nyata:
     *  1. meta    (0–8%)  : company, mark, COA, dan hitung total transaksi.
     *  2. fetch   (8–80%) : transaksi diambil per chunk — progress = loaded/total.
     *  3. process (80–100%): resolusi mark/split/COA per slice — progress = processed/total.
     */
    async loadData() {
      // Load yang sudah berjalan jangan digandakan; antrekan satu refresh ekstra.
      if (this.loadProgress.active) {
        this._reloadQueued = true;
        return;
      }
      this.isLoading = true;
      this.loadProgress = { active: true, phase: 'meta', percent: 2, loaded: 0, total: null, message: 'Menyiapkan data referensi…' };
      try {
        // Load persistence filters first if not already loaded
        if (!this.allTransactions.length) {
            await this.loadFilters();
        }

        const [compRes, markRes, coaRes, countRes] = await Promise.all([
            companyApi.getCompanies(),
            marksApi.getMarks(),
            coaApi.getCoa(),
            historyApi.getTransactionCount().catch(() => null)
        ]);

        const marks = markRes.data.marks || [];
        const coas = coaRes.data.coa || [];
        const total = countRes?.data?.count != null ? Number(countRes.data.count) : null;
        this.loadProgress.percent = 8;
        this.loadProgress.total = total;

        // Fase fetch: ambil transaksi per chunk agar progress benar-benar bergerak.
        this.loadProgress.phase = 'fetch';
        this.loadProgress.message = 'Mengambil transaksi…';

        let transactions = [];
        if (total != null && total > 0) {
            for (let offset = 0; offset < total; offset += TXN_CHUNK_SIZE) {
                const res = await historyApi.getTransactions({ limit: TXN_CHUNK_SIZE, offset });
                const chunk = res.data.transactions || [];
                transactions = transactions.concat(chunk);
                this.loadProgress.loaded = transactions.length;
                this.loadProgress.percent = 8 + 72 * Math.min(transactions.length / total, 1);
                if (chunk.length < TXN_CHUNK_SIZE) break;
            }
        } else {
            // Fallback: endpoint count tidak tersedia (backend lama) — ambil sekali penuh.
            const res = await historyApi.getTransactions();
            transactions = res.data.transactions || [];
            this.loadProgress.total = transactions.length;
            this.loadProgress.loaded = transactions.length;
        }

        // Fase proses: resolusi mark/split/COA, dipecah per slice agar UI tetap hidup.
        this.loadProgress.phase = 'process';
        this.loadProgress.message = 'Memproses marking & COA…';
        await this._decorateTransactions(transactions, marks, coas, (done, totalRows) => {
            this.loadProgress.loaded = done;
            this.loadProgress.percent = 80 + 20 * (totalRows > 0 ? done / totalRows : 1);
        });

        this.allTransactions = transactions;
        this.companies = compRes.data.companies || [];
        this.marks = marks;
        this.coaList = coas;
        this.hasLoadedOnce = true;
        // Muat konfigurasi AI di latar belakang (kontrol AI muncul bila aktif).
        this.ensureAiSettings();
      } catch (err) {
        this.error = "Failed to load data";
        console.error(err);
      } finally {
        this.isLoading = false;
        this.loadProgress.percent = 100;
        this.loadProgress.loaded = this.allTransactions.length;
        // Biarkan bar mencapai 100% sekejap sebelum menghilang.
        setTimeout(() => {
            const shouldReload = this._reloadQueued && !this.error;
            this._reloadQueued = false;
            this.loadProgress = { active: false, phase: 'idle', percent: 0, loaded: 0, total: null, message: '' };
            if (shouldReload) this.loadData();
        }, 350);
      }
    },

    /**
     * Resolusi sisi klien untuk setiap transaksi: status split, mark hilang,
     * mapping COA dari mark sendiri/child/manual, dan normalisasi db_cr.
     * Dijalankan per slice dengan jeda ke UI supaya progress bar tetap bernafas.
     */
    async _decorateTransactions(transactions, marks, coas, onProgress) {
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
        const coaById = new Map(
            coas
                .filter(coa => normalizeId(coa.id))
                .map(coa => [normalizeId(coa.id), coa])
        );
        const mapCoaMapping = (mapping = {}) => {
            const code = normalizeId(mapping.code);
            const name = mapping.name || '';
            const type = normalizeId(mapping.type || mapping.mapping_type);
            const coaId = normalizeId(mapping.coa_id || mapping.id) || coaIdByCode.get(code) || '';
            return { id: coaId || '', coa_id: coaId || '', code, name, type };
        };
        const collectDirectCoa = (coaId, bucket, idSet, uniqSet) => {
            const normalizedCoaId = normalizeId(coaId);
            if (!normalizedCoaId) return false;

            const directCoa = coaById.get(normalizedCoaId);
            const normalized = {
                id: normalizedCoaId,
                coa_id: normalizedCoaId,
                code: normalizeId(directCoa?.code),
                name: directCoa?.name || '',
                type: ''
            };
            const uniqKey = `${normalized.coa_id}|${normalized.code}|${normalized.name}|${normalized.type}`;
            if (!uniqSet.has(uniqKey)) {
                uniqSet.add(uniqKey);
                bucket.push(normalized);
            }
            idSet.add(normalizedCoaId);
            return true;
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

        // Pass 1: kumpulkan seluruh parent split (butuh dataset penuh).
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

        // Pass 2: enrich per slice.
        const totalRows = transactions.length;
        for (let start = 0; start < totalRows; start += PROCESS_SLICE_SIZE) {
          const slice = transactions.slice(start, start + PROCESS_SLICE_SIZE);
          for (const txn of slice) {
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

            // Reference-only manual journal links should still surface the journal mark/COA
            // so the source transaction does not appear unclassified in history.
            if (txn.manual_mark_id) {
              txn.is_linked_to_manual = true;
              const hasLinkedManualMark = collectCoasFromMarkId(txn.manual_mark_id, resolvedCoas, resolvedCoaIds, uniqCoas);
              if (hasLinkedManualMark) {
                  relatedMarkIds.add(txn.manual_mark_id);
              }
            }

            collectDirectCoa(txn.coa_id, resolvedCoas, resolvedCoaIds, uniqCoas);
            collectDirectCoa(txn.coa_id_coretax, resolvedCoas, resolvedCoaIds, uniqCoas);

            txn.coas = resolvedCoas;
            txn.coa_ids = Array.from(resolvedCoaIds).filter(Boolean);
            txn.related_mark_ids = Array.from(relatedMarkIds);
            txn.is_multi_marked = txn.is_split && splitMarkedCount > 0;

            const normalizedDbCr = normalizeDbCr(txn.db_cr);
            if (normalizedDbCr) {
              txn.db_cr = normalizedDbCr;
            }
          }
          onProgress?.(Math.min(start + PROCESS_SLICE_SIZE, totalRows), totalRows);
          await yieldToUi();
        }

        const splitTxns = transactions.filter(t => t.is_split);
        console.log('HistoryStore: Marked', splitTxns.length, 'transactions as having splits');
        return transactions;
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

    async fetchUploadChecklist(year) {
      this.isLoading = true;
      try {
        const res = await historyApi.getUploadChecklist(year || this.checklistYear);
        this.uploadChecklist = res.data;
        this.checklistYear = res.data.year || year || this.checklistYear;
      } catch (err) {
        this.error = 'Failed to load upload checklist';
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

    /** Set tahun periode; tahun dan rentang tanggal saling menggantikan, bukan di-AND diam-diam. */
    setYearFilter(year) {
        this.filters.year = year || '';
        if (this.filters.year) {
            this.filters.dateStart = '';
            this.filters.dateEnd = '';
        }
        this.currentPage = 1;
        this.saveFilters();
    },

    /** Set tanggal periode (dateStart/dateEnd); mengganti filter tahun bila diisi. */
    setDateFilter(key, value) {
        if (key !== 'dateStart' && key !== 'dateEnd') return;
        this.filters[key] = value || '';
        if ((this.filters.dateStart || this.filters.dateEnd) && this.filters.year) {
            this.filters.year = '';
        }
        this.currentPage = 1;
        this.saveFilters();
    },

    /** Hapus satu grup filter berdasarkan kunci (dipakai chip filter aktif). */
    clearFilterKeys(keys) {
        for (const key of keys) {
            if (key === 'year' || key === 'dateStart' || key === 'dateEnd') {
                this.filters[key] = '';
            } else if (key === 'amountMin' || key === 'amountMax') {
                this.filters[key] = null;
            } else if (Array.isArray(this.filters[key])) {
                this.filters[key] = [];
            } else {
                this.filters[key] = '';
            }
        }
        this.currentPage = 1;
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
        // Debounced: filter tersimpan 600ms setelah perubahan terakhir,
        // bukan satu panggilan API per ketikan.
        if (filterSaveTimer) clearTimeout(filterSaveTimer);
        return new Promise((resolve) => {
            filterSaveTimer = setTimeout(async () => {
                filterSaveTimer = null;
                try {
                    await filterApi.saveFilters('history', this.filters);
                } catch (e) {
                    console.error("Failed to save history filters:", e);
                }
                resolve();
            }, 600);
        });
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
    
    /**
     * Terapkan mark ke satu objek transaksi secara lokal (tanpa refetch):
     * dipakai assign-mark manual maupun penerimaan saran AI.
     */
    applyMarkLocally(txn, markId) {
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
            txn.coa_ids = [
                normalizeId(txn.coa_id),
                normalizeId(txn.coa_id_coretax)
            ].filter(Boolean);
            txn.related_mark_ids = [];
        }
    },

    async assignMark(id, markId) {
        try {
            await historyApi.assignMark(id, markId);
            const txn = this.allTransactions.find(t => t.id === id);
            if (txn) {
                this.applyMarkLocally(txn, markId);
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

    // --------------------------------------------------------------- AI mark assist

    async ensureAiSettings() {
        if (this.aiSettings) return this.aiSettings;
        try {
            const { data } = await aiApi.getSettings();
            this.aiSettings = data.settings || { enabled: false };
        } catch (e) {
            console.error('Failed to load AI settings:', e);
            this.aiSettings = { enabled: false };
        }
        return this.aiSettings;
    },

    /** Buang cache settings AI — dipanggil setelah pengaturan disimpan/dihapus. */
    invalidateAiSettings() {
        this.aiSettings = null;
    },

    applySuggestionLocally(txnId, result) {
        const txn = this.allTransactions.find(t => t.id === txnId);
        if (!txn) return;
        txn.ai_suggested_mark_id = result.ai_suggested_mark_id || result.mark_id || null;
        txn.ai_confidence = result.ai_confidence ?? null;
        txn.ai_reason = result.ai_reason || null;
        txn.ai_source = result.ai_source || 'llm';
        txn.ai_status = result.auto_applied ? 'auto_applied' : 'pending';
        if (result.auto_applied && txn.ai_suggested_mark_id) {
            // Auto-mark: langsung masuk ke marked (masih bertanda AI, bisa di-undo).
            this.applyMarkLocally(txn, txn.ai_suggested_mark_id);
        }
    },

    /** Minta satu saran AI untuk satu transaksi. */
    async suggestMark(txnId) {
        if (this.aiBusyTxnIds.includes(txnId)) return null;
        await this.ensureAiSettings();
        if (!this.aiSettings?.enabled) {
            throw new Error('Fitur AI belum diaktifkan di pengaturan.');
        }
        this.aiBusyTxnIds.push(txnId);
        try {
            const { data } = await aiApi.suggestMarks([txnId], this.aiSettings);
            const result = (data.results || [])[0];
            if (!result) throw new Error('Tidak ada hasil dari server AI.');
            if (result.status !== 'suggested') {
                throw new Error(result.error || result.reason || 'Saran AI gagal dibuat.');
            }
            this.applySuggestionLocally(txnId, result);
            return result;
        } catch (e) {
            console.error(e);
            throw e;
        } finally {
            this.aiBusyTxnIds = this.aiBusyTxnIds.filter(id => id !== txnId);
        }
    },

    /** Minta saran AI untuk semua transaksi terpilih, per chunk dengan progres. */
    async aiSuggestSelected(ids = null) {
        // Simpan argumen asli: ids eksplisit (alur banner converter) tidak boleh menghapus seleksi History.
        const idsArg = ids;
        ids = ids || [...this.selectedTxnIds];
        if (ids.length === 0) return { suggested: 0, skipped: 0, failed: 0 };
        await this.ensureAiSettings();
        if (!this.aiSettings?.enabled) {
            throw new Error('Fitur AI belum diaktifkan di pengaturan.');
        }

        this.aiBulkBusy = true;
        this.aiBulkProgress = { done: 0, total: ids.length };
        const summary = { suggested: 0, auto_applied: 0, skipped: 0, failed: 0 };
        const CHUNK_SIZE = 5; // tiap transaksi = 1 panggilan LLM lokal, kirim per chunk kecil
        try {
            for (let i = 0; i < ids.length; i += CHUNK_SIZE) {
                const chunk = ids.slice(i, i + CHUNK_SIZE);
                // Tandai baris chunk sebagai "sedang diproses" agar spinner per-baris tampil.
                this.aiBusyTxnIds.push(...chunk);
                try {
                    const { data } = await aiApi.suggestMarks(chunk, this.aiSettings);
                    for (const result of data.results || []) {
                        if (result.status === 'auto_applied') {
                            this.applySuggestionLocally(result.id, result);
                            summary.auto_applied += 1;
                        } else if (result.status === 'suggested') {
                            this.applySuggestionLocally(result.id, result);
                            summary.suggested += 1;
                        } else if (result.status === 'skipped') {
                            summary.skipped += 1;
                        } else {
                            summary.failed += 1;
                        }
                    }
                } finally {
                    const chunkSet = new Set(chunk);
                    this.aiBusyTxnIds = this.aiBusyTxnIds.filter(id => !chunkSet.has(id));
                }
                this.aiBulkProgress.done = Math.min(i + CHUNK_SIZE, ids.length);
            }
            if (idsArg == null) {
                this.selectedTxnIds = [];
            }
            return summary;
        } finally {
            this.aiBulkBusy = false;
        }
    },

    /** Terima/tolak banyak saran AI sekaligus (tanpa ids = semua yang relevan). */
    async bulkDecideSuggestion(decision, txnIds = null) {
        const { data } = await aiApi.bulkDecideSuggestion(txnIds, decision);
        await this.loadData();
        return data;
    },

    /** Terima/tolak saran AI untuk satu transaksi. */
    async decideSuggestion(txnId, decision) {
        const { data } = await aiApi.decideSuggestion(txnId, decision);
        const updated = data.transaction || {};
        const txn = this.allTransactions.find(t => t.id === txnId);
        if (txn) {
            if (decision === 'accept') {
                this.applyMarkLocally(txn, updated.mark_id || txn.ai_suggested_mark_id);
            }
            txn.ai_status = updated.ai_status || (decision === 'accept' ? 'accepted' : 'rejected');
            txn.ai_decided_at = updated.ai_decided_at || null;
        }
        return data;
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

    async importTransactions(file, bankCode, companyId, bankAccountNumber = null) {
        this.isLoading = true;
        try {
            const res = await historyApi.importTransactions(file, bankCode, companyId, bankAccountNumber);
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
