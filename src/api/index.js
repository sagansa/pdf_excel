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
    const payload = { source_file, bank_code };
    if (company_id !== undefined) payload.company_id = company_id;
    return api.post('/transactions/delete-by-source', payload);
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
  updateTransactionAmortizationGroup(txnId, payload = {}) {
    return api.put(`/transactions/${txnId}/amortization-group`, payload);
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
  },
  getServiceMarks(companyId, year) {
    const params = {};
    if (companyId) params.company_id = companyId;
    if (year) params.year = year;
    return api.get('/service-marks', { params });
  },
  updateServiceMark(markId, isService) {
    return api.put(`/service-marks/${markId}`, { is_service: isService });
  },
  getServiceTransactions(companyId, year, search = '') {
    const params = {};
    if (companyId) params.company_id = companyId;
    if (year) params.year = year;
    if (search) params.search = search;
    return api.get('/service-transactions', { params });
  },
  updateServiceTransactionTax(txnId, payload = {}) {
    const body = {
      has_npwp: Boolean(payload.has_npwp),
      npwp: payload.npwp || null
    };
    if (payload.calculation_method !== undefined) body.calculation_method = payload.calculation_method;
    if (payload.tax_payment_timing !== undefined) body.tax_payment_timing = payload.tax_payment_timing;
    if (payload.tax_payment_date !== undefined) body.tax_payment_date = payload.tax_payment_date;
    return api.put(`/service-transactions/${txnId}/npwp`, body);
  },
  updateServiceTransactionNpwp(txnId, hasNpwp, npwp) {
    return api.put(`/service-transactions/${txnId}/npwp`, {
      has_npwp: hasNpwp,
      npwp
    });
  },
  getPayrollUsers(search = '', employeesOnly = false) {
    const params = {};
    if (search) params.search = search;
    if (employeesOnly) params.employees_only = 1;
    return api.get('/payroll/users', { params });
  },
  async setPayrollUserEmployee(userId, isEmployee) {
    const encodedUserId = encodeURIComponent(userId);
    const payload = { is_employee: Boolean(isEmployee) };
    try {
      return await api.put(`/payroll/users/${encodedUserId}/employee`, payload);
    } catch (error) {
      const status = error?.response?.status;
      if (status === 404 || status === 405) {
        try {
          return await api.put(`/payroll/users/${encodedUserId}/employee/`, payload);
        } catch (retryError) {
          throw retryError;
        }
      }
      throw error;
    }
  },
  getPayrollTransactions(companyId, year, month, search = '', userId = '') {
    const params = {};
    if (companyId) params.company_id = companyId;
    if (year) params.year = year;
    if (month) params.month = month;
    if (search) params.search = search;
    if (userId) params.user_id = userId;
    return api.get('/payroll/transactions', { params });
  },
  assignPayrollUser(txnId, sagansaUserId = null) {
    return api.put(`/payroll/transactions/${txnId}/assign-user`, {
      sagansa_user_id: sagansaUserId
    });
  },
  updatePayrollPeriodMonth(txnId, payrollPeriodMonth = null) {
    return api.put(`/payroll/transactions/${txnId}/period-month`, {
      payroll_period_month: payrollPeriodMonth
    });
  },
  bulkAssignPayrollUser(txnIds, sagansaUserId = null) {
    return api.put('/payroll/transactions/bulk-assign-user', {
      transaction_ids: txnIds,
      sagansa_user_id: sagansaUserId
    });
  },
  getPayrollMonthlySummary(companyId, year, month) {
    const params = {};
    if (companyId) params.company_id = companyId;
    if (year) params.year = year;
    if (month) params.month = month;
    return api.get('/payroll/monthly-summary', { params });
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
  getCashFlow(startDate, endDate, companyId) {
    const params = { start_date: startDate, end_date: endDate };
    if (companyId) params.company_id = companyId;
    return api.get('/reports/cash-flow', { params });
  },
  getPayrollSalarySummary(startDate, endDate, companyId) {
    const params = { start_date: startDate, end_date: endDate };
    if (companyId) params.company_id = companyId;
    return api.get('/reports/payroll-salary-summary', { params });
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
  generateAmortizationJournals(data) {
    return api.post('/amortization-items/generate-journal', data);
  },
  
  // Asset Marks (for mark-based amortization)
  getAmortizationEligibleMarks(companyId) {
    const params = { company_id: companyId };
    return api.get('/marks/amortization-eligible', { params });
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
