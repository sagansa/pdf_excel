<template>
  <BaseModal :isOpen="isOpen" @close="close">
    <template #title>Data Preview (Review Before Saving)</template>
    
    <div class="p-6 overflow-y-auto max-h-[60vh]">
      <div v-if="loading" class="text-center py-8">
         <span class="spinner-border text-indigo-600 w-8 h-8" role="status"></span>
         <p class="mt-2 text-gray-500">Processing...</p>
      </div>

      <div v-else>
          <p class="text-sm text-gray-500 mb-4">
              Review extracted data for <span class="font-bold text-gray-900">{{ companyName }}</span> before committing to the database.
          </p>

          
          <div class="border border-gray-200 rounded-xl overflow-hidden shadow-sm">
            <table class="min-w-full divide-y divide-gray-200">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-6 py-3 text-left text-xs font-bold text-gray-400 uppercase tracking-wider">Date</th>
                  <th class="px-6 py-3 text-left text-xs font-bold text-gray-400 uppercase tracking-wider">Description</th>
                  <th class="px-6 py-3 text-right text-xs font-bold text-gray-400 uppercase tracking-wider">Amount</th>
                  <th class="px-6 py-3 text-center text-xs font-bold text-gray-400 uppercase tracking-wider">Type</th>
                </tr>
              </thead>
              <tbody class="bg-white divide-y divide-gray-100">
                  <tr v-if="transactions.length === 0">
                      <td colspan="4" class="text-center py-8 text-gray-400 italic">No transactions found</td>
                  </tr>
                  <tr v-for="(t, index) in transactions" :key="index" class="hover:bg-gray-50">
                      <td class="px-6 py-2 text-sm text-gray-900 font-medium">
                          {{ t.txn_date || t.Date || '-' }}
                      </td>
                      <td class="px-6 py-2 text-sm text-gray-500">
                          {{ t.description || t.Description || '-' }}
                      </td>
                      <td class="px-6 py-2 text-sm text-right font-mono font-bold" 
                          :class="isCredit(t) ? 'text-green-600' : 'text-red-500'">
                          {{ formatAmount(t.amount || t.Amount) }}
                      </td>
                      <td class="px-6 py-2 text-center">
                           <span class="px-2 py-0.5 rounded-full text-xs font-bold"
                             :class="isCredit(t) ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'">
                             {{ getDbCr(t) }}
                           </span>
                      </td>
                  </tr>
              </tbody>
            </table>
          </div>

          <div class="mt-4 p-4 bg-indigo-50 border border-indigo-100 rounded-xl flex justify-between items-center">
            <span class="text-sm font-bold text-indigo-700">{{ transactions.length }} Transactions Found</span>
            <!-- Total calculation could go here -->
          </div>
      </div>
    </div>

    <template #footer>
      <button @click="close" class="btn-secondary">Discard & Cancel</button>
      <button 
        @click="confirm" 
        :disabled="loading || transactions.length === 0"
        class="btn-primary !bg-green-600 hover:!bg-green-700 border-none shadow-lg shadow-green-100 flex items-center"
      >
        <i class="bi bi-check-circle-fill me-2"></i> Confirm & Save
      </button>
    </template>
  </BaseModal>
</template>

<script setup>
import BaseModal from '../ui/BaseModal.vue';

const props = defineProps({
  isOpen: Boolean,
  loading: Boolean,
  transactions: {
    type: Array,
    default: () => []
  },
  companyName: {
    type: String,
    default: 'No Company'
  }
});


const emit = defineEmits(['close', 'confirm']);

const close = () => emit('close');
const confirm = () => emit('confirm');

// Helpers
const getDbCr = (t) => t.db_cr || t['DB/CR'] || (t.amount < 0 ? 'DB' : 'CR');
const isCredit = (t) => getDbCr(t) === 'CR';

const formatAmount = (val) => {
    if (!val) return '0.00';
    return new Intl.NumberFormat('id-ID').format(val);
};
</script>
