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
  deleteTransaction(id) {
    return api.delete(`/transactions/${id}`);
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
