<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50/30">
    <!-- Header -->
    <div class="bg-white border-b border-gray-200 sticky top-0 z-10 shadow-sm">
      <div class="max-w-7xl mx-auto px-6 py-4">
        <div class="flex items-center justify-between">
          <div>
            <h1 class="text-2xl font-bold text-gray-900">General Ledger</h1>
            <p class="text-sm text-gray-500 mt-1">Laporan Buku Besar</p>
          </div>
          <div class="flex items-center gap-2">
            <button
              v-if="ledgerData.coa_groups && ledgerData.coa_groups.length > 0"
              @click="showExportMenu = !showExportMenu"
              class="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors flex items-center gap-2"
            >
              <i class="bi bi-download"></i>
              <span>Export</span>
              <i class="bi bi-chevron-down text-xs"></i>
            </button>
            
            <!-- Export Dropdown -->
            <div 
              v-if="showExportMenu" 
              class="absolute right-0 top-full mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-100 py-1 z-50"
            >
              <button
                @click="handleExport('excel')"
                class="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
              >
                <i class="bi bi-file-earmark-spreadsheet text-green-600"></i>
                Excel (.xlsx)
              </button>
              <button
                @click="handleExport('pdf')"
                class="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
              >
                <i class="bi bi-file-earmark-pdf text-red-600"></i>
                PDF
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="max-w-7xl mx-auto px-6 py-6">
      <!-- Filters -->
      <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
        <form @submit.prevent="loadGeneralLedger">
          <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">Company</label>
              <select 
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors" 
                v-model="filters.companyId" 
                required
              >
                <option value="">-- Pilih Company --</option>
                <option v-for="company in companies" :key="company.id" :value="company.id">
                  {{ company.name || company.id }}
                </option>
              </select>
            </div>
            
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">Tanggal Mulai</label>
              <input 
                type="date" 
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors" 
                v-model="filters.startDate" 
                required
              >
            </div>
            
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">Tanggal Akhir</label>
              <input 
                type="date" 
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors" 
                v-model="filters.endDate" 
                required
              >
            </div>
            
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">COA Code (Opsional)</label>
              <input 
                type="text" 
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors" 
                v-model="filters.coaCode" 
                placeholder="Contoh: 1101"
              >
            </div>
          </div>
          
          <div class="mt-4">
            <button 
              type="submit" 
              class="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed" 
              :disabled="loading || !filters.companyId"
            >
              <i class="bi bi-search" v-if="!loading"></i>
              <div v-if="loading" class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              {{ loading ? 'Memuat...' : 'Tampilkan Laporan' }}
            </button>
          </div>
        </form>
      </div>

      <!-- Summary Cards -->
      <div v-if="!loading && ledgerData.coa_groups && ledgerData.coa_groups.length > 0" class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div class="flex items-center">
            <div class="flex-1">
              <p class="text-sm font-medium text-gray-600">Total Transaksi</p>
              <p class="text-2xl font-bold text-gray-900">{{ ledgerData.total_transactions }}</p>
            </div>
            <div class="flex-shrink-0">
              <i class="bi bi-receipt text-3xl text-indigo-600 opacity-20"></i>
            </div>
          </div>
        </div>
        
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div class="flex items-center">
            <div class="flex-1">
              <p class="text-sm font-medium text-gray-600">Total Debit</p>
              <p class="text-2xl font-bold text-green-600">Rp {{ formatNumber(ledgerData.grand_total_debit) }}</p>
            </div>
            <div class="flex-shrink-0">
              <i class="bi bi-arrow-up-circle text-3xl text-green-600 opacity-20"></i>
            </div>
          </div>
        </div>
        
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div class="flex items-center">
            <div class="flex-1">
              <p class="text-sm font-medium text-gray-600">Total Kredit</p>
              <p class="text-2xl font-bold text-red-600">Rp {{ formatNumber(ledgerData.grand_total_credit) }}</p>
            </div>
            <div class="flex-shrink-0">
              <i class="bi bi-arrow-down-circle text-3xl text-red-600 opacity-20"></i>
            </div>
          </div>
        </div>
      </div>

      <!-- Balance Alert -->
      <div v-if="!loading && ledgerData.coa_groups && ledgerData.coa_groups.length > 0" 
           :class="ledgerData.is_balanced ? 'bg-green-50 border-green-200 text-green-800' : 'bg-yellow-50 border-yellow-200 text-yellow-800'" 
           class="rounded-lg border p-4 mb-6">
        <div class="flex items-center">
          <i :class="ledgerData.is_balanced ? 'bi bi-check-circle-fill text-green-600' : 'bi bi-exclamation-triangle-fill text-yellow-600'" class="mr-3"></i>
          <div>
            <strong>{{ ledgerData.is_balanced ? 'Balance!' : 'Unbalanced!' }}</strong>
            <span v-if="!ledgerData.is_balanced" class="ml-2">
              Selisih: Rp {{ formatNumber(Math.abs(ledgerData.grand_total_debit - ledgerData.grand_total_credit)) }}
            </span>
            <span v-else> Total Debit dan Kredit seimbang.</span>
          </div>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="flex flex-col items-center justify-center py-12">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
        <p class="mt-4 text-gray-600">Memuat General Ledger...</p>
      </div>

      <!-- No Data -->
      <div v-if="!loading && (!ledgerData.coa_groups || ledgerData.coa_groups.length === 0)" 
           class="text-center py-12">
        <i class="bi bi-journal-x text-6xl text-gray-300"></i>
        <p class="text-gray-500 mt-4">Belum ada data. Silakan pilih filter dan klik Tampilkan Laporan.</p>
      </div>

      <!-- Ledger Table -->
      <div v-if="!loading && ledgerData.coa_groups && ledgerData.coa_groups.length > 0" class="space-y-6">
        <div v-for="coaGroup in ledgerData.coa_groups" :key="coaGroup.coa_code" class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <!-- COA Header -->
          <div class="bg-gray-50 border-b border-gray-200 px-6 py-4">
            <div class="flex items-center justify-between">
              <div class="flex-1">
                <h3 class="text-lg font-semibold text-gray-900 flex items-center gap-2">
                  <i class="bi bi-folder2-open text-indigo-600"></i>
                  {{ coaGroup.coa_code }} - {{ coaGroup.coa_name }}
                </h3>
                <p class="text-sm text-gray-600 mt-1">{{ coaGroup.coa_category }}</p>
              </div>
              <div class="flex items-center gap-6">
                <div class="text-right">
                  <p class="text-xs text-gray-500 uppercase tracking-wide">Debit</p>
                  <p class="text-lg font-semibold text-green-600">Rp {{ formatNumber(coaGroup.total_debit) }}</p>
                </div>
                <div class="text-right">
                  <p class="text-xs text-gray-500 uppercase tracking-wide">Kredit</p>
                  <p class="text-lg font-semibold text-red-600">Rp {{ formatNumber(coaGroup.total_credit) }}</p>
                </div>
                <div class="text-right">
                  <p class="text-xs text-gray-500 uppercase tracking-wide">Saldo</p>
                  <p class="text-lg font-semibold" :class="coaGroup.ending_balance >= 0 ? 'text-indigo-600' : 'text-red-600'">
                    Rp {{ formatNumber(Math.abs(coaGroup.ending_balance)) }}
                  </p>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Transactions Table -->
          <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-200">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider" width="100">
                    Tanggal
                  </th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Deskripsi
                  </th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider" width="150">
                    Mark
                  </th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider" width="100">
                    COA
                  </th>
                  <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider" width="120">
                    Debit
                  </th>
                  <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider" width="120">
                    Kredit
                  </th>
                  <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider" width="130">
                    Saldo
                  </th>
                </tr>
              </thead>
              <tbody class="bg-white divide-y divide-gray-200">
                <template v-for="txn in coaGroup.transactions" :key="txn.transaction_id">
                  <!-- Show all entries for this transaction -->
                  <tr v-for="(entry, idx) in txn.entries" :key="txn.transaction_id + '_' + idx"
                      :class="{'bg-indigo-50': idx === 0, 'hover:bg-gray-50': true}">
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      <div v-if="idx === 0">{{ formatDate(txn.txn_date) }}</div>
                    </td>
                    <td class="px-6 py-4 text-sm text-gray-900">
                      <div v-if="idx === 0" class="font-medium">{{ txn.description }}</div>
                      <div v-else class="text-gray-500 text-xs flex items-center gap-1">
                        <i class="bi bi-arrow-return-right"></i>
                        {{ txn.entries[0].coa_code }} → {{ entry.coa_code }}
                      </div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      <span v-if="idx === 0" class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                        {{ txn.mark_name || '-' }}
                      </span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm">
                      <span :class="idx === 0 ? 'font-medium text-indigo-600' : 'text-gray-500'">
                        {{ entry.coa_code }}
                      </span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900">
                      <span v-if="entry.debit > 0" :class="idx === 0 ? 'font-semibold text-green-600' : 'text-green-600'">
                        {{ formatNumber(entry.debit) }}
                      </span>
                      <span v-else class="text-gray-400">-</span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900">
                      <span v-if="entry.credit > 0" :class="idx === 0 ? 'font-semibold text-red-600' : 'text-red-600'">
                        {{ formatNumber(entry.credit) }}
                      </span>
                      <span v-else class="text-gray-400">-</span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-right">
                      <span v-if="idx > 0" class="text-gray-400">...</span>
                      <strong v-else :class="entry.current_entry && entry.current_entry.running_balance >= 0 ? 'text-indigo-600' : 'text-red-600'">
                        {{ formatNumber(Math.abs(entry.current_entry ? entry.current_entry.running_balance : 0)) }}
                      </strong>
                    </td>
                  </tr>
                  <!-- Separator row between transactions -->
                  <tr v-if="txn !== coaGroup.transactions[coaGroup.transactions.length - 1]" class="bg-gray-100">
                    <td colspan="7" class="px-6 py-1"></td>
                  </tr>
                </template>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'GeneralLedger',
  data() {
    return {
      loading: false,
      companies: [],
      showExportMenu: false,
      filters: {
        companyId: '',
        startDate: new Date().toISOString().split('T')[0],
        endDate: new Date().toISOString().split('T')[0],
        coaCode: ''
      },
      ledgerData: {
        company_id: '',
        start_date: '',
        end_date: '',
        coa_groups: [],
        total_accounts: 0,
        total_transactions: 0,
        grand_total_debit: 0,
        grand_total_credit: 0,
        is_balanced: true
      }
    }
  },
  mounted() {
    this.loadCompanies()
  },
  methods: {
    async loadCompanies() {
      try {
        const response = await fetch('/api/companies')
        const data = await response.json()
        this.companies = data.companies || data || []
        
        if (this.companies.length === 1 && !this.filters.companyId) {
          this.filters.companyId = this.companies[0].id
        }
      } catch (error) {
        console.error('Error loading companies:', error)
      }
    },
    
    async loadGeneralLedger() {
      if (!this.filters.companyId) {
        alert('Pilih company terlebih dahulu')
        return
      }
      
      this.loading = true
      try {
        const params = new URLSearchParams({
          company_id: this.filters.companyId,
          start_date: this.filters.startDate,
          end_date: this.filters.endDate
        })
        
        if (this.filters.coaCode) {
          params.append('coa_code', this.filters.coaCode)
        }
        
        const response = await fetch(`/api/reports/general-ledger?${params}`)
        const data = await response.json()
        
        if (data.success) {
          this.ledgerData = data.data
        } else {
          alert('Gagal memuat General Ledger: ' + (data.error || 'Unknown error'))
        }
      } catch (error) {
        console.error('Error loading general ledger:', error)
        alert('Gagal memuat General Ledger')
      } finally {
        this.loading = false
      }
    },
    
    formatNumber(num) {
      return new Intl.NumberFormat('id-ID').format(num)
    },
    
    formatDate(dateStr) {
      if (!dateStr) return '-'
      const date = new Date(dateStr)
      return date.toLocaleDateString('id-ID', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      })
    },

    async handleExport(format) {
      this.showExportMenu = false;
      try {
        const params = new URLSearchParams({
          company_id: this.filters.companyId,
          start_date: this.filters.startDate,
          end_date: this.filters.endDate,
          format: format
        });
        
        if (this.filters.coaCode) {
          params.append('coa_code', this.filters.coaCode);
        }

        const response = await fetch(`/api/reports/general-ledger/export?${params}`);
        
        if (response.ok) {
          const blob = await response.blob();
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `general-ledger-${this.filters.companyId}-${this.filters.startDate}-to-${this.filters.endDate}.${format === 'excel' ? 'xlsx' : 'pdf'}`;
          document.body.appendChild(a);
          a.click();
          window.URL.revokeObjectURL(url);
          document.body.removeChild(a);
        } else {
          const errorData = await response.json();
          alert('Export failed: ' + (errorData.error || 'Unknown error'));
        }
      } catch (error) {
        console.error('Export error:', error);
        alert('Export failed. Please try again.');
      }
    }
  }
}
</script>

<style scoped>
/* Additional custom styles if needed */
</style>
