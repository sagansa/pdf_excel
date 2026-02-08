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
  getInventoryBalances(year, companyId) {
    const params = { year, company_id: companyId };
    return api.get('/inventory-balances', { params });
  },
  saveInventoryBalances(data) {
    return api.post('/inventory-balances', data);
  }
};
