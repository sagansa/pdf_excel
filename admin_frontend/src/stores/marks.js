import { defineStore } from 'pinia';
import { marksApi } from '../api';

export const useMarksStore = defineStore('marks', {
  state: () => ({
    marks: [],
    isLoading: false,
    error: null
  }),

  getters: {
    sortedMarks(state) {
      return [...state.marks].sort((a, b) => {
        const nameA = (a.personal_use || '').trim().toLowerCase();
        const nameB = (b.personal_use || '').trim().toLowerCase();
        return nameA.localeCompare(nameB, 'id');
      });
    }
  },

  actions: {
    async fetchMarks() {
      this.isLoading = true;
      try {
        const response = await marksApi.getMarks();
        this.marks = response.data.marks || [];
      } catch (err) {
        this.error = err.message;
      } finally {
        this.isLoading = false;
      }
    },

    async createMark(data) {
      this.isLoading = true;
      try {
        await marksApi.createMark(data);
        await this.fetchMarks();
      } catch (err) {
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    async updateMark(id, data) {
      this.isLoading = true;
      try {
        await marksApi.updateMark(id, data);
        await this.fetchMarks();
      } catch (err) {
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    async updateMarkFlag(id, flagKey, value) {
      const idx = this.marks.findIndex((mark) => mark.id === id);
      if (idx === -1) {
        throw new Error('Mark not found');
      }

      const previousValue = Boolean(this.marks[idx][flagKey]);
      this.marks[idx][flagKey] = Boolean(value);

      try {
        await marksApi.updateMark(id, { [flagKey]: Boolean(value) });
      } catch (err) {
        this.marks[idx][flagKey] = previousValue;
        throw err;
      }
    },

    async deleteMark(id) {
      this.isLoading = true;
      try {
        await marksApi.deleteMark(id);
        // Immediately refresh to ensure we get the latest data from server
        await this.fetchMarks();
      } catch (err) {
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    async assignMark(txnId, markId) {
        this.isLoading = true;
        try {
            await marksApi.assignMark(txnId, markId);
            // We usually need to refresh transactions list after this
            // or return success so component can handle it
        } catch (err) {
            throw err;
        } finally {
            this.isLoading = false;
        }
    }
  }
});
