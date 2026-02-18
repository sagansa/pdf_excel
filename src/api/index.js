import axios from 'axios';

// Create generic axios instance
const api = axios.create({
  baseURL: '/api', // Vite proxy will handle this
  headers: {
    'Content-Type': 'application/json',
  },
});

export default api;

// specialized services (can be moved to separate files later)
export const converterApi = {
  uploadFile(formData) {
    return api.post('/convert', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  checkPassword(formData) {
      return api.post('/check-password', formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        }
      });
  }
};

export const historyApi = {
  getTransactions() {
    return api.get('/transactions');
  },
  getUploadSummary() {
    return api.get('/transactions/upload-summary');
  },
  deleteTransaction(id) {
    return api.delete(`/transactions/${id}`);
  },
  deleteBySourceFile(source_file, bank_code, company_id) {
    return api.post('/transactions/delete-by-source', { source_file, bank_code, company_id });
  },
  bulkDelete(ids) {
    return api.post('/transactions/bulk-delete', { transaction_ids: ids });
  },
  assignMark(txnId, markId) {
    return api.post(`/transactions/${txnId}/assign-mark`, { mark_id: markId });
  },
  bulkAssignMark(ids, markId) {
    return api.post('/transactions/bulk-mark', { transaction_ids: ids, mark_id: markId });
  },
  assignCompany(txnId, companyId) {
    return api.post(`/transactions/${txnId}/assign-company`, { company_id: companyId });
  },
  bulkAssignCompany(ids, companyId) {
    return api.post('/transactions/bulk-assign-company', { transaction_ids: ids, company_id: companyId });
  },
  updateNotes(txnId, notes) {
    return api.put(`/transactions/${txnId}/notes`, { notes });
  },
  getSplits(txnId) {
    return api.get(`/transactions/${txnId}/splits`);
  },
  saveSplits(txnId, splits) {
    return api.post(`/transactions/${txnId}/splits`, { splits });
  },
  importTransactions(file, bankCode, companyId) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('bank_code', bankCode || 'MANUAL');
    if (companyId) formData.append('company_id', companyId);
    return api.post('/transactions/import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  exportTransactions(format, filters = {}) {
    return api.post('/transactions/export', { format, ...filters }, {
      responseType: 'blob'
    });
  }
};

export const companyApi = {
  getCompanies() {
    return api.get('/companies');
  },
  createCompany(data) {
    return api.post('/companies', data);
  },
  updateCompany(id, data) {
    return api.put(`/companies/${id}`, data);
  },
  deleteCompany(id) {
    return api.delete(`/companies/${id}`);
  }
};

export const marksApi = {
  getMarks() {
      return api.get('/marks');
  },
  createMark(data) {
      return api.post('/marks', data);
  },
  updateMark(id, data) {
      return api.put(`/marks/${id}`, data);
  },
  deleteMark(id) {
      return api.delete(`/marks/${id}`);
  },
  assignMark(txnId, markId) {
      return api.post(`/transactions/${txnId}/assign-mark`, { mark_id: markId });
  }
};

export const coaApi = {
  getCoa() {
    return api.get('/coa');
  }
};

export const filterApi = {
  getFilters(viewName) {
    return api.get(`/filters/${viewName}`);
  },
  saveFilters(viewName, filters) {
    return api.post('/filters', { view_name: viewName, filters });
  }
};

export const reportsApi = {
  getIncomeStatement(startDate, endDate, companyId) {
    const params = { start_date: startDate, end_date: endDate };
    if (companyId) params.company_id = companyId;
    return api.get('/reports/income-statement', { params });
  },
  getMonthlyRevenue(year, companyId) {
    const params = { year };
    if (companyId) params.company_id = companyId;
    return api.get('/reports/monthly-revenue', { params });
  },
  getBalanceSheet(asOfDate, companyId) {
    const params = { as_of_date: asOfDate };
    if (companyId) params.company_id = companyId;
    return api.get('/reports/balance-sheet', { params });
  },
  getInventoryBalances(year, companyId) {
    const params = { year, company_id: companyId };
    return api.get('/inventory-balances', { params });
  },
  saveInventoryBalances(data) {
    return api.post('/inventory-balances', data);
  },
  // Amortization Items
  getAmortizationItems(year, companyId) {
    const params = { year, company_id: companyId };
    return api.get('/amortization-items', { params });
  },
  createAmortizationItem(data) {
    return api.post('/amortization-items', data);
  },
  updateAmortizationItem(itemId, data) {
    return api.put(`/amortization-items/${itemId}`, data);
  },
  deleteAmortizationItem(itemId) {
    return api.delete(`/amortization-items/${itemId}`);
  },
  
  // Amortization Settings
  getAmortizationSettings(companyId) {
    const params = companyId ? { company_id: companyId } : {};
    return api.get('/amortization-settings', { params });
  },
  saveAmortizationSettings(data) {
    return api.post('/amortization-settings', data);
  },
  getAmortizationCoaCodes(companyId) {
    const params = companyId ? { company_id: companyId } : {};
    return api.get('/amortization-coa-codes', { params });
  },
  
  getCoaDetail(params) {
    return api.get('/reports/coa-detail', { params });
  },

  // Prepaid Expenses
  getPrepaidExpenses(companyId, asOfDate) {
    const params = { company_id: companyId, as_of_date: asOfDate };
    return api.get('/reports/prepaid-expenses', { params });
  },
  addPrepaidExpense(data) {
    return api.post('/reports/prepaid-expenses', data);
  },
  updatePrepaidExpense(itemId, data) {
    return api.put(`/reports/prepaid-expenses/${itemId}`, data);
  },
  deletePrepaidExpense(itemId) {
    return api.delete(`/reports/prepaid-expenses/${itemId}`);
  },
  getPrepaidLinkableTransactions(company_id, current_transaction_id = null) {
    const params = { company_id };
    if (current_transaction_id) params.current_transaction_id = current_transaction_id;
    return api.get('/reports/prepaid-linkable-transactions', { params });
  },
  getPrepaidJournalEntries(itemId) {
    return api.get(`/reports/prepaid-journal-entries/${itemId}`);
  },
  postPrepaidJournal(itemId) {
    return api.post(`/reports/prepaid-expenses/${itemId}/post-journal`);
  }
};

// Rental Location Management API
export const rentalApi = {
  // Locations
  getLocations(companyId) {
    const params = companyId ? { company_id: companyId } : {};
    return api.get('/rental-locations', { params });
  },
  createLocation(data) {
    return api.post('/rental-locations', data);
  },
  updateLocation(locationId, data) {
    return api.put(`/rental-locations/${locationId}`, data);
  },
  deleteLocation(locationId) {
    return api.delete(`/rental-locations/${locationId}`);
  },

  // Stores
  getStores(companyId) {
    const params = companyId ? { company_id: companyId } : {};
    return api.get('/stores', { params });
  },
  createStore(data) {
    return api.post('/stores', data);
  },
  updateStore(storeId, data) {
    return api.put(`/stores/${storeId}`, data);
  },
  deleteStore(storeId) {
    return api.delete(`/stores/${storeId}`);
  },

  // Contracts
  getContracts(companyId, status = null) {
    const params = { company_id: companyId };
    if (status) params.status = status;
    return api.get('/rental-contracts', { params });
  },
  getExpiringContracts(companyId, days = 30) {
    const params = { company_id: companyId, days };
    return api.get('/rental-contracts/expiring', { params });
  },
  createContract(data) {
    return api.post('/rental-contracts', data);
  },
  updateContract(contractId, data) {
    return api.put(`/rental-contracts/${contractId}`, data);
  },
  deleteContract(contractId) {
    return api.delete(`/rental-contracts/${contractId}`);
  },

  // Contract-Transaction Linking
  getContractTransactions(contractId) {
    return api.get(`/rental-contracts/${contractId}/transactions`);
  },
  linkTransaction(contractId, transactionId) {
    return api.post(`/rental-contracts/${contractId}/link-transaction`, { transaction_id: transactionId });
  },
  unlinkTransaction(contractId, transactionId) {
    return api.delete(`/rental-contracts/${contractId}/unlink-transaction/${transactionId}`);
  },
  
  // Linkable Transactions
  getLinkableTransactions(companyId, currentContractId = null) {
    const params = { company_id: companyId };
    if (currentContractId) params.current_contract_id = currentContractId;
    return api.get('/rental-contracts/linkable-transactions', { params });
  },
  
  // Journal Generation
  generateJournals(contractId, companyId) {
    return api.post(`/rental-contracts/${contractId}/generate-journals`, { company_id: companyId });
  }
};
